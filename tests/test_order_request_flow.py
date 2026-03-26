from datetime import date, datetime, timezone

from app.schemas.client import CreateOrderRequestPayload, OrderRequestItemPayload
from app.schemas.provider_order_request import ProviderOrderRequestDecisionPayload
from app.schemas.user import UserResponse
from app.services.client_orders_service import ClientOrdersService
from app.services.provider_order_request_service import ProviderOrderRequestService


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


class _FakeClientRepo:
    def __init__(self, *, has_products: bool) -> None:
        self.has_products = has_products

    def service_by_id(self, service_id: str) -> dict | None:
        return {
            "id": service_id,
            "provider_id": "provider-1",
            "name": "Salon BJ",
            "unit_price_cents": 200000,
            "status": "published",
            "is_active": True,
            "is_published": True,
        }

    def service_has_published_products(self, provider_id: str, service_id: str) -> bool:
        return self.has_products

    def visible_product_by_service_and_id(self, service_id: str, product_id: str):
        if product_id != "prod-1":
            if product_id == "prod-price":
                return self.service_by_id(service_id), {
                    "id": product_id,
                    "name": "Juegos infantibles",
                    "price": 1500,
                    "status": "published",
                    "is_active": True,
                    "is_published": True,
                }
            return None
        return self.service_by_id(service_id), {
            "id": product_id,
            "name": "Paquete basico",
            "unit_price_cents": 200000,
            "status": "published",
            "is_active": True,
            "is_published": True,
        }

    def product_by_service_and_id(self, provider_id: str, service_id: str, product_id: str) -> dict | None:
        return None


class _FakeOrderRequestRepo:
    def __init__(self) -> None:
        self.created_payload = None

    def create_request(self, *, client_id: str, order_payload: dict, provider_requests: list, provider_notifications: list):
        self.created_payload = {
            "client_id": client_id,
            "order_payload": order_payload,
            "provider_requests": provider_requests,
            "provider_notifications": provider_notifications,
        }
        return {
            "id": order_payload["id"],
            **order_payload,
            "created_at": datetime.now(tz=timezone.utc),
        }


def test_order_request_without_product_still_works_with_service_base_price() -> None:
    service = ClientOrdersService()
    service.repository = _FakeClientRepo(has_products=True)
    service.order_request_repository = _FakeOrderRequestRepo()

    payload = CreateOrderRequestPayload(
        event_date=date.today(),
        notes="",
        items=[OrderRequestItemPayload(service_id="svc-1")],
    )

    response = service.create_order_request(_client_user(), payload)
    assert response.order.status == "pending_provider_approval"


def test_order_request_create_pending_provider_approval() -> None:
    service = ClientOrdersService()
    service.repository = _FakeClientRepo(has_products=True)
    fake_request_repo = _FakeOrderRequestRepo()
    service.order_request_repository = fake_request_repo

    payload = CreateOrderRequestPayload(
        event_date=date.today(),
        notes="Mesa principal",
        items=[OrderRequestItemPayload(service_id="svc-1", product_id="prod-1")],
    )
    response = service.create_order_request(_client_user(), payload)

    assert response.order.status == "pending_provider_approval"
    assert fake_request_repo.created_payload is not None


def test_order_request_with_selected_products_uses_real_price() -> None:
    service = ClientOrdersService()
    service.repository = _FakeClientRepo(has_products=True)
    fake_request_repo = _FakeOrderRequestRepo()
    service.order_request_repository = fake_request_repo

    payload = CreateOrderRequestPayload(
        event_date=date.today(),
        notes="Con adicionales",
        items=[OrderRequestItemPayload(service_id="svc-1", selected_product_ids=["prod-price"])],
    )
    response = service.create_order_request(_client_user(), payload)

    assert response.order.subtotal_cents == 350000
    stored_items = fake_request_repo.created_payload["order_payload"]["items"]
    assert stored_items[0]["selected_products_snapshot"][0]["unit_price_cents"] == 150000
    assert stored_items[0]["total_item_cents"] == 350000


class _FakeProviderRequestRepo:
    def __init__(self) -> None:
        now = datetime.now(tz=timezone.utc)
        self.request = {
            "id": "req-1",
            "order_id": "FST-REQ-111111",
            "client_id": "client-1",
            "client_name": "Client User",
            "event_date": date.today().isoformat(),
            "notes": "",
            "title": "Salon BJ",
            "status": "pending_provider_approval",
            "total_label": "$2,000 MXN",
            "items": [
                {
                    "service_id": "svc-1",
                    "service_name": "Salon BJ",
                    "product_id": "prod-1",
                    "product_name": "Paquete basico",
                    "unit_price_cents": 200000,
                }
            ],
            "created_at": now,
            "updated_at": now,
        }
        self.decisions: list[str] = []

    def list_provider_requests(self, provider_id: str, status: str | None = None) -> list[dict]:
        return [self.request]

    def get_provider_request(self, provider_id: str, request_id: str) -> dict | None:
        return dict(self.request)

    def decide_provider_request(self, *, provider_id: str, request_id: str, decision: str, order_id: str, client_id: str):
        self.decisions.append(decision)
        return {
            "id": order_id,
            "title": "Salon BJ",
            "status": "confirmed" if decision == "accepted" else "cancelled",
            "total_label": "$2,000 MXN",
            "created_at": datetime.now(tz=timezone.utc),
        }


class _FakeBookingRepo:
    def __init__(self) -> None:
        self.created = 0

    def generate_id(self, provider_id: str) -> str:
        return "booking-1"

    def create(self, provider_id: str, booking_id: str, data: dict) -> dict:
        self.created += 1
        return {"id": booking_id, **data}

    def delete(self, provider_id: str, booking_id: str) -> None:
        return None


class _FakeAvailabilityRepo:
    def __init__(self) -> None:
        self.reserved = 0

    def reserve_date(self, provider_id: str, service_id: str, product_id: str, date_key: str, booking_summary: dict) -> dict:
        self.reserved += 1
        return {}

    def clear_reserved_date(self, provider_id: str, service_id: str, product_id: str, date_key: str, booking_id: str) -> dict:
        return {}


def test_provider_accepts_request_creates_booking_and_blocks_availability() -> None:
    service = ProviderOrderRequestService()
    service.repository = _FakeProviderRequestRepo()
    service.booking_repository = _FakeBookingRepo()
    service.availability_repository = _FakeAvailabilityRepo()

    response = service.decide_request(
        "provider-1",
        "req-1",
        ProviderOrderRequestDecisionPayload(decision="accepted"),
    )
    assert response.order.status == "confirmed"
    assert service.booking_repository.created == 1
    assert service.availability_repository.reserved == 1


def test_provider_rejects_request_marks_client_order_cancelled() -> None:
    service = ProviderOrderRequestService()
    service.repository = _FakeProviderRequestRepo()
    service.booking_repository = _FakeBookingRepo()
    service.availability_repository = _FakeAvailabilityRepo()

    response = service.decide_request(
        "provider-1",
        "req-1",
        ProviderOrderRequestDecisionPayload(decision="rejected"),
    )
    assert response.order.status == "cancelled"
