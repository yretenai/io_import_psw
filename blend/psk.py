import itertools
from os.path import basename, splitext

import bpy.types
import io_import_pskx.utils as utils
import numpy
from bpy.types import Property, Context, Armature, Object, EditBone, MeshUVLoopLayer, MeshLoopColorLayer, VertexGroup, ArmatureModifier, ShapeKey
from io_import_pskx.io import read_actorx, Mesh
from mathutils import Quaternion, Vector, Matrix


class ActorXMesh:
    path: str
    settings: dict[str, Property]
    resize_mod: float
    psk: Mesh | None
    name: str

    def __init__(self, path: str, settings: dict[str, Property]):
        self.path = path
        self.name = splitext(basename(path))[0]
        self.settings = settings
        self.resize_mod = self.settings['resize_by']

        with open(self.path, 'rb') as stream:
            self.psk = read_actorx(stream, settings)

    def execute(self, context: Context) -> set[str]:
        if self.psa is None or self.psa.TYPE != DataType.Mesh:
            return {'ERROR'}

        utils.select_all('DESELECT')

        mesh_data: Mesh = bpy.data.meshes.new(self.name)
        mesh_obj: Object = bpy.data.objects.new(mesh_data.name, mesh_data)
        context.collection.objects.link(mesh_obj)

        has_armature: bool = self.psk.Bones is not None and self.psk.Weights is not None
        armature_data: Armature | None = None
        armature_obj: Object | None = None

        for material_name in self.psk.MaterialNames:
            material_data = bpy.data.materials.get(material_name) or bpy.data.materials.new(material_name)
            mesh_data.materials.append(material_data)

        if has_armature:
            vertex_groups: list[VertexGroup] = [None] * len(self.psk.Bones)
            (armature_data, armature_obj) = self.import_armature(context, self.name, self.psk.Bones)

            for bone_id, (bone_name, _, _, _, _) in enumerate(self.psk.Bones):
                if len(bone_name) > 63:
                    bone_name = '%s:%d' % (bone_name[:57], bone_id)
                vertex_groups[bone_id] = mesh_obj.vertex_groups.new(name=bone_name)

            mesh_obj.parent = armature_obj
            mesh_obj.parent_type = 'OBJECT'

        utils.select_all('DESELECT')

        mesh_data.from_pydata(self.psk.Vertices, [], self.psk.Faces)

        mesh_data.polygons.foreach_set('material_index', self.psk.Materials)

        if self.psk.Normals is not None:
            mesh_data.polygons.foreach_set('use_smooth', numpy.full(self.psk.NumFaces, True))
            mesh_data.normals_split_custom_set_from_vertices(self.psk.Normals)
            mesh_data.use_auto_smooth = True

        if self.psk.Colors is not None:
            color_layer: MeshLoopColorLayer = mesh_data.vertex_colors.new(name='Color', do_init=False)
            color_layer.data.foreach_set('color', list(itertools.chain.from_iterable(self.psk.Colors)))

        for uv_id, uv_data in enumerate(self.psk.UVs):
            name: str = 'UV' if uv_id == 0 else 'UV_%03d' % uv_id
            uv_layer: MeshUVLoopLayer = mesh_data.uv_layers.new(name=name)
            if uv_layer is None:
                break

            uv_layer.data.foreach_set('uv', list(itertools.chain.from_iterable(uv_data)))

        if self.psk.NumShapes > 0:
            shape_basis: ShapeKey = mesh_obj.shape_key_add(name='Basis', from_mix=False)
            shape_basis.interpolation = 'KEY_LINEAR'
            mesh_data.shape_keys.use_relative = True

            for shape_name, shape_data in self.psk.ShapeKeys.items():
                shape = mesh_obj.shape_key_add(name=shape_name, from_mix=False)
                shape.interpolation = 'KEY_LINEAR'
                shape.relative_key = shape_basis
                shape.data.foreach_set('co', list(itertools.chain.from_iterable(shape_data)))

        mesh_data.validate()
        mesh_data.update()

        utils.select_all('DESELECT')

        if has_armature:
            for weight, vertex_id, bone_id in self.psk.Weights:
                vertex_groups[bone_id].add((vertex_id,), weight, 'ADD')

            armature_modifier: ArmatureModifier = mesh_obj.modifiers.new(armature_obj.data.name, type='ARMATURE')
            armature_modifier.show_expanded = False
            armature_modifier.use_vertex_groups = True
            armature_modifier.use_bone_envelopes = False
            armature_modifier.object = armature_obj

            utils.select_set(context, armature_obj, True)
            utils.set_active(context, armature_obj)
        else:
            utils.select_set(context, mesh_obj, True)
            utils.set_active(context, mesh_obj)

        return {'FINISHED'}

    @staticmethod
    def import_armature(context: Context, name: str, bones: list[tuple[str, int, Quaternion, Vector, Vector]]) -> set[Armature, Object]:
        armature_data: Armature = bpy.data.armatures.new(name + ' Armature')
        armature_obj: Object = bpy.data.objects.new(armature_data.name, armature_data)
        context.collection.objects.link(armature_obj)

        armature_data.show_axes = False
        armature_data.display_type = 'STICK'
        armature_obj.show_in_front = True

        utils.select_set(context, armature_obj, True)
        utils.set_active(context, armature_obj)
        utils.set_mode('EDIT')

        edit_bones: list[EditBone] = [None] * len(bones)
        bone_matrices: List[Matrix] = [None] * len(bones)

        for bone_id, (bone_name, parent_id, bone_rot, bone_pos, bone_scale) in enumerate(bones):
            orig_bone_name: str = bone_name
            if len(bone_name) > 63:
                bone_name = '%s:%d' % (bone_name[:57], bone_id)
            edit_bone: EditBone = armature_data.edit_bones.new(bone_name)
            edit_bones[bone_id] = edit_bone
            edit_bone['actorx:full_bone_name'] = orig_bone_name
            edit_bone.tail = Vector((0.0, 0.001, 0.0))

            if parent_id == -1:
                bone_rot.conjugate()

            bone_matrix: Matrix = Matrix.Translation(bone_pos) @ bone_rot.conjugated().to_matrix().to_4x4()

            if parent_id > -1:
                edit_bone.parent = edit_bones[parent_id]
                bone_matrix = bone_matrices[parent_id] @ bone_matrix

            bone_matrices[bone_id] = bone_matrix
            edit_bone.matrix = bone_matrix

            edit_bone['actorx:bind_rest_rot'] = bone_rot.copy()
            edit_bone['actorx:bind_rest_pos'] = bone_pos.copy()

        utils.set_mode('OBJECT')

        return (armature_data, armature_obj)
