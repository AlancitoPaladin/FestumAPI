from datetime import date
import hashlib
import logging
from random import randint
from uuid import uuid4

from app.core.config import get_settings
from app.core.exceptions import ApiError, ForbiddenError, ResourceConflictError, ResourceNotFoundError
from app.repositories.client_repository import ClientRepository
from app.repositories.order_request_repository import OrderRequestRepository
from app.repositories.provider_availability_repository import ProviderAvailabilityRepository
from app.schemas.client import (
    CheckoutItemResponse,
    CheckoutOrderResponse,
    CheckoutProviderEffectsResponse,
    CheckoutRequestPayload,
    CheckoutResponse,
    CreateOrderRequestPayload,
    CreateOrderRequest,
    OrderRequestCreateResponse,
    OkResponse,
    OrderItem,
    OrdersResponse,
    UpdateOrderStatusRequest,
)
from app.schemas.user import UserResponse

logger = logging.getLogger(__name__)

VALID_TRANSITIONS: dict[str, set[str]] = {
    "pending_provider_approval": {"cancelled", "pending_payment", "confirmed"},
    "pending_payment": {"confirmed", "cancelled"},
    "confirmed": {"in_progress", "cancelled"},
    "in_progress": {"completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
    "rejected": set(),
}


class ClientOrdersService:
    def __init__(self) -> None:
        self.repository = ClientRepository()
        self.order_request_repository = OrderRequestRepository()
        self.availability_repository = ProviderAvailabilityRepository()
        self.settings = get_settings()

    def list_orders(self, user_id: str) -> OrdersResponse:
        items = self.repository.order_list(user_id)
        normalized: list[OrderItem] = []
        for item in items:
            enriched = self._enrich_order_payload(item)
            missing_financials = any(
                enriched.get(field) is None
                for field in ("subtotal_cents", "service_fee_cents", "tax_cents", "total_cents")
            )
            if missing_financials:
                self.repository.order_update_fields(
                    user_id=user_id,
                    order_id=str(enriched.get("id") or ""),
                    payload={
                        "subtotal_cents": None,
                        "service_fee_cents": None,
                        "tax_cents": None,
                        "total_cents": None,
                        "currency": self.settings.order_currency,
                        "fee_rate": self.settings.order_fee_rate,
                        "tax_rate": self.settings.order_tax_rate,
                    },
                )
            else:
                self.repository.order_update_fields(
                    user_id=user_id,
                    order_id=str(enriched.get("id") or ""),
                    payload={
                        "items": enriched.get("items", []),
                        "subtotal_cents": enriched.get("subtotal_cents"),
                        "service_fee_cents": enriched.get("service_fee_cents"),
                        "tax_cents": enriched.get("tax_cents"),
                        "total_cents": enriched.get("total_cents"),
                        "currency": enriched.get("currency"),
                        "fee_rate": enriched.get("fee_rate"),
                        "tax_rate": enriched.get("tax_rate"),
                        "total_label": enriched.get("total_label"),
                    },
                )

            normalized.append(OrderItem(**enriched))

        return OrdersResponse(items=normalized)

    def create_order(self, user_id: str, payload: CreateOrderRequest | None = None) -> OrderItem:
        cart_items = self.repository.cart_list(user_id)
        if not cart_items:
            raise ResourceConflictError(
                detail="Cart is empty",
                code="CART_EMPTY",
            )

        validated_items: list[dict] = []
        total_cents = 0
        for item in cart_items:
            service_id = str(item.get("id") or "")
            product_id = item.get("product_id")
            if not service_id:
                raise ResourceNotFoundError("Service not found", code="NOT_FOUND")

            if product_id:
                lookup = self.repository.visible_product_by_service_and_id(service_id, str(product_id))
                if not lookup:
                    raise ResourceNotFoundError("Service or product not found", code="NOT_FOUND")
                service, product = lookup
                product_price = self._resolve_product_unit_price_cents(product)
                if product_price is None or product_price <= 0:
                    raise ApiError(
                        detail=f"Invalid selected products for service: {str(product_id)}",
                        code="INVALID_SELECTED_PRODUCTS",
                        message="Invalid selected products",
                    )
                price = product_price
                product_name = str(product.get("name") or item.get("product_name") or "")
            else:
                service = self.repository.visible_service_by_id(service_id)
                if not service:
                    raise ResourceNotFoundError("Service not found", code="NOT_FOUND")
                price = int(service.get("unit_price_cents", item.get("unit_price_cents", 0)) or 0)
                product_name = None

            service_name = str(service.get("name") or item.get("service_name") or item.get("name") or "")
            validated_items.append(
                {
                    "service_id": service_id,
                    "service_name": service_name,
                    "product_id": str(product_id) if product_id else None,
                    "product_name": product_name,
                    "selected_product_ids": [str(product_id)] if product_id else [],
                    "selected_products_snapshot": (
                        [
                            {
                                "id": str(product_id),
                                "name": product_name or "",
                                "unit_price_cents": price,
                            }
                        ]
                        if product_id
                        else []
                    ),
                    "quantity": 1,
                    "unit_price_cents": price,
                    "total_item_cents": price,
                }
            )
            total_cents += price

        primary_service = validated_items[0]["service_name"] if validated_items else "Servicio"
        title = (
            primary_service
            if len(validated_items) == 1
            else f"{primary_service} +{len(validated_items) - 1} servicios"
        )
        financials = self._calculate_order_financials(total_cents)
        total_label = self._format_mxn(financials["total_cents"])

        order_id = f"FST-{randint(1000, 9999)}"
        created = self.repository.order_create(
            user_id=user_id,
            payload={
                "id": order_id,
                "title": title,
                "status": "pending_payment",
                "subtotal_cents": financials["subtotal_cents"],
                "service_fee_cents": financials["service_fee_cents"],
                "tax_cents": financials["tax_cents"],
                "total_cents": financials["total_cents"],
                "currency": financials["currency"],
                "fee_rate": financials["fee_rate"],
                "tax_rate": financials["tax_rate"],
                "total_label": total_label,
                "items": validated_items,
            },
        )
        self.repository.cart_clear(user_id)
        return OrderItem(**created)

    def checkout(
        self,
        current_user: UserResponse,
        payload: CheckoutRequestPayload | None = None,
    ) -> CheckoutResponse:
        if current_user.role != "client":
            raise ForbiddenError("Only client users can perform checkout")

        cart_items = self.repository.cart_list(current_user.id)
        source_items: list[dict]
        if payload and payload.items:
            source_items = [
                {
                    "id": item.service_id,
                    "service_id": item.service_id,
                    "product_id": item.product_id,
                    "selected_product_ids": item.selected_product_ids or [],
                }
                for item in payload.items
            ]
        else:
            source_items = cart_items

        if not source_items:
            raise ApiError(
                detail="Cart is empty",
                code="CHECKOUT_EMPTY_CART",
            )

        validated_items: list[dict] = []
        provider_actions: list[dict] = []
        total_cents = 0
        customer_name = f"{current_user.first_name} {current_user.last_name}".strip()

        for item in source_items:
            service_id = str(item.get("id") or item.get("service_id") or "")
            if not service_id:
                raise ResourceNotFoundError("Service not found", code="SERVICE_NOT_FOUND")

            service = self.repository.service_by_id(service_id)
            if not service:
                raise ResourceNotFoundError("Service not found", code="SERVICE_NOT_FOUND")
            if not self._is_service_available(service):
                raise ResourceConflictError(
                    detail="Service is not available for checkout",
                    code="SERVICE_NOT_AVAILABLE",
                )

            provider_id = str(service.get("provider_id") or "")
            if not provider_id:
                raise ResourceConflictError(
                    detail="Service provider is missing",
                    code="CHECKOUT_FAILED",
                )

            resolved_products = self._resolve_selected_products(
                service_id=service_id,
                item=item,
            )
            selected_product_ids = resolved_products["selected_product_ids"]
            selected_products_snapshot = resolved_products["selected_products_snapshot"]
            product_id = resolved_products["product_id"]
            product_name = resolved_products["product_name"]

            service_base_cents = int(service.get("unit_price_cents", item.get("unit_price_cents", 0)) or 0)
            addons_cents = int(resolved_products["selected_total_cents"])
            unit_price_cents = service_base_cents + addons_cents

            service_name = str(service.get("name") or item.get("service_name") or item.get("name") or "")
            validated_item = {
                "service_id": service_id,
                "service_name": service_name,
                "provider_id": provider_id,
                "product_id": product_id,
                "product_name": product_name,
                "selected_product_ids": selected_product_ids,
                "selected_products_snapshot": selected_products_snapshot,
                "quantity": 1,
                "unit_price_cents": unit_price_cents,
                "total_item_cents": unit_price_cents,
            }
            validated_items.append(validated_item)
            total_cents += unit_price_cents

        checkout_key = self._build_checkout_key(current_user.id, source_items)
        order_id = f"FST-{checkout_key[:10].upper()}"
        primary_service = validated_items[0]["service_name"]
        title = (
            primary_service
            if len(validated_items) == 1
            else f"{primary_service} +{len(validated_items) - 1} servicios"
        )
        financials = self._calculate_order_financials(total_cents)
        total_label = self._format_mxn(financials["total_cents"])

        for index, item in enumerate(validated_items):
            provider_id = item["provider_id"]
            reservation_id = f"{order_id}-R{index + 1}"
            notification_id = f"checkout-{order_id}-{index + 1}"
            total_amount = item["unit_price_cents"] / 100

            provider_actions.append(
                {
                    "provider_id": provider_id,
                    "reservation_id": reservation_id,
                    "reservation_payload": {
                        "service_id": item["service_id"],
                        "service_name": item["service_name"],
                        "product_id": item["product_id"] or "",
                        "product_name": item["product_name"] or "",
                        "selected_product_ids": item["selected_product_ids"],
                        "selected_products_snapshot": item["selected_products_snapshot"],
                        "customer_name": customer_name or "Cliente",
                        "customer_image_url": "",
                        "event_date": date.today().isoformat(),
                        "has_specific_schedule": False,
                        "start_time": "",
                        "end_time": "",
                        "event_type": "Por definir",
                        "guests": 0,
                        "contact_phone": str(current_user.phone or ""),
                        "contact_email": str(current_user.email or ""),
                        "event_location": "",
                        "payment_details": "",
                        "total_amount": total_amount,
                        "paid_amount": 0,
                        "notes": f"Reserva creada por checkout {order_id}",
                        "source": "client",
                        "status": "pending",
                        "order_id": order_id,
                    },
                    "notification_id": notification_id,
                    "notification_payload": {
                        "title": "Nueva reserva desde checkout",
                        "subtitle": f"{item['service_name']} · {customer_name or 'Cliente'}",
                        "booking_id": reservation_id,
                        "order_id": order_id,
                        "service_id": item["service_id"],
                        "product_id": item["product_id"] or "",
                        "selected_product_ids": item["selected_product_ids"],
                        "selected_products_snapshot": item["selected_products_snapshot"],
                        "notification_type": "checkout_created",
                    },
                }
            )

        try:
            created = self.repository.checkout_commit(
                user_id=current_user.id,
                order_payload={
                    "id": order_id,
                    "title": title,
                    "status": "pending_payment",
                    "subtotal_cents": financials["subtotal_cents"],
                    "service_fee_cents": financials["service_fee_cents"],
                    "tax_cents": financials["tax_cents"],
                    "total_cents": financials["total_cents"],
                    "currency": financials["currency"],
                    "fee_rate": financials["fee_rate"],
                    "tax_rate": financials["tax_rate"],
                    "total_label": total_label,
                    "items": validated_items,
                },
                cart_item_ids=[str(item["id"]) for item in cart_items if item.get("id")],
                provider_actions=provider_actions,
                checkout_key=checkout_key,
            )
        except ApiError:
            raise
        except Exception as exc:
            checkout_error = ApiError(
                detail="Checkout failed",
                code="CHECKOUT_FAILED",
            )
            checkout_error.status_code = 500
            raise checkout_error from exc

        return CheckoutResponse(
            order=CheckoutOrderResponse(
                id=created["id"],
                title=created["title"],
                status=created["status"],
                subtotal_cents=int(created.get("subtotal_cents", financials["subtotal_cents"]) or 0),
                service_fee_cents=int(created.get("service_fee_cents", financials["service_fee_cents"]) or 0),
                tax_cents=int(created.get("tax_cents", financials["tax_cents"]) or 0),
                total_cents=int(created.get("total_cents", financials["total_cents"]) or 0),
                currency=str(created.get("currency") or financials["currency"]),
                fee_rate=float(created.get("fee_rate", financials["fee_rate"]) or 0),
                tax_rate=float(created.get("tax_rate", financials["tax_rate"]) or 0),
                total_label=str(created.get("total_label") or total_label),
                created_at=created["created_at"],
            ),
            items=[
                CheckoutItemResponse(
                    service_id=item["service_id"],
                    service_name=item["service_name"],
                    product_id=item["product_id"],
                    product_name=item["product_name"],
                    selected_product_ids=item["selected_product_ids"],
                    selected_products_snapshot=item["selected_products_snapshot"],
                    unit_price_cents=item["unit_price_cents"],
                    total_item_cents=item["total_item_cents"],
                )
                for item in validated_items
            ],
            provider_effects=CheckoutProviderEffectsResponse(
                reservations_created=int(created.get("reservations_created", len(provider_actions)) or 0),
                notifications_created=int(created.get("notifications_created", len(provider_actions)) or 0),
            ),
        )

    def create_order_request(
        self,
        current_user: UserResponse,
        payload: CreateOrderRequestPayload,
    ) -> OrderRequestCreateResponse:
        if current_user.role != "client":
            raise ForbiddenError("Only client users can perform this action")

        if payload.event_date < date.today():
            event_date_error = ApiError(
                detail="event_date cannot be in the past",
                code="VALIDATION_ERROR",
                message="Validation failed",
            )
            event_date_error.status_code = 422
            raise event_date_error

        validated_items: list[dict] = []
        total_cents = 0
        for item in payload.items:
            service = self.repository.service_by_id(item.service_id)
            if not service:
                raise ResourceNotFoundError("Service not found", code="SERVICE_NOT_FOUND")
            if not self._is_service_available(service):
                raise ResourceConflictError(
                    detail="Service is not available for checkout",
                    code="SERVICE_NOT_AVAILABLE",
                )

            provider_id = str(service.get("provider_id") or "")
            if not provider_id:
                raise ResourceConflictError(
                    detail="Service provider is missing",
                    code="CHECKOUT_FAILED",
                )

            normalized_item = {
                "service_id": item.service_id,
                "product_id": item.product_id,
                "selected_product_ids": item.selected_product_ids or [],
            }
            resolved_products = self._resolve_selected_products(
                service_id=item.service_id,
                item=normalized_item,
            )
            product_id = resolved_products["product_id"]
            product_name = resolved_products["product_name"]
            selected_product_ids = resolved_products["selected_product_ids"]
            selected_products_snapshot = resolved_products["selected_products_snapshot"]
            service_base_cents = int(service.get("unit_price_cents", 0) or 0)
            unit_price_cents = service_base_cents + int(resolved_products["selected_total_cents"])

            service_name = str(service.get("name") or item.service_name or "")
            validated_items.append(
                {
                    "service_id": item.service_id,
                    "service_name": service_name,
                    "product_id": product_id,
                    "product_name": product_name,
                    "selected_product_ids": selected_product_ids,
                    "selected_products_snapshot": selected_products_snapshot,
                    "provider_id": provider_id,
                    "unit_price_cents": unit_price_cents,
                    "total_item_cents": unit_price_cents,
                }
            )
            total_cents += unit_price_cents

        order_id = f"FST-REQ-{randint(100000, 999999)}"
        primary_service = validated_items[0]["service_name"] if validated_items else "Servicio"
        title = (
            primary_service
            if len(validated_items) == 1
            else f"{primary_service} +{len(validated_items) - 1} servicios"
        )

        financials = self._calculate_order_financials(total_cents)
        grouped_by_provider: dict[str, list[dict]] = {}
        for item in validated_items:
            grouped_by_provider.setdefault(item["provider_id"], []).append(item)

        provider_requests: list[dict] = []
        provider_notifications: list[dict] = []
        client_name = f"{current_user.first_name} {current_user.last_name}".strip() or "Cliente"
        for index, (provider_id, items) in enumerate(grouped_by_provider.items(), start=1):
            request_id = f"{order_id}-P{index}"
            selected_ids_for_provider = list(
                dict.fromkeys(
                    [
                        selected_id
                        for provider_item in items
                        for selected_id in provider_item.get("selected_product_ids", [])
                    ]
                )
            )
            selected_snapshot_for_provider = [
                snapshot
                for provider_item in items
                for snapshot in provider_item.get("selected_products_snapshot", [])
            ]
            provider_requests.append(
                {
                    "id": request_id,
                    "order_id": order_id,
                    "client_id": current_user.id,
                    "client_name": client_name,
                    "event_date": payload.event_date.isoformat(),
                    "notes": payload.notes,
                    "title": title,
                    "status": "pending_provider_approval",
                    **self._calculate_order_financials(sum(int(item["total_item_cents"]) for item in items)),
                    "total_label": self._format_mxn(
                        self._calculate_order_financials(sum(int(item["total_item_cents"]) for item in items))[
                            "total_cents"
                        ]
                    ),
                    "items": items,
                    "provider_id": provider_id,
                }
            )
            provider_notifications.append(
                {
                    "provider_id": provider_id,
                    "id": f"order-request-{request_id}",
                    "payload": {
                        "title": "Nueva solicitud de orden",
                        "subtitle": f"{title} · {client_name}",
                        "type": "order_request_created",
                        "source": "client_order_request",
                        "order_id": order_id,
                        "request_id": request_id,
                        "selected_product_ids": selected_ids_for_provider,
                        "selected_products_snapshot": selected_snapshot_for_provider,
                        "event_date": payload.event_date.isoformat(),
                    },
                }
            )

        created = self.order_request_repository.create_request(
            client_id=current_user.id,
            order_payload={
                "id": order_id,
                "title": title,
                "status": "pending_provider_approval",
                **financials,
                "total_label": self._format_mxn(financials["total_cents"]),
                "event_date": payload.event_date.isoformat(),
                "notes": payload.notes,
                "items": validated_items,
                "flow": "order_request",
            },
            provider_requests=provider_requests,
            provider_notifications=provider_notifications,
        )

        return OrderRequestCreateResponse(
            order=CheckoutOrderResponse(
                id=created["id"],
                title=str(created.get("title") or title),
                status=str(created.get("status") or "pending_provider_approval"),
                subtotal_cents=int(created.get("subtotal_cents", financials["subtotal_cents"]) or 0),
                service_fee_cents=int(created.get("service_fee_cents", financials["service_fee_cents"]) or 0),
                tax_cents=int(created.get("tax_cents", financials["tax_cents"]) or 0),
                total_cents=int(created.get("total_cents", financials["total_cents"]) or 0),
                currency=str(created.get("currency") or financials["currency"]),
                fee_rate=float(created.get("fee_rate", financials["fee_rate"]) or 0),
                tax_rate=float(created.get("tax_rate", financials["tax_rate"]) or 0),
                total_label=str(created.get("total_label") or self._format_mxn(financials["total_cents"])),
                created_at=created["created_at"],
            )
        )

    def update_status(
        self,
        user_id: str,
        order_id: str,
        payload: UpdateOrderStatusRequest,
        *,
        actor: str = "client",
        trace_id: str | None = None,
    ) -> OkResponse:
        current = self.repository.order_get(user_id, order_id)
        if not current:
            raise ResourceNotFoundError("Order not found", code="NOT_FOUND")

        current_status = current["status"]
        next_status = payload.status
        active_trace_id = trace_id or str(uuid4())

        if next_status == current_status and next_status == "cancelled":
            return OkResponse(ok=True, idempotent=True)

        allowed_next = VALID_TRANSITIONS.get(str(current_status), set())
        if next_status != current_status and next_status not in allowed_next:
            self._log_status_conflict(
                order_id=order_id,
                current_status=str(current_status),
                requested_status=str(next_status),
                actor=actor,
                trace_id=active_trace_id,
            )
            raise ResourceConflictError(
                detail=f"Invalid transition: {current_status} -> {next_status}",
                code="ORDER_INVALID_TRANSITION",
                message=f"Order transition conflict: {current_status} -> {next_status}",
            )

        if next_status == "confirmed" and current_status == "pending_payment":
            latest = self.repository.order_get(user_id, order_id)
            latest_status = str((latest or {}).get("status") or current_status)
            if latest_status in {"cancelled", "rejected"}:
                self._log_status_conflict(
                    order_id=order_id,
                    current_status=latest_status,
                    requested_status=str(next_status),
                    actor=actor,
                    trace_id=active_trace_id,
                )
                raise ResourceConflictError(
                    detail=f"Invalid transition: {latest_status} -> {next_status}",
                    code="ORDER_INVALID_TRANSITION",
                    message=f"Order transition conflict: {latest_status} -> {next_status}",
                )

        self.repository.order_update_status(user_id, order_id, next_status)
        if next_status == "cancelled":
            related = self.order_request_repository.cancel_related_entities(
                client_id=user_id,
                order_id=order_id,
            )
            for target in related.get("availability_release_targets", []):
                try:
                    self.availability_repository.clear_reserved_date(
                        provider_id=str(target.get("provider_id") or ""),
                        service_id=str(target.get("service_id") or ""),
                        product_id=str(target.get("product_id") or ""),
                        date_key=str(target.get("event_date") or ""),
                        booking_id=str(target.get("booking_id") or ""),
                    )
                except Exception:
                    logger.exception(
                        "order_cancel_availability_release_failed",
                        extra={
                            "order_id": order_id,
                            "current_status": current_status,
                            "requested_status": next_status,
                            "actor": actor,
                            "trace_id": active_trace_id,
                        },
                    )
        return OkResponse(ok=True, idempotent=False)

    def _enrich_order_payload(self, payload: dict) -> dict:
        items = self._normalize_order_items(list(payload.get("items") or []))
        computed_subtotal = sum(int(item.get("total_item_cents", 0) or 0) for item in items) if items else None

        subtotal_cents = payload.get("subtotal_cents")
        service_fee_cents = payload.get("service_fee_cents")
        tax_cents = payload.get("tax_cents")
        total_cents = payload.get("total_cents")

        if subtotal_cents is None and computed_subtotal is not None:
            financials = self._calculate_order_financials(computed_subtotal)
            subtotal_cents = financials["subtotal_cents"]
            service_fee_cents = financials["service_fee_cents"]
            tax_cents = financials["tax_cents"]
            total_cents = financials["total_cents"]
            currency = payload.get("currency") or financials["currency"]
            fee_rate = payload.get("fee_rate", financials["fee_rate"])
            tax_rate = payload.get("tax_rate", financials["tax_rate"])
        elif subtotal_cents is None:
            currency = payload.get("currency") or self.settings.order_currency
            fee_rate = payload.get("fee_rate", self.settings.order_fee_rate)
            tax_rate = payload.get("tax_rate", self.settings.order_tax_rate)
        else:
            currency = payload.get("currency") or self.settings.order_currency
            fee_rate = payload.get("fee_rate", self.settings.order_fee_rate)
            tax_rate = payload.get("tax_rate", self.settings.order_tax_rate)

        normalized = {
            **payload,
            "items": items,
            "subtotal_cents": int(subtotal_cents) if subtotal_cents is not None else None,
            "service_fee_cents": int(service_fee_cents) if service_fee_cents is not None else None,
            "tax_cents": int(tax_cents) if tax_cents is not None else None,
            "total_cents": int(total_cents) if total_cents is not None else None,
            "currency": str(currency),
            "fee_rate": float(fee_rate),
            "tax_rate": float(tax_rate),
            "total_label": str(
                payload.get("total_label")
                or self._format_mxn(int(total_cents))
                if total_cents is not None
                else payload.get("total_label", "")
            ),
        }
        return normalized

    def _normalize_order_items(self, items: list[dict]) -> list[dict]:
        normalized: list[dict] = []
        for item in items:
            selected_ids = list(item.get("selected_product_ids") or [])
            snapshots = list(item.get("selected_products_snapshot") or [])
            if not selected_ids and item.get("product_id"):
                selected_ids = [str(item.get("product_id"))]

            normalized_item = {
                **item,
                "product_id": item.get("product_id"),
                "selected_product_ids": selected_ids,
                "selected_products_snapshot": snapshots,
            }
            normalized_item = self._try_rehydrate_item_pricing(normalized_item)
            total_item_cents = int(
                normalized_item.get("total_item_cents", normalized_item.get("unit_price_cents", 0)) or 0
            )
            normalized.append(
                {
                    **normalized_item,
                    "total_item_cents": total_item_cents,
                }
            )
        return normalized

    def _try_rehydrate_item_pricing(self, item: dict) -> dict:
        service_id = str(item.get("service_id") or "")
        selected_ids = list(item.get("selected_product_ids") or [])
        snapshots = list(item.get("selected_products_snapshot") or [])
        has_invalid_snapshot = any(int(snapshot.get("unit_price_cents", 0) or 0) <= 0 for snapshot in snapshots)
        if not service_id or not selected_ids:
            return item
        if snapshots and not has_invalid_snapshot and int(item.get("total_item_cents", 0) or 0) > 0:
            return item

        service = self.repository.service_by_id(service_id)
        if not service:
            return item

        try:
            resolved = self._resolve_selected_products(
                service_id=service_id,
                item={
                    "selected_product_ids": selected_ids,
                    "product_id": item.get("product_id"),
                },
            )
        except ApiError:
            return item

        service_base_cents = int(service.get("unit_price_cents", item.get("unit_price_cents", 0)) or 0)
        selected_total_cents = int(resolved.get("selected_total_cents", 0) or 0)
        total_item_cents = service_base_cents + selected_total_cents
        return {
            **item,
            "product_id": resolved.get("product_id"),
            "product_name": resolved.get("product_name"),
            "selected_product_ids": resolved.get("selected_product_ids", []),
            "selected_products_snapshot": resolved.get("selected_products_snapshot", []),
            "unit_price_cents": total_item_cents,
            "total_item_cents": total_item_cents,
        }

    def _calculate_order_financials(self, subtotal_cents: int) -> dict:
        fee_rate = float(self.settings.order_fee_rate)
        tax_rate = float(self.settings.order_tax_rate)
        service_fee_cents = int(round(subtotal_cents * fee_rate))
        tax_cents = int(round((subtotal_cents + service_fee_cents) * tax_rate))
        total_cents = int(subtotal_cents + service_fee_cents + tax_cents)
        return {
            "subtotal_cents": int(subtotal_cents),
            "service_fee_cents": service_fee_cents,
            "tax_cents": tax_cents,
            "total_cents": total_cents,
            "currency": self.settings.order_currency,
            "fee_rate": fee_rate,
            "tax_rate": tax_rate,
        }

    @staticmethod
    def _log_status_conflict(
        *,
        order_id: str,
        current_status: str,
        requested_status: str,
        actor: str,
        trace_id: str,
    ) -> None:
        logger.warning(
            "order_status_conflict",
            extra={
                "order_id": order_id,
                "current_status": current_status,
                "requested_status": requested_status,
                "actor": actor,
                "trace_id": trace_id,
            },
        )

    @staticmethod
    def _format_mxn(total_cents: int) -> str:
        amount = total_cents / 100
        return f"${amount:,.0f} MXN"

    @staticmethod
    def _is_service_available(service: dict) -> bool:
        status = str(service.get("status") or "").strip().lower()
        is_active = service.get("is_active")
        is_published = service.get("is_published")
        status_ok = status in {"published", "active"} if status else True
        active_ok = is_active is not False
        published_ok = is_published is not False
        return status_ok and active_ok and published_ok

    @staticmethod
    def _build_checkout_key(user_id: str, cart_items: list[dict]) -> str:
        normalized = "|".join(
            sorted(
                [
                    (
                        f"{item.get('id','')}:{item.get('product_id','')}:"
                        f"{','.join(item.get('selected_product_ids', []) or [])}:"
                        f"{item.get('updated_at','')}:{item.get('unit_price_cents',0)}"
                    )
                    for item in cart_items
                ]
            )
        )
        raw = f"{user_id}:{normalized}"
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()

    def _resolve_selected_products(
        self,
        *,
        service_id: str,
        item: dict,
    ) -> dict:
        raw_selected = item.get("selected_product_ids")
        if raw_selected:
            selected_ids = [str(product_id).strip() for product_id in raw_selected if str(product_id).strip()]
        else:
            legacy_product_id = str(item.get("product_id") or "").strip()
            selected_ids = [legacy_product_id] if legacy_product_id else []

        deduped_ids = list(dict.fromkeys(selected_ids))
        if not deduped_ids:
            return {
                "selected_product_ids": [],
                "selected_products_snapshot": [],
                "selected_total_cents": 0,
                "product_id": None,
                "product_name": None,
            }

        snapshots: list[dict] = []
        invalid_product_ids: list[str] = []
        selected_total_cents = 0
        for product_id in deduped_ids:
            lookup = self.repository.visible_product_by_service_and_id(service_id, product_id)
            if not lookup:
                invalid_product_ids.append(product_id)
                continue
            _, product = lookup
            product_price = self._resolve_product_unit_price_cents(product)
            if product_price is None or product_price <= 0:
                invalid_product_ids.append(product_id)
                continue
            selected_total_cents += product_price
            snapshots.append(
                {
                    "id": product_id,
                    "name": str(product.get("name") or ""),
                    "unit_price_cents": product_price,
                }
            )

        if invalid_product_ids:
            invalid_products_error = ApiError(
                detail=f"Invalid selected products for service: {', '.join(invalid_product_ids)}",
                code="INVALID_SELECTED_PRODUCTS",
                message="Invalid selected products",
            )
            invalid_products_error.status_code = 422
            raise invalid_products_error

        first_snapshot = snapshots[0] if snapshots else None
        return {
            "selected_product_ids": deduped_ids,
            "selected_products_snapshot": snapshots,
            "selected_total_cents": selected_total_cents,
            "product_id": first_snapshot["id"] if first_snapshot else None,
            "product_name": first_snapshot["name"] if first_snapshot else None,
        }

    @staticmethod
    def _resolve_product_unit_price_cents(product: dict) -> int | None:
        raw_unit_price_cents = product.get("unit_price_cents")
        if raw_unit_price_cents is not None:
            try:
                unit_price_cents = int(raw_unit_price_cents)
                if unit_price_cents > 0:
                    return unit_price_cents
            except (TypeError, ValueError):
                pass

        raw_price = product.get("price")
        if raw_price is None:
            return None
        try:
            price_value = float(raw_price)
        except (TypeError, ValueError):
            return None
        if price_value <= 0:
            return None
        return int(round(price_value * 100))
