TIPO_NO_PRINCIPAL = "N"
CUENTA_PRINCIPAL = "S"


def respuesta(mensaje: str, botones=None, data_salida=None):
    return {
        "mensaje": mensaje,
        "botones": botones,
        "data_salida": data_salida or {},
    }
