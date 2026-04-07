import logging

from app.core.exceptions import ApiError, ResourceConflictError, ResourceNotFoundError
from app.repositories.order_request_repository import OrderRequestRepository
from app.repositories.provider_availability_repository import ProviderAvailabilityRepository
from app.repositories.provider_booking_repository import ProviderBookingRepository
from app.schemas.provider_availability import ProviderAvailabilityBookingSummary
from app.schemas.provider_order_request import (
    ProviderOrderRequestDecisionPayload,
    ProviderOrderRequestDecisionResponse,
    ProviderOrderRequestListResponse,
    ProviderOrderRequestResponse,
    ProviderOrderSummaryResponse,
)
from app.services.push_notification_service import PushNotificationService

logger = logging.getLogger(__name__)


class ProviderOrderRequestService:
    def __init__(self) -> None:
        self.repository = OrderRequestRepository()
        self.booking_repository = ProviderBookingRepository()
        self.availability_repository = ProviderAvailabilityRepository()
        self.push_notification_service = PushNotificationService()

    def list_requests(
        self,
        provider_id: str,
        status: str | None = "pending_provider_approval",
    ) -> ProviderOrderRequestListResponse:
        items = self.repository.list_provider_requests(provider_id, status=status)
        return ProviderOrderRequestListResponse(
            items=[ProviderOrderRequestResponse(**item) for item in items],
            total=len(items),
        )

    def decide_request(
        self,
        provider_id: str,
        request_id: str,
        payload: ProviderOrderRequestDecisionPayload,
    ) -> ProviderOrderRequestDecisionResponse:
        request_doc = self.repository.get_provider_request(provider_id, request_id)
        if not request_doc:
            raise ResourceNotFoundError("Order request not found", code="NOT_FOUND")

        current_status = str(request_doc.get("status") or "")
        if current_status != "pending_provider_approval":
            raise ResourceConflictError(
                detail="Order request is not pending",
                code="ORDER_REQUEST_NOT_PENDING",
            )

        decision = payload.decision
        order_id = str(request_doc.get("order_id") or "")
        client_id = str(request_doc.get("client_id") or "")
        if not order_id or not client_id:
            raise ApiError(
                detail="Order request is malformed",
                code="ORDER_REQUEST_INVALID",
            )

        created_bookings: list[tuple[str, str, str, str]] = []
        if decision == "accepted":
            try:
                for item in list(request_doc.get("items") or []):
                    booking_id = self.booking_repository.generate_id(provider_id)
                    product_id = str(item.get("product_id") or "")
                    product_name = str(item.get("product_name") or "")
                    selected_product_ids = list(item.get("selected_product_ids") or [])
                    selected_products_snapshot = list(item.get("selected_products_snapshot") or [])
                    event_date = str(request_doc.get("event_date") or "")
                    total_item_cents = int(item.get("total_item_cents", item.get("unit_price_cents", 0)) or 0)

                    booking_payload = {
                        "service_id": str(item.get("service_id") or ""),
                        "service_name": str(item.get("service_name") or ""),
                        "product_id": product_id,
                        "product_name": product_name,
                        "selected_product_ids": selected_product_ids,
                        "selected_products_snapshot": selected_products_snapshot,
                        "customer_name": str(request_doc.get("client_name") or "Cliente"),
                        "customer_image_url": "",
                        "event_date": event_date,
                        "has_specific_schedule": False,
                        "start_time": "",
                        "end_time": "",
                        "event_type": "Evento",
                        "guests": 0,
                        "contact_phone": "",
                        "contact_email": "",
                        "event_location": "",
                        "payment_details": "",
                        "total_amount": float(total_item_cents) / 100,
                        "paid_amount": 0,
                        "notes": str(request_doc.get("notes") or ""),
                        "source": "client",
                        "status": "confirmed",
                        "order_id": order_id,
                        "client_id": client_id,
                    }
                    self.booking_repository.create(provider_id, booking_id, booking_payload)
                    if product_id:
                        self.availability_repository.reserve_date(
                            provider_id=provider_id,
                            service_id=str(item.get("service_id") or ""),
                            product_id=product_id,
                            date_key=event_date,
                            booking_summary=self._build_availability_summary(
                                booking_id=booking_id,
                                client_name=str(request_doc.get("client_name") or "Cliente"),
                                event_date=event_date,
                                total_amount=float(total_item_cents) / 100,
                            ),
                        )
                    created_bookings.append((booking_id, str(item.get("service_id") or ""), product_id, event_date))
            except Exception:
                self._rollback_created_bookings(provider_id, created_bookings)
                raise

        try:
            order_doc = self.repository.decide_provider_request(
                provider_id=provider_id,
                request_id=request_id,
                decision=decision,
                order_id=order_id,
                client_id=client_id,
            )
        except Exception:
            self._rollback_created_bookings(provider_id, created_bookings)
            raise

        self._notify_client_order_request_decision(
            provider_id=provider_id,
            client_id=client_id,
            request_id=request_id,
            order_id=order_id,
            decision=decision,
        )

        return ProviderOrderRequestDecisionResponse(
            order=ProviderOrderSummaryResponse(
                id=str(order_doc.get("id") or ""),
                title=str(order_doc.get("title") or ""),
                status=str(order_doc.get("status") or decision),
                subtotal_cents=int(order_doc.get("subtotal_cents", 0) or 0),
                service_fee_cents=int(order_doc.get("service_fee_cents", 0) or 0),
                tax_cents=int(order_doc.get("tax_cents", 0) or 0),
                total_cents=int(order_doc.get("total_cents", 0) or 0),
                currency=str(order_doc.get("currency") or "MXN"),
                fee_rate=float(order_doc.get("fee_rate", 0) or 0),
                tax_rate=float(order_doc.get("tax_rate", 0) or 0),
                total_label=str(order_doc.get("total_label") or ""),
                created_at=order_doc.get("created_at"),
            )
        )

    @staticmethod
    def _build_availability_summary(
        *,
        booking_id: str,
        client_name: str,
        event_date: str,
        total_amount: float,
    ) -> dict:
        summary = ProviderAvailabilityBookingSummary(
            id=booking_id,
            booking_id=booking_id,
            customer_name=client_name,
            customer_image_url="",
            date=event_date,
            time="Todo el dia",
            event_type="Evento",
            guests=0,
            total_amount=total_amount,
            paid_amount=0,
            status="Confirmada",
            notes="Reserva creada desde solicitud de orden",
        )
        return summary.model_dump(mode="json")

    def _rollback_created_bookings(
        self,
        provider_id: str,
        created_bookings: list[tuple[str, str, str, str]],
    ) -> None:
        for booking_id, service_id, product_id, event_date in created_bookings:
            self.booking_repository.delete(provider_id, booking_id)
            if product_id:
                self.availability_repository.clear_reserved_date(
                    provider_id=provider_id,
                    service_id=service_id,
                    product_id=product_id,
                    date_key=event_date,
                    booking_id=booking_id,
                )

    def _notify_client_order_request_decision(
        self,
        *,
        provider_id: str,
        client_id: str,
        request_id: str,
        order_id: str,
        decision: str,
    ) -> None:
        notification_type = "order_accepted" if decision == "accepted" else "order_rejected"
        body = (
            "Tu solicitud fue aceptada por el proveedor."
            if decision == "accepted"
            else "Tu solicitud fue rechazada por el proveedor."
        )
        try:
            self.push_notification_service.send_to_user(
                user_id=client_id,
                title="Solicitud de orden actualizada",
                body=body,
                data={
                    "type": notification_type,
                    "order_id": order_id,
                    "request_id": request_id,
                    "target_screen": "client_orders",
                },
                context={
                    "actor": "provider",
                    "provider_id": provider_id,
                    "client_id": client_id,
                    "order_id": order_id,
                    "request_id": request_id,
                    "trace_id": request_id,
                },
            )
        except Exception:
            logger.exception(
                "push_order_request_decision_failed",
                extra={
                    "client_id": client_id,
                    "request_id": request_id,
                    "order_id": order_id,
                    "decision": decision,
                },
            )
