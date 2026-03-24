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

    def order_create(self, user_id: str, payload: dict) -> dict:
        try:
            now = datetime.now(tz=timezone.utc)
            doc_ref = self._orders_collection(user_id).document(payload["id"])
            data = {**payload, "created_at": now, "updated_at": now}
            doc_ref.set(data)
            return {"id": doc_ref.id, **data}
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

    def services_by_category(self, category: str) -> list[dict]:
        try:
            query = self.db.collection("services").where(
                filter=FieldFilter("category", "==", category)
            )
            return [{"id": doc.id, **doc.to_dict()} for doc in query.stream()]
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def service_by_id(self, service_id: str) -> dict | None:
        try:
            doc = self.db.collection("services").document(service_id).get()
            if not doc.exists:
                return None
            return {"id": doc.id, **doc.to_dict()}
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

