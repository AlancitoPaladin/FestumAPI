from datetime import datetime, timezone

from google.api_core.exceptions import GoogleAPICallError, PermissionDenied, RetryError
from google.cloud.firestore_v1.base_query import FieldFilter

from app.core.exceptions import ServiceUnavailableError
from app.core.firebase import get_firestore_client


class UserRepository:
    collection_name = "users"

    def __init__(self) -> None:
        self.db = get_firestore_client()
        self.collection = self.db.collection(self.collection_name)

    @staticmethod
    def _raise_firestore_unavailable(exc: Exception) -> None:
        raise ServiceUnavailableError(
            "Firestore is unavailable or not configured correctly. Verify Firebase credentials and Cloud Firestore API."
        ) from exc

    def create(self, data: dict) -> dict:
        try:
            now = datetime.now(tz=timezone.utc)
            payload = {**data, "created_at": now, "updated_at": now}
            document_ref = self.collection.document()
            document_ref.set(payload)
            return {"id": document_ref.id, **payload}
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def get_by_id(self, user_id: str) -> dict | None:
        try:
            document = self.collection.document(user_id).get()
            if not document.exists:
                return None
            return {"id": document.id, **document.to_dict()}
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def get_by_email(self, email: str) -> dict | None:
        try:
            query = self.collection.where(filter=FieldFilter("email", "==", email)).limit(1)
            docs = list(query.stream())
            if not docs:
                return None
            doc = docs[0]
            return {"id": doc.id, **doc.to_dict()}
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def list(self, page: int, page_size: int) -> tuple[list[dict], int]:
        try:
            offset = (page - 1) * page_size
            query = (
                self.collection.order_by("created_at")
                .offset(offset)
                .limit(page_size)
                .stream()
            )
            items = [{"id": doc.id, **doc.to_dict()} for doc in query]
            total = len(list(self.collection.stream()))
            return items, total
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def update(self, user_id: str, data: dict) -> dict | None:
        try:
            document_ref = self.collection.document(user_id)
            document = document_ref.get()
            if not document.exists:
                return None

            payload = {**data, "updated_at": datetime.now(tz=timezone.utc)}
            document_ref.update(payload)
            updated_document = document_ref.get()
            return {"id": updated_document.id, **updated_document.to_dict()}
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def delete(self, user_id: str) -> bool:
        try:
            document_ref = self.collection.document(user_id)
            document = document_ref.get()
            if not document.exists:
                return False
            document_ref.delete()
            return True
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)
