from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.models import Categoria, Cuenta, Deuda, Moneda, Movimiento, TipoMov, Usuario
from app.db.session import SessionLocal
from app.schemas import DebtCreateRequest, DebtResponse, MovementCreateRequest, MovementResponse, MovementUpdateRequest
from app.services.business_rules import CUENTA_PRINCIPAL
from app.settings import GLOBAL_APP_USER_ID, GLOBAL_APP_USER_NAME


@dataclass
class ResolvedMovementData:
    currency: Moneda
    movement_type: TipoMov
    category: Categoria
    movement_date: date
    source_account_id: int | None
    destination_account_id: int | None
    debt: Deuda | None


ZERO = Decimal('0')


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=404, detail=detail)


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=400, detail=detail)


def _server_error(detail: str) -> HTTPException:
    return HTTPException(status_code=500, detail=detail)


def _load_movement(db: Session, movement_id: int) -> Movimiento:
    movement = db.execute(
        select(Movimiento)
        .options(joinedload(Movimiento.usuario))
        .options(joinedload(Movimiento.moneda_mov))
        .options(joinedload(Movimiento.tipo_mov))
        .options(joinedload(Movimiento.categoria))
        .options(joinedload(Movimiento.deuda))
        .where(Movimiento.id == movement_id)
    ).scalar_one_or_none()
    if not movement:
        raise _not_found('Movimiento no encontrado')
    return movement


def _resolve_currency(db: Session, currency_id: int) -> Moneda:
    currency = db.get(Moneda, currency_id)
    if not currency:
        raise _not_found('Moneda no encontrada')
    return currency


def _resolve_type(db: Session, type_id: int) -> TipoMov:
    movement_type = db.get(TipoMov, type_id)
    if not movement_type:
        raise _not_found('Tipo de movimiento no encontrado')
    return movement_type


def _resolve_category(db: Session, category_id: int) -> Categoria:
    category = db.get(Categoria, category_id)
    if not category:
        raise _not_found('Categoria no encontrada')
    return category


def _resolve_account(db: Session, account_id: int) -> Cuenta:
    account = db.get(Cuenta, account_id)
    if not account:
        raise _not_found('Cuenta no encontrada')
    return account


def _resolve_debt(db: Session, debt_id: int) -> Deuda:
    debt = db.get(Deuda, debt_id)
    if not debt:
        raise _not_found('Deuda no encontrada')
    return debt


def _resolve_or_create_user(db: Session, legacy_user_id: int | None, user_name: str | None) -> Usuario:
    resolved_legacy_user_id = legacy_user_id or GLOBAL_APP_USER_ID
    resolved_user_name = user_name or GLOBAL_APP_USER_NAME

    user = db.execute(select(Usuario).where(Usuario.telegram_id == resolved_legacy_user_id)).scalar_one_or_none()
    if user:
        if not user.nombre and resolved_user_name:
            user.nombre = resolved_user_name
        return user

    user = Usuario(telegram_id=resolved_legacy_user_id, nombre=resolved_user_name)
    db.add(user)
    db.flush()
    return user


def _resolve_main_account(db: Session, currency_id: int) -> Cuenta:
    account = db.execute(
        select(Cuenta)
        .where(Cuenta.id_moneda == currency_id, Cuenta.main == CUENTA_PRINCIPAL)
        .order_by(Cuenta.id)
    ).scalar_one_or_none()
    if not account:
        raise _not_found('No existe una cuenta principal para la moneda seleccionada')
    return account


def _resolve_debt_account(db: Session, currency_id: int) -> Cuenta:
    account = db.execute(
        select(Cuenta)
        .where(Cuenta.id_moneda == currency_id, Cuenta.tipo == 'Deudas')
        .order_by(Cuenta.id)
    ).scalar_one_or_none()
    if not account:
        raise _not_found('No existe una cuenta de deudas para la moneda seleccionada')
    return account


