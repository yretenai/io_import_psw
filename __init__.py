from typing import Any


bl_info = {
		'name':        'Import PSW Scene (.psw)',
		'author':      'yretenai',
		'version':     (1, 2, 0),
		'blender':     (4, 0, 0),
		'location':    'File > Import > PSW',
		'description': 'Import PSW Scene files',
		'warning':     '',
		'tracker_url': 'https://github.com/yretenai/io_import_psw/issues',
		'support':     'COMMUNITY',
		'category':    'Import-Export'
}


def reload_package(module_dict_main: dict[str, Any]) -> None:
	from pathlib import Path

	import importlib

	def reload_package_recursive(current_dir: str, module_dict: dict[str, Any]):
		for path in current_dir.iterdir():
			if '__init__' in str(path) or path.stem not in module_dict:
				continue

			if path.is_file() and path.suffix == '.py':
				importlib.reload(module_dict[path.stem])
			elif path.is_dir():
				reload_package_recursive(path, module_dict[path.stem].__dict__)

	reload_package_recursive(Path(__file__).parent, module_dict_main)


if 'op' in locals():
	reload_package(locals())
else:
	from io_import_psw import op


def register():
	op.register()


def unregister():
	op.unregister()


if __name__ == '__main__':
	register()
