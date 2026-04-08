from time import perf_counter

from app.core.exceptions import ResourceConflictError, ResourceNotFoundError
from app.repositories.client_repository import ClientRepository
from app.services.client_cache import invalidate_user_bootstrap_cart_cache
from app.services.performance_logging import estimate_payload_bytes
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

    def list_items(
        self,
        user_id: str,
        *,
        include_metrics: bool = False,
    ) -> CartItemsResponse | tuple[CartItemsResponse, dict]:
        start_ts = perf_counter()
        db_start = perf_counter()
        raw_items = self.repository.cart_list(user_id)
        db_ms = (perf_counter() - db_start) * 1000
        map_start = perf_counter()
        response = CartItemsResponse(
            items=[self._to_cart_item(item) for item in raw_items]
        )
        mapping_ms = (perf_counter() - map_start) * 1000
        metrics = {
            "total_ms": (perf_counter() - start_ts) * 1000,
            "db_ms": db_ms,
            "mapping_ms": mapping_ms,
            "db_reads": 1,
            "items_count": len(response.items),
            "payload_bytes": estimate_payload_bytes(response.model_dump()),
        }
        return (response, metrics) if include_metrics else response

    def clear(self, user_id: str) -> OkResponse:
        self.repository.cart_clear(user_id)
        invalidate_user_bootstrap_cart_cache(user_id)
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

        if payload.product_id:
            lookup = self.repository.visible_product_by_service_and_id(
                service_id=payload.service_id,
                product_id=payload.product_id,
            )
            if not lookup:
                raise ResourceNotFoundError("Service or product not found", code="NOT_FOUND")
            service, product = lookup
            product_name = payload.product_name or str(product.get("name") or "")
            price = int(product.get("unit_price_cents", payload.unit_price_cents) or payload.unit_price_cents)
            service_name = str(service.get("name") or payload.name)
        else:
            service = self.repository.visible_service_by_id(payload.service_id)
            if not service:
                raise ResourceNotFoundError("Service not found", code="NOT_FOUND")
            price = int(service.get("unit_price_cents", payload.unit_price_cents) or payload.unit_price_cents)
            service_name = str(service.get("name") or payload.name)
            product_name = None

        created = self.repository.cart_create(
            user_id=user_id,
            item_id=payload.service_id,
            payload={
                "name": payload.name,
                "quantity": 1,
                "unit_price_cents": price,
                "service_name": service_name,
                "product_id": payload.product_id,
                "product_name": product_name,
            },
        )
        invalidate_user_bootstrap_cart_cache(user_id)
        return self._to_cart_item(created)

    def remove(self, user_id: str, item_id: str) -> RemovedCartItemResponse:
        removed = self.repository.cart_delete(user_id, item_id)
        if not removed:
            raise ResourceNotFoundError("Cart item not found", code="NOT_FOUND")
        invalidate_user_bootstrap_cart_cache(user_id)
        return RemovedCartItemResponse(item=self._to_cart_item(removed))

    def restore(self, user_id: str, payload: RestoreCartItemRequest) -> OkResponse:
        self.repository.cart_create(
            user_id=user_id,
            item_id=payload.item.id,
            payload={
                "name": payload.item.name,
                "quantity": payload.item.quantity,
                "unit_price_cents": payload.item.unit_price_cents,
                "service_name": payload.item.service_name,
                "product_id": payload.item.product_id,
                "product_name": payload.item.product_name,
                "restored_index": payload.index,
            },
        )
        invalidate_user_bootstrap_cart_cache(user_id)
        return OkResponse(ok=True)

    @staticmethod
    def _to_cart_item(data: dict) -> CartItem:
        return CartItem(
            id=data["id"],
            name=data["name"],
            quantity=int(data.get("quantity", 1)),
            unit_price_cents=int(data.get("unit_price_cents", 0)),
            service_name=str(data.get("service_name") or data.get("name") or ""),
            product_id=data.get("product_id"),
            product_name=data.get("product_name"),
        )
