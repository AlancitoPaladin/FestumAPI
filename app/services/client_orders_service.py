from random import randint

from app.core.exceptions import ResourceConflictError, ResourceNotFoundError
from app.repositories.client_repository import ClientRepository
from app.schemas.client import (
    CreateOrderRequest,
    OkResponse,
    OrderItem,
    OrdersResponse,
    UpdateOrderStatusRequest,
)

VALID_TRANSITIONS: dict[str, set[str]] = {
    "pending_payment": {"confirmed", "cancelled"},
    "confirmed": {"in_progress", "cancelled"},
    "in_progress": {"completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}


class ClientOrdersService:
    def __init__(self) -> None:
        self.repository = ClientRepository()

    def list_orders(self, user_id: str) -> OrdersResponse:
        items = self.repository.order_list(user_id)
        return OrdersResponse(items=[OrderItem(**item) for item in items])

    def create_order(self, user_id: str, payload: CreateOrderRequest) -> OrderItem:
        order_id = f"FST-{randint(1000, 9999)}"
        created = self.repository.order_create(
            user_id=user_id,
            payload={
                "id": order_id,
                "title": payload.title,
                "status": payload.status,
                "total_label": payload.total_label,
            },
        )
        return OrderItem(**created)

    def update_status(
        self, user_id: str, order_id: str, payload: UpdateOrderStatusRequest
    ) -> OkResponse:
        current = self.repository.order_get(user_id, order_id)
        if not current:
            raise ResourceNotFoundError("Order not found")

        current_status = current["status"]
        next_status = payload.status
        if next_status != current_status and next_status not in VALID_TRANSITIONS[current_status]:
            raise ResourceConflictError(
                detail=f"Invalid transition: {current_status} -> {next_status}",
                code="ORDER_INVALID_TRANSITION",
            )

        self.repository.order_update_status(user_id, order_id, next_status)
        return OkResponse(ok=True)

