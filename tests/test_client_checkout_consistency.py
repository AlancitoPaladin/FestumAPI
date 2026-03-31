from datetime import datetime, timezone

import pytest

from app.core.exceptions import ApiError
from app.schemas.user import UserResponse
from app.services.client_orders_service import ClientOrdersService


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


class _FakeCheckoutRepository:
    def __init__(self, *, cart_items: list[dict], service_has_products: bool) -> None:
        self._cart_items = cart_items
        self._service_has_products = service_has_products
        self.checkout_calls: list[dict] = []

    def cart_list(self, user_id: str) -> list[dict]:
        return list(self._cart_items)

    def list_orders_by_statuses(self, user_id: str, statuses: list[str]) -> list[dict]:
        return []

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
        return self._service_has_products

    def visible_product_by_service_and_id(self, service_id: str, product_id: str):
        if product_id == "prod-1":
            service = self.service_by_id(service_id)
            product = {
                "id": product_id,
                "name": "Paquete basico",
                "unit_price_cents": 200000,
                "status": "published",
                "is_active": True,
                "is_published": True,
            }
            return service, product
        if product_id == "prod-price":
            service = self.service_by_id(service_id)
            product = {
                "id": product_id,
                "name": "Juegos infantibles",
                "price": 1500,
                "status": "published",
                "is_active": True,
                "is_published": True,
            }
            return service, product
        if product_id == "prod-2":
            service = self.service_by_id(service_id)
            product = {
                "id": product_id,
                "name": "Cabina extra",
                "price": 500,
                "status": "published",
                "is_active": True,
                "is_published": True,
            }
            return service, product
        if product_id == "prod-zero":
            service = self.service_by_id(service_id)
            product = {
                "id": product_id,
                "name": "Extra invalido",
                "price": 0,
                "status": "published",
                "is_active": True,
                "is_published": True,
            }
            return service, product
        return None

    def product_by_service_and_id(self, provider_id: str, service_id: str, product_id: str) -> dict | None:
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
        self.checkout_calls.append(
            {
                "order_payload": order_payload,
                "cart_item_ids": cart_item_ids,
                "provider_actions": provider_actions,
                "checkout_key": checkout_key,
            }
        )
        now = datetime.now(tz=timezone.utc)
        return {
            "id": order_payload["id"],
            "title": order_payload["title"],
            "status": order_payload["status"],
            "total_label": order_payload["total_label"],
            "created_at": now,
            "reservations_created": len(provider_actions),
            "notifications_created": len(provider_actions),
        }


class _FakeAvailabilityRepository:
    def __init__(self, status_by_key: dict[tuple[str, str, str, str], str] | None = None) -> None:
        self.status_by_key = status_by_key or {}

    def get_date_status(self, provider_id: str, service_id: str, product_id: str, date_key: str) -> str:
        return self.status_by_key.get((provider_id, service_id, product_id, date_key), "available")


def test_checkout_without_product_still_works_with_service_base_price() -> None:
    service = ClientOrdersService()
    service.repository = _FakeCheckoutRepository(
        cart_items=[
            {
                "id": "svc-1",
                "service_name": "Salon BJ",
                "unit_price_cents": 200000,
            }
        ],
        service_has_products=True,
    )
    service.availability_repository = _FakeAvailabilityRepository()

    response = service.checkout(_build_client_user())

    assert response.order.status == "pending_payment"
    assert response.items[0].product_id is None
    assert response.items[0].selected_product_ids == []


def test_checkout_with_product_creates_order_reservation_and_notification() -> None:
    service = ClientOrdersService()
    fake_repo = _FakeCheckoutRepository(
        cart_items=[
            {
                "id": "svc-1",
                "service_name": "Salon BJ",
                "product_id": "prod-1",
                "product_name": "Paquete basico",
                "unit_price_cents": 200000,
            }
        ],
        service_has_products=True,
    )
    service.repository = fake_repo
    service.availability_repository = _FakeAvailabilityRepository()

    response = service.checkout(_build_client_user())

    assert response.order.status == "pending_payment"
    assert response.provider_effects.reservations_created == 1
    assert response.provider_effects.notifications_created == 1
    assert response.items[0].product_id == "prod-1"
    assert len(fake_repo.checkout_calls) == 1
    reservation_payload = fake_repo.checkout_calls[0]["provider_actions"][0]["reservation_payload"]
    assert reservation_payload["product_id"] == "prod-1"


