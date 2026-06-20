from datetime import date
from decimal import Decimal

from sqlalchemy import and_, case, delete, func, select, update
from sqlalchemy.orm import Session, aliased, joinedload

from app.core.exceptions import DatabaseError
from app.db.models import Categoria, Cuenta, Moneda, Movimiento, TipoMov, Usuario


def crear_movimiento(
    db: Session,
    telegram_id: int,
    concepto: str,
    monto: Decimal,
    moneda: int,
    tipo: int,
    fecha: date,
    categoria_id: int,
    cuenta_origen: int | None,
    cuenta_destino: int | None,
) -> int:
    usuario = db.execute(select(Usuario).where(Usuario.telegram_id == telegram_id)).scalar_one()

    movimiento = Movimiento(
        usuario_id=usuario.id,
        concepto=concepto,
        monto=monto,
        moneda_id=moneda,
        tipo_id=tipo,
        fecha=fecha,
        categoria_id=categoria_id,
        cuenta_origen_id=cuenta_origen,
        cuenta_destino_id=cuenta_destino,
    )

    try:
        db.add(movimiento)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise DatabaseError("Error al crear movimiento") from exc

    return movimiento.id


def encontrar_movimiento_por_id(db: Session, mov_id: int):
    return db.execute(
        select(Movimiento)
        .options(joinedload(Movimiento.usuario))
        .options(joinedload(Movimiento.tipo_mov))
        .options(joinedload(Movimiento.categoria))
        .options(joinedload(Movimiento.moneda_mov))
        .where(Movimiento.id == mov_id)
    ).scalar_one_or_none()


def listar_movimientos_por_periodo(db: Session, year: int, month: int, moneda: str | None = None):
    inicio = date(year, month, 1)
    fin = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)

    query = (
        select(Movimiento)
        .options(joinedload(Movimiento.usuario))
        .options(joinedload(Movimiento.tipo_mov))
        .options(joinedload(Movimiento.categoria))
        .options(joinedload(Movimiento.moneda_mov))
        .where(
            Movimiento.fecha >= inicio,
            Movimiento.fecha < fin,
        )
        .order_by(Movimiento.fecha.desc(), Movimiento.id.desc())
    )

    if moneda:
        query = query.join(Moneda, Movimiento.moneda_id == Moneda.id).where(Moneda.nombre_corto == moneda)

    return db.execute(query).scalars().all()


def generar_resumen_movimientos(db: Session, year: int, month: int, moneda: str):
    inicio = date(year, month, 1)
    fin = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)

    return db.execute(
        select(
            Movimiento.fecha,
            Movimiento.concepto,
            Categoria.nombre,
            TipoMov.nombre,
            Movimiento.monto,
        )
        .join(Categoria, Movimiento.categoria_id == Categoria.id)
        .join(Moneda, Movimiento.moneda_id == Moneda.id)
        .join(TipoMov, Movimiento.tipo_id == TipoMov.id)
        .where(
            Movimiento.fecha >= inicio,
            Movimiento.fecha < fin,
            Moneda.nombre_corto == moneda,
        )
        .order_by(Movimiento.fecha)
    ).all()


def actualizar_movimiento(
    db: Session,
    mov_id: int,
    tipo: int | None = None,
    categoria_id: int | None = None,
    monto: Decimal | None = None,
    moneda: int | None = None,
    concepto: str | None = None,
    fecha: date | None = None,
):
    campos_actualizar = {}

    if tipo is not None:
        campos_actualizar["tipo_id"] = tipo
    if categoria_id is not None:
        campos_actualizar["categoria_id"] = categoria_id
    if monto is not None:
        campos_actualizar["monto"] = monto
    if concepto is not None:
        campos_actualizar["concepto"] = concepto
    if moneda is not None:
        campos_actualizar["moneda_id"] = moneda
    if fecha is not None:
        campos_actualizar["fecha"] = fecha

    if not campos_actualizar:
        return None

    resultado = db.execute(update(Movimiento).where(Movimiento.id == mov_id).values(**campos_actualizar))
    if resultado.rowcount == 0:
        return False

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise DatabaseError("Error al actualizar movimiento") from exc

    return True


def borrar_movimiento(db: Session, mov_id: int):
    resultado = db.execute(delete(Movimiento).where(Movimiento.id == mov_id))
    if resultado.rowcount == 0:
        return False

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise DatabaseError("Error al borrar movimiento") from exc

    return True


def generar_saldo_periodo_anterior(db: Session, year: int, month: int):
    inicio = date(year, month, 1)
    return db.execute(
        select(
            Moneda.nombre_corto,
            func.coalesce(
                func.sum(
                    case(
                        (Movimiento.tipo_id == 1, Movimiento.monto),
                        (Movimiento.tipo_id == 2, -Movimiento.monto),
                        (
                            Movimiento.tipo_id == 3,
                            case((Cuenta.main == "S", -Movimiento.monto), else_=Movimiento.monto),
                        ),
                    )
                ),
                0,
            ).label("saldo"),
        )
        .select_from(Moneda)
        .outerjoin(Movimiento, and_(Movimiento.moneda_id == Moneda.id, Movimiento.fecha < inicio))
        .outerjoin(Cuenta, Movimiento.cuenta_origen_id == Cuenta.id)
        .group_by(Moneda.nombre_corto)
    ).all()


def generar_resumen_categorias(db: Session, year: int, month: int):
    cuenta_destino = aliased(Cuenta)
    cuenta_origen = aliased(Cuenta)

    inicio = date(year, month, 1)
    fin = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)

    return db.execute(
        select(
            TipoMov.nombre,
            Categoria.nombre,
            Moneda.nombre_corto,
            func.coalesce(func.sum(Movimiento.monto), 0).label("total"),
            cuenta_destino.tipo.label("cuenta_destino_tipo"),
            cuenta_origen.tipo.label("cuenta_origen_tipo"),
        )
        .select_from(Moneda)
        .outerjoin(
            Movimiento,
            and_(Movimiento.moneda_id == Moneda.id, Movimiento.fecha >= inicio, Movimiento.fecha < fin),
        )
        .join(Categoria, Movimiento.categoria_id == Categoria.id)
        .join(TipoMov, TipoMov.id == Movimiento.tipo_id)
        .outerjoin(cuenta_destino, Movimiento.cuenta_destino_id == cuenta_destino.id)
        .outerjoin(cuenta_origen, Movimiento.cuenta_origen_id == cuenta_origen.id)
        .group_by(
            TipoMov.nombre,
            Categoria.nombre,
            Moneda.nombre_corto,
            cuenta_destino.tipo,
            cuenta_origen.tipo,
        )
    ).all()


def generar_monto_deudas(db: Session, year: int, month: int):
    inicio = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)

    return db.execute(
        select(Moneda.nombre_corto, func.sum(Movimiento.monto).label("total"))
        .join(Moneda, Moneda.id == Movimiento.moneda_id)
        .join(Cuenta, Cuenta.id == Movimiento.cuenta_destino_id)
        .where(Movimiento.fecha < inicio, Cuenta.tipo == "Deudas")
        .group_by(Moneda.nombre_corto)
    ).all()
