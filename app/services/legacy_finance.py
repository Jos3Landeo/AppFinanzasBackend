from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import joinedload

from app.db.models import Categoria, Cuenta, Deuda, Moneda, Movimiento, TipoMov
from app.db.session import SessionLocal
from app.services.business_rules import CUENTA_PRINCIPAL, TIPO_NO_PRINCIPAL
from app.services.database_service import (
    agregar_deuda,
    agregar_movimiento,
    buscar_movimiento_por_id,
    buscar_tipos_trans,
    eliminar_movimiento,
    encontrar_deudas,
    listar_movimientos_periodo,
    modificar_movimiento,
    obtener_categorias,
    obtener_moneda_por_id,
    obtener_monedas,
    obtener_o_crear_usuario,
    obtener_tipos,
    obtener_tipos_por_id,
)
from app.services.movement_accounting import (
    create_debt_service,
    create_movement_service,
    delete_movement_service,
    update_movement_service,
)
from app.services.resumen_logic import calcular_resumen, resumen_movimientos_service
from app.schemas import (
    AccountItem,
    BootstrapResponse,
    CategoryItem,
    CurrencyItem,
    DebtCreateRequest,
    DebtDetailResponse,
    DebtItem,
    DebtPaymentItem,
    DebtResponse,
    ExchangeCreateRequest,
    ExchangeResponse,
    MovementCreateRequest,
    MovementListItem,
    MovementListResponse,
    MovementResponse,
    MovementTypeItem,
    MovementUpdateRequest,
    MovementsReportResponse,
    MovementsReportRow,
    SummaryReportResponse,
    SummarySectionItem,
)
from app.utils.dates import parse_periodo


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=404, detail=detail)


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=400, detail=detail)


def _serialize_decimal(value: Any) -> float:
    if isinstance(value, Decimal):
        return float(value)
    return float(value or 0)


def _serialize_money_map(data: dict[str, Any]) -> dict[str, float]:
    return {key: _serialize_decimal(value) for key, value in data.items()}


def _serialize_summary_rows(data: dict[str, dict[str, Any]]) -> list[SummarySectionItem]:
    rows = []
    for categoria, montos in data.items():
        rows.append(
            SummarySectionItem(
                categoria=categoria,
                montos=_serialize_money_map(dict(montos)),
            )
        )
    return rows


def _serialize_chart_data(data: dict[str, defaultdict[str, Decimal]]) -> dict[str, list[SummarySectionItem]]:
    serializado: dict[str, list[SummarySectionItem]] = {}
    for moneda, categorias in data.items():
        serializado[moneda] = [
            SummarySectionItem(
                categoria=categoria,
                montos={moneda: _serialize_decimal(monto)},
            )
            for categoria, monto in categorias.items()
        ]
    return serializado


def _resolve_account(account_id: int) -> Cuenta:
    with SessionLocal() as db:
        account = db.get(Cuenta, account_id)
        if not account:
            raise _not_found("Cuenta no encontrada")
        return account


def _resolve_category(category_id: int) -> Categoria:
    with SessionLocal() as db:
        category = db.get(Categoria, category_id)
        if not category:
            raise _not_found("CategorÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â­a no encontrada")
        return category


def _resolve_type_by_name(type_name: str) -> TipoMov:
    types = obtener_tipos() or []
    for item in types:
        if item.nombre.lower() == type_name.lower():
            return item
    raise _not_found(f"Tipo de movimiento '{type_name}' no encontrado")


def _resolve_currency_by_code(code: str) -> Moneda:
    currencies = obtener_monedas() or []
    for item in currencies:
        if item.nombre_corto.upper() == code.upper():
            return item
    raise _not_found(f"Moneda '{code}' no encontrada")


def _resolve_change_category_id(type_id: int) -> int:
    categories = obtener_categorias(type_id) or []
    for item in categories:
        if item.nombre.lower() == "cambio moneda":
            return item.id
    raise _not_found("No existe la categorÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â­a 'Cambio Moneda' para ese tipo")


