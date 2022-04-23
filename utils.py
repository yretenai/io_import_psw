import bpy
import numpy
from bpy.types import Context, Object
from numpy import ndarray


def fix_string(string: str) -> str:
    return string.rstrip(b'\0').decode(errors='replace', encoding='utf8')


def fix_string_np(string: ndarray) -> str:
    return numpy.trim_zeros(string).tobytes().decode(errors='replace', encoding='utf8')
