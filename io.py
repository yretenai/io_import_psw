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
        'PNTS0000':     dtype([('xyz', '3f')]),
        'VTXW0000':     dtype([('vertex_id', 'I'), ('uv', '2f'), ('mat_id', 'B')], align=True),
        'VTXW3200':     dtype([('vertex_id', 'I'), ('uv', '2f'), ('mat_id', 'B')], align=True),
        'FACE0000':     dtype([('abc', '3H'), ('mat_id', 'B'), ('aux_mat_id', 'B'), ('group', 'I')]),
        'FACE3200':     dtype([('abc', '3I'), ('mat_id', 'B'), ('aux_mat_id', 'B'), ('group', 'I')]),
        'VTXNORMS':     dtype([('xyz', '3f')]),
        'VTXTANGS':     dtype([('xyzw', '4f')]),
        'MATT0000':     dtype([('name', '64b'), ('tex_id', 'i'), ('poly_flags', 'I'), ('aux_mat_id', 'i'), ('aux_flags', 'I'), ('lod_bias', 'i'), ('lod_style', 'i')]),
        'REFSKELT':     dtype([('name', '64b'), ('flags', 'I'), ('num_children', 'i'), ('parent_id', 'i'), ('rot', '4f'), ('pos', '3f'), ('length', 'f'), ('scale', '3f')]),
        'REFSKEL0':     dtype([('name', '64b'), ('flags', 'I'), ('num_children', 'i'), ('parent_id', 'i'), ('rot', '4f'), ('pos', '3f'), ('length', 'f'), ('scale', '3f')]),
        'BONENAMES':    dtype([('name', '64b'), ('flags', 'I'), ('num_children', 'i'), ('parent_id', 'i'), ('rot', '4f'), ('pos', '3f'), ('length', 'f'), ('scale', '3f')]),
        'RAWWEIGHTS':   dtype([('weight', 'f'), ('vertex_id', 'i'), ('bone_id', 'i')]),
        'RAWW0000':     dtype([('weight', 'f'), ('vertex_id', 'i'), ('bone_id', 'i')]),
        'VERTEXCOLOR':  dtype([('rgba', '4B')]),
        'EXTRAUVS':     dtype([('uv', '2f')]),
        'MORPHTARGET':  dtype([('vertex_id', 'i'), ('xyz', '3f')]),
        'MORPHNAMES':   dtype([('name', '64b')]),
        'PHYSICS0':     dtype([('name', '64b'), ('type', 'B'), ('center', '3f'), ('rot', '3f'), ('scale', '3f')]),
        'SHAPEELEMS':   dtype([('name', '64b'), ('type', 'i'), ('center', '3f'), ('D:\rot', '4f'), ('scale', '3f')]),
        'ANIMINFO':     dtype([('name', '64b'), ('group', '64b'), ('total_bones', 'i'), ('root_included', 'i'), ('key_compression_style', 'i'), ('key_quotum', 'i'), ('key_reduction', 'f'), ('duration', 'f'), ('frame_rate', 'f'), ('start_bone', 'i'), ('first_frame', 'i'), ('num_frames', 'i')]),
        'ANIMKEYS':     dtype([('pos', '3f'), ('rot', '4f'), ('time', 'f')]),
        'SCALEKEYS':    dtype([('scale', '3f'), ('time', 'f')]),
        'SEQUENCES':    dtype([('name', '64b'), ('framerate', 'f')]),
        'ROTTRACK':     dtype([('time', 'f'), ('xyzw', '4f')]),
        'POSTRACK':     dtype([('time', 'f'), ('xyz', '3f')]),
        'WORLDACTORS':  dtype([('name', '64b'), ('asset', '256b'), ('parent', 'i'), ('pos', '3f'), ('rot', '4f'), ('scale', '3f'), ('flags', 'i')]),
        'LANDSCAPE':    dtype([('name', '256b'), ('actor_id', 'i'), ('x', 'i'), ('y', 'i'), ('type', 'i'), ('size', 'i'), ('scale', 'f'), ('offset', 'f')]),
        'INSTMATERIAL': dtype([('actor_id', 'i'), ('material_id', 'i'), ('name', '64b')])
}


class PhysicsShape(Enum):
    Cube = 0
    Sphere = 1
    Cylinder = 2
    Convex = 3
    Cone = 4


class DataType(Enum):
    Mesh = 0
    Animation = 1
    AnimationV2 = 2
    World = 3


