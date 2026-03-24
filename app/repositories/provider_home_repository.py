from datetime import datetime, timezone

from google.api_core.exceptions import GoogleAPICallError, PermissionDenied, RetryError

from app.core.exceptions import ResourceNotFoundError, ServiceUnavailableError
from app.core.firebase import get_firestore_client


class ProviderHomeRepository:
    provider_profiles_collection = "provider_profiles"
    notifications_collection = "notifications"

    def __init__(self) -> None:
        self.db = get_firestore_client()

    @staticmethod
    def _raise_firestore_unavailable(exc: Exception) -> None:
        raise ServiceUnavailableError(
            "Firestore is unavailable or not configured correctly. Verify Firebase credentials and Cloud Firestore API."
        ) from exc

    def list_notifications(self, provider_id: str) -> list[dict]:
        try:
            collection = self._notifications_collection(provider_id)
            documents = collection.order_by("created_at", direction="DESCENDING").stream()
            return [{"id": document.id, **document.to_dict()} for document in documents]
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def mark_notification_as_read(self, provider_id: str, notification_id: str) -> dict:
        try:
            document_ref = self._notifications_collection(provider_id).document(notification_id)
            document = document_ref.get()
            if not document.exists:
                raise ResourceNotFoundError("Notification not found")

            payload = {
                **document.to_dict(),
                "is_unread": False,
                "updated_at": datetime.now(tz=timezone.utc),
            }
            document_ref.set(payload)

            updated_document = document_ref.get()
            return {"id": updated_document.id, **updated_document.to_dict()}
        except ResourceNotFoundError:
            raise
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def mark_all_notifications_as_read(self, provider_id: str) -> int:
        try:
            collection = self._notifications_collection(provider_id)
            documents = list(collection.where("is_unread", "==", True).stream())
            if not documents:
                return 0

            batch = self.db.batch()
            now = datetime.now(tz=timezone.utc)
            for document in documents:
                batch.update(
                    collection.document(document.id),
                    {
                        "is_unread": False,
                        "updated_at": now,
                    },
                )
            batch.commit()
            return len(documents)
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def clear_notifications(self, provider_id: str) -> int:
        try:
            collection = self._notifications_collection(provider_id)
            documents = list(collection.stream())
            if not documents:
                return 0

            batch = self.db.batch()
            for document in documents:
                batch.delete(collection.document(document.id))
            batch.commit()
            return len(documents)
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def _notifications_collection(self, provider_id: str):
        return (
            self.db.collection(self.provider_profiles_collection)
            .document(provider_id)
            .collection(self.notifications_collection)
        )
