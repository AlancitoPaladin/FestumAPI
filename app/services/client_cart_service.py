from app.core.exceptions import ResourceConflictError, ResourceNotFoundError
from app.repositories.client_repository import ClientRepository
from app.schemas.client import (
    AddCartItemRequest,
    CartContainsResponse,
    CartItem,
    CartItemsResponse,
    OkResponse,
    RemovedCartItemResponse,
    RestoreCartItemRequest,
)


class ClientCartService:
    def __init__(self) -> None:
        self.repository = ClientRepository()

    def list_items(self, user_id: str) -> CartItemsResponse:
        raw_items = self.repository.cart_list(user_id)
        return CartItemsResponse(
            items=[self._to_cart_item(item) for item in raw_items]
        )

    def clear(self, user_id: str) -> OkResponse:
        self.repository.cart_clear(user_id)
        return OkResponse(ok=True)

    def contains(self, user_id: str, service_id: str) -> CartContainsResponse:
        item = self.repository.cart_get(user_id, service_id)
        return CartContainsResponse(contains=item is not None)

    def add(self, user_id: str, payload: AddCartItemRequest) -> CartItem:
        existing = self.repository.cart_get(user_id, payload.service_id)
        if existing:
            raise ResourceConflictError(
                detail="Service already in cart",
                code="CART_DUPLICATE_ITEM",
            )

        created = self.repository.cart_create(
            user_id=user_id,
            item_id=payload.service_id,
            payload={
                "name": payload.name,
                "quantity": 1,
                "unit_price_cents": payload.unit_price_cents,
            },
        )
        return self._to_cart_item(created)

    def remove(self, user_id: str, item_id: str) -> RemovedCartItemResponse:
        removed = self.repository.cart_delete(user_id, item_id)
        if not removed:
            raise ResourceNotFoundError("Cart item not found")
        return RemovedCartItemResponse(item=self._to_cart_item(removed))

    def restore(self, user_id: str, payload: RestoreCartItemRequest) -> OkResponse:
        self.repository.cart_create(
            user_id=user_id,
            item_id=payload.item.id,
            payload={
                "name": payload.item.name,
                "quantity": payload.item.quantity,
                "unit_price_cents": payload.item.unit_price_cents,
                "restored_index": payload.index,
            },
        )
        return OkResponse(ok=True)

    @staticmethod
    def _to_cart_item(data: dict) -> CartItem:
        return CartItem(
            id=data["id"],
            name=data["name"],
            quantity=int(data.get("quantity", 1)),
            unit_price_cents=int(data.get("unit_price_cents", 0)),
        )