def _resolve_transfer_category(db: Session, type_id: int) -> Categoria:
    category = db.execute(
        select(Categoria)
        .where(Categoria.tipo_id == type_id)
        .order_by(Categoria.id)
    ).scalar_one_or_none()
    if not category:
        raise _bad_request('No hay una categoria de transferencia configurada')
    return category


def _ensure_category_matches_type(category: Categoria, type_id: int) -> None:
    if category.tipo_id != type_id:
        raise _bad_request('La categoria no corresponde al tipo de movimiento seleccionado')


def _validate_transfer_account(account: Cuenta, currency_id: int) -> None:
    if account.id_moneda != currency_id:
        raise _bad_request('La cuenta destino no pertenece a la moneda seleccionada')
    if account.main == CUENTA_PRINCIPAL:
        raise _bad_request('La cuenta destino debe ser una cuenta secundaria')
    if account.estado.lower() != 'activo':
        raise _bad_request('La cuenta destino esta inactiva')


def _apply_debt_payment(debt: Deuda, amount: Decimal, movement_date: date) -> None:
    remaining = Decimal(debt.monto_restante)
    if debt.estado == 'pagado' or remaining <= ZERO:
        raise _bad_request(f'La deuda DEU-{debt.id} ya no tiene saldo pendiente')
    if amount > remaining:
        raise _bad_request(
            f'El pago excede el saldo pendiente de la deuda DEU-{debt.id}. Pendiente actual: {remaining}'
        )

    new_remaining = remaining - amount
    debt.monto_restante = new_remaining
    if new_remaining == ZERO:
        debt.estado = 'pagado'
        debt.fecha_fin = movement_date
    else:
        debt.estado = 'vigente'
        debt.fecha_fin = None


def _revert_debt_payment(debt: Deuda, amount: Decimal) -> None:
    total_amount = Decimal(debt.monto_total)
    current_remaining = Decimal(debt.monto_restante)
    new_remaining = current_remaining + amount
    if new_remaining > total_amount:
        raise _bad_request(
            f'No se puede revertir el pago de la deuda DEU-{debt.id} porque excederia su monto total'
        )

    debt.monto_restante = new_remaining
    debt.estado = 'vigente'
    debt.fecha_fin = None


def _resolve_movement_data(
    db: Session,
    *,
    currency_id: int,
    type_id: int,
    category_id: int | None,
    destination_account_id: int | None,
    debt_id: int | None,
    movement_date: date | None,
) -> ResolvedMovementData:
    currency = _resolve_currency(db, currency_id)
    movement_type = _resolve_type(db, type_id)
    resolved_date = movement_date or date.today()
    main_account = _resolve_main_account(db, currency_id)

    source_account_id: int | None = None
    resolved_destination_account_id: int | None = None
    debt: Deuda | None = None

    if type_id == 1:
        if category_id is None:
            raise _bad_request('category_id es obligatorio para ingresos')
        if destination_account_id is not None:
            raise _bad_request('destination_account_id solo se permite para transferencias')
        if debt_id is not None:
            raise _bad_request('debt_id solo se permite para pagos de deuda')
        category = _resolve_category(db, category_id)
        _ensure_category_matches_type(category, type_id)
        resolved_destination_account_id = main_account.id
    elif type_id == 2:
        if category_id is None:
            raise _bad_request('category_id es obligatorio para gastos')
        if destination_account_id is not None:
            raise _bad_request('destination_account_id solo se permite para transferencias')
        if debt_id is not None:
            raise _bad_request('debt_id solo se permite para pagos de deuda')
        category = _resolve_category(db, category_id)
        _ensure_category_matches_type(category, type_id)
        source_account_id = main_account.id
    elif type_id == 3:
        if destination_account_id is None:
            raise _bad_request('destination_account_id es obligatorio para transferencias')

        category = _resolve_transfer_category(db, type_id)
        source_account_id = main_account.id

        destination_account = _resolve_account(db, destination_account_id)
        _validate_transfer_account(destination_account, currency_id)
        resolved_destination_account_id = destination_account.id

        if destination_account.tipo.lower() == 'deudas':
            if debt_id is None:
                raise _bad_request('debt_id es obligatorio cuando la cuenta destino es Deudas')
            debt = _resolve_debt(db, debt_id)
            if debt.moneda_id != currency_id:
                raise _bad_request('La deuda seleccionada no pertenece a la moneda del movimiento')
            if debt.cuenta_id in (None, destination_account.id):
                debt.cuenta_id = destination_account.id
            elif debt.cuenta_id != destination_account.id:
                raise _bad_request('La deuda seleccionada no pertenece a la cuenta destino elegida')
            if Decimal(debt.monto_restante) <= ZERO or debt.estado == 'pagado':
                raise _bad_request(f'La deuda DEU-{debt.id} ya se encuentra pagada')
        elif debt_id is not None:
            raise _bad_request('debt_id solo se permite cuando la cuenta destino es Deudas')
    else:
        raise _bad_request('type_id no soportado')

    return ResolvedMovementData(
        currency=currency,
        movement_type=movement_type,
        category=category,
        movement_date=resolved_date,
        source_account_id=source_account_id,
        destination_account_id=resolved_destination_account_id,
        debt=debt,
    )


