from app.repositories.notification_token_repository import NotificationTokenRepository
from app.schemas.notification import (
    DeviceTokenDeleteRequest,
    DeviceTokenDeleteResponse,
    DeviceTokenRequest,
    DeviceTokenResponse,
)


class NotificationService:
    def __init__(self) -> None:
        self.repository = NotificationTokenRepository()

    def register_device_token(self, *, user_id: str, payload: DeviceTokenRequest) -> DeviceTokenResponse:
        stored = self.repository.upsert_token(
            user_id=user_id,
            token=payload.token,
            platform=payload.platform,
        )
        return DeviceTokenResponse(
            ok=True,
            token=str(stored.get("token") or payload.token),
            platform=str(stored.get("platform") or payload.platform),
        )

    def delete_device_token(self, *, user_id: str, payload: DeviceTokenDeleteRequest) -> DeviceTokenDeleteResponse:
        deleted = self.repository.delete_token(user_id=user_id, token=payload.token)
        return DeviceTokenDeleteResponse(deleted=deleted)
