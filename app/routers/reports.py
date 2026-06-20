from fastapi import APIRouter

from app.schemas import MovementsReportResponse, SummaryReportResponse
from app.services.legacy_finance import get_movements_report, get_summary_report


router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/summary/{periodo}", response_model=SummaryReportResponse)
def summary_report(periodo: str) -> SummaryReportResponse:
    return get_summary_report(periodo)


@router.get("/movements/{periodo}/{moneda}", response_model=MovementsReportResponse)
def movements_report(periodo: str, moneda: str) -> MovementsReportResponse:
    return get_movements_report(periodo, moneda)
