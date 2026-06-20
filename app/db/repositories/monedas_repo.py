from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import Moneda
from app.settings import MONEDAS_INICIALES


def crear_monedas_iniciales(db: Session):
    for codigo, (nombre_largo, bandera) in MONEDAS_INICIALES.items():
        consulta = db.scalar(select(Moneda).where(Moneda.nombre_corto == codigo))
        if not consulta:
            db.add(Moneda(nombre_corto=codigo, nombre_largo=nombre_largo, bandera=bandera))

    db.commit()


def buscar_monedas(db: Session):
    return db.query(Moneda).order_by(desc(Moneda.id)).all() or []


def buscar_monedas_por_id(db: Session, moneda_id: int):
    return db.get(Moneda, moneda_id)
