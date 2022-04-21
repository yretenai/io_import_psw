import typing
from struct import unpack

import numpy
from numpy import dtype
from numpy.typing import ArrayLike, DTypeLike


dispatch: dict[str, DTypeLike] = {
    # name    : [[ format      ), multiple]
    'PNTS0000': dtype([('xyz', '3f')]),
    'VTXW0000': dtype([('vertex_id', 'H'), ('uv', '2f'), ('mat_id', 'B')], align=True),
    'VTXW3200': dtype([('vertex_id', 'I'), ('uv', '2f'), ('mat_id', 'B')], align=True),
    'FACE0000': dtype([('abc', '3H'), ('mat_id', 'B'), ('aux_mat_id', 'B'), ('group', 'I')]),
    'FACE3200': dtype([('abc', '3I'), ('mat_id', 'B'), ('aux_mat_id', 'B'), ('group', 'I')]),
    'VTXNORMS': dtype([('rgb', '3f')]),
    'MATT0000': dtype([('name', '64b'), ('tex_id', 'i'), ('poly_flags', 'I'), ('aux_mat_id', 'i'), ('aux_flags', 'I'), ('lod_bias', 'i'), ('lod_style', 'i')]),
    'REFSKELT': dtype([('name', '64b'), ('flags', 'I'), ('num_children', 'i'), ('parent_id', 'i'), ('rot', '4f'), ('pos', '3f'), ('length', 'f'), ('scale', '3f')]),
    'REFSKEL0': dtype([('name', '64b'), ('flags', 'I'), ('num_children', 'i'), ('parent_id', 'i'), ('rot', '4f'), ('pos', '3f'), ('length', 'f'), ('scale', '3f')]),
    'BONENAMES': dtype([('name', '64b'), ('flags', 'I'), ('num_children', 'i'), ('parent_id', 'i'), ('rot', '4f'), ('pos', '3f'), ('length', 'f'), ('scale', '3f')]),
    'RAWWEIGHTS': dtype([('weight', 'f'), ('vertex_id', 'i'), ('bone_id', 'i')]),
    'RAWW0000': dtype([('weight', 'f'), ('vertex_id', 'i'), ('bone_id', 'i')]),
    'VERTEXCOLOR': dtype([('rgba', '4B')]),
    'EXTRAUVS': dtype([('uv', '2f')]),
    'MORPHTARGET': dtype([('vertex_id', 'i'), ('xyz', '3f')]),
    'MORPHNAMES': dtype([('name', '64b')]),
    'PHYSICS0': dtype([('name', '64b'), ('type', 'B'), ('center', '3f'), ('rot', '3f'), ('scale', '3f')]),
    'ANIMINFO': dtype([('name', '64b'), ('group', '64b'), ('total_bones', 'i'), ('root_included', 'i'), ('key_compression_style', 'i'), ('key_quotum', 'i'), ('key_reduction', 'f'), ('duration', 'f'), ('frame_rate', 'f'), ('start_bone', 'i'), ('first_frame', 'i'), ('num_frames', 'i')]),
    'ANIMKEYS': dtype([('pos', '3f'), ('rot', '4f'), ('time', 'f')]),
    'SCALEKEYS': dtype([('scale', '3f'), ('time', 'f')]),
}


class Mesh:
    TYPE: str = 'MESH'
    Points: ArrayLike
    Wedges: ArrayLike
    Faces: ArrayLike
    Normals: ArrayLike | None = None
    Materials: ArrayLike | None = None
    Bones: ArrayLike | None = None
    Colors: ArrayLike | None = None
    UVs: list[ArrayLike] = list()
    ShapeKeys: list[ArrayLike] = list()
    ShapeNames: ArrayLike | None = None
    Physics: ArrayLike | None = None

    def __setitem__(self, key, value):
        if key == 'PNTS0000':
            self.Points = value
        elif key == 'VTXW0000' or key == 'VTXW3200':
            self.Wedges = value
        elif key == 'FACE0000' or key == 'FACE0000':
            self.Faces = value
        elif key == 'VTXNORMS':
            self.Normals = value
        elif key == 'MATT0000':
            self.Materials = value
        elif key == 'REFSKELT' or key == 'REFSKEL0' or key == 'BONENAMES':
            self.Bones = value
        elif key == 'VERTEXCOLOR':
            self.Colors = value
        elif key[:8] == 'EXTRAUVS':
            self.UVs.append(value)
        elif key[:8] == 'MORPHTARGET':
            self.ShapeKeys.append(value)
        elif key == 'MORPHNAMES':
            self.ShapeNames = value
        elif key == 'PHYSICS0':
            self.Physics = value


class Animation:
    TYPE: str = 'ANIM'
    Name: str
    Group: str
    TotalBones: int
    RootIncluded: bool
    CompressionStyle: bool
    Quotum: float
    Reduce: float
    Duration: float
    FrameRate: float
    StartBone: int
    FirstFrame: int
    NumFrames: int
    Bones: ArrayLike | None = None
    Keys: ArrayLike | None = None
    ScaleKeys: ArrayLike | None = None

    def __setitem__(self, key: str, value: ArrayLike):
        if key == 'ANIMINFO':
            (self.Name, self.Group, self.TotalBones, self.RootIncluded, self.CompressionStyle, self.Quotum, self.Reduce, self.Duration, self.FrameRate, self.StartBone, self.FirstFrame, self.NumFrames) = value[0]
            self.Name = fix_string_np(self.Name)
            self.Group = fix_string_np(self.Group)
            self.RootIncluded = self.RootIncluded == 1
        elif key == 'REFSKELT' or key == 'REFSKEL0' or key == 'BONENAMES':
            self.Bones = value
        elif key == 'ANIMKEYS':
            self.Keys = value
        elif key == 'SCALEKEYS':
            self.ScaleKeys = value


def fix_string(string: str) -> str:
    return string.rstrip(b'\0').decode(errors='replace', encoding='ascii')


def fix_string_np(string: ArrayLike) -> str:
    return numpy.trim_zeros(string).tobytes().decode(errors='replace', encoding='ascii')


def read_chunk(stream: typing.BinaryIO) -> tuple[ArrayLike | None, str]:
    (chunk_id, chunk_type, chunk_size, chunk_count) = unpack('20s3i', stream.read(32))
    chunk_id = fix_string(chunk_id)
    total_size = chunk_size * chunk_count
    
    if chunk_id in dispatch:
        return (numpy.fromfile(stream, dtype=dispatch[chunk_id], count=chunk_count),  chunk_id)

    stream.seek(total_size, 1)

    return (None, chunk_id)


def read_actorx(stream: typing.BinaryIO) -> Animation | Mesh | None:
    ob = None
    magic = fix_string(unpack('20s', stream.read(20))[0])
    if magic == 'ACTRHEAD':
        ob = Mesh()
    elif magic == 'ANIMHEAD':
        ob = Animation()
    else:
        return None
    stream.seek(0, 2)
    size = stream.tell()
    stream.seek(32, 0)
    while stream.tell() < size:
        (data, name) = read_chunk(stream)
        if data is not None:
            ob[name] = data

    return ob
