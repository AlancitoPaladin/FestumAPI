from fastapi import APIRouter, Depends, Query

from app.api.dependencies.auth import get_current_user
from app.schemas.client import ClientProductAvailabilityResponse
from app.schemas.user import UserResponse
from app.services.client_product_availability_service import ClientProductAvailabilityService

router = APIRouter()


@router.get("/products/{product_id}/availability", response_model=ClientProductAvailabilityResponse)
def product_availability(
    product_id: str,
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    _: UserResponse = Depends(get_current_user),
    service: ClientProductAvailabilityService = Depends(ClientProductAvailabilityService),
) -> ClientProductAvailabilityResponse:
    return service.get_month(product_id, year, month)
