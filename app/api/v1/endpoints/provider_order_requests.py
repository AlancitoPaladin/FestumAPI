from fastapi import APIRouter, Depends, Query

from app.api.dependencies.provider import get_current_provider
from app.schemas.provider_order_request import (
    ProviderOrderRequestDecisionPayload,
    ProviderOrderRequestDecisionResponse,
    ProviderOrderRequestListResponse,
)
from app.schemas.user import UserResponse
from app.services.provider_order_request_service import ProviderOrderRequestService

router = APIRouter()


@router.get("/me/order-requests", response_model=ProviderOrderRequestListResponse)
def list_my_order_requests(
    status: str | None = Query(default="pending_provider_approval"),
    service: ProviderOrderRequestService = Depends(ProviderOrderRequestService),
    current_provider: UserResponse = Depends(get_current_provider),
) -> ProviderOrderRequestListResponse:
    return service.list_requests(current_provider.id, status=status)


@router.patch("/me/order-requests/{request_id}/decision", response_model=ProviderOrderRequestDecisionResponse)
def decide_my_order_request(
    request_id: str,
    payload: ProviderOrderRequestDecisionPayload,
    service: ProviderOrderRequestService = Depends(ProviderOrderRequestService),
    current_provider: UserResponse = Depends(get_current_provider),
) -> ProviderOrderRequestDecisionResponse:
    return service.decide_request(current_provider.id, request_id, payload)
