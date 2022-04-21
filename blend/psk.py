import bpy.types
from bpy.types import Property, Context, Armature, Object, Material, EditBone
from mathutils import Quaternion, Vector, Matrix

from os.path import basename, splitext
from numpy import ndarray

import io_import_pskx.utils as utils
from io_import_pskx.io import read_actorx, Mesh


class ActorXMesh:
    path: str
    settings: dict[str, Property]
    psk: Mesh | None
    name: str

    def __init__(self, path: str, settings: dict[str, Property]):
        self.path = path
        self.name = splitext(basename(path))[0]
        self.settings = settings
        with open(self.path, 'rb') as stream:
            self.psk = read_actorx(stream)

    def execute(self, context: Context) -> set[str]:
        resize_mod: float = self.settings['resize_by']

        utils.select_all('DESELECT')

        mesh_data: Mesh = bpy.data.meshes.new(self.name)
        mesh_obj: Object = bpy.data.objects.new(mesh_data.name, mesh_data)
        context.collection.objects.link(mesh_obj)

        has_armature: bool = self.psk.Bones is not None
        armature_data: Armature | None = None
        armature_obj: Object | None = None

        materials: list[Material] = []
        for material in self.psk.Materials:
            material_name = utils.fix_string_np(material['name'])
            material_data = bpy.data.materials.get(material_name) or bpy.data.materials.new(material_name)
            materials.append(material_data)
            mesh_data.materials.append(material_data)

        if has_armature:
            (armature_data, armature_obj) = self.import_armature(context, self.name, self.psk.Bones, resize_mod)

        utils.select_all('DESELECT')

        return {'FINISHED'}

    @staticmethod
    def import_armature(context: Context, name: str, bones: ndarray, resize_mod: float) -> set[Armature, Object]:
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

        for bone_id, bone in enumerate(bones):
            bone_name: str = utils.fix_string_np(bone['name'])
            orig_bone_name: str = bone_name
            if len(bone_name) > 63:
                bone_name = '%s:%d' % (bone[:57], bone_id)
            edit_bone: EditBone = armature_data.edit_bones.new(bone_name)
            edit_bones[bone_id] = edit_bone
            edit_bone['full_bone_name'] = orig_bone_name

            bone_length: float = bone['length']

            if bone_length < 0.01:
                bone_length = 0.5

            edit_bone.tail = Vector((0.0, bone_length, 0.0))

            parent_id: int = bone['parent_id']

            bone_rot: Quaternion = Quaternion((bone['rot'][3], bone['rot'][0], bone['rot'][1], bone['rot'][2]))
            bone_pos: Vector = Vector(bone['pos']) * resize_mod

            if parent_id == -1:
                bone_rot.conjugate()

            bone_matrix: Matrix = Matrix.Translation(bone_pos) @ bone_rot.conjugated().to_matrix().to_4x4()

            if parent_id > -1:
                edit_bone.parent = edit_bones[parent_id]
                bone_matrix = bone_matrices[parent_id] @ bone_matrix

            bone_matrices[bone_id] = bone_matrix
            edit_bone.matrix = bone_matrix

            edit_bone['bind_rest_rot'] = bone_rot.copy()
            edit_bone['bind_rest_pos'] = bone_pos.copy()

        utils.set_mode('OBJECT')

        return (armature_data, armature_obj)
