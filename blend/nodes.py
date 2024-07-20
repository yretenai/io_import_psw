import bpy
import os.path


def register():
	path = os.path.join(os.path.dirname(__file__), 'nodes.blend')
	if os.path.exists(path):
		with bpy.data.libraries.load(path, link=False, relative=True) as (data_from, data_to):
			data_to.node_groups = [node_name for node_name in data_from.node_groups if node_name not in bpy.data.node_groups and node_name.startswith('PSW ')]
		blocks = [node for node in bpy.data.node_groups if node.name.startswith('PSW ')]
		for block in blocks:
			bpy.data.node_groups[block.name].use_fake_user = True


def create():
	path = os.path.join(os.path.dirname(__file__), 'nodes.blend')
	blocks = set([node for node in bpy.data.node_groups if node.name.startswith('PSW ')])
	for node in blocks:
		bpy.data.node_groups[node.name].use_fake_user = True
	bpy.data.libraries.write(path, blocks, fake_user=True, path_remap='RELATIVE_ALL', compress=False)
	return blocks


def unregister():
	keys = bpy.data.node_groups.keys()
	for key in keys:
		if key.startswith('PSW '):
			bpy.data.node_groups.remove(bpy.data.node_groups[key])
