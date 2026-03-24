from fastapi import APIRouter, Depends, Query

from app.api.dependencies.provider import get_current_provider
from app.schemas.provider_booking import (
    ProviderBookingListResponse,
    ProviderBookingResponse,
    ProviderBookingStatus,
    ProviderBookingUpdate,
    ProviderBookingStatusUpdate,
    ProviderManualBookingCreate,
)
from app.schemas.user import UserResponse
from app.services.provider_booking_service import ProviderBookingService

router = APIRouter()


@router.post(
    "/me/products/{product_id}/bookings/manual",
    response_model=ProviderBookingResponse,
    status_code=201,
)
def create_my_manual_booking(
    product_id: str,
    payload: ProviderManualBookingCreate,
    service: ProviderBookingService = Depends(ProviderBookingService),
    current_provider: UserResponse = Depends(get_current_provider),
) -> ProviderBookingResponse:
    return service.create_manual_booking(current_provider.id, product_id, payload)


@router.get("/me/bookings", response_model=ProviderBookingListResponse)
def list_my_bookings(
    status: ProviderBookingStatus | None = Query(default=None),
    year: int | None = Query(default=None, ge=2000, le=3000),
    month: int | None = Query(default=None, ge=1, le=12),
    product_id: str | None = Query(default=None),
    service: ProviderBookingService = Depends(ProviderBookingService),
    current_provider: UserResponse = Depends(get_current_provider),
) -> ProviderBookingListResponse:
    return service.list_bookings(
        current_provider.id,
        status=status,
        year=year,
        month=month,
        product_id=product_id,
    )


@router.get("/me/bookings/{booking_id}", response_model=ProviderBookingResponse)
def get_my_booking(
    booking_id: str,
    service: ProviderBookingService = Depends(ProviderBookingService),
    current_provider: UserResponse = Depends(get_current_provider),
) -> ProviderBookingResponse:
    return service.get_booking(current_provider.id, booking_id)


@router.patch("/me/bookings/{booking_id}", response_model=ProviderBookingResponse)
def update_my_booking(
    booking_id: str,
    payload: ProviderBookingUpdate,
    service: ProviderBookingService = Depends(ProviderBookingService),
    current_provider: UserResponse = Depends(get_current_provider),
) -> ProviderBookingResponse:
    return service.update_booking(current_provider.id, booking_id, payload)


@router.patch("/me/bookings/{booking_id}/status", response_model=ProviderBookingResponse)
def update_my_booking_status(
    booking_id: str,
    payload: ProviderBookingStatusUpdate,
    service: ProviderBookingService = Depends(ProviderBookingService),
    current_provider: UserResponse = Depends(get_current_provider),
) -> ProviderBookingResponse:
    return service.update_booking_status(current_provider.id, booking_id, payload)
