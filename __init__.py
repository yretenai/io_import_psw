from typing import Any


bl_info = {
		'name':        'Import PSW Scene (.psw)',
		'author':      'yretenai',
		'version':     (3, 0, 0),
		'blender':     (4, 0, 0),
		'location':    'File > Import > PSW',
		'description': 'Import PSW Scene files',
		'warning':     '',
		'tracker_url': 'https://github.com/yretenai/io_import_psw/issues',
		'support':     'COMMUNITY',
		'category':    'Import-Export'
}

from . import op

def register():
	op.register()

def unregister():
	op.unregister()

if __name__ == '__main__':
	register()
