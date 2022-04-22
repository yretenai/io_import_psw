import typing
from enum import Enum
from struct import unpack

import numpy
from bpy.types import Property
from io_import_pskx.utils import fix_string_np, fix_string
from mathutils import Quaternion, Vector
from numpy import dtype, ndarray
from numpy.typing import DTypeLike


dispatch: dict[str, DTypeLike] = {
        'PNTS0000':    dtype([('xyz', '3f')]),
        'VTXW0000':    dtype([('vertex_id', 'I'), ('uv', '2f'), ('mat_id', 'B')], align=True),
        'VTXW3200':    dtype([('vertex_id', 'I'), ('uv', '2f'), ('mat_id', 'B')], align=True),
        'FACE0000':    dtype([('abc', '3H'), ('mat_id', 'B'), ('aux_mat_id', 'B'), ('group', 'I')]),
        'FACE3200':    dtype([('abc', '3I'), ('mat_id', 'B'), ('aux_mat_id', 'B'), ('group', 'I')]),
        'VTXNORMS':    dtype([('xyz', '3f')]),
        'VTXTANGS':    dtype([('xyzw', '4f')]),
        'MATT0000':    dtype([('name', '64b'), ('tex_id', 'i'), ('poly_flags', 'I'), ('aux_mat_id', 'i'), ('aux_flags', 'I'), ('lod_bias', 'i'), ('lod_style', 'i')]),
        'REFSKELT':    dtype([('name', '64b'), ('flags', 'I'), ('num_children', 'i'), ('parent_id', 'i'), ('rot', '4f'), ('pos', '3f'), ('length', 'f'), ('scale', '3f')]),
        'REFSKEL0':    dtype([('name', '64b'), ('flags', 'I'), ('num_children', 'i'), ('parent_id', 'i'), ('rot', '4f'), ('pos', '3f'), ('length', 'f'), ('scale', '3f')]),
        'BONENAMES':   dtype([('name', '64b'), ('flags', 'I'), ('num_children', 'i'), ('parent_id', 'i'), ('rot', '4f'), ('pos', '3f'), ('length', 'f'), ('scale', '3f')]),
        'RAWWEIGHTS':  dtype([('weight', 'f'), ('vertex_id', 'i'), ('bone_id', 'i')]),
        'RAWW0000':    dtype([('weight', 'f'), ('vertex_id', 'i'), ('bone_id', 'i')]),
        'VERTEXCOLOR': dtype([('rgba', '4B')]),
        'EXTRAUVS':    dtype([('uv', '2f')]),
        'MORPHTARGET': dtype([('vertex_id', 'i'), ('xyz', '3f')]),
        'MORPHNAMES':  dtype([('name', '64b')]),
        'PHYSICS0':    dtype([('name', '64b'), ('type', 'B'), ('center', '3f'), ('rot', '3f'), ('scale', '3f')]),
        'ANIMINFO':    dtype([('name', '64b'), ('group', '64b'), ('total_bones', 'i'), ('root_included', 'i'), ('key_compression_style', 'i'), ('key_quotum', 'i'), ('key_reduction', 'f'), ('duration', 'f'), ('frame_rate', 'f'), ('start_bone', 'i'), ('first_frame', 'i'), ('num_frames', 'i')]),
        'ANIMKEYS':    dtype([('pos', '3f'), ('rot', '4f'), ('time', 'f')]),
        'SCALEKEYS':   dtype([('scale', '3f'), ('time', 'f')]),
}


class PhysicsShape(Enum):
    Cube = 0
    Sphere = 1
    Cylinder = 2
    Convex = 3


class DataType(Enum):
    Mesh = 0
    Animation = 1