def _resolve_main_account_id(currency_id: int) -> int:
    accounts = buscar_tipos_trans(currency_id, CUENTA_PRINCIPAL) or []
    if not accounts:
        raise _not_found("No existe una cuenta principal para la moneda seleccionada")
    return int(accounts[0].id)


def _fetch_movement_detail(movement_id: int) -> Movimiento:
    with SessionLocal() as db:
        movement = (
            db.query(Movimiento)
            .options(joinedload(Movimiento.usuario))
            .options(joinedload(Movimiento.moneda_mov))
            .options(joinedload(Movimiento.tipo_mov))
            .options(joinedload(Movimiento.categoria))
            .filter(Movimiento.id == movement_id)
            .one_or_none()
        )
        if not movement:
            raise _not_found("Movimiento no encontrado")
        return movement


def _movement_message(
    movement_id: int,
    payload: MovementCreateRequest,
    type_name: str,
    category_name: str,
    currency_code: str,
) -> str:
    return (
        f"Movimiento MOV-{movement_id} registrado. "
        f"Concepto: {payload.concept}. "
        f"Tipo: {type_name}. "
        f"CategorÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â­a: {category_name}. "
        f"Moneda: {currency_code}. "
        f"Monto: {payload.amount}."
    )


def _serialize_movement_entity(movement: Movimiento, message: str = '') -> MovementResponse:
    return MovementResponse(
        id=movement.id,
        legacy_user_id=movement.usuario.telegram_id,
        concept=movement.concepto,
        amount=movement.monto,
        currency_id=movement.moneda_id,
        currency_code=movement.moneda_mov.nombre_corto,
        type_id=movement.tipo_id,
        type_name=movement.tipo_mov.nombre,
        category_id=movement.categoria_id,
        category_name=movement.categoria.nombre,
        movement_date=movement.fecha,
        source_account_id=movement.cuenta_origen_id,
        destination_account_id=movement.cuenta_destino_id,
        message=message,
    )


def _serialize_movement_list_item(movement: Movimiento) -> MovementListItem:
    return MovementListItem(
        id=movement.id,
        legacy_user_id=movement.usuario.telegram_id,
        concept=movement.concepto,
        amount=movement.monto,
        currency_id=movement.moneda_id,
        currency_code=movement.moneda_mov.nombre_corto,
        type_id=movement.tipo_id,
        type_name=movement.tipo_mov.nombre,
        category_id=movement.categoria_id,
        category_name=movement.categoria.nombre,
        movement_date=movement.fecha,
    )


def get_bootstrap_catalogs() -> BootstrapResponse:
    currencies = obtener_monedas() or []
    types = obtener_tipos() or []

    categories_by_type: dict[str, list[CategoryItem]] = {}
    transfer_accounts_by_currency: dict[str, list[AccountItem]] = {}

    for type_item in types:
        categories = obtener_categorias(type_item.id) or []
        categories_by_type[str(type_item.id)] = [
            CategoryItem.model_validate(category) for category in categories
        ]

    for currency in currencies:
        accounts = buscar_tipos_trans(currency.id, TIPO_NO_PRINCIPAL) or []
        transfer_accounts_by_currency[currency.nombre_corto] = [
            AccountItem(id=int(account.id), nombre=account.nombre, tipo=account.tipo)
            for account in accounts
        ]

    return BootstrapResponse(
        monedas=[CurrencyItem.model_validate(currency) for currency in currencies],
        tipos_movimiento=[MovementTypeItem.model_validate(type_item) for type_item in types],
        categorias_por_tipo=categories_by_type,
        cuentas_transferencia_por_moneda=transfer_accounts_by_currency,
    )


def get_categories(type_id: int) -> list[CategoryItem]:
    type_item = obtener_tipos_por_id(type_id)
    if not type_item:
        raise _not_found("Tipo de movimiento no encontrado")
    return [CategoryItem.model_validate(item) for item in (obtener_categorias(type_id) or [])]


