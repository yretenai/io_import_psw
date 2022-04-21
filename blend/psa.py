from bpy.types import Property, Context


class ActorXAnimation:
    path: str
    settings: dict[str, Property]

    def __init__(self, path: str, settings: dict[str, Property]):
        self.path = path
        self.settings = settings

    def execute(self, context: Context):
        return {'FINISHED'}
