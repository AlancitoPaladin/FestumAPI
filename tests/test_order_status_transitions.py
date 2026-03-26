from datetime import datetime, timezone

import pytest

from app.core.exceptions import ApiError
from app.schemas.client import UpdateOrderStatusRequest
from app.services.client_orders_service import ClientOrdersService


class _FakeClientOrderRepo:
    def __init__(self, statuses: list[str]) -> None:
        self.statuses = statuses
        self.order_update_calls: list[str] = []
        self._read_count = 0

    def order_get(self, user_id: str, order_id: str) -> dict | None:
        if self._read_count >= len(self.statuses):
            current_status = self.statuses[-1]
        else:
            current_status = self.statuses[self._read_count]
        self._read_count += 1
        return {
            "id": order_id,
            "status": current_status,
            "title": "Order",
            "total_label": "$1,000 MXN",
            "created_at": datetime.now(tz=timezone.utc),
        }

    def order_update_status(self, user_id: str, order_id: str, status: str) -> dict | None:
        self.order_update_calls.append(status)
        return {"id": order_id, "status": status}


class _FakeOrderRequestRepository:
    def __init__(self) -> None:
        self.cancel_calls: list[dict] = []

    def cancel_related_entities(self, *, client_id: str, order_id: str) -> dict:
        self.cancel_calls.append({"client_id": client_id, "order_id": order_id})
        return {"availability_release_targets": []}


class _FakeAvailabilityRepository:
    def clear_reserved_date(self, provider_id: str, service_id: str, product_id: str, date_key: str, booking_id: str) -> dict:
        return {}


def _build_service(repo: _FakeClientOrderRepo) -> ClientOrdersService:
    service = ClientOrdersService()
    service.repository = repo
    service.order_request_repository = _FakeOrderRequestRepository()
    service.availability_repository = _FakeAvailabilityRepository()
    return service


def test_cancel_pending_order_success() -> None:
    service = _build_service(_FakeClientOrderRepo(["pending_provider_approval"]))
    response = service.update_status(
        "client-1",
        "ord-1",
        UpdateOrderStatusRequest(status="cancelled"),
        actor="client",
        trace_id="trace-1",
    )
    assert response.ok is True
    assert response.idempotent is False


def test_cancel_already_cancelled_is_idempotent() -> None:
    service = _build_service(_FakeClientOrderRepo(["cancelled"]))
    response = service.update_status(
        "client-1",
        "ord-1",
        UpdateOrderStatusRequest(status="cancelled"),
        actor="client",
        trace_id="trace-2",
    )
    assert response.ok is True
    assert response.idempotent is True


def test_invalid_transition_returns_409_not_500() -> None:
    service = _build_service(_FakeClientOrderRepo(["completed"]))
    with pytest.raises(ApiError) as exc:
        service.update_status(
            "client-1",
            "ord-1",
            UpdateOrderStatusRequest(status="cancelled"),
            actor="client",
            trace_id="trace-3",
        )
    assert exc.value.status_code == 409
    assert exc.value.code == "ORDER_INVALID_TRANSITION"


def test_confirm_race_with_provider_cancel_returns_409() -> None:
    service = _build_service(_FakeClientOrderRepo(["pending_payment", "cancelled"]))
    with pytest.raises(ApiError) as exc:
        service.update_status(
            "client-1",
            "ord-1",
            UpdateOrderStatusRequest(status="confirmed"),
            actor="client",
            trace_id="trace-4",
        )
    assert exc.value.status_code == 409
    assert exc.value.code == "ORDER_INVALID_TRANSITION"
