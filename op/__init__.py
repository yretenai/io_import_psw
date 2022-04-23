from . import op_import_psa
from . import op_import_psk
from . import op_import_psw


def register():
    op_import_psk.register()
    op_import_psa.register()
    op_import_psw.register()


def unregister():
    op_import_psk.unregister()
    op_import_psa.unregister()
    op_import_psw.unregister()
