from typing import Union, Set

import bpy
from bpy.props import StringProperty, CollectionProperty, FloatProperty
from bpy.types import Operator, Context, Property, OperatorFileListElement, TOPBAR_MT_file_import
from bpy_extras.io_utils import ImportHelper
from io_import_pskx.blend.mat import CUEMaterial
from io_import_pskx.utils import find_root_from_path


class op_import_mat(Operator, ImportHelper):
	bl_idname = 'import_material.cuejson'
	bl_label = 'Import CUE JSON Material'
	bl_options = {'REGISTER', 'UNDO'}

	filter_glob: StringProperty(default='*.json', options={'HIDDEN'})

	files: CollectionProperty(
			name='File Path',
			type=OperatorFileListElement,
	)

	base_game_dir: StringProperty(
			name='Asset Directory',
			description='If empty will try to walk directories to find it',
			default='',
			subtype='DIR_PATH'
	)

	def draw(self, context: Context):
		layout = self.layout

		layout.use_property_split = True
		layout.use_property_decorate = True

		layout.prop(self, 'base_game_dir')

	def execute(self, context: Context) -> Union[Set[str], Set[int]]:
		if len(self.base_game_dir) == 0:
			self.base_game_dir = find_root_from_path(self.filepath) or ''
			if len(self.base_game_dir) == 0:
				self.report({'ERROR'}, 'Did not select a game directory')
				return {'CANCELLED'}

		import os

		settings: dict[str, Property] = self.as_keywords()

		if self.files:
			dirname = os.path.dirname(self.filepath)
			ret = {'CANCELLED'}
			for file in self.files:
				path = os.path.join(dirname, file.name)
				if CUEMaterial(path, settings).execute(context) == {'FINISHED'}:
					ret = {'FINISHED'}
			return ret
		else:
			return CUEMaterial(self.filepath, settings).execute(context)
