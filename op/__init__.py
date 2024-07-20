import bpy

from io_import_pskx.op import op_import_psa, op_import_psk, op_import_psw, op_import_mat


class actorx_menu(bpy.types.Menu):
	bl_idname = 'ACTORX_MT_actorx_menu'
	bl_label = 'Select'

	def draw(self, context):
		self.layout.operator(op_import_psk.op_import_psk.bl_idname, text='Mesh (.psk/.pskx)')
		self.layout.operator(op_import_psa.op_import_psa.bl_idname, text='Animation (.psa/.psax)')
		self.layout.operator(op_import_psw.op_import_psw.bl_idname, text='World (.psw)')
		self.layout.operator(op_import_mat.op_import_mat.bl_idname, text='World (.psw)')

	@staticmethod
	def menu_draw(self, context):
		self.layout.menu('ACTORX_MT_actorx_menu', text='ActorX')


def register():
	bpy.utils.register_class(op_import_psk.op_import_psk)
	bpy.utils.register_class(op_import_psa.op_import_psa)
	bpy.utils.register_class(op_import_psw.op_import_psw)
	bpy.utils.register_class(op_import_mat.op_import_mat)
	bpy.utils.register_class(actorx_menu)
	bpy.types.TOPBAR_MT_file_import.append(actorx_menu.menu_draw)


def unregister():
	bpy.types.TOPBAR_MT_file_import.remove(actorx_menu.menu_draw)
	bpy.utils.unregister_class(actorx_menu)
	bpy.utils.unregister_class(op_import_mat.op_import_mat)
	bpy.utils.unregister_class(op_import_psw.op_import_psw)
	bpy.utils.unregister_class(op_import_psa.op_import_psa)
	bpy.utils.unregister_class(op_import_psk.op_import_psk)
