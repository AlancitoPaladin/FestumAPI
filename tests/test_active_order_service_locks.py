from datetime import date, datetime, timezone

import pytest

from app.core.exceptions import ApiError
from app.schemas.client import CreateOrderRequestPayload, OrderRequestItemPayload
from app.schemas.user import UserResponse
from app.services.client_orders_service import ClientOrdersService


class _FakeOrderRequestRepository:
    def create_request(self, *, client_id: str, order_payload: dict, provider_requests: list[dict], provider_notifications: list[dict]) -> dict:
        return {
            "id": order_payload["id"],
            **order_payload,
            "created_at": datetime.now(tz=timezone.utc),
        }


class _FakeCheckoutRepository:
    def __init__(self, *, cart_items: list[dict], active_orders: list[dict]) -> None:
        self._cart_items = cart_items
        self._active_orders = active_orders

    def list_orders_by_statuses(self, user_id: str, statuses: list[str]) -> list[dict]:
        allowed = set(statuses)
        return [order for order in self._active_orders if str(order.get("status") or "") in allowed]

    def cart_list(self, user_id: str) -> list[dict]:
        return list(self._cart_items)

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

    def visible_product_by_service_and_id(self, service_id: str, product_id: str):
        return None

    def checkout_commit(
        self,
        user_id: str,
        *,
        order_payload: dict,
        cart_item_ids: list[str],
        provider_actions: list[dict],
        checkout_key: str,
    ) -> dict:
        return {
            "id": order_payload["id"],
            "title": order_payload["title"],
            "status": order_payload["status"],
            "total_label": order_payload["total_label"],
            "created_at": datetime.now(tz=timezone.utc),
            "reservations_created": len(provider_actions),
            "notifications_created": len(provider_actions),
            "subtotal_cents": order_payload["subtotal_cents"],
            "service_fee_cents": order_payload["service_fee_cents"],
            "tax_cents": order_payload["tax_cents"],
            "total_cents": order_payload["total_cents"],
            "currency": order_payload["currency"],
            "fee_rate": order_payload["fee_rate"],
            "tax_rate": order_payload["tax_rate"],
        }


def _build_client_user() -> UserResponse:
    now = datetime.now(tz=timezone.utc)
    return UserResponse(
        id="client-1",
        first_name="Alan",
        last_name="Perez",
        email="alan@test.com",
        role="client",
        phone="+5212210000000",
        birth_date=None,
        is_active=True,
        created_at=now,
        updated_at=now,
    )


def test_checkout_blocked_when_service_has_active_order() -> None:
    service = ClientOrdersService()
    service.repository = _FakeCheckoutRepository(
        cart_items=[{"id": "svc-1", "service_name": "Salon BJ", "unit_price_cents": 200000}],
        active_orders=[
            {
                "id": "ord-active-1",
                "status": "pending_payment",
                "items": [{"service_id": "svc-1"}],
            }
        ],
    )

    with pytest.raises(ApiError) as exc:
        service.checkout(_build_client_user())

    assert exc.value.status_code == 409
    assert exc.value.code == "SERVICE_ALREADY_IN_ACTIVE_ORDER"
    assert exc.value.meta == {
        "service_ids": ["svc-1"],
        "blocking_order_ids": ["ord-active-1"],
    }


def test_checkout_allowed_when_previous_order_is_cancelled() -> None:
    service = ClientOrdersService()
    service.repository = _FakeCheckoutRepository(
        cart_items=[{"id": "svc-1", "service_name": "Salon BJ", "unit_price_cents": 200000}],
        active_orders=[
            {
                "id": "ord-old-1",
                "status": "cancelled",
                "items": [{"service_id": "svc-1"}],
            }
        ],
    )

    response = service.checkout(_build_client_user())

    assert response.order.status == "pending_payment"


def test_order_request_blocked_when_service_has_active_order() -> None:
    service = ClientOrdersService()
    service.repository = _FakeCheckoutRepository(
        cart_items=[],
        active_orders=[
            {
                "id": "ord-active-req-1",
                "status": "pending_provider_approval",
                "items": [{"service_id": "svc-1"}],
            }
        ],
    )
    service.order_request_repository = _FakeOrderRequestRepository()

    payload = CreateOrderRequestPayload(
        event_date=date.today(),
        notes="",
        items=[OrderRequestItemPayload(service_id="svc-1")],
    )

    with pytest.raises(ApiError) as exc:
        service.create_order_request(_build_client_user(), payload)

    assert exc.value.status_code == 409
    assert exc.value.code == "SERVICE_ALREADY_IN_ACTIVE_ORDER"
    assert exc.value.meta == {
        "service_ids": ["svc-1"],
        "blocking_order_ids": ["ord-active-req-1"],
    }


def test_checkout_multi_item_blocked_when_any_service_is_locked() -> None:
    service = ClientOrdersService()
    service.repository = _FakeCheckoutRepository(
        cart_items=[
            {"id": "svc-1", "service_name": "Salon BJ", "unit_price_cents": 200000},
            {"id": "svc-2", "service_name": "Catering", "unit_price_cents": 120000},
        ],
        active_orders=[
            {
                "id": "ord-active-2",
                "status": "confirmed",
                "items": [{"service_id": "svc-2"}],
            }
        ],
    )

    with pytest.raises(ApiError) as exc:
        service.checkout(_build_client_user())

    assert exc.value.status_code == 409
    assert exc.value.code == "SERVICE_ALREADY_IN_ACTIVE_ORDER"
    assert exc.value.meta == {
        "service_ids": ["svc-2"],
        "blocking_order_ids": ["ord-active-2"],
    }
