from datetime import datetime, timezone

from google.api_core.exceptions import GoogleAPICallError, PermissionDenied, RetryError

from app.core.exceptions import ServiceUnavailableError
from app.core.firebase import get_firestore_client


class ProviderRepository:
    collection_name = "provider_profiles"

    def __init__(self) -> None:
        self.db = get_firestore_client()
        self.collection = self.db.collection(self.collection_name)

    @staticmethod
    def _raise_firestore_unavailable(exc: Exception) -> None:
        raise ServiceUnavailableError(
            "Firestore is unavailable or not configured correctly. Verify Firebase credentials and Cloud Firestore API."
        ) from exc

    def get_by_provider_id(self, provider_id: str) -> dict | None:
        try:
            document = self.collection.document(provider_id).get()
            if not document.exists:
                return None
            return {"provider_id": document.id, **document.to_dict()}
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def upsert(self, provider_id: str, data: dict) -> dict:
        try:
            now = datetime.now(tz=timezone.utc)
            document_ref = self.collection.document(provider_id)
            current_document = document_ref.get()

            created_at = now
            if current_document.exists:
                current_data = current_document.to_dict()
                created_at = current_data.get("created_at", now)

            payload = {
                **data,
                "created_at": created_at,
                "updated_at": now,
            }
            document_ref.set(payload)

            updated_document = document_ref.get()
            return {"provider_id": updated_document.id, **updated_document.to_dict()}
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def set_logo(self, provider_id: str, logo_url: str, storage_path: str) -> dict:
        return self._merge_profile(
            provider_id=provider_id,
            data={
                "logo_url": logo_url,
                "logo_storage_path": storage_path,
            },
        )

    def add_photo(self, provider_id: str, photo_url: str, storage_path: str) -> dict:
        document = self.get_by_provider_id(provider_id)
        current_photo_urls = []
        current_photo_storage_paths = []
        if document:
            current_photo_urls = list(document.get("photo_urls", []))
            current_photo_storage_paths = list(document.get("photo_storage_paths", []))

        current_photo_urls.append(photo_url)
        current_photo_storage_paths.append(storage_path)

        return self._merge_profile(
            provider_id=provider_id,
            data={
                "photo_urls": current_photo_urls,
                "photo_storage_paths": current_photo_storage_paths,
            },
        )

    def _merge_profile(self, provider_id: str, data: dict) -> dict:
        try:
            now = datetime.now(tz=timezone.utc)
            document_ref = self.collection.document(provider_id)
            current_document = document_ref.get()

            current_data = current_document.to_dict() if current_document.exists else {}
            created_at = current_data.get("created_at", now)
            payload = {
                **current_data,
                **data,
                "created_at": created_at,
                "updated_at": now,
            }
            document_ref.set(payload)

            updated_document = document_ref.get()
            return {"provider_id": updated_document.id, **updated_document.to_dict()}
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)
