from typing import Union, Set

import bpy
from bpy.props import StringProperty, CollectionProperty, FloatProperty
from bpy.types import Operator, Context, Property, OperatorFileListElement, TOPBAR_MT_file_import
from bpy_extras.io_utils import ImportHelper
from io_import_pskx.blend.psk import ActorXMesh


class op_import_psk(Operator, ImportHelper):
    bl_idname = 'import_animation.psk'
    bl_label = 'Import ActorX PSK'
    bl_options = {'REGISTER', 'UNDO'}

    filter_glob: StringProperty(default='*.psk;*.pskx', options={'HIDDEN'})

    files: CollectionProperty(
        name='File Path',
        type=OperatorFileListElement,
    )

    resize_by: FloatProperty(
        name='Resize By',
        default=0.01,
        min=0.01,
        soft_max=10.0
    )

    def draw(self, context: Context):
        layout = self.layout

        layout.use_property_split = True
        layout.use_property_decorate = True

        layout.prop(self, 'resize_by')

    def execute(self, context: Context) -> Union[Set[str], Set[int]]:
        import os

        settings: dict[str, Property] = self.as_keywords()

        if self.files:
            dirname = os.path.dirname(self.filepath)
            for file in self.files:
                path = os.path.join(dirname, file.name)
                if ActorXMesh(path, settings).execute(context) == {'FINISHED'}:
                    ret = {'FINISHED'}
            return ret
        else:
            return ActorXMesh(self.filepath, settings).execute(context)


def register():
    bpy.utils.register_class(op_import_psk)
    TOPBAR_MT_file_import.append(operator)


def unregister():
    bpy.utils.unregister_class(op_import_psk)
    TOPBAR_MT_file_import.remove(operator)


def operator(self: Operator, context: Context):
    self.layout.operator(op_import_psk.bl_idname, text='ActorX Mesh (.psk)')
