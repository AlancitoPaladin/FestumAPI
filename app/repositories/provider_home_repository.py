from datetime import datetime, timezone

from google.api_core.exceptions import GoogleAPICallError, PermissionDenied, RetryError
from google.cloud.firestore_v1.base_query import FieldFilter

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

    def upsert_notification(
        self,
        provider_id: str,
        notification_id: str,
        payload: dict,
    ) -> dict:
        try:
            document_ref = self._notifications_collection(provider_id).document(notification_id)
            document = document_ref.get()
            now = datetime.now(tz=timezone.utc)
            if document.exists:
                current_data = document.to_dict()
                data = {
                    **current_data,
                    **payload,
                    "is_unread": bool(current_data.get("is_unread", True)),
                    "created_at": current_data.get("created_at", now),
                    "updated_at": now,
                }
            else:
                data = {
                    **payload,
                    "is_unread": True,
                    "created_at": now,
                    "updated_at": now,
                }
            document_ref.set(data)
            created_document = document_ref.get()
            return {"id": created_document.id, **created_document.to_dict()}
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def delete_notifications_by_ids(self, provider_id: str, notification_ids: list[str]) -> int:
        try:
            unique_ids = [item for item in dict.fromkeys(notification_ids) if item]
            if not unique_ids:
                return 0

            batch = self.db.batch()
            collection = self._notifications_collection(provider_id)
            for notification_id in unique_ids:
                batch.delete(collection.document(notification_id))
            batch.commit()
            return len(unique_ids)
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
            documents = list(
                collection.where(filter=FieldFilter("is_unread", "==", True)).stream()
            )
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