class Mesh:
    TYPE: DataType = DataType.Mesh

    NumVertices: int
    NumFaces: int
    NumMaterials: int
    NumShapes: int
    NumUVs: int
    NumBones: int
    NumHitboxes: int

    Vertices: list[list[float]]
    Faces: list[list[int]]
    Normals: list[list[float]] | None
    Tangents: list[list[float]] | None
    Materials: list[int] | None
    MaterialNames: list[str] | None
    Bones: list[tuple[str, int, Quaternion, Vector, Vector]] | None
    Weights: list[tuple[int, int, float]] | None
    Colors: list[list[float]] | None
    UVs: list[list[float]]
    ShapeKeys: dict[str, list[float]]
    Physics: list[tuple[str, PhysicsShape, Vector, Quaternion, Vector]]

    NPPoints: ndarray
    NPWedges: ndarray
    NPFaces: ndarray
    NPNormals: ndarray | None
    NPTangents: ndarray | None
    NPMaterials: ndarray | None
    NPBones: ndarray | None
    NPWeights: ndarray | None
    NPColors: ndarray | None
    NPUVs: list[ndarray]
    NPShapeKeys: list[ndarray]
    NPShapeNames: ndarray | None
    NPPhysics: ndarray | None

    def __init__(self):
        self.NumMaterials = 0
        self.NumShapes = 0
        self.NumUVs = 0
        self.NumBones = 0
        self.NumHitboxes = 0

        self.Normals = None
        self.Tangents = None
        self.Materials = None
        self.MaterialNames = None
        self.Bones = None
        self.Weights = None
        self.Colors = None
        self.UVs = list()
        self.ShapeKeys = list()
        self.Physics = None

        self.NPNormals = None
        self.NPTangents = None
        self.NPMaterials = None
        self.NPBones = None
        self.NPWeights = None
        self.NPColors = None
        self.NPUVs = list()
        self.NPShapeKeys = list()
        self.NPShapeNames = None
        self.NPPhysics = None

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
        elif key == 'SHAPEELEMS':
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
        has_materials = self.NPMaterials is not None and len(self.NPMaterials) > 0
        if has_materials:
            self.Materials = [None] * self.NumFaces
        for face_id, (rgb, material_id, _, _) in enumerate(self.NPFaces):
            self.Faces[face_id] = [rgb[1], rgb[0], rgb[2]]
            self.UVs[0][face_id * 3 + 0] = NPWedgeUV[self.Faces[face_id][0]]
            self.UVs[0][face_id * 3 + 1] = NPWedgeUV[self.Faces[face_id][1]]
            self.UVs[0][face_id * 3 + 2] = NPWedgeUV[self.Faces[face_id][2]]
            if has_materials:
                self.Materials[face_id] = material_id

        if self.NPNormals is not None and len(self.NPNormals) > 0:
            self.Normals = [None] * self.NumVertices
            for wedge_id, rgb in enumerate(self.NPNormals['xyz']):
                self.Normals[wedge_id] = rgb

        if self.NPTangents is not None and len(self.NPNormals) > 0:
            self.Tangents = [None] * self.NumVertices
            for wedge_id, rgb in enumerate(self.NPTangents['xyzw']):
                self.Tangents[wedge_id] = rgb

        if has_materials:
            self.NumMaterials = len(self.NPMaterials)
            self.MaterialNames = [None] * self.NumMaterials
            for material_id, material_name in enumerate(self.NPMaterials['name']):
                self.MaterialNames[material_id] = fix_string_np(material_name)

        if self.NPBones is not None and len(self.NPBones) > 0:
            self.NumBones = len(self.NPBones)
            self.Bones = [None] * self.NumBones
            for bone_id, (bone_name, flags, num_children, parent_id, rot, pos, length, scale) in enumerate(self.NPBones):
                self.Bones[bone_id] = (fix_string_np(bone_name), parent_id, Quaternion((rot[3], rot[0], rot[1], rot[2])), Vector((pos[0], pos[1], pos[2])) * resize_by, Vector((scale[0], scale[1], scale[2])) * resize_by)

        if self.NPWeights is not None and len(self.NPWeights) > 0:
            self.Weights = self.NPWeights.tolist()

        if self.NPColors is not None and len(self.NPColors) > 0:
            self.Colors = [None] * self.NumFaces * 3
            NPColorsFloat = (self.NPColors['rgba'] / 0xff).tolist()
            for face_id, (a, b, c) in enumerate(self.Faces):
                self.Colors[face_id * 3] = NPColorsFloat[a]
                self.Colors[face_id * 3 + 1] = NPColorsFloat[b]
                self.Colors[face_id * 3 + 2] = NPColorsFloat[c]

        if self.NPUVs is not None and len(self.NPUVs) > 0:
            for uv_id, NPUV in enumerate(self.NPUVs):
                NPExtraUV = (NPUV['uv'] * [(1.0, -1.0)] + [(0.0, 1.0)]).tolist()
                ExtraUV = [None] * self.NumFaces * 3
                for face_id, (a, b, c) in enumerate(self.Faces):
                    ExtraUV[face_id * 3 + 0] = NPExtraUV[a]
                    ExtraUV[face_id * 3 + 1] = NPExtraUV[b]
                    ExtraUV[face_id * 3 + 2] = NPExtraUV[c]
                self.UVs.append(ExtraUV)
        self.NumUVs = len(self.UVs)

        if self.NPShapeKeys is not None and self.NPShapeNames is not None and len(self.NPShapeKeys) > 0 and len(self.NPShapeNames) > 0:
            self.NumShapes = len(self.NPShapeKeys)
            for shape_id, shape_data in enumerate(self.NPShapeKeys):
                shape_data['xyz'] *= resize_by
                shape_name = fix_string_np(self.NPShapeNames['name'][shape_id])
                self.ShapeKeys[shape_name] = self.Vertices.copy()
                for vertex_id, shape_delta in shape_data.tolist():
                    self.ShapeKeys[shape_name][int(vertex_id)] = shape_delta

        if self.NPPhysics is not None and len(self.NPPhysics) > 0:
            self.NumHitboxes = len(self.NPPhysics)
            # todo(naomi): physics


