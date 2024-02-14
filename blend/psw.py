from os.path import basename, splitext, sep, normpath, exists
from os.path import join as join_path

import numpy
import bpy.types
import io_import_pskx.utils as utils
from bpy.types import Property, Context, Collection, Mesh, Object, NodesModifier, GeometryNodeTree, NodeGroupOutput, GeometryNodeGroup, Image, Material, ShaderNodeTexCoord, ShaderNodeSeparateXYZ, NodeReroute, ShaderNodeTexImage
from mathutils import Quaternion, Vector, Color
from io_import_pskx.io import read_actorx, World, DataType
from io_import_pskx.blend.psk import ActorXMesh
from io_import_pskx.utils import log_error, log_warning, log_info

enable_ueformat = False
try:
    log_info('WORLD', "trying to load ue_format for uemodel support")
    from ue_format import UEFormatImport, UEModelOptions
    enable_ueformat = True
    log_info('WORLD', "successfully loaded ue_format")
except: 
    log_error('WORLD', "failed to load ue_format")
    pass

ignore_names = ['CUBE', 'SPHERE', 'CONE', 'CYLINDER', 'CAPSULE', 'BOX', 'ARROW', 'SPLINE', 'PLANE']


def is_ignored_name(path: str) -> bool:
    test = basename(path).split('.')[0].upper()
    if test.startswith('SM_'):
        test = test[3:]
    elif test.startswith('SHAPE_'):
        test = test[6:]
    elif test.startswith('1M_'):
        test = test[3:].split('_')[0]
    if 'VFX_' in test: return True
    return test in ignore_names


def is_lodactor_or_hlod(path: str) -> bool:
    test = basename(path).split('.')[0].upper()
    return 'LODACTOR_' in test or '_HLOD_' in test


def convert_temperature(temperature: float) -> Color:
    temperature = numpy.clip(temperature, 1000, 40000)
    temperature = temperature / 100.0

    if temperature <= 66:
        red = 255
    else:
        red = 329.698727446 * (temperature - 60)**-0.1332047592

    if temperature <= 66:
        green = 99.4708025861 * numpy.log(temperature) - 161.1195681661
    else:
        green = 288.1221695283 * (temperature - 60)**-0.0755148492

    if temperature >= 66:
        blue = 255
    elif temperature <= 19:
        blue = 0
    else:
        blue = 138.5177312231 * numpy.log(temperature - 10) - 305.0447927307

    rgb = numpy.clip((red, green, blue), 0, 255) / 255
    return Color((rgb[0], rgb[1], rgb[2]))


def undeduplicate_name(name: str) -> str:
    if len(name) < 4:
        return name
    if name[-4] == '.':
        return name[:-4]
    return name

