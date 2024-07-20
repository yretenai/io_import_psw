import bpy
from bpy.types import Material,  Property, Context
from os.path import basename, dirname, sep, normpath, exists
from os.path import join as join_path
import json

class CUEMaterial:
	path: str
	settings: dict[str, Property]
	game_dir: str
	material_data: dict

	def __init__(self, path: str, settings: dict[str, Property]):
		self.path = path
		self.settings = settings
		self.game_dir = self.settings['base_game_dir']

		with open(self.path, 'r') as stream:
			self.material_data = json.load(stream)


	def try_find_texture(self, path: str) -> str or None:
		png_path = normpath(join_path(self.game_dir, path + '.png'))
		if exists(png_path):
			return png_path

		png_path = normpath(join_path(self.game_dir, path + '.0.png'))
		if exists(png_path):
			return png_path

		name = basename(path)
		if not '.' in name:
			return None

		return self.try_find_texture(join_path(dirname(path), name[:name.index('.')]))


	def execute(self, context: Context) -> set[str]:
		return {'FINISHED'} if self.import_material() else {'CANCELLED'}

	def import_material(self) -> Material or None:
		if self.material_data is None or len(self.material_data) == 0:
			return None

		if 'Name' not in self.material_data:
			return None

		name = self.material_data['Name']
		textures = self.material_data.get('Textures', {})
		scalars = self.material_data.get('Scalars', {})
		vectors = self.material_data.get('Vectors', {})
		doubleVectors = self.material_data.get('DoubleVectors', {})
		switches = self.material_data.get('Switches', {})
		masks = self.material_data.get('Masks', {})

		mat = bpy.data.materials.new(name) if name not in bpy.data.materials else bpy.data.materials[name]
		mat.use_nodes = True

		while mat.node_tree.nodes:
			mat.node_tree.nodes.remove(mat.node_tree.nodes[0])

		group_node = mat.node_tree.nodes.new('ShaderNodeGroup')

		out_node = mat.node_tree.nodes.new('ShaderNodeOutputMaterial')
		group_node.location = 10, 300
		out_node.location = 300, 300
		found = False
		for workflow_name in self.material_data.get('Hierarchy', [name]):
			if workflow_name in bpy.data.node_groups:
				found = True
				group_node.node_tree = bpy.data.node_groups[workflow_name]
				mat.node_tree.links.new(group_node.outputs[0], out_node.inputs[0])
				group_node.label = workflow_name
				break

		if not found:
			workflow_name = self.material_data.get('Hierarchy', [name])[0]
			group_node.label = workflow_name
			print('unknown workflow "%s" on material "%s"' % (workflow_name, mat.name))

		x = -750
		y = 300
		height = 300
		mapping_x = -950
		mapping_y = 300
		mapping_height = 750
		uv_x = -1150
		uv_y = 300
		uv_height = 180
		uv_matrix = {}
		mapping_matrix = {}
		for (texture_name, texture_info) in textures.items():
			alpha_node_name = texture_name + ' Alpha'
			texture_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
			texture_node.location = x, y
			texture_node.label = texture_name

			if texture_name in group_node.inputs:
				mat.node_tree.links.new(texture_node.outputs[0], group_node.inputs[texture_name])

			if alpha_node_name in group_node.inputs:
				mat.node_tree.links.new(texture_node.outputs[1], group_node.inputs[alpha_node_name])

			y -= height
			sampling_scale = texture_info['SamplingScale']
			uv_index = int(texture_info['UVChannelIndex'])

			mapping_matrix_key = (uv_index, sampling_scale)
			if mapping_matrix_key not in mapping_matrix:
				if uv_index not in uv_matrix:
					uv_matrix[uv_index] = mat.node_tree.nodes.new('ShaderNodeUVMap')
					uv_node = uv_matrix[uv_index]
					uv_node.uv_map = 'UV%d' % (uv_index)
					uv_node.location = uv_x, uv_y
					uv_y -= uv_height
				uv_node = uv_matrix[uv_index]
				mapping_matrix[mapping_matrix_key] = mat.node_tree.nodes.new('ShaderNodeMapping')
				mapping_node = mapping_matrix[mapping_matrix_key]
				mapping_node.inputs[3].default_value[0] = sampling_scale
				mapping_node.inputs[3].default_value[1] = sampling_scale
				mapping_node.vector_type = 'TEXTURE'
				mapping_node.location = mapping_x, mapping_y
				mapping_y -= mapping_height
				mat.node_tree.links.new(uv_node.outputs[0], mapping_node.inputs[0])

			mat.node_tree.links.new(mapping_matrix[mapping_matrix_key].outputs[0], texture_node.inputs[0])

			result_path = texture_info['Path'].strip('/').strip('\\')

			if sep != '/':
				result_path = result_path.replace('/', sep)

			tex_path = self.try_find_texture(result_path)
			if tex_path is None:
				continue

			real_name = basename(tex_path)
			texture_node.image = bpy.data.images.load(tex_path) if real_name not in bpy.data.images else bpy.data.images[real_name]
			texture_node.image.alpha_mode = 'CHANNEL_PACKED'

		x = -450
		y = 300
		height = 100
		for (scalar_name, scalar_value) in scalars.items():
			value_node = mat.node_tree.nodes.new('ShaderNodeValue')
			value_node.label = scalar_name
			value_node.location = x, y
			value_node.outputs[0].default_value = scalar_value
			if scalar_name in group_node.inputs:
				mat.node_tree.links.new(value_node.outputs[0], group_node.inputs[scalar_name])
			y -= height

		for (scalar_name, scalar_value) in switches.items():
			value_node = mat.node_tree.nodes.new('ShaderNodeValue')
			value_node.label = scalar_name
			value_node.location = x, y
			value_node.outputs[0].default_value = 1.0 if scalar_value else 0.0
			if scalar_name in group_node.inputs:
				mat.node_tree.links.new(value_node.outputs[0], group_node.inputs[scalar_name])
			y -= height

		x = -275
		y = 300
		height2 = 200
		for (vectors_name, vectors_value) in vectors.items():
			value_node = mat.node_tree.nodes.new('ShaderNodeRGB')
			value_node.label = vectors_name
			value_node.location = x, y
			value_node.outputs[0].default_value = (vectors_value['R'], vectors_value['G'], vectors_value['B'], vectors_value['A'])
			if vectors_name in group_node.inputs:
				mat.node_tree.links.new(value_node.outputs[0], group_node.inputs[vectors_name])
			y -= height2

			alpha_node_name = vectors_name + ' Alpha'
			value_node = mat.node_tree.nodes.new('ShaderNodeValue')
			value_node.label = alpha_node_name
			value_node.location = x, y
			value_node.outputs[0].default_value = vectors_value['A']
			if alpha_node_name in group_node.inputs:
				mat.node_tree.links.new(value_node.outputs[0], group_node.inputs[alpha_node_name])
			y -= height

		height2 = 200
		for (vectors_name, vectors_value) in doubleVectors.items():
			value_node = mat.node_tree.nodes.new('ShaderNodeCombineXYZ')
			value_node.label = vectors_name
			value_node.location = x, y
			value_node.outputs[0].default_value = vectors_value['X']
			value_node.outputs[1].default_value = vectors_value['Y']
			value_node.outputs[2].default_value = vectors_value['Z']
			if vectors_name in group_node.inputs:
				mat.node_tree.links.new(value_node.outputs[0], group_node.inputs[vectors_name])
			y -= height2

			alpha_node_name = vectors_name + ' Alpha'
			value_node = mat.node_tree.nodes.new('ShaderNodeValue')
			value_node.label = alpha_node_name
			value_node.location = x, y
			value_node.outputs[0].default_value = vectors_value['W']
			if alpha_node_name in group_node.inputs:
				mat.node_tree.links.new(value_node.outputs[0], group_node.inputs[alpha_node_name])
			y -= height

		return mat