class Animation:
    TYPE: DataType = DataType.Animation

    NumSequences: int
    NumBones: int
    NumKeys: int

    Sequences: list[tuple[str, str, int, int, float]] | None
    Bones: list[tuple[str, int, Quaternion, Vector, Vector]] | None
    Keys: list[tuple[float, Vector, Quaternion]] | None

    NPSequences: ndarray | None
    NPBones: ndarray | None
    NPKeys: ndarray | None

    def __init__(self):
        self.NumSequences = 0
        self.NumBones = 0
        self.NumKeys = 0

        self.Sequences = None
        self.Bones = None
        self.Keys = None

        self.NPSequences = None
        self.NPBones = None
        self.NPKeys = None

    def __setitem__(self, key: str, value: ndarray):
        if len(value) == 0:
            return

        if key == 'ANIMINFO':
            self.NPSequences = value
        elif key == 'REFSKELT' or key == 'REFSKEL0' or key == 'BONENAMES':
            self.NPBones = value
        elif key == 'ANIMKEYS':
            self.NPKeys = value

    def finalize(self, settings: dict[str, Property]):
        resize_by: float = settings['resize_by'] if 'resize_by' in settings else 0.01

        self.NumSequences = len(self.NPSequences)
        self.Sequences = [None] * self.NumSequences
        for sequence_id, (name, group, total_bones, rooted, compression_style, quotum, reduction, duration, framerate, first_bone, first_frame, raw_frames) in enumerate(self.NPSequences):
            self.Sequences[sequence_id] = (fix_string_np(name), fix_string_np(group), total_bones, raw_frames, framerate)

        self.NumBones = len(self.NPBones)
        self.Bones = [None] * self.NumBones
        for bone_id, (bone_name, flags, num_children, parent_id, rot, pos, length, scale) in enumerate(self.NPBones):
            self.Bones[bone_id] = (fix_string_np(bone_name), parent_id, Quaternion((rot[3], rot[0], rot[1], rot[2])), Vector((pos[0], pos[1], pos[2])) * resize_by, Vector((scale[0], scale[1], scale[2])) * resize_by)

        self.NumKeys = len(self.NPKeys)
        self.Keys = [None] * self.NumKeys

        for key_id, (pos, rot, time) in enumerate(self.NPKeys.tolist()):
            self.Keys[key_id] = (time, Vector(pos) * resize_by, Quaternion((rot[3], rot[0], rot[1], rot[2])))


