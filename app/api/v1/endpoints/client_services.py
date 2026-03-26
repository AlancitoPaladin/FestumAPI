from fastapi import APIRouter, Depends, Query

from app.api.dependencies.auth import get_current_user
from app.schemas.client import HomeServicesResponse, ServiceItem, ServiceListResponse
from app.schemas.user import UserResponse
from app.services.client_services_service import ClientServicesService

router = APIRouter()


@router.get("/services/home", response_model=HomeServicesResponse, response_model_by_alias=True)
def services_home(
    _: UserResponse = Depends(get_current_user),
    service: ClientServicesService = Depends(ClientServicesService),
) -> HomeServicesResponse:
    return service.home()


@router.get("/services", response_model=ServiceListResponse)
def services_by_category(
    category: str = Query(..., min_length=1),
    q: str | None = Query(default=None),
    min_price_cents: int | None = Query(default=None, ge=0),
    max_price_cents: int | None = Query(default=None, ge=0),
    sort: str = Query(default="relevance", pattern="^(relevance|price_asc|price_desc|name_asc|name_desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: UserResponse = Depends(get_current_user),
    service: ClientServicesService = Depends(ClientServicesService),
) -> ServiceListResponse:
    return service.by_category(
        category=category,
        q=q,
        min_price_cents=min_price_cents,
        max_price_cents=max_price_cents,
        sort=sort,
        page=page,
        page_size=page_size,
    )


@router.get("/services/{serviceId}", response_model=ServiceItem)
def service_detail(
    serviceId: str,
    category: str = Query(..., min_length=1),
    _: UserResponse = Depends(get_current_user),
    service: ClientServicesService = Depends(ClientServicesService),
) -> ServiceItem:
    return service.detail(serviceId, category)
