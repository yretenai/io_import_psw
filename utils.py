import bpy
from bpy.types import Context, Object

import numpy
from numpy import ndarray


def fix_string(string: str) -> str:
    return string.rstrip(b'\0').decode(errors='replace', encoding='ascii')


def fix_string_np(string: ndarray) -> str:
    return numpy.trim_zeros(string).tobytes().decode(errors='replace', encoding='ascii')


def select_all(select_mode: str) -> None:
    if bpy.ops.object.select_all.poll():
        bpy.ops.object.select_all(action=select_mode)
    elif bpy.ops.mesh.select_all.poll():
        bpy.ops.mesh.select_all(action=select_mode)
    elif bpy.ops.pose.select_all.poll():
        bpy.ops.pose.select_all(action=select_mode)


def select_set(context: Context, obj: Object, state: bool) -> None:
    if obj.name in context.view_layer.objects:
        return obj.select_set(state)


def set_active(context: Context, obj: Object) -> None:
    context.view_layer.objects.active = obj


def set_mode(mode: str) -> None:
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode=mode, toggle=False)