class AnimationV2:
    TYPE: DataType = DataType.AnimationV2

    NumBones: int

    SequenceName: str | None
    Bones: list[tuple[str, int, Quaternion, Vector, Vector]] | None
    PosKeys: list[list[tuple[float, Vector]]] | None
    RotKeys: list[list[tuple[float, Quaternion]]] | None
    PosKeyLength = list[int]
    RotKeyLength = list[int]

    NPBones: ndarray | None
    NPSequences: ndarray | None
    NPPosTracks: list[list[ndarray]] | None
    NPRotTracks: list[list[ndarray]] | None

    def __init__(self):
        self.NumSequences = 0
        self.NumBones = 0

        self.SequenceName = None
        self.Bones = None
        self.PosKeys = None
        self.RotKeys = None
        self.PosKeyLength = None
        self.RotKeyLength = None

        self.NPBones = None
        self.NPSequences = None
        self.NPPosTracks = list()
        self.NPRotTracks = list()

    def __setitem__(self, key: str, value: ndarray):
        if key == 'REFSKELT' or key == 'REFSKEL0' or key == 'BONENAMES':
            self.NPBones = value
        elif key == 'SEQUENCES':
            self.NPSequences = value
        elif key[:8] == 'POSTRACK':
            self.NPPosTracks.append(value)
        elif key[:8] == 'ROTTRACK':
            self.NPRotTracks.append(value)

    def finalize(self, settings: dict[str, Property]):
        resize_by: float = settings['resize_by'] if 'resize_by' in settings else 0.01

        self.NumBones = len(self.NPBones)
        self.Bones = [None] * self.NumBones
        for bone_id, (bone_name, flags, num_children, parent_id, rot, pos, length, scale) in enumerate(self.NPBones):
            self.Bones[bone_id] = (fix_string_np(bone_name), parent_id, Quaternion((rot[3], rot[0], rot[1], rot[2])), Vector(pos) * resize_by, Vector(pos) * resize_by)

        self.SequenceName = fix_string_np(self.NPSequences[0]["name"])

        self.PosKeys = [None] * self.NumBones
        self.RotKeys = [None] * self.NumBones
        self.PosKeyLength = [len(keys) for keys in self.NPPosTracks]
        self.RotKeyLength = [len(keys) for keys in self.NPRotTracks]

        for bone_id in range(self.NumBones):
            NBBonePosKeys: list[tuple[time, list[float]]] = self.NPPosTracks[bone_id].tolist()
            self.PosKeys[bone_id] = [None] * len(NBBonePosKeys)
            for pos_id, (time, pos) in enumerate(NBBonePosKeys):
                self.PosKeys[bone_id][pos_id] = (time, Vector(pos) * resize_by)

            NBBoneRotKeys: list[tuple[time, list[float]]] = self.NPRotTracks[bone_id].tolist()
            self.RotKeys[bone_id] = [None] * len(NBBoneRotKeys)
            for rot_id, (time, rot) in enumerate(NBBoneRotKeys):
                self.RotKeys[bone_id][rot_id] = (time, Quaternion((rot[3], rot[0], rot[1], rot[2])))


class World:
    TYPE: DataType = DataType.World

    NumActors: int

    Actors: list[tuple[str, str, int, Vector, Quaternion, Vector, bool, bool]]  # bools = no shadow, hidden
    OverrideMaterials: list[dict[int, str]]
    Landscapes: list[tuple[str, int, Vector, Vector, int, int, int, int]]  # name, actor, pos, size, type, x, y, quad

    NPActors: ndarray
    NPMaterials: ndarray | None
    NPLandscapes: ndarray | None

    def __init__(self):
        self.NumActors = 0

        self.Actors = []
        self.OverrideMaterials = []
        self.Landscapes = []

        self.NPActors = None
        self.NPMaterials = None
        self.NPLandscapes = None

    def __setitem__(self, key: str, value: ndarray):
        if key == 'WORLDACTORS':
            self.NPActors = value
        elif key == 'INSTMATERIAL':
            self.NPMaterials = value
        elif key == 'LANDSCAPE':
            self.NPLandscapes = value

    def finalize(self, settings: dict[str, Property]):
        resize_by: float = settings['resize_by'] if 'resize_by' in settings else 0.01

        self.NumActors = len(self.NPActors)
        self.Actors = [(fix_string_np(x[0]), fix_string_np(x[1]), int(x[2]), Vector(x[3]) * resize_by, Quaternion((x[4][3], x[4][0], x[4][1], x[4][2])), Vector(x[5]), x[6] & 1 == 1, x[6] & 3 == 3) for x in self.NPActors]

        self.OverrideMaterials = [{}] * self.NumActors
        if self.NPMaterials is not None and len(self.NPMaterials) > 0:
            for (actor_id, material_id, material_name) in self.NPMaterials:
                self.OverrideMaterials[actor_id][material_id] = fix_string_np(material_name)

        if self.NPLandscapes is not None and len(self.NPLandscapes) > 0:
            self.Landscapes = [(fix_string_np(x[0]), x[1], Vector((x[2] + x[5] / 2, -(x[3] + x[5] / 2), 0.0)) * resize_by, Vector((x[5], x[5], x[5])) * resize_by, x[4], x[2], x[3], x[5]) for x in self.NPLandscapes]


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
    elif magic == 'ANIXHEAD':
        ob = AnimationV2()
    elif magic == 'ANIMHEAD':
        ob = Animation()
    elif magic == 'WRLDHEAD':
        ob = World()
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
