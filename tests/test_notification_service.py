from app.schemas.notification import DeviceTokenDeleteRequest, DeviceTokenRequest
from app.services.notification_service import NotificationService


class _FakeTokenRepository:
    def __init__(self) -> None:
        self.upsert_calls: list[dict] = []
        self.delete_calls: list[dict] = []

    def upsert_token(self, *, user_id: str, token: str, platform: str) -> dict:
        self.upsert_calls.append({"user_id": user_id, "token": token, "platform": platform})
        return {
            "id": "hash-1",
            "token": token,
            "platform": platform,
            "user_id": user_id,
        }

    def delete_token(self, *, user_id: str, token: str) -> bool:
        self.delete_calls.append({"user_id": user_id, "token": token})
        return True


def _build_service(repo: _FakeTokenRepository) -> NotificationService:
    service = NotificationService.__new__(NotificationService)
    service.repository = repo
    return service


def test_register_device_token_uses_current_user_scope() -> None:
    repo = _FakeTokenRepository()
    service = _build_service(repo)

    response = service.register_device_token(
        user_id="client-1",
        payload=DeviceTokenRequest(token="token-1234567890", platform="android"),
    )

    assert response.ok is True
    assert response.token == "token-1234567890"
    assert response.platform == "android"
    assert repo.upsert_calls == [
        {"user_id": "client-1", "token": "token-1234567890", "platform": "android"}
    ]


def test_delete_device_token_uses_current_user_scope() -> None:
    repo = _FakeTokenRepository()
    service = _build_service(repo)

    response = service.delete_device_token(
        user_id="client-1",
        payload=DeviceTokenDeleteRequest(token="token-1234567890"),
    )

    assert response.deleted is True
    assert repo.delete_calls == [{"user_id": "client-1", "token": "token-1234567890"}]
