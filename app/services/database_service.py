from datetime import date
from decimal import Decimal

from app.db.repositories.categorias_repo import (
    buscar_categoria_por_id,
    buscar_categorias,
    crear_categorias_iniciales,
)
from app.db.repositories.cuentas_repo import crear_cuentas_iniciales, obtener_tipos_trans, total_cuentas
from app.db.repositories.deudas_repo import crear_deuda, obtener_deuda, sumar_deudas
from app.db.repositories.monedas_repo import buscar_monedas, buscar_monedas_por_id, crear_monedas_iniciales
from app.db.repositories.movimientos_repo import (
    actualizar_movimiento,
    borrar_movimiento,
    crear_movimiento,
    encontrar_movimiento_por_id,
    generar_monto_deudas,
    generar_resumen_categorias,
    generar_resumen_movimientos,
    generar_saldo_periodo_anterior,
    listar_movimientos_por_periodo,
)
from app.db.repositories.tipos_repo import buscar_tipos, buscar_tipos_por_id
from app.db.repositories.usuarios_repo import consultar_o_generar_usuario
from app.db.session import SessionLocal


def obtener_categoria_por_id(categoria_id: int):
    with SessionLocal() as db:
        return buscar_categoria_por_id(db=db, categoria_id=categoria_id)


def obtener_categorias(tipo: int):
    with SessionLocal() as db:
        return buscar_categorias(db=db, tipo=tipo)


def obtener_o_crear_usuario(telegram_id: int, nombre: str | None = None):
    with SessionLocal() as db:
        return consultar_o_generar_usuario(db=db, telegram_id=telegram_id, nombre=nombre)


def agregar_movimiento(
    telegram_id: int,
    concepto: str,
    monto: Decimal,
    moneda: int,
    tipo: int,
    fecha: date,
    categoria_id: int,
    cuenta_origen: int | None,
    cuenta_destino: int | None,
):
    with SessionLocal() as db:
        return crear_movimiento(
            db=db,
            telegram_id=telegram_id,
            concepto=concepto,
            monto=monto,
            moneda=moneda,
            tipo=tipo,
            fecha=fecha,
            categoria_id=categoria_id,
            cuenta_origen=cuenta_origen,
            cuenta_destino=cuenta_destino,
        )


def buscar_movimiento_por_id(mov_id: int):
    with SessionLocal() as db:
        return encontrar_movimiento_por_id(db=db, mov_id=mov_id)


def buscar_movimiento_por_periodo(year: int, month: int, moneda: str):
    with SessionLocal() as db:
        return generar_resumen_movimientos(db=db, year=year, month=month, moneda=moneda)


def listar_movimientos_periodo(year: int, month: int, moneda: str | None = None):
    with SessionLocal() as db:
        return listar_movimientos_por_periodo(db=db, year=year, month=month, moneda=moneda)


def modificar_movimiento(
    mov_id: int,
    tipo: int | None = None,
    categoria_id: int | None = None,
    monto: Decimal | None = None,
    moneda: int | None = None,
    concepto: str | None = None,
    fecha: date | None = None,
):
    with SessionLocal() as db:
        return actualizar_movimiento(
            db=db,
            mov_id=mov_id,
            tipo=tipo,
            categoria_id=categoria_id,
            monto=monto,
            moneda=moneda,
            concepto=concepto,
            fecha=fecha,
        )


def eliminar_movimiento(mov_id: int):
    with SessionLocal() as db:
        return borrar_movimiento(db=db, mov_id=mov_id)


def calcular_saldo_periodo_anterior(year: int, month: int):
    with SessionLocal() as db:
        return generar_saldo_periodo_anterior(db=db, year=year, month=month)


def calcular_resumen_categorias(year: int, month: int):
    with SessionLocal() as db:
        return generar_resumen_categorias(db=db, year=year, month=month)


def obtener_total_cuentas(year: int, month: int):
    with SessionLocal() as db:
        return total_cuentas(db=db, year=year, month=month)


def inicializar_tablas():
    with SessionLocal() as db:
        crear_monedas_iniciales(db=db)
        crear_categorias_iniciales(db=db)
        crear_cuentas_iniciales(db=db)


def agregar_deuda(concepto: str, monto: Decimal, moneda_id: int, fecha: date):
    with SessionLocal() as db:
        return crear_deuda(db=db, concepto=concepto, monto=monto, moneda_id=moneda_id, fecha=fecha)


def encontrar_deudas(moneda_id: int):
    with SessionLocal() as db:
        return obtener_deuda(db=db, moneda_id=moneda_id)


def grupo_deudas(year: int, month: int):
    with SessionLocal() as db:
        return sumar_deudas(db=db, year=year, month=month)


def encontrar_monto_deudas(year: int, month: int):
    with SessionLocal() as db:
        return generar_monto_deudas(db=db, year=year, month=month)


def obtener_monedas():
    with SessionLocal() as db:
        return buscar_monedas(db=db)


def obtener_moneda_por_id(moneda_id: int):
    with SessionLocal() as db:
        return buscar_monedas_por_id(db=db, moneda_id=moneda_id)


def obtener_tipos():
    with SessionLocal() as db:
        return buscar_tipos(db=db)


def obtener_tipos_por_id(tipo_id: int):
    with SessionLocal() as db:
        return buscar_tipos_por_id(db=db, tipo_id=tipo_id)


def buscar_tipos_trans(moneda_id: int, main: str):
    with SessionLocal() as db:
        return obtener_tipos_trans(db=db, moneda_id=moneda_id, main=main)