def get_transfer_accounts(currency_id: int) -> list[AccountItem]:
    currency = obtener_moneda_por_id(currency_id)
    if not currency:
        raise _not_found("Moneda no encontrada")

    accounts = buscar_tipos_trans(currency_id, TIPO_NO_PRINCIPAL) or []
    return [AccountItem(id=int(account.id), nombre=account.nombre, tipo=account.tipo) for account in accounts]


def get_debts(currency_id: int) -> list[DebtItem]:
    currency = obtener_moneda_por_id(currency_id)
    if not currency:
        raise _not_found("Moneda no encontrada")
    return [DebtItem.model_validate(item) for item in (encontrar_deudas(currency_id) or [])]


def get_debt_detail(debt_id: int) -> DebtDetailResponse:
    with SessionLocal() as db:
        debt = (
            db.query(Deuda)
            .options(joinedload(Deuda.moneda_deuda))
            .filter(Deuda.id == debt_id)
            .one_or_none()
        )
        if not debt:
            raise _not_found("Deuda no encontrada")

        payments = (
            db.query(Movimiento)
            .options(joinedload(Movimiento.moneda_mov))
            .options(joinedload(Movimiento.tipo_mov))
            .filter(Movimiento.deuda_id == debt_id)
            .order_by(Movimiento.fecha.desc(), Movimiento.id.desc())
            .all()
        )

        total_amount = Decimal(debt.monto_total)
        remaining_amount = Decimal(debt.monto_restante)
        paid_amount = total_amount - remaining_amount

        return DebtDetailResponse(
            id=debt.id,
            code=f"DEU-{debt.id}",
            concept=debt.concepto,
            status=debt.estado,
            currency_id=debt.moneda_id,
            currency_code=debt.moneda_deuda.nombre_corto if debt.moneda_deuda else None,
            total_amount=total_amount,
            remaining_amount=remaining_amount,
            paid_amount=paid_amount,
            created_at=debt.fecha_creacion,
            closed_at=debt.fecha_fin,
            payments_count=len(payments),
            payments=[
                DebtPaymentItem(
                    id=movement.id,
                    concept=movement.concepto,
                    amount=movement.monto,
                    currency_code=movement.moneda_mov.nombre_corto,
                    movement_date=movement.fecha,
                    type_name=movement.tipo_mov.nombre,
                )
                for movement in payments
            ],
        )


def create_movement(payload: MovementCreateRequest) -> MovementResponse:
    return create_movement_service(payload)


def update_movement(movement_id: int, payload: MovementUpdateRequest) -> MovementResponse:
    return update_movement_service(movement_id, payload)


def get_movement_detail(movement_id: int) -> MovementResponse:
    movement = _fetch_movement_detail(movement_id)
    return _serialize_movement_entity(
        movement,
        message=f"Movimiento MOV-{movement.id} cargado correctamente.",
    )


def list_movements(periodo: str, moneda: str | None = None) -> MovementListResponse:
    parsed = parse_periodo(periodo)
    if not parsed:
        raise _bad_request("Formato invÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡lido. Usa YYYY-MM")

    currency_filter = moneda.upper() if moneda else None
    if currency_filter:
        _resolve_currency_by_code(currency_filter)

    year, month = parsed
    movimientos = listar_movimientos_periodo(year, month, currency_filter)

    return MovementListResponse(
        periodo=periodo,
        moneda=currency_filter,
        total=len(movimientos),
        movimientos=[_serialize_movement_list_item(movement) for movement in movimientos],
    )


def delete_movement(movement_id: int) -> dict[str, str]:
    return delete_movement_service(movement_id)


def create_debt(payload: DebtCreateRequest) -> DebtResponse:
    return create_debt_service(payload)


