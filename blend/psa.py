import itertools
from os.path import basename, splitext
from typing import Any

import bpy
from bpy.types import Property, Context, Object, Armature, Bone, PoseBone, FCurve, Action
from io_import_pskx.blend.psk import ActorXMesh
from io_import_pskx.io import read_actorx, Animation, DataType
from mathutils import Vector, Quaternion


class ActorXAnimation:
    path: str
    settings: dict[str, Property]
    resize_mod: float
    psa: Animation | None
    name: str

    def __init__(self, path: str, settings: dict[str, Property]):
        self.path = path
        self.name = splitext(basename(path))[0]
        self.settings = settings
        self.resize_mod = self.settings['resize_by']

        with open(self.path, 'rb') as stream:
            self.psa = read_actorx(stream, settings)

    @staticmethod
    def __get_armature(context: Context) -> Object | None:
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE' and obj.select_get(view_layer=context.view_layer):
                return obj
            elif obj.type == 'MESH' and obj.select_get(view_layer=context.view_layer):
                for modifier in obj.modifiers:
                    if modifier.type == 'ARMATURE':
                        return modifier.object
        return None

    def execute(self, context: Context):
        if self.psa is None or (self.psa.TYPE != DataType.Animation and self.psa.TYPE != DataType.AnimationV2):
            return {'ERROR'}

        if self.psa.TYPE == DataType.Animation:
            return self.execute_legacy(context)

        armature_obj: Object = self.__get_armature(context)
        if armature_obj is None:
            (armature_data, armature_obj) = ActorXMesh.import_armature(context, self.name, self.psa.Bones)

        armature_data: Armature = armature_obj.data

        bone_map: dict[str, Bone] = {bone['actorx:full_bone_name']: bone for bone in armature_data.bones}
        bones: list[tuple[Bone, PoseBone, Vector, Quaternion]] = [None] * self.psa.NumBones

        if armature_obj.animation_data is None:
            armature_obj.animation_data_create()

        for bone_id, (bone_name, _, _, _, _) in enumerate(self.psa.Bones):
            if bone_name not in bone_map:
                continue
            bone: Bone = bone_map[bone_name]
            pose_bone: PoseBone = armature_obj.pose.bones[bone.name]
            rot_basis: Any = bone['actorx:bind_rest_rot']
            pos_basis: Any = bone['actorx:bind_rest_pos']
            bones[bone_id] = (bone, pose_bone, Vector(pos_basis), Quaternion(rot_basis))

        action: Action = bpy.data.actions.new(name=self.psa.SequenceName)

        fcurves: list[tuple[list[FCurve], list[FCurve]]] = [None] * self.psa.NumBones

        for bone_id in range(self.psa.NumBones):
            if bones[bone_id] is None:
                continue

            (_, pose_bone, _, _) = bones[bone_id]

            data_path_rot: str = pose_bone.path_from_id('rotation_quaternion')
            data_path_pos: str = pose_bone.path_from_id('location')

            rot: list[FCurve] = [action.fcurves.new(data_path_rot, index=index) for index in range(4)]
            pos: list[FCurve] = [action.fcurves.new(data_path_pos, index=index) for index in range(3)]

            for fcurve in rot:
                fcurve.keyframe_points.add(self.psa.RotKeyLength[bone_id])

            for fcurve in pos:
                fcurve.keyframe_points.add(self.psa.PosKeyLength[bone_id])

            fcurves[bone_id] = (rot, pos)

        for bone_id in range(self.psa.NumBones):
            if fcurves[bone_id] is None:
                continue

            (fcurve_rot, fcurve_pos) = fcurves[bone_id]
            (bone, pose_bone, pos_basis, rot_basis) = bones[bone_id]

            for frame_id, (keyframe_time, keyframe_rot) in enumerate(self.psa.RotKeys[bone_id]):
                rot: Quaternion = rot_basis.conjugated()
                rot.rotate(rot_basis)

                rot_parent: Quaternion = rot_basis.conjugated()
                if bone.parent is not None:
                    rot_parent.rotate(keyframe_rot)
                else:
                    rot_parent.rotate(keyframe_rot.conjugated())

                rot.rotate(rot_parent)
                rot.conjugate()

                for i in range(4):
                    fcurve_rot[i].keyframe_points[frame_id].co = keyframe_time + 1, rot[i]
                    fcurve_rot[i].keyframe_points[frame_id].interpolation = 'LINEAR'

            for frame_id, (keyframe_time, keyframe_pos) in enumerate(self.psa.PosKeys[bone_id]):
                pos: Vector = keyframe_pos - pos_basis
                pos.rotate(rot_basis)

                for i in range(3):
                    fcurve_pos[i].keyframe_points[frame_id].co = keyframe_time + 1, pos[i]
                    fcurve_pos[i].keyframe_points[frame_id].interpolation = 'LINEAR'

        armature_obj.animation_data.action = action

        return {'FINISHED'}

    def execute_legacy(self, context: Context):
        armature_obj: Object = self.__get_armature(context)
        if armature_obj is None:
            (armature_data, armature_obj) = ActorXMesh.import_armature(context, self.name, self.psa.Bones)

        armature_data: Armature = armature_obj.data

        bone_map: dict[str, Bone] = {bone['actorx:full_bone_name']: bone for bone in armature_data.bones}
        bones: list[tuple[Bone, PoseBone, Vector, Quaternion]] = [None] * self.psa.NumBones

        if armature_obj.animation_data is None:
            armature_obj.animation_data_create()

        for bone_id, (bone_name, _, _, _, _) in enumerate(self.psa.Bones):
            if bone_name not in bone_map:
                continue
            bone: Bone = bone_map[bone_name]
            pose_bone: PoseBone = armature_obj.pose.bones[bone.name]
            rot_basis: Any = bone['actorx:bind_rest_rot']
            pos_basis: Any = bone['actorx:bind_rest_pos']
            bones[bone_id] = (bone, pose_bone, Vector(pos_basis), Quaternion(rot_basis))

        base_action: Action = None
        for sequence_id, (name, group, total_bones, frame_count, frame_rate) in enumerate(self.psa.Sequences):
            if group != 'None':
                name = '%s: %s' % (group, name)

            action: Action = bpy.data.actions.new(name=name)
            if base_action is None:
                base_action = action

            fcurves: list[tuple[list[FCurve], list[FCurve]]] = [None] * total_bones

            for bone_id in range(total_bones):
                if bones[bone_id] is None:
                    continue

                (_, pose_bone, _, _) = bones[bone_id]

                data_path_rot: str = pose_bone.path_from_id('rotation_quaternion')
                data_path_pos: str = pose_bone.path_from_id('location')

                rot: list[FCurve] = [action.fcurves.new(data_path_rot, index=index) for index in range(4)]
                pos: list[FCurve] = [action.fcurves.new(data_path_pos, index=index) for index in range(3)]

                for fcurve in itertools.chain(rot, pos):
                    fcurve.keyframe_points.add(frame_count)

                fcurves[bone_id] = (rot, pos)

            keyframe_time: list[float] = [1.0] * total_bones

            for frame_id in range(frame_count):
                frame_offset: int = total_bones * frame_id
                for bone_id in range(total_bones):
                    if fcurves[bone_id] is None:
                        continue

                    (fcurve_rot, fcurve_pos) = fcurves[bone_id]
                    (bone, pose_bone, pos_basis, rot_basis) = bones[bone_id]
                    (keyframe_duration, keyframe_pos, keyframe_rot) = self.psa.Keys[frame_offset + bone_id]

                    rot: Quaternion = rot_basis.conjugated()
                    rot.rotate(rot_basis)

                    rot_parent: Quaternion = rot_basis.conjugated()
                    if bone.parent is not None:
                        rot_parent.rotate(keyframe_rot)
                    else:
                        rot_parent.rotate(keyframe_rot.conjugated())

                    rot.rotate(rot_parent)
                    rot.conjugate()

                    pos: Vector = keyframe_pos - pos_basis
                    pos.rotate(rot_basis)

                    for i in range(4):
                        fcurve_rot[i].keyframe_points[frame_id].co = keyframe_time[bone_id], rot[i]
                        fcurve_rot[i].keyframe_points[frame_id].interpolation = 'LINEAR'

                    for i in range(3):
                        fcurve_pos[i].keyframe_points[frame_id].co = keyframe_time[bone_id], pos[i]
                        fcurve_pos[i].keyframe_points[frame_id].interpolation = 'LINEAR'

                    keyframe_time[bone_id] += keyframe_duration

        if base_action is not None:
            armature_obj.animation_data.action = base_action

        return {'FINISHED'}
