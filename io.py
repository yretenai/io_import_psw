import typing
from struct import unpack

import numpy
from bpy.types import Property
from io_import_psw.utils import fix_string_np, fix_string, log_error
from mathutils import Quaternion, Vector, Color
from numpy import dtype, ndarray
from numpy.typing import DTypeLike


dispatch: dict[str, DTypeLike] = {
		'WORLDACTORS::3': dtype([('name', '256b'), ('asset', '256b'), ('parent', 'i'), ('pos', '3f'), ('rot', '4f'), ('scale', '3f'), ('flags', 'i'), ('material_start', 'i'), ('material_len', 'i')]),
		'WORLDACTORS::2': dtype([('name', '256b'), ('asset', '256b'), ('parent', 'i'), ('pos', '3f'), ('rot', '4f'), ('scale', '3f'), ('flags', 'i')]),
		'WORLDACTORS':  dtype([('name', '64b'), ('asset', '256b'), ('parent', 'i'), ('pos', '3f'), ('rot', '4f'), ('scale', '3f'), ('flags', 'i')]),
		'WORLDLIGHTS':  dtype([('parent', 'i'), ('color', '4B'), ('type', 'i'), ('whl', '3f'), ('attenuation', 'f'), ('radius', 'f'), ('temp', 'f'), ('bias', 'f'), ('lumens', 'f'), ('angle', 'f')]),
		'LANDSCAPE':    dtype([('name', '256b'), ('actor_id', 'i'), ('x', 'i'), ('y', 'i'), ('type', 'i'), ('size', 'i'), ('bias', 'i'), ('offset', '2f'), ('dim', '2i')]),
		'INSTMATERIAL::2': dtype([('actor_id', 'i'), ('material_id', 'i'), ('name', '256b')]),
		'INSTMATERIAL': dtype([('actor_id', 'i'), ('material_id', 'i'), ('name', '64b')]),
		'ACTORMATERIALS': dtype([('name', '256b'), ('asset', '256b')]),
}


class World:
	NumActors: int

	Actors: list[tuple[str, str, int, Vector, Quaternion, Vector, bool, bool, bool, bool, int, int]]  # bools = no shadow, hidden, use_temp, is_static
	Lights: list[tuple[int, Color, int, Vector, float, float, float, float, float, float]]
	Materials: list[tuple[str, str]]
	Landscapes: list[tuple[str, int, Vector, int, int, int, int, float, Vector, Vector]]  # name, actor, pos, size, type, x, y, bias, offset, dim

	NPActors: ndarray
	NPLights: ndarray
	NPMaterials: ndarray | None
	NPLandscapes: ndarray | None
	NPActorsVer: int

	def __init__(self):
		self.NumActors = 0

		self.Actors = []
		self.Lights = []
		self.Materials = []
		self.Landscapes = []

		self.NPActors = None
		self.NPLights = None
		self.NPMaterials = None
		self.NPLandscapes = None
		self.NPActorsVer = 0

	def __setitem__(self, key: str, value: ndarray):
		if key == 'WORLDACTORS' or key == 'WORLDACTORS::2' or key == 'WORLDACTORS::3':
			self.NPActorsVer = 1 if key == 'WORLDACTORS::3' else 0
			self.NPActors = value
		elif key == 'WORLDLIGHTS':
			self.NPLights = value
		elif key == 'INSTMATERIAL' or key == 'INSTMATERIAL::2':
			pass
		elif key == 'ACTORMATERIALS':
			self.NPMaterials = value
		elif key == 'LANDSCAPE':
			self.NPLandscapes = value
		else:
			log_error('PSW', 'Unhandled chunk %s' % (key))

	def finalize(self, settings: dict[str, Property]):
		resize_by: float = settings['resize_by'] if 'resize_by' in settings else 0.01

		if self.NPActors is not None and len(self.NPActors) > 0:
			self.NumActors = len(self.NPActors)
			"""
			x[6] =
				1 = NoShadow
				2 = Hidden
				4 = UseTemperature
				8 = IsSkeleton
			"""
			self.Actors = [(fix_string_np(x[0]), fix_string_np(x[1]), int(x[2]), Vector(x[3]) * resize_by, Quaternion((x[4][3], x[4][0], x[4][1], x[4][2])), Vector(x[5]), x[6] & 1 == 1, x[6] & 2 == 2, x[6] & 4 == 4, x[6] & 8 == 0, x[7] if self.NPActorsVer >= 1 else 0, x[8] if self.NPActorsVer >= 1 else 0) for x in self.NPActors]

			if self.NPLights is not None and len(self.NPLights) > 0:
				self.Lights = [(x['parent'], Color((x['color'][0] / 255, x['color'][1] / 255, x['color'][2] / 255)), int(x['type']), Vector(x['whl']) * resize_by, x['attenuation'], x['radius'], x['temp'], x['bias'], x['lumens'], x['angle']) for x in self.NPLights]

			if self.NPMaterials is not None and len(self.NPMaterials) > 0:
				self.Materials = [(fix_string_np(x['name']), fix_string_np(x['asset'])) for x in self.NPMaterials]

		if self.NPLandscapes is not None and len(self.NPLandscapes) > 0:
			self.Landscapes = [(fix_string_np(x['name']), x['actor_id'], Vector((x['x'], -x['y'], 0)), int(x['size']), x['type'], x['x'], x['y'], x['bias'], Vector((x['offset'][0], x['offset'][1], 0.0)), Vector((x['dim'][0], x['dim'][1], 1.0))) for x in self.NPLandscapes]


def read_chunk(stream: typing.BinaryIO) -> tuple[ndarray | None, str]:
	(chunk_id, chunk_type, chunk_size, chunk_count) = unpack('20s3i', stream.read(32))
	chunk_id = fix_string(chunk_id)
	total_size = chunk_size * chunk_count

	for chunk_key in dispatch.keys():
		if chunk_key == chunk_id or chunk_id.startswith(chunk_key):
			return (numpy.fromfile(stream, dtype=dispatch[chunk_key], count=chunk_count), chunk_id)

	log_error('PSW', 'No parser found for %s!' % (chunk_id))

	stream.seek(total_size, 1)

	return (None, chunk_id)


def read_file(stream: typing.BinaryIO, settings: dict[str, Property]) -> World | None:
	ob = None
	magic = fix_string(unpack('20s', stream.read(20))[0])
	if magic == 'WRLDHEAD':
		ob = World()
	else:
		return None
	stream.seek(0, 2)
	size = stream.tell()
	stream.seek(32, 0)
	while stream.tell() < size:
		(data, name) = read_chunk(stream)
		if data is not None:
			ob[name] = data

	ob.finalize(settings)

	return ob