def _serialize_movement(movement: Movimiento, message: str) -> MovementResponse:
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
        debt_id=movement.deuda_id,
        message=message,
    )


def create_movement_service(payload: MovementCreateRequest) -> MovementResponse:
    with SessionLocal() as db:
        try:
            resolved = _resolve_movement_data(
                db,
                currency_id=payload.currency_id,
                type_id=payload.type_id,
                category_id=payload.category_id,
                destination_account_id=payload.destination_account_id,
                debt_id=payload.debt_id,
                movement_date=payload.movement_date,
            )
            user = _resolve_or_create_user(db, payload.legacy_user_id, payload.user_name)

            movement = Movimiento(
                usuario_id=user.id,
                concepto=payload.concept,
                categoria_id=resolved.category.id,
                monto=payload.amount,
                moneda_id=resolved.currency.id,
                tipo_id=resolved.movement_type.id,
                fecha=resolved.movement_date,
                cuenta_origen_id=resolved.source_account_id,
                cuenta_destino_id=resolved.destination_account_id,
                deuda_id=resolved.debt.id if resolved.debt else None,
            )
            db.add(movement)
            db.flush()

            if resolved.debt is not None:
                _apply_debt_payment(resolved.debt, payload.amount, resolved.movement_date)

            db.commit()
            refreshed = _load_movement(db, movement.id)
            return _serialize_movement(
                refreshed,
                (
                    f'Movimiento MOV-{refreshed.id} registrado. '
                    f'Concepto: {refreshed.concepto}. '
                    f'Tipo: {refreshed.tipo_mov.nombre}. '
                    f'Categoria: {refreshed.categoria.nombre}. '
                    f'Moneda: {refreshed.moneda_mov.nombre_corto}. '
                    f'Monto: {refreshed.monto}.'
                ),
            )
        except HTTPException:
            db.rollback()
            raise
        except Exception as exc:
            db.rollback()
            raise _server_error('No se pudo registrar el movimiento') from exc


