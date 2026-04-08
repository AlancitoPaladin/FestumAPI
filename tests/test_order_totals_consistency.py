from datetime import datetime, timezone

from app.schemas.user import UserResponse
from app.services.client_orders_service import ClientOrdersService


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


class _FakeCheckoutRepo:
    def __init__(self) -> None:
        self.checkout_payload = None

    def cart_list(self, user_id: str) -> list[dict]:
        return [
            {
                "id": "svc-1",
                "service_name": "Salon BJ",
                "selected_product_ids": ["prod-1"],
                "unit_price_cents": 200000,
            }
        ]

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

    def visible_product_by_service_and_id(self, service_id: str, product_id: str):
        if product_id != "prod-1":
            return None
        return self.service_by_id(service_id), {
            "id": "prod-1",
            "name": "Extra luces",
            "unit_price_cents": 50000,
            "status": "published",
            "is_active": True,
            "is_published": True,
        }

    def checkout_commit(self, user_id: str, *, order_payload: dict, cart_item_ids: list[str], provider_actions: list[dict], checkout_key: str) -> dict:
        self.checkout_payload = order_payload
        return {
            **order_payload,
            "created_at": datetime.now(tz=timezone.utc),
            "reservations_created": len(provider_actions),
            "notifications_created": len(provider_actions),
        }


def test_checkout_calculates_financial_breakdown_with_selected_products() -> None:
    service = ClientOrdersService()
    service.repository = _FakeCheckoutRepo()

    response = service.checkout(_client_user())

    assert response.order.subtotal_cents == 250000
    assert response.order.service_fee_cents == 12500
    assert response.order.tax_cents == 42000
    assert response.order.total_cents == 304500
    assert response.order.total_label == "$3,045 MXN"


class _FakeOrdersListRepo:
    def __init__(self, orders: list[dict]) -> None:
        self.orders = orders

    def order_list(self, user_id: str) -> list[dict]:
        return self.orders


def test_get_orders_backfills_totals_from_items_when_missing() -> None:
    now = datetime.now(tz=timezone.utc)
    order = {
        "id": "FST-1",
        "title": "Order",
        "status": "pending_payment",
        "total_label": "",
        "created_at": now,
        "items": [
            {"service_id": "svc-1", "unit_price_cents": 100000, "total_item_cents": 100000},
            {"service_id": "svc-2", "unit_price_cents": 50000, "total_item_cents": 50000},
        ],
    }
    service = ClientOrdersService()
    fake_repo = _FakeOrdersListRepo([order])
    service.repository = fake_repo

    response = service.list_orders("client-1")
    first = response.items[0]
    assert first.subtotal_cents == 150000
    assert first.total_cents == 182700
    assert first.total_label == "$1,827 MXN"


def test_get_orders_marks_null_when_backfill_is_not_possible() -> None:
    now = datetime.now(tz=timezone.utc)
    order = {
        "id": "FST-2",
        "title": "Legacy",
        "status": "pending_payment",
        "total_label": "",
        "created_at": now,
        "items": [],
    }
    service = ClientOrdersService()
    fake_repo = _FakeOrdersListRepo([order])
    service.repository = fake_repo

    response = service.list_orders("client-1")
    first = response.items[0]
    assert first.subtotal_cents is None
    assert first.total_cents is None
