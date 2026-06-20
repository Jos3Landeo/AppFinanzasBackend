from fastapi import APIRouter, Query

from app.schemas import ApiMessage, ExchangeCreateRequest, ExchangeResponse, MovementCreateRequest, MovementListResponse, MovementResponse, MovementUpdateRequest
from app.services.legacy_finance import create_exchange, create_movement, delete_movement, get_movement_detail, list_movements, update_movement


router = APIRouter(prefix="/movements", tags=["movements"])


@router.post("", response_model=MovementResponse)
def post_movement(payload: MovementCreateRequest) -> MovementResponse:
    return create_movement(payload)


@router.get("", response_model=MovementListResponse)
def get_movements(periodo: str = Query(...), moneda: str | None = Query(default=None)) -> MovementListResponse:
    return list_movements(periodo, moneda)


@router.get("/{movement_id}", response_model=MovementResponse)
def get_movement(movement_id: int) -> MovementResponse:
    return get_movement_detail(movement_id)


@router.patch("/{movement_id}", response_model=MovementResponse)
def patch_movement(movement_id: int, payload: MovementUpdateRequest) -> MovementResponse:
    return update_movement(movement_id, payload)


@router.delete("/{movement_id}", response_model=ApiMessage)
def delete_movement_route(movement_id: int) -> ApiMessage:
    return ApiMessage(**delete_movement(movement_id))


@router.post("/exchange", response_model=ExchangeResponse)
def post_exchange(payload: ExchangeCreateRequest) -> ExchangeResponse:
    return create_exchange(payload)
