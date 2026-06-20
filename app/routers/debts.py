from fastapi import APIRouter

from app.schemas import DebtCreateRequest, DebtDetailResponse, DebtResponse
from app.services.legacy_finance import create_debt, get_debt_detail


router = APIRouter(prefix="/debts", tags=["debts"])


@router.post("", response_model=DebtResponse)
def post_debt(payload: DebtCreateRequest) -> DebtResponse:
    return create_debt(payload)


@router.get("/{debt_id}", response_model=DebtDetailResponse)
def get_debt(debt_id: int) -> DebtDetailResponse:
    return get_debt_detail(debt_id)