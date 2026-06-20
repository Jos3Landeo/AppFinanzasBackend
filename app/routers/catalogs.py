from fastapi import APIRouter

from app.schemas import AccountItem, BootstrapResponse, CategoryItem, DebtItem
from app.services.legacy_finance import (
    get_bootstrap_catalogs,
    get_categories,
    get_debts,
    get_transfer_accounts,
)


router = APIRouter(prefix="/catalogs", tags=["catalogs"])


@router.get("/bootstrap", response_model=BootstrapResponse)
def bootstrap_catalogs() -> BootstrapResponse:
    return get_bootstrap_catalogs()


@router.get("/types/{type_id}/categories", response_model=list[CategoryItem])
def list_categories(type_id: int) -> list[CategoryItem]:
    return get_categories(type_id)


@router.get("/currencies/{currency_id}/transfer-accounts", response_model=list[AccountItem])
def list_transfer_accounts(currency_id: int) -> list[AccountItem]:
    return get_transfer_accounts(currency_id)


@router.get("/currencies/{currency_id}/debts", response_model=list[DebtItem])
def list_debts(currency_id: int) -> list[DebtItem]:
    return get_debts(currency_id)
