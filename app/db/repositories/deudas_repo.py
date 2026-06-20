from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import DatabaseError
from app.db.models import Deuda, Moneda


def crear_deuda(
    db: Session,
    concepto: str,
    monto: Decimal,
    moneda_id: int,
    fecha: date,
) -> int:
    deuda = Deuda(
        estado="vigente",
        concepto=concepto,
        monto_total=monto,
        monto_restante=monto,
        moneda_id=moneda_id,
        fecha_creacion=fecha,
    )
    try:
        db.add(deuda)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise DatabaseError("Error al guardar la deuda") from exc

    return deuda.id


def obtener_deuda(db: Session, moneda_id: int):
    return db.execute(
        select(Deuda).where(Deuda.moneda_id == moneda_id).order_by(Deuda.id)
    ).scalars().all()


def sumar_deudas(db: Session, year: int, month: int):
    inicio = date(year, month, 1)
    return db.execute(
        select(Moneda.nombre_corto, func.sum(Deuda.monto_total).label("total"))
        .join(Moneda, Moneda.id == Deuda.moneda_id)
        .where(
            Deuda.fecha_creacion < inicio,
            func.coalesce(Deuda.fecha_fin, date(1900, 1, 1)) < inicio,
        )
        .group_by(Moneda.nombre_corto)
    ).all()