class Mesh:
    TYPE: DataType = DataType.Mesh

    NumVertices: int
    NumFaces: int
    NumMaterials: int = 0
    NumShapes: int = 0
    NumUVs: int = 1
    NumBones: int = 0
    NumHitboxes: int = 0

    Vertices: list[list[float]]
    Faces: list[list[int]]
    Normals: list[list[float]] | None = None
    Tangents: list[list[float]] | None = None
    Materials: list[int] | None = None
    MaterialNames: list[str] | None = None
    Bones: list[tuple[str, int, Quaternion, Vector]] | None = None
    Weights: list[tuple[int, int, float]] | None = None
    Colors: list[list[float]] | None = None
    UVs: list[list[float]]
    ShapeKeys: dict[str, list[float]]
    Physics: list[tuple[str, PhysicsShape, Vector, Quaternion, Vector]]

    NPPoints: ndarray
    NPWedges: ndarray
    NPFaces: ndarray
    NPNormals: ndarray | None = None
    NPTangents: ndarray | None = None
    NPMaterials: ndarray | None = None
    NPBones: ndarray | None = None
    NPWeights: ndarray | None = None
    NPColors: ndarray | None = None
    NPUVs: list[ndarray]
    NPShapeKeys: list[ndarray]
    NPShapeNames: ndarray | None = None
    NPPhysics: ndarray | None = None

    def __init__(self):
        self.UVs = list()
        self.ShapeKeys = list()
        self.NPUVs = list()
        self.NPShapeKeys = list()

    def __setitem__(self, key: str, value: ndarray):
        if key == 'PNTS0000':
            self.NPPoints = value
        elif key == 'VTXW0000' or key == 'VTXW3200':
            self.NPWedges = value
        elif key == 'FACE0000' or key == 'FACE3200':
            self.NPFaces = value
        elif key == 'VTXNORMS':
            self.NPNormals = value
        elif key == 'VTXTANGS':
            self.NPNormals = value
        elif key == 'MATT0000':
            self.NPMaterials = value
        elif key == 'REFSKELT' or key == 'REFSKEL0' or key == 'BONENAMES':
            self.NPBones = value
        elif key == 'RAWWEIGHTS' or key == 'RAWW0000':
            self.NPWeights = value
        elif key == 'VERTEXCOLOR':
            self.NPColors = value
        elif key[:8] == 'EXTRAUVS':
            self.NPUVs.append(value)
        elif key[:11] == 'MORPHTARGET':
            self.NPShapeKeys.append(value)
        elif key == 'MORPHNAMES':
            self.NPShapeNames = value
        elif key == 'PHYSICS0':
            self.NPPhysics = value

    def finalize(self, settings: dict[str, Property]):
        # todo(naomi): investigate if this can be converted to numpy.
        self.NumVertices = len(self.NPWedges)
        self.NumFaces = len(self.NPFaces)

        self.Vertices = [None] * self.NumVertices

        resize_by: float = settings['resize_by'] if 'resize_by' in settings else 0.01

        for wedge_id, (vertex_id, uv, material_id) in enumerate(self.NPWedges):
            self.Vertices[wedge_id] = (self.NPPoints[vertex_id]['xyz'] * resize_by).tolist()

        self.Faces = [None] * self.NumFaces
        self.UVs = [[None] * self.NumFaces * 3]
        NPWedgeUV = (self.NPWedges['uv'] * [(1.0, -1.0)] + [(0.0, 1.0)]).tolist()
        has_materials = self.NPMaterials is not None
        if has_materials:
            self.Materials = [None] * self.NumFaces
        for face_id, (rgb, material_id, _, _) in enumerate(self.NPFaces):
            self.Faces[face_id] = [rgb[1], rgb[0], rgb[2]]
            self.UVs[0][face_id * 3 + 0] = NPWedgeUV[self.Faces[face_id][0]]
            self.UVs[0][face_id * 3 + 1] = NPWedgeUV[self.Faces[face_id][1]]
            self.UVs[0][face_id * 3 + 2] = NPWedgeUV[self.Faces[face_id][2]]
            if has_materials:
                self.Materials[face_id] = material_id

        if self.NPNormals is not None:
            self.Normals = [None] * self.NumVertices
            for wedge_id, rgb in enumerate(self.NPNormals['xyz']):
                self.Normals[wedge_id] = rgb

        if self.NPTangents is not None:
            self.Tangents = [None] * self.NumVertices
            for wedge_id, rgb in enumerate(self.NPTangents['xyzw']):
                self.Tangents[wedge_id] = rgb

        if has_materials:
            self.NumMaterials = len(self.NPMaterials)
            self.MaterialNames = [None] * self.NumMaterials
            for material_id, material_name in enumerate(self.NPMaterials['name']):
                self.MaterialNames[material_id] = fix_string_np(material_name)

        if self.NPBones is not None and self.NPWeights is not None:
            self.NumBones = len(self.NPBones)
            self.Bones = [None] * self.NumBones
            for bone_id, (bone_name, flags, num_children, parent_id, rot, pos, length, scale) in enumerate(self.NPBones):
                self.Bones[bone_id] = (fix_string_np(bone_name), parent_id, Quaternion((rot[3], rot[0], rot[1], rot[2])), Vector((pos[0], pos[1], pos[2])) * resize_by)

            self.Weights = self.NPWeights.tolist()

        if self.NPColors is not None:
            self.Colors = [None] * self.NumFaces * 3
            NPColorsFloat = (self.NPColors['rgba'] / 0xff).tolist()
            for face_id, (a, b, c) in enumerate(self.Faces):
                self.Colors[face_id * 3] = NPColorsFloat[a]
                self.Colors[face_id * 3 + 1] = NPColorsFloat[b]
                self.Colors[face_id * 3 + 2] = NPColorsFloat[c]

        if self.NPUVs is not None:
            for uv_id, NPUV in enumerate(self.NPUVs):
                NPExtraUV = (NPUV['uv'] * [(1.0, -1.0)] + [(0.0, 1.0)]).tolist()
                ExtraUV = [None] * self.NumFaces * 3
                for face_id, (a, b, c) in enumerate(self.Faces):
                    ExtraUV[face_id * 3 + 0] = NPExtraUV[a]
                    ExtraUV[face_id * 3 + 1] = NPExtraUV[b]
                    ExtraUV[face_id * 3 + 2] = NPExtraUV[c]
                self.UVs.append(ExtraUV)
        self.NumUVs = len(self.UVs)

        if self.NPShapeKeys is not None and self.NPShapeNames is not None:
            self.NumShapes = len(self.NPShapeKeys)
            for shape_id, shape_data in enumerate(self.NPShapeKeys):
                shape_data['xyz'] *= resize_by
                shape_name = fix_string_np(self.NPShapeNames['name'][shape_id])
                self.ShapeKeys[shape_name] = self.Vertices.copy()
                for vertex_id, shape_delta in shape_data.tolist():
                    self.ShapeKeys[shape_name][int(vertex_id)] = shape_delta

        # if self.NPPhysics is not None:
        # self.NumHitboxes = len(self.NPPhysics)
        # todo(naomi): physics


