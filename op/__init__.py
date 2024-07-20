import bpy

from io_import_psw.op import op_import_psw, op_import_mat


class psw_menu(bpy.types.Menu):
	bl_idname = 'PSW_MT_menu'
	bl_label = 'Select'

	def draw(self, context):
		self.layout.operator(op_import_psw.op_import_psw.bl_idname, text='World (.psw)')
		self.layout.operator(op_import_mat.op_import_mat.bl_idname, text='CUEMaterial (.json)')

	@staticmethod
	def menu_draw(self, context):
		self.layout.menu('PSW_MT_menu', text='PSW')


def register():
	bpy.utils.register_class(op_import_psw.op_import_psw)
	bpy.utils.register_class(op_import_mat.op_import_mat)
	bpy.utils.register_class(psw_menu)
	bpy.types.TOPBAR_MT_file_import.append(psw_menu.menu_draw)


def unregister():
	bpy.types.TOPBAR_MT_file_import.remove(psw_menu.menu_draw)
	bpy.utils.unregister_class(psw_menu)
	bpy.utils.unregister_class(op_import_mat.op_import_mat)
	bpy.utils.unregister_class(op_import_psw.op_import_psw)