def test_checkout_with_invalid_selected_products_returns_422() -> None:
    service = ClientOrdersService()
    service.repository = _FakeCheckoutRepository(
        cart_items=[
            {
                "id": "svc-1",
                "service_name": "Salon BJ",
                "selected_product_ids": ["prod-invalid"],
                "unit_price_cents": 200000,
            }
        ],
        service_has_products=True,
    )
    service.availability_repository = _FakeAvailabilityRepository()

    with pytest.raises(ApiError) as exc:
        service.checkout(_build_client_user())

    assert exc.value.status_code == 422
    assert exc.value.code == "INVALID_SELECTED_PRODUCTS"


def test_checkout_with_selected_product_uses_real_price_field_for_snapshot_and_totals() -> None:
    service = ClientOrdersService()
    fake_repo = _FakeCheckoutRepository(
        cart_items=[
            {
                "id": "svc-1",
                "service_name": "Salon BJ",
                "selected_product_ids": ["prod-price"],
                "unit_price_cents": 200000,
            }
        ],
        service_has_products=True,
    )
    service.repository = fake_repo
    service.availability_repository = _FakeAvailabilityRepository()

    response = service.checkout(_build_client_user())

    assert response.items[0].selected_products_snapshot[0].id == "prod-price"
    assert response.items[0].selected_products_snapshot[0].unit_price_cents == 150000
    assert response.items[0].total_item_cents == 350000
    assert response.order.subtotal_cents == 350000


def test_checkout_with_multiple_selected_products_sums_exactly() -> None:
    service = ClientOrdersService()
    fake_repo = _FakeCheckoutRepository(
        cart_items=[
            {
                "id": "svc-1",
                "service_name": "Salon BJ",
                "selected_product_ids": ["prod-price", "prod-2"],
                "unit_price_cents": 200000,
            }
        ],
        service_has_products=True,
    )
    service.repository = fake_repo
    service.availability_repository = _FakeAvailabilityRepository()

    response = service.checkout(_build_client_user())
    assert response.items[0].total_item_cents == 400000
    assert response.order.subtotal_cents == 400000


def test_checkout_rejects_selected_product_with_zero_price() -> None:
    service = ClientOrdersService()
    fake_repo = _FakeCheckoutRepository(
        cart_items=[
            {
                "id": "svc-1",
                "service_name": "Salon BJ",
                "selected_product_ids": ["prod-zero"],
                "unit_price_cents": 200000,
            }
        ],
        service_has_products=True,
    )
    service.repository = fake_repo
    service.availability_repository = _FakeAvailabilityRepository()

    with pytest.raises(ApiError) as exc:
        service.checkout(_build_client_user())
    assert exc.value.status_code == 422
    assert exc.value.code == "INVALID_SELECTED_PRODUCTS"


def test_checkout_rejects_when_selected_product_is_reserved_for_business_today() -> None:
    service = ClientOrdersService()
    fake_repo = _FakeCheckoutRepository(
        cart_items=[
            {
                "id": "svc-1",
                "service_name": "Salon BJ",
                "selected_product_ids": ["prod-1"],
                "unit_price_cents": 200000,
            }
        ],
        service_has_products=True,
    )
    service.repository = fake_repo
    business_date = service._business_today().isoformat()
    service.availability_repository = _FakeAvailabilityRepository(
        {
            ("provider-1", "svc-1", "prod-1", business_date): "reserved",
        }
    )

    with pytest.raises(ApiError) as exc:
        service.checkout(_build_client_user())

    assert exc.value.status_code == 409
    assert exc.value.code == "PRODUCT_NOT_AVAILABLE_FOR_DATE"
    assert exc.value.meta == {
        "event_date": business_date,
        "conflicts": [
            {
                "service_id": "svc-1",
                "product_id": "prod-1",
                "status": "reserved",
            }
        ],
    }
