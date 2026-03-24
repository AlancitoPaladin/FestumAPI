from fastapi import APIRouter, Depends, Query

from app.api.dependencies.auth import get_current_user
from app.schemas.client import HomeServicesResponse, ServiceCategory, ServiceItem
from app.schemas.user import UserResponse
from app.services.client_services_service import ClientServicesService

router = APIRouter()


@router.get("/services/home", response_model=HomeServicesResponse, response_model_by_alias=True)
def services_home(
    _: UserResponse = Depends(get_current_user),
    service: ClientServicesService = Depends(ClientServicesService),
) -> HomeServicesResponse:
    return service.home()


@router.get("/services", response_model=list[ServiceItem])
def services_by_category(
    category: ServiceCategory = Query(...),
    _: UserResponse = Depends(get_current_user),
    service: ClientServicesService = Depends(ClientServicesService),
) -> list[ServiceItem]:
    return service.by_category(category)


@router.get("/services/{serviceId}", response_model=ServiceItem)
def service_detail(
    serviceId: str,
    category: ServiceCategory = Query(...),
    _: UserResponse = Depends(get_current_user),
    service: ClientServicesService = Depends(ClientServicesService),
) -> ServiceItem:
    return service.detail(serviceId, category)
