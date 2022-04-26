from io_import_pskx.op import op_import_psa
from io_import_pskx.op import op_import_psk
from io_import_pskx.op import op_import_psw


def register():
    op_import_psk.register()
    op_import_psa.register()
    op_import_psw.register()


def unregister():
    op_import_psk.unregister()
    op_import_psa.unregister()
    op_import_psw.unregister()
