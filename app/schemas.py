from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str
    backend_root: str


class CurrencyItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre_corto: str
    nombre_largo: str
    bandera: str | None = None


class MovementTypeItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str


class CategoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    tipo_id: int


class AccountItem(BaseModel):
    id: int
    nombre: str
    tipo: str


class DebtItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    concepto: str
    estado: str
    monto_total: Decimal
    monto_restante: Decimal
    moneda_id: int | None = None
    fecha_creacion: date


class DebtPaymentItem(BaseModel):
    id: int
    concept: str
    amount: Decimal
    currency_code: str
    movement_date: date
    type_name: str


class DebtDetailResponse(BaseModel):
    id: int
    code: str
    concept: str
    status: str
    currency_id: int | None = None
    currency_code: str | None = None
    total_amount: Decimal
    remaining_amount: Decimal
    paid_amount: Decimal
    created_at: date
    closed_at: date | None = None
    payments_count: int
    payments: list[DebtPaymentItem]


class BootstrapResponse(BaseModel):
    monedas: list[CurrencyItem]
    tipos_movimiento: list[MovementTypeItem]
    categorias_por_tipo: dict[str, list[CategoryItem]]
    cuentas_transferencia_por_moneda: dict[str, list[AccountItem]]


class MovementCreateRequest(BaseModel):
    legacy_user_id: int | None = Field(default=None, description='Temporal. Si no llega, el backend usara un usuario global de la app')
    user_name: str | None = None
    concept: str = Field(..., min_length=1)
    amount: Decimal = Field(..., gt=0)
    currency_id: int
    type_id: int
    category_id: int | None = None
    source_account_id: int | None = None
    destination_account_id: int | None = None
    debt_id: int | None = None
    movement_date: date | None = None


class MovementUpdateRequest(BaseModel):
    concept: str | None = Field(default=None, min_length=1)
    amount: Decimal | None = Field(default=None, gt=0)
    type_id: int | None = None
    category_id: int | None = None
    currency_id: int | None = None
    source_account_id: int | None = None
    destination_account_id: int | None = None
    debt_id: int | None = None
    movement_date: date | None = None


class MovementResponse(BaseModel):
    id: int
    legacy_user_id: int
    concept: str
    amount: Decimal
    currency_id: int
    currency_code: str
    type_id: int
    type_name: str
    category_id: int
    category_name: str
    movement_date: date
    source_account_id: int | None = None
    destination_account_id: int | None = None
    debt_id: int | None = None
    message: str


class MovementListItem(BaseModel):
    id: int
    legacy_user_id: int
    concept: str
    amount: Decimal
    currency_id: int
    currency_code: str
    type_id: int
    type_name: str
    category_id: int
    category_name: str
    movement_date: date
    debt_id: int | None = None


class MovementListResponse(BaseModel):
    periodo: str
    moneda: str | None = None
    total: int
    movimientos: list[MovementListItem]


class DebtCreateRequest(BaseModel):
    concept: str = Field(..., min_length=1)
    amount: Decimal = Field(..., gt=0)
    currency_id: int
    debt_date: date | None = None


class DebtResponse(BaseModel):
    id: int
    code: str
    concept: str
    amount: Decimal
    currency_id: int
    currency_code: str
    debt_date: date
    status: str


class ExchangeCreateRequest(BaseModel):
    legacy_user_id: int
    user_name: str | None = None
    source_currency_code: str
    target_currency_code: str
    source_amount: Decimal = Field(..., gt=0)
    target_amount: Decimal = Field(..., gt=0)
    exchange_date: date | None = None


class ExchangeResponse(BaseModel):
    source_movement_id: int
    target_movement_id: int
    source_currency_code: str
    target_currency_code: str
    source_amount: Decimal
    target_amount: Decimal
    exchange_rate: float
    exchange_date: date
    message: str


class ApiMessage(BaseModel):
    message: str


class SummarySectionItem(BaseModel):
    categoria: str
    montos: dict[str, float]


class SummaryReportResponse(BaseModel):
    periodo: str
    ingresos: list[SummarySectionItem]
    gastos: list[SummarySectionItem]
    gastos_chart: dict[str, list[SummarySectionItem]]
    totales: dict[str, Any]


class MovementsReportRow(BaseModel):
    fecha: str
    descripcion: str
    categoria: str
    tipo: str
    monto: float


class MovementsReportResponse(BaseModel):
    periodo: str
    moneda: str
    saldo_inicial: float
    saldo_final: float
    movimientos: list[MovementsReportRow]
