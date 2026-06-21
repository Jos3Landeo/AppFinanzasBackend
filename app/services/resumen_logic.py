from collections import defaultdict
from decimal import Decimal

from app.services.database_service import (
    calcular_resumen_categorias,
    calcular_saldo_periodo_anterior,
    buscar_movimiento_por_periodo,
    encontrar_monto_deudas,
    grupo_deudas,
    obtener_monedas,
    obtener_total_cuentas,
)


def calcular_resumen(year: int, month: int):
    monedas = obtener_monedas()

    saldo_per_anterior = calcular_saldo_periodo_anterior(year, month)
    saldo_inicial = {moneda: saldo or Decimal("0") for moneda, saldo in saldo_per_anterior}

    ingresos = defaultdict(lambda: {m.nombre_corto: Decimal("0") for m in monedas})
    gastos = defaultdict(lambda: {m.nombre_corto: Decimal("0") for m in monedas})
    gastos_chart = {m.nombre_corto: defaultdict(lambda: Decimal("0")) for m in monedas}

    inversiones_per = {m.nombre_corto: Decimal("0") for m in monedas}
    ahorros_per = {m.nombre_corto: Decimal("0") for m in monedas}
    deudas_per = {m.nombre_corto: Decimal("0") for m in monedas}

    total_ingresos = {m.nombre_corto: Decimal("0") for m in monedas}
    total_gastos = {m.nombre_corto: Decimal("0") for m in monedas}
    transferencias_entrantes = {m.nombre_corto: Decimal("0") for m in monedas}

    deudas_balance = {m.nombre_corto: Decimal("0") for m in monedas}
    deudas_mov = {m.nombre_corto: Decimal("0") for m in monedas}
    inversiones_final = {m.nombre_corto: Decimal("0") for m in monedas}
    ahorros_final = {m.nombre_corto: Decimal("0") for m in monedas}

    periodo_completo = calcular_resumen_categorias(year, month)
    deudas_completo = grupo_deudas(year, month)
    deudas_movimiento = encontrar_monto_deudas(year, month)
    cuentas = obtener_total_cuentas(year, month)

    for moneda, tipo, monto in cuentas:
        if tipo == "Inversiones":
            inversiones_final[moneda] += Decimal(monto)
        elif tipo == "Ahorros":
            ahorros_final[moneda] += Decimal(monto)

    for tipo, categoria, moneda, total, cuenta_destino, cuenta_origen in periodo_completo:
        if tipo == "Ingreso":
            ingresos[categoria][moneda] += Decimal(total)
            total_ingresos[moneda] += Decimal(total)
        elif tipo == "Gasto":
            gastos[categoria][moneda] += Decimal(total)
            total_gastos[moneda] += Decimal(total)
            if total > 0:
                gastos_chart[moneda][categoria] += Decimal(total)
        elif tipo == "Transferencia" and cuenta_destino and cuenta_origen:
            if cuenta_destino == "Inversiones":
                inversiones_per[moneda] += Decimal(total)
            elif cuenta_destino == "Ahorros":
                ahorros_per[moneda] += Decimal(total)
            elif cuenta_destino == "Deudas":
                deudas_per[moneda] += Decimal(total)

            if cuenta_origen == "Inversiones":
                transferencias_entrantes[moneda] += Decimal(total)
            elif cuenta_origen == "Ahorros":
                transferencias_entrantes[moneda] += Decimal(total)

    for moneda, total in deudas_completo:
        deudas_balance[moneda] += Decimal(total)

    for moneda, total in deudas_movimiento:
        deudas_mov[moneda] += Decimal(total)

    deudas_final = {
        moneda.nombre_corto: deudas_balance[moneda.nombre_corto] - deudas_mov[moneda.nombre_corto]
        for moneda in monedas
    }
    transferencias = {
        moneda.nombre_corto: (
            inversiones_per[moneda.nombre_corto]
            + ahorros_per[moneda.nombre_corto]
            + deudas_per[moneda.nombre_corto]
        )
        for moneda in monedas
    }
    balance = {
        moneda.nombre_corto: total_ingresos[moneda.nombre_corto] - total_gastos[moneda.nombre_corto]
        for moneda in monedas
    }
    saldo_final = {
        moneda.nombre_corto: saldo_inicial.get(moneda.nombre_corto, Decimal("0"))
        + balance.get(moneda.nombre_corto, Decimal("0"))
        - transferencias.get(moneda.nombre_corto, Decimal("0"))
        + transferencias_entrantes.get(moneda.nombre_corto, Decimal("0"))
        for moneda in monedas
    }

    return {
        "ingresos": ingresos,
        "gastos": gastos,
        "gastos_chart": gastos_chart,
        "totales": {
            "ingresos": total_ingresos,
            "gastos": total_gastos,
            "balance": balance,
            "saldo_inicial": saldo_inicial,
            "saldo_final": saldo_final,
            "inversiones_per": inversiones_per,
            "ahorros_per": ahorros_per,
            "deudas_per": deudas_per,
            "deudas": deudas_final,
            "inversiones": inversiones_final,
            "ahorros": ahorros_final,
        },
    }


def resumen_movimientos_service(year: int, month: int, moneda: str):
    movimientos_ini = buscar_movimiento_por_periodo(year, month, moneda)
    movimientos = []

    for mov in movimientos_ini:
        movimientos.append(
            {
                "fecha": mov[0].strftime("%d-%m-%Y"),
                "descripcion": mov[1],
                "categoria": mov[2],
                "tipo": mov[3],
                "monto": Decimal(mov[4]),
            }
        )

    saldo_inicial_ini = calcular_saldo_periodo_anterior(year, month)
    saldo_inicial_cal = {codigo: saldo or Decimal("0") for codigo, saldo in saldo_inicial_ini}
    saldo_inicial_fin = saldo_inicial_cal[moneda]

    return movimientos, saldo_inicial_fin