class Animation:
    TYPE: DataType = DataType.Animation
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
    Bones: ndarray | None = None
    Keys: ndarray | None = None
    ScaleKeys: ndarray | None = None

    def __setitem__(self, key: str, value: ndarray):
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


def read_chunk(stream: typing.BinaryIO) -> tuple[ndarray | None, str]:
    (chunk_id, chunk_type, chunk_size, chunk_count) = unpack('20s3i', stream.read(32))
    chunk_id = fix_string(chunk_id)
    print('Reading %d elements for chunk %s' % (chunk_count, chunk_id))
    total_size = chunk_size * chunk_count

    for chunk_key in dispatch.keys():
        if chunk_key == chunk_id or chunk_id.startswith(chunk_key):
            return (numpy.fromfile(stream, dtype=dispatch[chunk_key], count=chunk_count), chunk_id)

    print('No parser found for %s!' % (chunk_id))

    stream.seek(total_size, 1)

    return (None, chunk_id)


def read_actorx(stream: typing.BinaryIO, settings: dict[str, Property]) -> Animation | Mesh | None:
    ob = None
    magic = fix_string(unpack('20s', stream.read(20))[0])
    if magic == 'ACTRHEAD':
        ob = Mesh()
    elif magic == 'ANIMHEAD':
        ob = Animation()
    else:
        return None
    print('Reading %s' % magic)
    stream.seek(0, 2)
    size = stream.tell()
    stream.seek(32, 0)
    while stream.tell() < size:
        (data, name) = read_chunk(stream)
        if data is not None:
            ob[name] = data

    ob.finalize(settings)

    return ob