class ActorXWorld:
    path: str
    settings: dict[str, Property]
    resize_mod: float
    adjust_intensity: float
    adjust_spot_intensity: float
    adjust_area_intensity: float
    adjust_sun_intensity: float
    skip_offcenter: bool
    no_static_instances: bool
    no_skeletons: bool
    ignore_shapes: bool
    game_dir: str
    psw: World | None
    name: str

    def __init__(self, path: str, settings: dict[str, Property]):
        self.path = path
        self.name = basename(path)
        if '.' in self.name: self.name = self.name[:self.name.index('.')]
        self.settings = settings
        self.resize_mod = self.settings['resize_by']
        self.adjust_intensity = self.settings['adjust_intensity']
        self.adjust_spot_intensity = self.settings['adjust_spot_intensity']
        self.adjust_area_intensity = self.settings['adjust_area_intensity']
        self.adjust_sun_intensity = self.settings['adjust_sun_intensity']
        self.skip_offcenter = self.settings['skip_offcenter']
        self.no_static_instances = self.settings['no_static_instances']
        self.no_skeletons = self.settings['no_skeletons']
        self.use_actor_name = self.settings['use_actor_name']
        self.game_dir = self.settings['base_game_dir']
        self.import_mesh = self.settings['import_mesh']
        self.import_landscape = self.settings['import_landscape']
        self.import_light = self.settings['import_light']
        self.ignore_shapes = self.settings['ignore_shapes']
        self.ignore_lodactors = self.settings['ignore_lodactors']

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
        instance_collection = bpy.data.collections.new(self.name + ' Actor Instances')
        landscape_collection = bpy.data.collections.new(self.name + ' Landscape')
        point_light_collection = bpy.data.collections.new(self.name + ' Point Lights')
        sun_light_collection = bpy.data.collections.new(self.name + ' Sun Lights')
        spot_light_collection = bpy.data.collections.new(self.name + ' Spot Lights')
        area_light_collection = bpy.data.collections.new(self.name + ' Area Lights')

        world_collection.children.link(actor_collection)
        actor_layer = world_layer.children[-1]
        
        world_collection.children.link(instance_collection)
        instance_layer = world_layer.children[-1]
        
        world_collection.children.link(landscape_collection)
        landscape_layer = world_layer.children[-1]

        world_collection.children.link(point_light_collection)
        world_collection.children.link(sun_light_collection)
        world_collection.children.link(spot_light_collection)
        world_collection.children.link(area_light_collection)

        old_active_layer = context.view_layer.active_layer_collection

        mesh_cache: dict[tuple[str, frozenset], Collection] = {}

        actor_cache: list[Collection] = [None] * self.psw.NumActors

        for actor_id, (name, game_path, parent, pos, rot, scale, no_shadow, hidden, _, is_static) in enumerate(self.psw.Actors):
            if self.ignore_shapes and is_ignored_name(name):
                continue
            if self.ignore_lodactors and is_lodactor_or_hlod(name):
                continue

            mesh_key = (game_path, frozenset(self.psw.OverrideMaterials[actor_id].items()))

            if self.no_skeletons and not is_static:
                continue
            
            if self.no_static_instances:
                is_static = False
            
            mesh_obj = None
            if mesh_key in mesh_cache and is_static:
                mesh_obj = mesh_cache[mesh_key]
            elif game_path != 'None' and self.import_mesh:
                if self.ignore_shapes and is_ignored_name(game_path):
                    continue
                if self.ignore_lodactors and is_lodactor_or_hlod(game_path):
                    continue
                result_path = game_path.strip('/').strip('\\')

                if sep != '/':
                    result_path = result_path.replace('/', sep)
                
                if enable_ueformat:
                    uemodel_path = normpath(join_path(self.game_dir, result_path + '.uemodel'))
                    if exists(uemodel_path):
                        import_settings = UEModelOptions(link=True, scale_factor=self.resize_mod, bone_length=5, reorient_bones=False)
                        if is_static:
                            mesh_obj = bpy.data.collections.new(name)
                            actor_collection.children.link(mesh_obj)
                            context.view_layer.active_layer_collection = actor_layer.children[-1]
                            uemodel_obj = UEFormatImport(import_settings).import_file(uemodel_path)
                            mesh_obj.name = undeduplicate_name(uemodel_obj.name)
                            mesh_cache[mesh_key] = mesh_obj
                        else:
                            context.view_layer.active_layer_collection = instance_layer
                            mesh_obj = UEFormatImport(import_settings).import_file(uemodel_path)
                else:
                    psk_path = normpath(join_path(self.game_dir, result_path + '.psk'))
                    if not exists(psk_path):  # try getting pskx instead of psk
                        psk_path += 'x'

                    if is_static and exists(psk_path):
                        log_info('WORLD', "importing model %s" % (psk_path))
                        import_settings = self.settings.copy()
                        import_settings['override_materials'] = self.psw.OverrideMaterials[actor_id]
                        psk = ActorXMesh(psk_path, import_settings)
                        mesh_obj = bpy.data.collections.new(psk.name)
                        actor_collection.children.link(mesh_obj)
                        context.view_layer.active_layer_collection = actor_layer.children[-1]
                        psk.execute(context)
                        mesh_cache[mesh_key] = mesh_obj
                    else:
                        log_error('WORLD', 'Can\'t find asset %s' % result_path)
                        mesh_obj = None
            
            instance_name = name

            if mesh_obj is not None:
                if not self.use_actor_name or instance_name.startswith('StaticMeshActor') or instance_name.startswith('SkeletalMeshActor'):
                    instance_name = undeduplicate_name(mesh_obj.name)
                else:
                    instance_name = '%s %s' % (name, undeduplicate_name(mesh_obj.name))

            if is_static or mesh_obj is None:
                instance = bpy.data.objects.new(instance_name, None)

                if mesh_obj is not None:
                    instance.instance_type = 'COLLECTION'
                    instance.instance_collection = mesh_obj
            else:
                instance = mesh_obj

            instance.location = pos
            instance.rotation_mode = 'QUATERNION'
            instance.rotation_quaternion = rot
            instance.scale = scale

            if no_shadow:
                instance.visible_shadow = False

            if hidden:
                instance.hide_render = True
                instance.show_instancer_for_render = False

            if parent > -1:
                instance.parent = actor_cache[parent]

            actor_cache[actor_id] = instance

            if is_static:
                instance_collection.objects.link(instance)
        
        actor_collection.hide_render = True
        actor_collection.hide_viewport = True

        if self.import_light:
            for (actor_id, color, light_type, whl, attenuation, radius, temp, bias, lumens, angle) in self.psw.Lights:
                light_type_bl = 'POINT'
                if light_type == 0:
                    if self.adjust_sun_intensity <= 0.0001:
                        continue
                    light_type_bl = 'SUN'
                elif light_type == 1:
                    if self.adjust_intensity <= 0.0001:
                        continue
                elif light_type == 2:
                    if self.adjust_spot_intensity <= 0.0001:
                        continue
                    light_type_bl = 'SPOT'
                elif light_type == 3:
                    if self.adjust_area_intensity <= 0.0001:
                        continue
                    light_type_bl = 'AREA'
                actor = actor_cache[actor_id]
                actor_data = self.psw.Actors[actor_id]
                bl_light_data = bpy.data.lights.new(name=actor.name + '_light', type=light_type_bl)
                bl_light_data.use_shadow = not actor_data[6]
                bl_light_data.color = color
                if actor_data[8]:
                    bl_light_data.color = convert_temperature(temp)
                    lumens = lumens * 100
                bl_light_data.shadow_soft_size = bias
                if light_type == 0:
                    bl_light_data.energy = lumens * self.adjust_sun_intensity
                elif light_type == 1:
                    bl_light_data.energy = lumens * self.adjust_intensity
                elif light_type == 2:
                    bl_light_data.energy = lumens * self.adjust_spot_intensity
                    bl_light_data.spot_size = angle
                elif light_type == 3:
                    bl_light_data.energy = lumens * self.adjust_area_intensity
                    bl_light_data.shape = 'RECTANGLE'
                    bl_light_data.size = whl.x
                    bl_light_data.size_y = whl.y
                bl_light_obj = bpy.data.objects.new(name=actor.name + '_light', object_data=bl_light_data)
                bl_light_obj.parent = actor
                bl_light_obj.rotation_mode = 'QUATERNION'
                bl_light_obj.rotation_quaternion = Quaternion((0.707107, 0, -0.707107, 0))
                if light_type == 0:
                    sun_light_collection.objects.link(bl_light_obj)
                elif light_type == 1:
                    point_light_collection.objects.link(bl_light_obj)
                elif light_type == 2:
                    spot_light_collection.objects.link(bl_light_obj)
                elif light_type == 3:
                    area_light_collection.objects.link(bl_light_obj)

        if self.import_landscape:
            tiles: map[tuple[int, int], tuple[Object, Material, ShaderNodeTexCoord, set[str]]] = {}
            for (tex_path, actor_id, pos, scale, type_id, tile_x, tile_y, bias, offset, dim) in self.psw.Landscapes:
                result_path = tex_path.strip('/').strip('\\')
                if not result_path.endswith('.png'):
                    result_path += '.png'
                if sep != '/':
                    result_path = result_path.replace('/', sep)
                result_path = normpath(join_path(self.game_dir, result_path))

                if not exists(result_path):
                    log_error('WORLD', 'Can\'t find asset %s' % (tex_path))
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
                    image_node.image.colorspace_settings.name = 'Non-Color'
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

                    # todo: X, Y, Z, or W needs to be connected to the Invert Alpha node

                    continue

                actor = actor_cache[0 if actor_id == -1 else actor_id]
                landscape_name = actor.name + '_Sector%d_%d' % (tile_x, tile_y)

                if offset > Vector((0.0, 0.0, 0.0)):
                    log_warning('WORLD', 'Off-center landscape: %s (%f, %f, %f)' % (landscape_name, offset.x, offset.y, offset.z))

                    if self.skip_offcenter:
                        continue

                base_scale = Vector((scale, scale, 255))
                adj_scale = base_scale * dim
                pos_offset = (adj_scale - base_scale) / 2
                pos_offset.y *= -1
                adj_pos = (pos + offset) + pos_offset
                global_offset = ((scale + 1) / 2) - 1
                adj_pos.x += global_offset
                adj_pos.y -= global_offset
                adj_pos.z = -bias / 1000

                adj_scale *= self.resize_mod
                adj_pos *= self.resize_mod

                landscape_data: Mesh = bpy.data.meshes.new(landscape_name)
                landscape_obj: Object = bpy.data.objects.new(name=landscape_data.name, object_data=landscape_data)
                landscape_obj.parent = actor
                landscape_obj.scale = adj_scale
                landscape_obj.location = adj_pos

                landscape_nodes: GeometryNodeTree = bpy.data.node_groups.new(landscape_obj.name, 'GeometryNodeTree')
                if hasattr(landscape_nodes, 'outputs'):
                    landscape_nodes.outputs.new('NodeSocketGeometry')
                elif hasattr(landscape_nodes, 'interface'):
                    landscape_nodes.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
                output_node: NodeGroupOutput = landscape_nodes.nodes.new(type='NodeGroupOutput')
                output_node.location = (400, 0)
                output_node.is_active_output = True
                output_node.select = False
                group_node: GeometryNodeGroup = landscape_nodes.nodes.new(type='GeometryNodeGroup')
                group_node.node_tree = bpy.data.node_groups['PSW Height']
                group_node.select = False
                img: Image = bpy.data.images.load(filepath=result_path, check_existing=True)
                img.colorspace_settings.name = 'Non-Color'
                group_node.inputs['Dimensions'].default_value = dim
                group_node.inputs['Heightmap'].default_value = img
                landscape_nodes.links.new(group_node.outputs[0], output_node.inputs[0])

                node_modifier: NodesModifier = landscape_obj.modifiers.new('Landscape Geometry', type='NODES')
                if node_modifier.node_group is not None:
                    bpy.data.node_groups.remove(node_modifier.node_group)
                node_modifier.node_group = landscape_nodes

                landscape_collection.objects.link(landscape_obj)

                material_data: Material = bpy.data.materials.get(landscape_data.name)

                if material_data is None:
                    material_data = bpy.data.materials.new(landscape_data.name)
                    material_data.blend_method = 'HASHED'
                    material_data.use_nodes = True
                    bsdf = material_data.node_tree.nodes['Principled BSDF']
                    tex_coord = material_data.node_tree.nodes.new(type='ShaderNodeTexCoord')
                    tex_coord.location = bsdf.location + Vector((-1200, 0))
                    invert_color: ShaderNodeInvert = material_data.node_tree.nodes.new(type='ShaderNodeInvert')
                    invert_color.location = bsdf.location + Vector((-300, 0))
                    material_data.node_tree.links.new(invert_color.outputs['Color'], bsdf.inputs['Alpha'])

                landscape_data.materials.append(material_data)
                landscape_obj.material_slots[0].link = 'OBJECT'
                landscape_obj.material_slots[0].material = material_data

                tiles[(tile_x, tile_y)] = (landscape_obj, material_data, tex_coord, set())

        context.view_layer.active_layer_collection = old_active_layer

        collections = [
            actor_collection,
            instance_collection,
            landscape_collection,
            point_light_collection,
            sun_light_collection,
            spot_light_collection,
            area_light_collection
        ]

        for collection in collections:
            if len(collection.all_objects) == 0:
                world_collection.children.unlink(collection)

        return {'FINISHED'}
