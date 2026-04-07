from datetime import datetime, timezone

import pytest

from app.core.exceptions import ApiError
from app.schemas.client import CreateOrderRequestPayload, OrderRequestItemPayload
from app.schemas.user import UserResponse
from app.services.client_orders_service import ClientOrdersService


class _FakeClientRepo:
    def service_by_id(self, service_id: str) -> dict | None:
        return {
            "id": service_id,
            "provider_id": "provider-1",
            "name": f"Service {service_id}",
            "unit_price_cents": 200000,
            "status": "published",
            "is_active": True,
            "is_published": True,
        }

    def list_orders_by_statuses(self, user_id: str, statuses: list[str]) -> list[dict]:
        return []

    def visible_product_by_service_and_id(self, service_id: str, product_id: str):
        if product_id == "prod-1":
            return self.service_by_id(service_id), {
                "id": "prod-1",
                "name": "Paquete basico",
                "unit_price_cents": 200000,
                "status": "published",
                "is_active": True,
                "is_published": True,
            }
        if product_id == "prod-2":
            return self.service_by_id(service_id), {
                "id": "prod-2",
                "name": "Cabina extra",
                "price": 500,
                "status": "published",
                "is_active": True,
                "is_published": True,
            }
        return None


class _FakeOrderRequestRepository:
    def __init__(self) -> None:
        self.created = 0

    def create_request(self, *, client_id: str, order_payload: dict, provider_requests: list[dict], provider_notifications: list[dict]) -> dict:
        self.created += 1
        return {
            "id": order_payload["id"],
            **order_payload,
            "created_at": datetime.now(tz=timezone.utc),
        }


class _FakeAvailabilityRepository:
    def __init__(self, status_by_key: dict[tuple[str, str, str, str], str] | None = None) -> None:
        self.status_by_key = status_by_key or {}

    def get_date_status(self, provider_id: str, service_id: str, product_id: str, date_key: str) -> str:
        return self.status_by_key.get((provider_id, service_id, product_id, date_key), "available")

    def clear_reserved_date(self, provider_id: str, service_id: str, product_id: str, date_key: str, booking_id: str) -> dict:
        return {}


def _client_user() -> UserResponse:
    now = datetime.now(tz=timezone.utc)
    return UserResponse(
        id="client-1",
        first_name="Client",
        last_name="User",
        email="client@test.com",
        role="client",
        phone="",
        birth_date=None,
        is_active=True,
        created_at=now,
        updated_at=now,
    )


def test_order_request_rejects_reserved_product_for_selected_event_date() -> None:
    service = ClientOrdersService()
    service.repository = _FakeClientRepo()
    service.order_request_repository = _FakeOrderRequestRepository()

    event_date = service._business_today()
    service.availability_repository = _FakeAvailabilityRepository(
        {
            ("provider-1", "svc-1", "prod-1", event_date.isoformat()): "reserved",
        }
    )

    payload = CreateOrderRequestPayload(
        event_date=event_date,
        notes="",
        items=[OrderRequestItemPayload(service_id="svc-1", selected_product_ids=["prod-1"])],
    )

    with pytest.raises(ApiError) as exc:
        service.create_order_request(_client_user(), payload)

    assert exc.value.status_code == 409
    assert exc.value.code == "PRODUCT_NOT_AVAILABLE_FOR_DATE"
    assert exc.value.meta == {
        "event_date": event_date.isoformat(),
        "conflicts": [{"service_id": "svc-1", "product_id": "prod-1", "status": "reserved"}],
    }


def test_order_request_rejects_blocked_product_for_legacy_product_id() -> None:
    service = ClientOrdersService()
    service.repository = _FakeClientRepo()
    service.order_request_repository = _FakeOrderRequestRepository()

    event_date = service._business_today()
    service.availability_repository = _FakeAvailabilityRepository(
        {
            ("provider-1", "svc-1", "prod-2", event_date.isoformat()): "blocked",
        }
    )

    payload = CreateOrderRequestPayload(
        event_date=event_date,
        notes="",
        items=[OrderRequestItemPayload(service_id="svc-1", product_id="prod-2")],
    )

    with pytest.raises(ApiError) as exc:
        service.create_order_request(_client_user(), payload)

    assert exc.value.status_code == 409
    assert exc.value.code == "PRODUCT_NOT_AVAILABLE_FOR_DATE"
    assert exc.value.meta == {
        "event_date": event_date.isoformat(),
        "conflicts": [{"service_id": "svc-1", "product_id": "prod-2", "status": "blocked"}],
    }


def test_order_request_creates_when_all_products_available_and_event_date_is_today() -> None:
    service = ClientOrdersService()
    service.repository = _FakeClientRepo()
    fake_order_repo = _FakeOrderRequestRepository()
    service.order_request_repository = fake_order_repo

    event_date = service._business_today()
    service.availability_repository = _FakeAvailabilityRepository()

    payload = CreateOrderRequestPayload(
        event_date=event_date,
        notes="",
        items=[OrderRequestItemPayload(service_id="svc-1", selected_product_ids=["prod-1", "prod-2"])],
    )

    response = service.create_order_request(_client_user(), payload)

    assert response.order.status == "pending_provider_approval"
    assert fake_order_repo.created == 1
