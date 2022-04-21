from . import op_import_psa
from . import op_import_psk


def register():
    op_import_psk.register()
    op_import_psa.register()


def unregister():
    op_import_psk.unregister()
    op_import_psa.unregister()
