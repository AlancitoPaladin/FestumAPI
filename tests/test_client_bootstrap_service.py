from datetime import datetime, timezone

from app.schemas.client import HomeServicesResponse, ServiceItem, UpdateOrderStatusRequest
from app.services.client_bootstrap_service import ClientBootstrapService
from app.services.client_orders_service import ClientOrdersService
from app.services.client_cache import invalidate_user_bootstrap_cache


class _FakeHomeService:
    def __init__(self, home_response: HomeServicesResponse) -> None:
        self.home_response = home_response
        self.calls = 0
        self.image_modes: list[str] = []

    def home(
        self,
        request_id: str | None = None,
        *,
        user_id: str | None = None,
        include_products: bool = True,
        image_mode: str = "full",
        include_all_images: bool = True,
        include_metrics: bool = False,
    ):
        self.calls += 1
        self.image_modes.append(image_mode)
        if include_metrics:
            return self.home_response, {"total_ms": 1.0, "db_ms": 1.0, "image_sign_ms": 1.0, "images_signed_count": 1}
        return self.home_response


class _FakeBootstrapRepo:
    def __init__(self, *, cart_items: list[dict], orders: list[dict]) -> None:
        self._cart_items = cart_items
        self._orders = orders
        self.order_reads = 0

    def cart_list(self, user_id: str) -> list[dict]:
        return list(self._cart_items)

    def order_list(self, user_id: str) -> list[dict]:
        self.order_reads += 1
        return list(self._orders)

    def order_get(self, user_id: str, order_id: str) -> dict | None:
        for order in self._orders:
            if str(order.get("id") or "") == order_id:
                return order
        return None

    def order_update_status(self, user_id: str, order_id: str, status: str) -> dict | None:
        for order in self._orders:
            if str(order.get("id") or "") == order_id:
                order["status"] = status
                return order
        return None


def _empty_home() -> HomeServicesResponse:
    return HomeServicesResponse(
        **{
            "salones-sociales": [],
            "mobiliario": [],
            "banquetes": [],
            "dj": [],
            "decoracion": [],
            "fotografia": [],
            "entretenimiento": [],
            "otros": [],
        }
    )


def test_bootstrap_contract_keys_and_empty_defaults() -> None:
    user_id = "bootstrap-user-1"
    invalidate_user_bootstrap_cache(user_id)
    service = ClientBootstrapService()
    service.repository = _FakeBootstrapRepo(cart_items=[], orders=[])
    service.home_service = _FakeHomeService(_empty_home())

    response = service.get_bootstrap(user_id)
    payload = response.model_dump(by_alias=True)

    assert set(payload.keys()) == {"home", "cart", "orders", "locks", "meta"}
    assert set(payload["home"].keys()) == {
        "salones-sociales",
        "mobiliario",
        "banquetes",
        "dj",
        "decoracion",
        "fotografia",
        "entretenimiento",
        "otros",
    }
    assert payload["cart"]["count"] == 0
    assert payload["cart"]["service_ids"] == []
    assert payload["orders"]["count"] == 0
    assert payload["locks"]["active_service_ids"] == []
    assert "generated_at" in payload["meta"]


def test_bootstrap_locks_include_only_active_statuses() -> None:
    user_id = "bootstrap-user-2"
    invalidate_user_bootstrap_cache(user_id)
    now = datetime.now(tz=timezone.utc)
    orders = [
        {"id": "A", "status": "pending_provider_approval", "items": [{"service_id": "svc_1"}], "created_at": now},
        {"id": "B", "status": "pending_payment", "items": [{"service_id": "svc_2"}], "created_at": now},
        {"id": "C", "status": "confirmed", "items": [{"service_id": "svc_3"}], "created_at": now},
        {"id": "D", "status": "in_progress", "items": [{"service_id": "svc_4"}], "created_at": now},
        {"id": "E", "status": "cancelled", "items": [{"service_id": "svc_5"}], "created_at": now},
        {"id": "F", "status": "completed", "items": [{"service_id": "svc_6"}], "created_at": now},
    ]
    service = ClientBootstrapService()
    service.repository = _FakeBootstrapRepo(cart_items=[], orders=orders)
    service.home_service = _FakeHomeService(_empty_home())

    response = service.get_bootstrap(user_id)

    assert response.locks.active_service_ids == ["svc_1", "svc_2", "svc_3", "svc_4"]