def update_movement_service(movement_id: int, payload: MovementUpdateRequest) -> MovementResponse:
    with SessionLocal() as db:
        try:
            movement = _load_movement(db, movement_id)
            fields_set = payload.model_fields_set

            final_type_id = payload.type_id if payload.type_id is not None else movement.tipo_id
            final_currency_id = payload.currency_id if payload.currency_id is not None else movement.moneda_id
            final_category_id = payload.category_id if payload.category_id is not None else movement.categoria_id
            final_date = payload.movement_date if payload.movement_date is not None else movement.fecha
            final_concept = payload.concept if payload.concept is not None else movement.concepto
            final_amount = payload.amount if payload.amount is not None else movement.monto

            if final_type_id == 3:
                if 'destination_account_id' in fields_set:
                    final_destination_account_id = payload.destination_account_id
                elif movement.tipo_id == 3:
                    final_destination_account_id = movement.cuenta_destino_id
                else:
                    final_destination_account_id = None

                if 'debt_id' in fields_set:
                    final_debt_id = payload.debt_id
                elif 'destination_account_id' in fields_set and payload.destination_account_id != movement.cuenta_destino_id:
                    final_debt_id = None
                elif movement.tipo_id == 3:
                    final_debt_id = movement.deuda_id
                else:
                    final_debt_id = None
            else:
                final_destination_account_id = None
                final_debt_id = None

            resolved = _resolve_movement_data(
                db,
                currency_id=final_currency_id,
                type_id=final_type_id,
                category_id=final_category_id,
                destination_account_id=final_destination_account_id,
                debt_id=final_debt_id,
                movement_date=final_date,
            )

            previous_debt = movement.deuda
            previous_amount = Decimal(movement.monto)
            new_amount = Decimal(final_amount)
            new_debt = resolved.debt

            if previous_debt is not None:
                debt_changed = new_debt is None or previous_debt.id != new_debt.id or previous_amount != new_amount
                if debt_changed:
                    _revert_debt_payment(previous_debt, previous_amount)

            if new_debt is not None:
                debt_changed = previous_debt is None or previous_debt.id != new_debt.id or previous_amount != new_amount
                if debt_changed:
                    _apply_debt_payment(new_debt, new_amount, resolved.movement_date)

            movement.concepto = final_concept
            movement.monto = new_amount
            movement.moneda_id = resolved.currency.id
            movement.tipo_id = resolved.movement_type.id
            movement.categoria_id = resolved.category.id
            movement.fecha = resolved.movement_date
            movement.cuenta_origen_id = resolved.source_account_id
            movement.cuenta_destino_id = resolved.destination_account_id
            movement.deuda_id = new_debt.id if new_debt else None

            db.commit()
            refreshed = _load_movement(db, movement_id)
            return _serialize_movement(
                refreshed,
                f'Movimiento MOV-{refreshed.id} actualizado correctamente.',
            )
        except HTTPException:
            db.rollback()
            raise
        except Exception as exc:
            db.rollback()
            raise _server_error('No se pudo actualizar el movimiento') from exc


def delete_movement_service(movement_id: int) -> dict[str, str]:
    with SessionLocal() as db:
        try:
            movement = _load_movement(db, movement_id)
            if movement.deuda is not None:
                _revert_debt_payment(movement.deuda, Decimal(movement.monto))

            db.delete(movement)
            db.commit()
            return {'message': f'Movimiento MOV-{movement_id} eliminado correctamente.'}
        except HTTPException:
            db.rollback()
            raise
        except Exception as exc:
            db.rollback()
            raise _server_error('No se pudo eliminar el movimiento') from exc


def create_debt_service(payload: DebtCreateRequest) -> DebtResponse:
    with SessionLocal() as db:
        try:
            currency = _resolve_currency(db, payload.currency_id)
            debt_account = _resolve_debt_account(db, payload.currency_id)
            debt_date = payload.debt_date or date.today()

            debt = Deuda(
                estado='vigente',
                concepto=payload.concept,
                fecha_creacion=debt_date,
                monto_total=payload.amount,
                monto_restante=payload.amount,
                moneda_id=currency.id,
                cuenta_id=debt_account.id,
            )
            db.add(debt)
            db.commit()
            db.refresh(debt)

            return DebtResponse(
                id=debt.id,
                code=f'DEU-{debt.id}',
                concept=debt.concepto,
                amount=debt.monto_total,
                currency_id=currency.id,
                currency_code=currency.nombre_corto,
                debt_date=debt.fecha_creacion,
                status=debt.estado,
            )
        except HTTPException:
            db.rollback()
            raise
        except Exception as exc:
            db.rollback()
            raise _server_error('No se pudo registrar la deuda') from exc