def create_exchange(payload: ExchangeCreateRequest) -> ExchangeResponse:
    if payload.source_currency_code.upper() == payload.target_currency_code.upper():
        raise _bad_request("La moneda origen y destino no pueden ser la misma")

    source_currency = _resolve_currency_by_code(payload.source_currency_code)
    target_currency = _resolve_currency_by_code(payload.target_currency_code)
    expense_type = _resolve_type_by_name("Gasto")
    income_type = _resolve_type_by_name("Ingreso")

    source_category_id = _resolve_change_category_id(expense_type.id)
    target_category_id = _resolve_change_category_id(income_type.id)
    source_main_account_id = _resolve_main_account_id(source_currency.id)
    target_main_account_id = _resolve_main_account_id(target_currency.id)
    exchange_date = payload.exchange_date or date.today()

    obtener_o_crear_usuario(payload.legacy_user_id, payload.user_name)

    source_movement_id = agregar_movimiento(
        telegram_id=payload.legacy_user_id,
        concepto=f"Cambio a {target_currency.nombre_corto}",
        monto=payload.source_amount,
        moneda=source_currency.id,
        tipo=expense_type.id,
        fecha=exchange_date.strftime("%Y-%m-%d"),
        categoria_id=source_category_id,
        cuenta_origen=source_main_account_id,
        cuenta_destino=None,
    )
    target_movement_id = agregar_movimiento(
        telegram_id=payload.legacy_user_id,
        concepto=f"Cambio a {target_currency.nombre_corto}",
        monto=payload.target_amount,
        moneda=target_currency.id,
        tipo=income_type.id,
        fecha=exchange_date.strftime("%Y-%m-%d"),
        categoria_id=target_category_id,
        cuenta_origen=None,
        cuenta_destino=target_main_account_id,
    )

    return ExchangeResponse(
        source_movement_id=int(source_movement_id),
        target_movement_id=int(target_movement_id),
        source_currency_code=source_currency.nombre_corto,
        target_currency_code=target_currency.nombre_corto,
        source_amount=payload.source_amount,
        target_amount=payload.target_amount,
        exchange_rate=float(payload.source_amount / payload.target_amount),
        exchange_date=exchange_date,
        message="Cambio registrado correctamente.",
    )


def get_summary_report(periodo: str) -> SummaryReportResponse:
    parsed = parse_periodo(periodo)
    if not parsed:
        raise _bad_request("Formato invÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡lido. Usa YYYY-MM")

    year, month = parsed
    data = calcular_resumen(year, month)

    totals = {
        key: _serialize_money_map(value)
        for key, value in data["totales"].items()
    }

    return SummaryReportResponse(
        periodo=periodo,
        ingresos=_serialize_summary_rows(dict(data["ingresos"])),
        gastos=_serialize_summary_rows(dict(data["gastos"])),
        gastos_chart=_serialize_chart_data(data["gastos_chart"]),
        totales=totals,
    )


def get_movements_report(periodo: str, moneda: str) -> MovementsReportResponse:
    parsed = parse_periodo(periodo)
    if not parsed:
        raise _bad_request("Formato invÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡lido. Usa YYYY-MM")

    year, month = parsed
    movimientos, saldo_inicial = resumen_movimientos_service(year, month, moneda.upper())

    saldo_final = Decimal(saldo_inicial)
    rows: list[MovementsReportRow] = []

    for item in movimientos:
        monto = Decimal(item["monto"])
        if item["tipo"] == "Ingreso":
            saldo_final += monto
        else:
            saldo_final -= monto

        rows.append(
            MovementsReportRow(
                fecha=item["fecha"],
                descripcion=item["descripcion"],
                categoria=item["categoria"],
                tipo=item["tipo"],
                monto=float(monto),
            )
        )

    return MovementsReportResponse(
        periodo=periodo,
        moneda=moneda.upper(),
        saldo_inicial=float(saldo_inicial),
        saldo_final=float(saldo_final),
        movimientos=rows,
    )
