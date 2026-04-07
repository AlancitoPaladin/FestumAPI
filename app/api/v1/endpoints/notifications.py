from fastapi import APIRouter, Depends

from app.api.dependencies.auth import get_current_user
from app.schemas.notification import (
    DeviceTokenDeleteRequest,
    DeviceTokenDeleteResponse,
    DeviceTokenRequest,
    DeviceTokenResponse,
)
from app.schemas.user import UserResponse
from app.services.notification_service import NotificationService

router = APIRouter()


@router.post("/device-token", response_model=DeviceTokenResponse)
def register_device_token(
    payload: DeviceTokenRequest,
    current_user: UserResponse = Depends(get_current_user),
    service: NotificationService = Depends(NotificationService),
) -> DeviceTokenResponse:
    return service.register_device_token(user_id=current_user.id, payload=payload)


@router.delete("/device-token", response_model=DeviceTokenDeleteResponse)
def remove_device_token(
    payload: DeviceTokenDeleteRequest,
    current_user: UserResponse = Depends(get_current_user),
    service: NotificationService = Depends(NotificationService),
) -> DeviceTokenDeleteResponse:
    return service.delete_device_token(user_id=current_user.id, payload=payload)
