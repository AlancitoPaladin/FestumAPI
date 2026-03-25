from datetime import date

from fastapi import APIRouter, Depends, Query

from app.api.dependencies.provider import get_current_provider
from app.schemas.provider_availability import (
    ProviderAvailabilityBlockRequest,
    ProviderAvailabilityMonthResponse,
    ProviderAvailabilityStatusResponse,
)
from app.schemas.user import UserResponse
from app.services.provider_availability_service import ProviderAvailabilityService

router = APIRouter()


@router.get("/me/products/{product_id}/availability", response_model=ProviderAvailabilityMonthResponse)
def get_product_availability_month(
    product_id: str,
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    service: ProviderAvailabilityService = Depends(ProviderAvailabilityService),
    current_provider: UserResponse = Depends(get_current_provider),
) -> ProviderAvailabilityMonthResponse:
    return service.get_month(current_provider.id, product_id, year, month)


@router.patch(
    "/me/products/{product_id}/availability/{target_date}/block",
    response_model=ProviderAvailabilityStatusResponse,
    include_in_schema=False,
)
def block_product_date(
    product_id: str,
    target_date: date,
    service: ProviderAvailabilityService = Depends(ProviderAvailabilityService),
    current_provider: UserResponse = Depends(get_current_provider),
) -> ProviderAvailabilityStatusResponse:
    return service.block_date(current_provider.id, product_id, target_date)


@router.patch(
    "/me/products/{product_id}/availability/{target_date}/unblock",
    response_model=ProviderAvailabilityStatusResponse,
    include_in_schema=False,
)
def unblock_product_date(
    product_id: str,
    target_date: date,
    service: ProviderAvailabilityService = Depends(ProviderAvailabilityService),
    current_provider: UserResponse = Depends(get_current_provider),
) -> ProviderAvailabilityStatusResponse:
    return service.unblock_date(current_provider.id, product_id, target_date)


@router.post(
    "/me/products/{product_id}/availability/blocks",
    response_model=ProviderAvailabilityStatusResponse,
)
def block_product_date_with_body(
    product_id: str,
    payload: ProviderAvailabilityBlockRequest,
    service: ProviderAvailabilityService = Depends(ProviderAvailabilityService),
    current_provider: UserResponse = Depends(get_current_provider),
) -> ProviderAvailabilityStatusResponse:
    return service.block_date_from_request(current_provider.id, product_id, payload)


@router.delete(
    "/me/products/{product_id}/availability/blocks",
    response_model=ProviderAvailabilityStatusResponse,
)
def unblock_product_date_with_body(
    product_id: str,
    payload: ProviderAvailabilityBlockRequest,
    service: ProviderAvailabilityService = Depends(ProviderAvailabilityService),
    current_provider: UserResponse = Depends(get_current_provider),
) -> ProviderAvailabilityStatusResponse:
    return service.unblock_date_from_request(current_provider.id, product_id, payload)
