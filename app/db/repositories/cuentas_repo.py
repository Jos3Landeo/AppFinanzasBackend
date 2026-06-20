from datetime import date

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.db.models import Cuenta, Moneda, Movimiento
from app.settings import CUENTAS_INICIALES


def crear_cuentas_iniciales(db: Session):
    for tipo, (nombre, estado, moneda, main) in CUENTAS_INICIALES.items():
        moneda_id = db.scalar(select(Moneda.id).where(Moneda.nombre_corto == moneda))
        if not moneda_id:
            raise ValueError(f"No existe la moneda '{moneda}'")

        existe = db.scalar(select(Cuenta).where(Cuenta.tipo == tipo, Cuenta.id_moneda == moneda_id))
        if not existe:
            db.add(Cuenta(nombre=nombre, tipo=tipo, estado=estado, id_moneda=moneda_id, main=main))

    db.commit()


def total_cuentas(db: Session, year: int, month: int):
    inicio = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)

    saldo_expr = func.coalesce(
        func.sum(
            case(
                (Movimiento.cuenta_destino_id == Cuenta.id, Movimiento.monto),
                (Movimiento.cuenta_origen_id == Cuenta.id, -Movimiento.monto),
                else_=0,
            )
        ),
        0,
    )

    query = (
        select(Moneda.nombre_corto, Cuenta.tipo, saldo_expr.label("saldo"))
        .outerjoin(
            Movimiento,
            or_(Movimiento.cuenta_destino_id == Cuenta.id, Movimiento.cuenta_origen_id == Cuenta.id),
        )
        .join(Moneda, Moneda.id == Cuenta.id_moneda)
        .where(
            Movimiento.fecha < inicio,
            Cuenta.main != "S",
            Cuenta.tipo.in_(["Inversiones", "Ahorros"]),
        )
        .group_by(Moneda.nombre_corto, Cuenta.tipo)
        .order_by(Moneda.nombre_corto, Cuenta.tipo)
    )
    return db.execute(query).all()


def obtener_tipos_trans(db: Session, moneda_id: int, main: str):
    return db.execute(
        select(Cuenta.nombre, Cuenta.id, Cuenta.tipo)
        .where(Cuenta.id_moneda == moneda_id, Cuenta.main == main)
        .group_by(Cuenta.tipo, Cuenta.id, Cuenta.nombre)
    ).all()