def test_bootstrap_keeps_home_items_even_if_image_is_null() -> None:
    user_id = "bootstrap-user-3"
    invalidate_user_bootstrap_cache(user_id)
    home = _empty_home()
    home.dj.append(
        ServiceItem(
            id="svc_dj_1",
            name="DJ Alex",
            subtitle="Set de 5 horas",
            description="Incluye sonido",
            price_label="Desde $5,000 MXN",
            unit_price_cents=500000,
            badge="Top",
            category="dj",
            image=None,
            image_url="https://legacy.example.com/dj-1.jpg",
            products=[],
        )
    )
    service = ClientBootstrapService()
    service.repository = _FakeBootstrapRepo(cart_items=[], orders=[])
    service.home_service = _FakeHomeService(home)

    response = service.get_bootstrap(user_id)

    assert len(response.home.dj) == 1
    assert response.home.dj[0].image is None
    assert response.home.dj[0].image_url == "https://legacy.example.com/dj-1.jpg"


def test_bootstrap_cache_and_invalidation_after_order_status_change() -> None:
    user_id = "bootstrap-user-4"
    invalidate_user_bootstrap_cache(user_id)
    now = datetime.now(tz=timezone.utc)
    repo = _FakeBootstrapRepo(
        cart_items=[],
        orders=[{"id": "ORD-1", "status": "in_progress", "items": [{"service_id": "svc_lock"}], "created_at": now}],
    )
    bootstrap_service = ClientBootstrapService()
    bootstrap_service.repository = repo
    bootstrap_service.home_service = _FakeHomeService(_empty_home())

    first = bootstrap_service.get_bootstrap(user_id)
    second = bootstrap_service.get_bootstrap(user_id)

    assert first.locks.active_service_ids == ["svc_lock"]
    assert second.locks.active_service_ids == ["svc_lock"]
    assert repo.order_reads == 1

    orders_service = ClientOrdersService()
    orders_service.repository = repo
    orders_service.update_status(
        user_id,
        "ORD-1",
        UpdateOrderStatusRequest(status="completed"),
    )

    third = bootstrap_service.get_bootstrap(user_id)
    assert third.locks.active_service_ids == []
    assert third.orders.count == 1
    assert repo.order_reads == 2


def test_bootstrap_includes_cart_service_ids_when_cart_has_items() -> None:
    user_id = "bootstrap-user-5"
    invalidate_user_bootstrap_cache(user_id)
    repo = _FakeBootstrapRepo(
        cart_items=[
            {"id": "svc1", "name": "Service 1"},
            {"id": "svc2", "name": "Service 2"},
            {"id": "svc3", "name": "Service 3"},
        ],
        orders=[],
    )
    service = ClientBootstrapService()
    service.repository = repo
    service.home_service = _FakeHomeService(_empty_home())

    response = service.get_bootstrap(user_id)

    assert response.cart.service_ids == ["svc1", "svc2", "svc3"]
    assert response.cart.count == len(response.cart.service_ids)


def test_bootstrap_images_mode_default_lite_and_accepts_full() -> None:
    user_id = "bootstrap-user-6"
    invalidate_user_bootstrap_cache(user_id)
    fake_home = _FakeHomeService(_empty_home())
    service = ClientBootstrapService()
    service.repository = _FakeBootstrapRepo(cart_items=[], orders=[])
    service.home_service = fake_home

    service.get_bootstrap(user_id)
    service.get_bootstrap(user_id + "-full", images="full")

    assert fake_home.image_modes[0] == "lite"
    assert fake_home.image_modes[1] == "full"
