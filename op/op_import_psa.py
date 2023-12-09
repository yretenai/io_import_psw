from typing import Union, Set

import bpy
from bpy.props import StringProperty, CollectionProperty, FloatProperty
from bpy.types import Operator, Context, Property, OperatorFileListElement, TOPBAR_MT_file_import
from bpy_extras.io_utils import ImportHelper
from io_import_pskx.blend.psa import ActorXAnimation


class op_import_psa(Operator, ImportHelper):
    bl_idname = 'import_animation.psa'
    bl_label = 'Import ActorX PSA'
    bl_options = {'REGISTER', 'UNDO'}

    filter_glob: StringProperty(default='*.psa;*.psax', options={'HIDDEN'})

    files: CollectionProperty(
            name='File Path',
            type=OperatorFileListElement,
    )

    resize_by: FloatProperty(
            name='Resize By',
            default=0.01,
            min=0.01,
            max=10.0
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
            ret = {'CANCELLED'}
            for file in self.files:
                path = os.path.join(dirname, file.name)
                if ActorXAnimation(path, settings).execute(context) == {'FINISHED'}:
                    ret = {'FINISHED'}
            return ret
        else:
            return ActorXAnimation(self.filepath, settings).execute(context)
