from datetime import datetime, timezone

from app.schemas.client import UpdateOrderStatusRequest
from app.services.client_orders_service import ClientOrdersService


class _FakeOrdersRepo:
    def __init__(self, orders: list[dict]) -> None:
        self.orders = orders
        self.active_reads = 0

    def order_list(self, user_id: str) -> list[dict]:
        return self.orders

    def order_get(self, user_id: str, order_id: str) -> dict | None:
        for item in self.orders:
            if item.get("id") == order_id:
                return item
        return None

    def list_orders_by_statuses(self, user_id: str, statuses: list[str]) -> list[dict]:
        allowed = set(statuses)
        return [item for item in self.orders if str(item.get("status") or "") in allowed]

    def list_order_status_and_items_by_statuses(self, user_id: str, statuses: list[str]) -> list[dict]:
        self.active_reads += 1
        allowed = set(statuses)
        return [
            {
                "id": str(item.get("id") or ""),
                "status": str(item.get("status") or ""),
                "items": list(item.get("items") or []),
            }
            for item in self.orders
            if str(item.get("status") or "") in allowed
        ]

    def order_update_status(self, user_id: str, order_id: str, status: str) -> dict | None:
        for item in self.orders:
            if item.get("id") == order_id:
                item["status"] = status
                return item
        return None


def _sample_order() -> dict:
    now = datetime.now(tz=timezone.utc)
    return {
        "id": "FST-2202",
        "title": "Salón Aurora +1 servicios",
        "status": "pending_payment",
        "subtotal_cents": 200000,
        "service_fee_cents": 10000,
        "tax_cents": 33600,
        "total_cents": 243600,
        "total_label": "$2,436 MXN",
        "created_at": now,
        "items": [
            {
                "service_id": "svc-1",
                "service_name": "Salón Aurora",
                "total_item_cents": 243600,
            }
        ],
    }


def test_orders_list_default_is_lightweight() -> None:
    service = ClientOrdersService()
    service.repository = _FakeOrdersRepo([_sample_order()])

    response = service.list_orders("client-1", include_items=False)

    assert len(response.items) == 1
    first = response.items[0]
    assert first.id == "FST-2202"
    assert first.service_name == "Salón Aurora"
    assert not hasattr(first, "items")


def test_orders_list_include_items_legacy() -> None:
    service = ClientOrdersService()
    service.repository = _FakeOrdersRepo([_sample_order()])

    response = service.list_orders("client-1", include_items=True)

    assert len(response.items) == 1
    assert response.items[0].items
    assert response.items[0].items[0]["service_id"] == "svc-1"


def test_order_detail_returns_full_payload() -> None:
    service = ClientOrdersService()
    service.repository = _FakeOrdersRepo([_sample_order()])

    response = service.get_order_detail("client-1", "FST-2202")

    assert response.id == "FST-2202"
    assert response.items
    assert response.total_cents == 243600


def test_active_service_ids_returns_unique_ids_from_active_orders() -> None:
    now = datetime.now(tz=timezone.utc)
    active_order = {
        "id": "FST-1",
        "title": "Active",
        "status": "pending_payment",
        "total_label": "$1",
        "created_at": now,
        "items": [
            {"service_id": "svc_123"},
            {"service_id": "svc_987"},
            {"service_id": "svc_123"},
        ],
    }
    inactive_order = {
        "id": "FST-2",
        "title": "Done",
        "status": "completed",
        "total_label": "$2",
        "created_at": now,
        "items": [{"service_id": "svc_555"}],
    }
    service = ClientOrdersService()
    service.repository = _FakeOrdersRepo([active_order, inactive_order])

    response = service.list_active_service_ids("client-1")

    assert response.service_ids == ["svc_123", "svc_987"]
    assert response.total == 2


def test_active_service_ids_excludes_cancelled_and_completed() -> None:
    now = datetime.now(tz=timezone.utc)
    orders = [
        {
            "id": "FST-3",
            "title": "Pending",
            "status": "pending_provider_approval",
            "total_label": "$1",
            "created_at": now,
            "items": [{"service_id": "svc_active"}],
        },
        {
            "id": "FST-4",
            "title": "Cancelled",
            "status": "cancelled",
            "total_label": "$1",
            "created_at": now,
            "items": [{"service_id": "svc_cancelled"}],
        },
        {
            "id": "FST-5",
            "title": "Completed",
            "status": "completed",
            "total_label": "$1",
            "created_at": now,
            "items": [{"service_id": "svc_completed"}],
        },
    ]
    service = ClientOrdersService()
    service.repository = _FakeOrdersRepo(orders)

    response = service.list_active_service_ids("client-2")

    assert response.service_ids == ["svc_active"]
    assert response.total == 1


def test_active_service_ids_returns_empty_when_no_active_orders() -> None:
    now = datetime.now(tz=timezone.utc)
    orders = [
        {
            "id": "FST-6",
            "title": "Done",
            "status": "completed",
            "total_label": "$1",
            "created_at": now,
            "items": [{"service_id": "svc_completed"}],
        }
    ]
    service = ClientOrdersService()
    service.repository = _FakeOrdersRepo(orders)

    response = service.list_active_service_ids("client-3")

    assert response.service_ids == []
    assert response.total == 0


def test_active_service_ids_uses_cache_and_invalidates_on_status_transition() -> None:
    now = datetime.now(tz=timezone.utc)
    repo = _FakeOrdersRepo(
        [
            {
                "id": "FST-7",
                "title": "Pending",
                "status": "in_progress",
                "total_label": "$1",
                "created_at": now,
                "items": [{"service_id": "svc_transition"}],
            }
        ]
    )
    service = ClientOrdersService()
    service.repository = repo

    first = service.list_active_service_ids("client-4")
    second = service.list_active_service_ids("client-4")

    assert first.service_ids == ["svc_transition"]
    assert second.service_ids == ["svc_transition"]
    assert repo.active_reads == 1

    service.update_status(
        "client-4",
        "FST-7",
        payload=UpdateOrderStatusRequest(status="completed"),
    )

    third = service.list_active_service_ids("client-4")
    assert third.service_ids == []
    assert third.total == 0
    assert repo.active_reads == 2
