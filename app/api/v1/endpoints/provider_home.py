from fastapi import APIRouter, Depends

from app.api.dependencies.provider import get_current_provider
from app.schemas.provider_home import (
    ProviderHomeDashboardResponse,
    ProviderNotificationListResponse,
    ProviderNotificationResponse,
    ProviderNotificationsBulkActionResponse,
)
from app.schemas.user import UserResponse
from app.services.provider_home_service import ProviderHomeService

router = APIRouter()


@router.get("/me/home", response_model=ProviderHomeDashboardResponse)
def get_provider_home(
    service: ProviderHomeService = Depends(ProviderHomeService),
    current_provider: UserResponse = Depends(get_current_provider),
) -> ProviderHomeDashboardResponse:
    return service.get_dashboard(current_provider)


@router.get("/me/notifications", response_model=ProviderNotificationListResponse)
def list_provider_notifications(
    service: ProviderHomeService = Depends(ProviderHomeService),
    current_provider: UserResponse = Depends(get_current_provider),
) -> ProviderNotificationListResponse:
    return service.list_notifications(current_provider.id)


@router.patch(
    "/me/notifications/read-all",
    response_model=ProviderNotificationsBulkActionResponse,
)
def mark_all_provider_notifications_as_read(
    service: ProviderHomeService = Depends(ProviderHomeService),
    current_provider: UserResponse = Depends(get_current_provider),
) -> ProviderNotificationsBulkActionResponse:
    return service.mark_all_notifications_as_read(current_provider.id)


@router.patch(
    "/me/notifications/{notification_id}/read",
    response_model=ProviderNotificationResponse,
)
def mark_provider_notification_as_read(
    notification_id: str,
    service: ProviderHomeService = Depends(ProviderHomeService),
    current_provider: UserResponse = Depends(get_current_provider),
) -> ProviderNotificationResponse:
    return service.mark_notification_as_read(current_provider.id, notification_id)


@router.delete(
    "/me/notifications",
    response_model=ProviderNotificationsBulkActionResponse,
)
def clear_provider_notifications(
    service: ProviderHomeService = Depends(ProviderHomeService),
    current_provider: UserResponse = Depends(get_current_provider),
) -> ProviderNotificationsBulkActionResponse:
    return service.clear_notifications(current_provider.id)
