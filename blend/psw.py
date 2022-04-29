from os.path import basename, splitext, sep, normpath, exists
from os.path import join as join_path

import bpy.types
import io_import_pskx.utils as utils
from bpy.types import Property, Context, Collection, Mesh, Object, NodesModifier, GeometryNodeTree, NodeGroupOutput, GeometryNodeGroup, Image, Material, ShaderNodeTexCoord, ShaderNodeSeparateXYZ, NodeReroute, ShaderNodeTexImage
from mathutils import Vector
from io_import_pskx.io import read_actorx, World, DataType
from io_import_pskx.blend.psk import ActorXMesh


class ActorXWorld:
    path: str
    settings: dict[str, Property]
    resize_mod: float
    game_dir: str
    psw: World | None
    name: str

    def __init__(self, path: str, settings: dict[str, Property]):
        self.path = path
        self.name = splitext(basename(path))[0]
        self.settings = settings
        self.resize_mod = self.settings['resize_by']
        self.game_dir = self.settings['base_game_dir']

        with open(self.path, 'rb') as stream:
            self.psw = read_actorx(stream, settings)

    def execute(self, context: Context) -> set[str]:
        if self.psw is None or self.psw.TYPE != DataType.World:
            return {'CANCELLED'}

        if len(self.game_dir) == 0:
            return {'CANCELLED'}

        world_collection = bpy.data.collections.new(self.name)
        context.collection.children.link(world_collection)
        world_layer = context.view_layer.active_layer_collection.children[-1]

        actor_collection = bpy.data.collections.new(self.name + ' Actors')
        actor_collection.hide_render = True
        actor_collection.hide_select = True
        actor_collection.hide_viewport = True
        world_collection.children.link(actor_collection)
        actor_layer = world_layer.children[-1]

        old_active_layer = context.view_layer.active_layer_collection

        mesh_cache: dict[tuple[str, frozenset], Collection] = {}

        actor_cache: list[Collection] = [None] * self.psw.NumActors

        for actor_id, (name, psk_path, parent, pos, rot, scale, no_shadow, hidden) in enumerate(self.psw.Actors):
            mesh_key = (psk_path, frozenset(self.psw.OverrideMaterials[actor_id].items()))

            mesh_obj = None
            if mesh_key in mesh_cache:
                mesh_obj = mesh_cache[mesh_key]
            elif psk_path != 'None':
                result_path = psk_path
                if not result_path.endswith('.psk'):
                    result_path += '.psk'

                if sep != '/':
                    result_path = result_path.replace('/', sep)

                result_path = normpath(join_path(self.game_dir, result_path))

                if not exists(result_path):  # try getting pskx instead of psk
                    result_path += 'x'

                if exists(result_path):
                    import_settings = self.settings.copy()
                    import_settings['override_materials'] = self.psw.OverrideMaterials[actor_id]
                    psk = ActorXMesh(result_path, import_settings)

                    mesh_obj = bpy.data.collections.new(psk.name)
                    actor_collection.children.link(mesh_obj)
                    context.view_layer.active_layer_collection = actor_layer.children[-1]

                    psk.execute(context)
                    mesh_cache[mesh_key] = mesh_obj
                else:
                    print('Can\'t find asset %s' % (psk_path))
                    mesh_obj = None

            instance = bpy.data.objects.new(name, None)
            instance.location = pos
            instance.rotation_mode = 'QUATERNION'
            instance.rotation_quaternion = rot
            instance.scale = scale

            if mesh_obj is not None:
                instance.instance_type = 'COLLECTION'
                instance.instance_collection = mesh_obj

            if no_shadow:
                instance.visible_shadow = False

            if hidden:
                instance.hide_render = True
                instance.show_instancer_for_render = False

            if parent > -1:
                instance.parent = actor_cache[parent]

            actor_cache[actor_id] = instance

            world_collection.objects.link(instance)

        tiles: map[tuple[int, int], tuple[Object, Material, ShaderNodeTexCoord, set[str]]] = {}

        landscape_hosts: set[Object] = set()

        for (tex_path, actor_id, pos, scale, type_id, tile_x, tile_y, bias, offset, dim) in self.psw.Landscapes:
            result_path = tex_path
            if not result_path.endswith('.png'):
                result_path += '.png'
            if sep != '/':
                result_path = result_path.replace('/', sep)
            result_path = normpath(join_path(self.game_dir, result_path))

            if not exists(result_path):
                print('Can\'t find asset %s' % (tex_path))
                continue

            if type_id != 0:
                if (tile_x, tile_y) not in tiles:
                    continue

                (landscape_obj, material, tex_coord, tracking) = tiles[(tile_x, tile_y)]
                if tex_path in tracking:
                    continue
                tracking.add(tex_path)

                material_data = landscape_obj.material_slots[0].material
                node_tree = material_data.node_tree

                # create nodes
                image_node: ShaderNodeTexImage = node_tree.nodes.new(type='ShaderNodeTexImage')
                image_node.image = bpy.data.images.load(filepath=result_path, check_existing=True)
                image_node.image.colorspace_settings.name = 'Raw'
                image_node.interpolation = 'Cubic'
                image_node.extension = 'EXTEND'
                image_node.location = tex_coord.location + Vector((240, -((type_id - 1) * 280)))
                image_node.label = 'Weightmap%d' % (type_id - 1)

                separate_xyz: ShaderNodeSeparateXYZ = node_tree.nodes.new(type='ShaderNodeSeparateXYZ')
                separate_xyz.location = image_node.location + Vector((360, 0))

                reroute: NodeReroute = node_tree.nodes.new(type='NodeReroute')
                reroute.location = separate_xyz.location + Vector((140, -160))
                reroute.label = 'W'

                # create links
                node_tree.links.new(tex_coord.outputs['Generated'], image_node.inputs['Vector'])
                node_tree.links.new(image_node.outputs['Color'], separate_xyz.inputs['Vector'])
                node_tree.links.new(image_node.outputs['Alpha'], reroute.inputs[0])

                continue

            if offset > Vector((0.0, 0.0, 0.0)):
                # only handle 0, 0
                continue

            base_scale = Vector((scale, scale, scale))
            adj_scale = base_scale * dim
            pos_offset = (adj_scale - base_scale) / 2
            pos_offset.y *= -1
            adj_pos = pos + pos_offset

            adj_scale *= self.resize_mod
            adj_pos *= self.resize_mod

            actor = actor_cache[0 if actor_id == -1 else actor_id]

            landscape_data: Mesh = bpy.data.meshes.new(actor.name + '_Sector%d_%d' % (tile_x, tile_y))
            landscape_obj: Object = bpy.data.objects.new(name=landscape_data.name, object_data=landscape_data)
            landscape_obj.parent = actor
            landscape_obj.scale = adj_scale
            landscape_obj.location = adj_pos
            landscape_hosts.add(parent)

            landscape_nodes: GeometryNodeTree = bpy.data.node_groups.new(landscape_obj.name, 'GeometryNodeTree')
            output_node: NodeGroupOutput = landscape_nodes.nodes.new(type='NodeGroupOutput')
            output_node.location = (400, 0)
            group_node: GeometryNodeGroup = landscape_nodes.nodes.new(type='GeometryNodeGroup')
            group_node.node_tree = bpy.data.node_groups['PSW Height']
            img: Image = bpy.data.images.load(filepath=result_path, check_existing=True)
            img.colorspace_settings.name = 'Raw'
            group_node.inputs['Dimensions'].default_value = dim
            group_node.inputs['Size'].default_value = bias
            group_node.inputs['Heightmap'].default_value = img
            landscape_nodes.links.new(group_node.outputs[0], output_node.inputs[0])

            node_modifier: NodesModifier = landscape_obj.modifiers.new('Landscape Geometry', type='NODES')
            old_group = node_modifier.node_group
            node_modifier.node_group = landscape_nodes
            bpy.data.node_groups.remove(old_group)

            world_collection.objects.link(landscape_obj)

            material_data: Material = bpy.data.materials.get(landscape_data.name)

            if material_data is None:
                material_data = bpy.data.materials.new(landscape_data.name)
                material_data.use_nodes = True
                tex_coord = material_data.node_tree.nodes.new(type='ShaderNodeTexCoord')
                tex_coord.location = material_data.node_tree.nodes['Principled BSDF'].location + Vector((-1200, 0))

            landscape_data.materials.append(material_data)
            landscape_obj.material_slots[0].link = 'OBJECT'
            landscape_obj.material_slots[0].material = material_data

            tiles[(tile_x, tile_y)] = (landscape_obj, material_data, tex_coord, set())

        for landscape_host in landscape_hosts:
            landscape_host.asset_mark()
            landscape_host.asset_data.tags.new(name='actorx', skip_if_exists=True)
            landscape_host.asset_data.tags.new(name='landscape', skip_if_exists=True)
            landscape_host.asset_generate_preview()

        context.view_layer.active_layer_collection = old_active_layer

        return {'FINISHED'}
