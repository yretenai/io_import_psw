from os.path import basename, splitext, sep, normpath, exists
from os.path import join as join_path

import bpy.types
import io_import_pskx.utils as utils
from bpy.types import Property, Context, Collection
from io_import_pskx.io import read_actorx, World, DataType

from .psk import ActorXMesh


class ActorXWorld:
    path: str
    settings: dict[str, Property]
    resize_mod: float
    game_dir: str
    psw: World | None
    name: str

    def __init__(self, path: str, settings: dict[str, Property]):
        self.path = path
        self.name = splitext(basename(path))[0]
        self.settings = settings
        self.resize_mod = self.settings['resize_by']
        self.game_dir = self.settings['base_game_dir']

        with open(self.path, 'rb') as stream:
            self.psw = read_actorx(stream, settings)

    def execute(self, context: Context) -> set[str]:
        if self.psw is None or self.psw.TYPE != DataType.World:
            return {'CANCELLED'}

        if len(self.game_dir) == 0:
            return {'CANCELLED'}

        world_collection = bpy.data.collections.new(self.name)
        context.collection.children.link(world_collection)
        world_layer = context.view_layer.active_layer_collection.children[-1]

        actor_collection = bpy.data.collections.new(self.name + " Actors")
        actor_collection.hide_render = True
        actor_collection.hide_select = True
        actor_collection.hide_viewport = True
        world_collection.children.link(actor_collection)
        actor_layer = world_layer.children[-1]

        old_active_layer = context.view_layer.active_layer_collection

        mesh_cache: dict[tuple[str, frozenset], Collection] = {}

        actor_cache: list[Collection] = [None] * self.psw.NumActors

        # todo: landscapes

        for actor_id, (name, psk_path, parent, pos, rot, scale, no_shadow, hidden) in enumerate(self.psw.Actors):
            mesh_key = (psk_path, frozenset(self.psw.OverrideMaterials[actor_id].items()))

            if mesh_key in mesh_cache:
                mesh_obj = mesh_cache[mesh_key]
            else:
                if not psk_path.endswith('.psk'):
                    psk_path += ".psk"

                if sep != '/':
                    psk_path = psk_path.replace('/', sep)

                result_path = normpath(join_path(self.game_dir, psk_path))

                if not exists(result_path):
                    result_path += 'x'
                    if not exists(result_path):
                        continue

                import_settings = self.settings.copy()
                import_settings['override_materials'] = self.psw.OverrideMaterials[actor_id]
                psk = ActorXMesh(result_path, import_settings)

                mesh_obj = bpy.data.collections.new(psk.name)
                actor_collection.children.link(mesh_obj)
                context.view_layer.active_layer_collection = actor_layer.children[-1]

                psk.execute(context)
                mesh_cache[mesh_key] = mesh_obj

            instance = bpy.data.objects.new(name, None)
            instance.location = pos
            instance.rotation_mode = 'QUATERNION'
            instance.rotation_quaternion = rot
            instance.scale = scale
            instance.instance_type = 'COLLECTION'
            instance.instance_collection = mesh_obj

            if no_shadow:
                instance.visible_shadow = False

            if hidden:
                instance.hide_render = True
                instance.show_instancer_for_render = False

            if parent > -1:
                instance.parent = actor_cache[parent]

            actor_cache[actor_id] = instance

            world_collection.objects.link(instance)

        context.view_layer.active_layer_collection = old_active_layer

        return {'FINISHED'}
