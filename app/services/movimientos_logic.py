from app.services.business_rules import CUENTA_PRINCIPAL
from app.services.database_service import buscar_tipos_trans, obtener_categorias


def buscar_categoria_transferencia(tipo_id: int):
    categoria_especial = obtener_categorias(tipo_id)
    if not categoria_especial:
        return None
    return categoria_especial[0].id


def obtener_cuentas(tipo_id: int, moneda_id: int):
    cuenta_destino = None
    cuenta_origen = None
    cuenta_busqueda = buscar_tipos_trans(moneda_id, CUENTA_PRINCIPAL)

    if tipo_id == 1:
        cuenta_destino = int(cuenta_busqueda[0].id)
    elif tipo_id in (2, 3):
        cuenta_origen = int(cuenta_busqueda[0].id)

    return cuenta_destino, cuenta_origen
