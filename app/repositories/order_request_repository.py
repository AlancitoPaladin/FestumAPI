from datetime import datetime, timezone

from google.api_core.exceptions import GoogleAPICallError, PermissionDenied, RetryError

from app.core.exceptions import ServiceUnavailableError
from app.core.firebase import get_firestore_client


class OrderRequestRepository:
    def __init__(self) -> None:
        self.db = get_firestore_client()

    @staticmethod
    def _raise_firestore_unavailable(exc: Exception) -> None:
        raise ServiceUnavailableError(
            "Firestore is unavailable or not configured correctly. Verify Firebase credentials and Cloud Firestore API."
        ) from exc

    def create_request(
        self,
        *,
        client_id: str,
        order_payload: dict,
        provider_requests: list[dict],
        provider_notifications: list[dict],
    ) -> dict:
        try:
            now = datetime.now(tz=timezone.utc)
            order_ref = self._client_orders_collection(client_id).document(str(order_payload["id"]))
            order_data = {
                **order_payload,
                "created_at": now,
                "updated_at": now,
            }

            batch = self.db.batch()
            batch.set(order_ref, order_data, merge=False)

            for request_payload in provider_requests:
                provider_id = str(request_payload["provider_id"])
                request_ref = self._provider_order_requests_collection(provider_id).document(str(request_payload["id"]))
                payload = {
                    **request_payload,
                    "created_at": now,
                    "updated_at": now,
                }
                batch.set(request_ref, payload, merge=False)

            for notification in provider_notifications:
                provider_id = str(notification["provider_id"])
                notification_ref = self._provider_notifications_collection(provider_id).document(str(notification["id"]))
                payload = {
                    **notification["payload"],
                    "is_unread": True,
                    "created_at": now,
                    "updated_at": now,
                }
                batch.set(notification_ref, payload, merge=True)

            batch.commit()
            return {"id": order_ref.id, **order_data}
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def list_provider_requests(self, provider_id: str, status: str | None = None) -> list[dict]:
        try:
            docs = list(self._provider_order_requests_collection(provider_id).stream())
            items = [{"id": doc.id, **(doc.to_dict() or {})} for doc in docs]
            if status:
                items = [item for item in items if str(item.get("status") or "") == status]
            items.sort(key=lambda item: item.get("created_at"), reverse=True)
            return items
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def get_provider_request(self, provider_id: str, request_id: str) -> dict | None:
        try:
            doc = self._provider_order_requests_collection(provider_id).document(request_id).get()
            if not doc.exists:
                return None
            return {"id": doc.id, **(doc.to_dict() or {})}
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def decide_provider_request(
        self,
        *,
        provider_id: str,
        request_id: str,
        decision: str,
        order_id: str,
        client_id: str,
    ) -> dict:
        try:
            now = datetime.now(tz=timezone.utc)
            request_ref = self._provider_order_requests_collection(provider_id).document(request_id)
            client_order_ref = self._client_orders_collection(client_id).document(order_id)
            client_order_status = "confirmed" if decision == "accepted" else "cancelled"

            batch = self.db.batch()
            batch.set(
                request_ref,
                {
                    "status": decision,
                    "decision_at": now,
                    "updated_at": now,
                },
                merge=True,
            )
            batch.set(
                client_order_ref,
                {
                    "status": client_order_status,
                    "updated_at": now,
                },
                merge=True,
            )

            client_notification_ref = self._client_notifications_collection(client_id).document(
                f"order-request-{request_id}-{decision}"
            )
            batch.set(
                client_notification_ref,
                {
                    "title": "Solicitud de evento actualizada",
                    "subtitle": "Tu solicitud fue aceptada" if decision == "accepted" else "Tu solicitud fue rechazada",
                    "type": "order_request_decision",
                    "order_id": order_id,
                    "request_id": request_id,
                    "decision": decision,
                    "is_unread": True,
                    "created_at": now,
                    "updated_at": now,
                },
                merge=True,
            )

            batch.commit()
            order_doc = client_order_ref.get()
            return {"id": order_doc.id, **(order_doc.to_dict() or {})}
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def _client_orders_collection(self, client_id: str):
        return self.db.collection("client_orders").document(client_id).collection("items")

    def _provider_order_requests_collection(self, provider_id: str):
        return self.db.collection("provider_profiles").document(provider_id).collection("order_requests")

    def _provider_notifications_collection(self, provider_id: str):
        return self.db.collection("provider_profiles").document(provider_id).collection("notifications")

    def _client_notifications_collection(self, client_id: str):
        return self.db.collection("client_notifications").document(client_id).collection("items")

    def cancel_related_entities(self, *, client_id: str, order_id: str) -> dict:
        try:
            now = datetime.now(tz=timezone.utc)
            provider_profiles = list(self.db.collection("provider_profiles").stream())
            batch = self.db.batch()
            requests_updated = 0
            bookings_updated = 0
            availability_release_targets: list[dict] = []

            for provider_doc in provider_profiles:
                provider_id = provider_doc.id
                provider_ref = self.db.collection("provider_profiles").document(provider_id)

                request_docs = list(
                    provider_ref.collection("order_requests").where("order_id", "==", order_id).stream()
                )
                for request_doc in request_docs:
                    data = request_doc.to_dict() or {}
                    current_status = str(data.get("status") or "")
                    if current_status not in {"cancelled", "rejected"}:
                        batch.set(
                            request_doc.reference,
                            {"status": "cancelled", "updated_at": now},
                            merge=True,
                        )
                        requests_updated += 1

                booking_docs = list(
                    provider_ref.collection("bookings").where("order_id", "==", order_id).stream()
                )
                for booking_doc in booking_docs:
                    data = booking_doc.to_dict() or {}
                    current_status = str(data.get("status") or "")
                    if current_status in {"cancelled", "completed", "rejected"}:
                        continue

                    batch.set(
                        booking_doc.reference,
                        {"status": "cancelled", "updated_at": now},
                        merge=True,
                    )
                    bookings_updated += 1

                    if current_status == "confirmed":
                        service_id = str(data.get("service_id") or "")
                        product_id = str(data.get("product_id") or "")
                        event_date = str(data.get("event_date") or "")
                        if service_id and product_id and event_date:
                            availability_release_targets.append(
                                {
                                    "provider_id": provider_id,
                                    "service_id": service_id,
                                    "product_id": product_id,
                                    "event_date": event_date,
                                    "booking_id": booking_doc.id,
                                }
                            )

            if requests_updated > 0 or bookings_updated > 0:
                batch.commit()

            return {
                "requests_updated": requests_updated,
                "bookings_updated": bookings_updated,
                "availability_release_targets": availability_release_targets,
            }
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)
