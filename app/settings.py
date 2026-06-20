from pathlib import Path

from dotenv import load_dotenv
import os


BACKEND_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = BACKEND_ROOT / ".env"

load_dotenv(ENV_FILE)

API_TITLE = "Bot Celular Backend"
API_VERSION = "0.1.0"
API_PREFIX = "/api/v1"

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        f"DATABASE_URL no estÃ¡ configurado. Crea {ENV_FILE} basÃ¡ndote en .env.example"
    )

CATEGORIAS_INICIALES = {
    "Ingreso": [
        "Sueldo Jose",
        "Sueldo Luz",
        "Bono",
        "Otros",
        "Cambio Moneda",
    ],
    "Gasto": [
        "Supermercado",
        "Transporte",
        "Internet",
        "Vivienda",
        "Electricidad",
        "DiversiÃ³n",
        "Medicina",
        "Plan Celular",
        "Medicamentos",
        "Cambio Moneda",
        "Tarjeta Credito",
        "Deudas",
        "Inversiones",
        "Ahorros",
        "Otros",
    ],
    "Transferencia": [
        "Ninguno",
    ],
}

MONEDAS_INICIALES = {
    "CLP": ("Peso Chileno", "ðŸ‡¨ðŸ‡±"),
    "RD": ("Peso Dominicano", "ðŸ‡©ðŸ‡´"),
}

CUENTAS_INICIALES = {
    "Inversiones": ("Inversiones", "activo", "CLP", "N"),
    "Deudas": ("Deudas CLP", "activo", "CLP", "N"),
    "Ahorros": ("Ahorros", "activo", "CLP", "N"),
    "Efectivo": ("Efectivo CLP", "activo", "CLP", "S"),
}

GLOBAL_APP_USER_ID = 999999001
GLOBAL_APP_USER_NAME = 'Bot Celular Global'
