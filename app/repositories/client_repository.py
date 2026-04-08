from datetime import datetime, timezone

from google.api_core.exceptions import GoogleAPICallError, PermissionDenied, RetryError
from google.cloud.firestore_v1.base_query import FieldFilter
from app.core.exceptions import ServiceUnavailableError
from app.core.firebase import get_firestore_client


class ClientRepository:
    def __init__(self) -> None:
        self.db = get_firestore_client()

    @staticmethod
    def _raise_firestore_unavailable(exc: Exception) -> None:
        raise ServiceUnavailableError(
            "Firestore is unavailable or not configured correctly. Verify Firebase credentials and Cloud Firestore API."
        ) from exc

    def _cart_collection(self, user_id: str):
        return self.db.collection("client_carts").document(user_id).collection("items")

    def _orders_collection(self, user_id: str):
        return self.db.collection("client_orders").document(user_id).collection("items")

    def _checkout_index_collection(self, user_id: str):
        return self.db.collection("client_orders").document(user_id).collection("checkout_index")

    def cart_list(self, user_id: str) -> list[dict]:
        try:
            docs = self._cart_collection(user_id).order_by("created_at").stream()
            return [{"id": doc.id, **doc.to_dict()} for doc in docs]
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def cart_get(self, user_id: str, item_id: str) -> dict | None:
        try:
            doc = self._cart_collection(user_id).document(item_id).get()
            if not doc.exists:
                return None
            return {"id": doc.id, **doc.to_dict()}
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def cart_create(self, user_id: str, item_id: str, payload: dict) -> dict:
        try:
            now = datetime.now(tz=timezone.utc)
            doc_ref = self._cart_collection(user_id).document(item_id)
            data = {**payload, "created_at": now, "updated_at": now}
            doc_ref.set(data)
            return {"id": item_id, **data}
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def cart_delete(self, user_id: str, item_id: str) -> dict | None:
        try:
            doc_ref = self._cart_collection(user_id).document(item_id)
            doc = doc_ref.get()
            if not doc.exists:
                return None
            payload = {"id": doc.id, **doc.to_dict()}
            doc_ref.delete()
            return payload
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def cart_clear(self, user_id: str) -> None:
        try:
            docs = list(self._cart_collection(user_id).stream())
            for doc in docs:
                doc.reference.delete()
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def order_list(self, user_id: str) -> list[dict]:
        try:
            docs = self._orders_collection(user_id).order_by("created_at", direction="DESCENDING").stream()
            return [{"id": doc.id, **doc.to_dict()} for doc in docs]
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def list_orders_by_statuses(self, user_id: str, statuses: list[str]) -> list[dict]:
        try:
            if not statuses:
                return []
            docs = self._orders_collection(user_id).where(
                filter=FieldFilter("status", "in", statuses)
            ).stream()
            return [{"id": doc.id, **doc.to_dict()} for doc in docs]
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def list_order_status_and_items_by_statuses(self, user_id: str, statuses: list[str]) -> list[dict]:
        try:
            if not statuses:
                return []
            docs = (
                self._orders_collection(user_id)
                .where(filter=FieldFilter("status", "in", statuses))
                .select(["status", "items"])
                .stream()
            )
            return [{"id": doc.id, **(doc.to_dict() or {})} for doc in docs]
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def order_create(self, user_id: str, payload: dict) -> dict:
        try:
            now = datetime.now(tz=timezone.utc)
            doc_ref = self._orders_collection(user_id).document(payload["id"])
            data = {**payload, "created_at": now, "updated_at": now}
            doc_ref.set(data)
            return {"id": doc_ref.id, **data}
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def checkout_commit(
        self,
        user_id: str,
        *,
        order_payload: dict,
        cart_item_ids: list[str],
        provider_actions: list[dict],
        checkout_key: str,
    ) -> dict:
        try:
            checkout_index_ref = self._checkout_index_collection(user_id).document(checkout_key)
            checkout_index_doc = checkout_index_ref.get()
            if checkout_index_doc.exists:
                index_data = checkout_index_doc.to_dict() or {}
                order_id = str(index_data.get("order_id") or "")
                if order_id:
                    existing_order = self.order_get(user_id, order_id)
                    if existing_order:
                        return {
                            **existing_order,
                            "reservations_created": int(index_data.get("reservations_created", 0) or 0),
                            "notifications_created": int(index_data.get("notifications_created", 0) or 0),
                        }

            now = datetime.now(tz=timezone.utc)
            order_base_id = str(order_payload["id"])
            order_id = order_base_id
            version = 1
            while self._orders_collection(user_id).document(order_id).get().exists:
                version += 1
                order_id = f"{order_base_id}-V{version}"

            order_ref = self._orders_collection(user_id).document(order_id)
            data = {
                **order_payload,
                "id": order_id,
                "checkout_key": checkout_key,
                "created_at": now,
                "updated_at": now,
            }

            batch = self.db.batch()
            batch.set(order_ref, data, merge=False)

            for action in provider_actions:
                provider_id = action["provider_id"]
                reservation_ref = (
                    self.db.collection("provider_profiles")
                    .document(provider_id)
                    .collection("bookings")
                    .document(action["reservation_id"])
                )
                reservation_data = {
                    **action["reservation_payload"],
                    "provider_id": provider_id,
                    "created_at": now,
                    "updated_at": now,
                }
                batch.set(reservation_ref, reservation_data, merge=True)

                notification_ref = (
                    self.db.collection("provider_profiles")
                    .document(provider_id)
                    .collection("notifications")
                    .document(action["notification_id"])
                )
                notification_data = {
                    **action["notification_payload"],
                    "is_unread": True,
                    "created_at": now,
                    "updated_at": now,
                }
                batch.set(notification_ref, notification_data, merge=True)

            for item_id in cart_item_ids:
                cart_ref = self._cart_collection(user_id).document(item_id)
                batch.delete(cart_ref)

            batch.set(
                checkout_index_ref,
                {
                    "checkout_key": checkout_key,
                    "order_id": order_id,
                    "reservations_created": len(provider_actions),
                    "notifications_created": len(provider_actions),
                    "created_at": now,
                    "updated_at": now,
                },
                merge=False,
            )

            batch.commit()
            return {
                "id": order_ref.id,
                **data,
                "reservations_created": len(provider_actions),
                "notifications_created": len(provider_actions),
            }
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def order_get(self, user_id: str, order_id: str) -> dict | None:
        try:
            doc = self._orders_collection(user_id).document(order_id).get()
            if not doc.exists:
                return None
            return {"id": doc.id, **doc.to_dict()}
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def order_update_status(self, user_id: str, order_id: str, status: str) -> dict | None:
        try:
            doc_ref = self._orders_collection(user_id).document(order_id)
            doc = doc_ref.get()
            if not doc.exists:
                return None
            doc_ref.update({"status": status, "updated_at": datetime.now(tz=timezone.utc)})
            updated_doc = doc_ref.get()
            return {"id": updated_doc.id, **updated_doc.to_dict()}
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def order_update_fields(self, user_id: str, order_id: str, payload: dict) -> dict | None:
        try:
            doc_ref = self._orders_collection(user_id).document(order_id)
            doc = doc_ref.get()
            if not doc.exists:
                return None
            doc_ref.set(
                {
                    **payload,
                    "updated_at": datetime.now(tz=timezone.utc),
                },
                merge=True,
            )
            updated_doc = doc_ref.get()
            return {"id": updated_doc.id, **updated_doc.to_dict()}
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def services_by_category(self, category: str) -> list[dict]:
        try:
            items = self.list_published_services()
            return [item for item in items if item.get("category") == category]
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def service_by_id(self, service_id: str) -> dict | None:
        try:
            doc = self.db.collection("services").document(service_id).get()
            if not doc.exists:
                return None
            data = doc.to_dict() or {}
            return {"id": doc.id, **data}
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def visible_service_by_id(self, service_id: str) -> dict | None:
        service = self.service_by_id(service_id)
        if not service:
            return None
        if not self._is_service_visible(service):
            return None
        return service

    def list_published_services(self) -> list[dict]:
        try:
            docs = list(self.db.collection("services").stream())
            items: list[dict] = []
            for doc in docs:
                data = doc.to_dict() or {}
                if not self._is_service_visible(data):
                    continue
                items.append({"id": doc.id, **data})
            items.sort(key=lambda item: item.get("created_at"), reverse=True)
            return items
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def published_service_by_product_id(self, product_id: str) -> tuple[dict, dict] | None:
        try:
            services = self.list_published_services()
            for service in services:
                provider_id = str(service.get("provider_id") or "")
                service_id = str(service.get("id") or "")
                if not provider_id or not service_id:
                    continue
                if not self._is_service_visible(service):
                    continue

                products_collection = (
                    self.db.collection("provider_profiles")
                    .document(provider_id)
                    .collection("services")
                    .document(service_id)
                    .collection("products")
                )
                product_doc = products_collection.document(product_id).get()
                if not product_doc.exists:
                    continue

                product_data = product_doc.to_dict() or {}
                status = str(product_data.get("status") or "").strip().lower()
                if status and status not in {"published", "active"}:
                    return None
                return {"id": service_id, **service}, {"id": product_doc.id, **product_data}

            return None
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def visible_product_by_service_and_id(self, service_id: str, product_id: str) -> tuple[dict, dict] | None:
        try:
            service = self.visible_service_by_id(service_id)
            if not service:
                return None

            provider_id = str(service.get("provider_id") or "")
            if not provider_id:
                return None

            product_doc = (
                self.db.collection("provider_profiles")
                .document(provider_id)
                .collection("services")
                .document(service_id)
                .collection("products")
                .document(product_id)
                .get()
            )
            if not product_doc.exists:
                return None

            product_data = product_doc.to_dict() or {}
            product = {"id": product_doc.id, **product_data}
            if not self._is_product_visible(product):
                return None
            return service, product
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def service_has_published_products(self, provider_id: str, service_id: str) -> bool:
        try:
            products = (
                self.db.collection("provider_profiles")
                .document(provider_id)
                .collection("services")
                .document(service_id)
                .collection("products")
                .stream()
            )
            for product_doc in products:
                payload = product_doc.to_dict() or {}
                if self._is_product_visible(payload):
                    return True
            return False
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def product_by_service_and_id(self, provider_id: str, service_id: str, product_id: str) -> dict | None:
        try:
            product_doc = (
                self.db.collection("provider_profiles")
                .document(provider_id)
                .collection("services")
                .document(service_id)
                .collection("products")
                .document(product_id)
                .get()
            )
            if not product_doc.exists:
                return None
            return {"id": product_doc.id, **(product_doc.to_dict() or {})}
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    @staticmethod
    def _is_service_visible(data: dict) -> bool:
        status = str(data.get("status") or "").strip().lower()
        is_active = data.get("is_active")
        is_published = data.get("is_published")

        status_ok = status in {"published", "active"} if status else True
        active_ok = is_active is not False
        published_ok = is_published is not False
        return status_ok and active_ok and published_ok

    @staticmethod
    def _is_product_visible(data: dict) -> bool:
        status = str(data.get("status") or "").strip().lower()
        is_active = data.get("is_active")
        is_published = data.get("is_published")

        status_ok = status in {"published", "active"} if status else True
        active_ok = is_active is not False
        published_ok = is_published is not False
        return status_ok and active_ok and published_ok
