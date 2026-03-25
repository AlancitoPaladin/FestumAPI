from datetime import datetime, timezone

from google.api_core.exceptions import GoogleAPICallError, PermissionDenied, RetryError

from app.core.exceptions import ResourceConflictError, ResourceNotFoundError, ServiceUnavailableError
from app.core.firebase import get_firestore_client


class ProviderServiceRepository:
    services_collection = "services"

    def __init__(self) -> None:
        self.db = get_firestore_client()

    @staticmethod
    def _raise_firestore_unavailable(exc: Exception) -> None:
        raise ServiceUnavailableError(
            "Firestore is unavailable or not configured correctly. Verify Firebase credentials and Cloud Firestore API."
        ) from exc

    def create(self, provider_id: str, data: dict) -> dict:
        try:
            now = datetime.now(tz=timezone.utc)
            document_ref = self._services_collection().document()
            payload = {
                **data,
                "id": document_ref.id,
                "provider_id": provider_id,
                "created_at": now,
                "updated_at": now,
            }
            document_ref.set(payload)
            return payload
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def list_all(self) -> list[dict]:
        try:
            documents = list(self._services_collection().stream())
            items = []
            for document in documents:
                data = document.to_dict() or {}
                if "id" not in data:
                    data["id"] = document.id
                items.append(data)
            items.sort(key=lambda item: item.get("created_at"), reverse=True)
            return items
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def list_by_provider(self, provider_id: str) -> list[dict]:
        return [item for item in self.list_all() if item.get("provider_id") == provider_id]

    def list_published(self) -> list[dict]:
        return [item for item in self.list_all() if item.get("status") == "published"]

    def list_published_by_category(self, category: str) -> list[dict]:
        return [
            item
            for item in self.list_published()
            if item.get("category") == category
        ]

    def get_by_id(self, provider_id: str, service_id: str) -> dict | None:
        service = self.get_by_id_any_owner(service_id)
        if not service or service.get("provider_id") != provider_id:
            return None
        return service

    def get_by_id_any_owner(self, service_id: str) -> dict | None:
        try:
            document = self._services_collection().document(service_id).get()
            if not document.exists:
                return None
            data = document.to_dict() or {}
            if "id" not in data:
                data["id"] = document.id
            return data
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def get_published_by_id(self, service_id: str) -> dict | None:
        service = self.get_by_id_any_owner(service_id)
        if not service or service.get("status") != "published":
            return None
        return service

    def get_by_name(self, provider_id: str, service_name: str) -> dict | None:
        items = [
            item
            for item in self.list_by_provider(provider_id)
            if str(item.get("name", "")) == service_name
        ]
        if not items:
            return None
        if len(items) > 1:
            raise ResourceConflictError(
                "Multiple provider services share the same name. Use service_id for this operation."
            )
        return items[0]

    def update(self, provider_id: str, service_id: str, data: dict) -> dict:
        try:
            document_ref = self._services_collection().document(service_id)
            document = document_ref.get()
            if not document.exists:
                raise ResourceNotFoundError("Provider service not found")

            current = document.to_dict() or {}
            if current.get("provider_id") != provider_id:
                raise ResourceNotFoundError("Provider service not found")

            payload = {
                **data,
                "updated_at": datetime.now(tz=timezone.utc),
            }
            document_ref.update(payload)
            updated_document = document_ref.get()
            updated_data = updated_document.to_dict() or {}
            if "id" not in updated_data:
                updated_data["id"] = updated_document.id
            return updated_data
        except ResourceNotFoundError:
            raise
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def add_image(
        self,
        provider_id: str,
        service_id: str,
        image_key: str,
        is_main: bool,
    ) -> dict:
        try:
            document_ref = self._services_collection().document(service_id)
            document = document_ref.get()
            if not document.exists:
                raise ResourceNotFoundError("Provider service not found")

            current_data = document.to_dict() or {}
            if current_data.get("provider_id") != provider_id:
                raise ResourceNotFoundError("Provider service not found")

            image_keys = list(current_data.get("image_keys", []))
            if image_key not in image_keys:
                image_keys.append(image_key)

            payload = {
                "image_keys": image_keys,
                "updated_at": datetime.now(tz=timezone.utc),
            }
            if is_main or not current_data.get("main_image_key"):
                payload["main_image_key"] = image_key

            document_ref.update(payload)
            updated_document = document_ref.get()
            updated_data = updated_document.to_dict() or {}
            if "id" not in updated_data:
                updated_data["id"] = updated_document.id
            return updated_data
        except ResourceNotFoundError:
            raise
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def set_main_image(self, provider_id: str, service_id: str, image_key: str) -> dict:
        try:
            document_ref = self._services_collection().document(service_id)
            document = document_ref.get()
            if not document.exists:
                raise ResourceNotFoundError("Provider service not found")

            current_data = document.to_dict() or {}
            if current_data.get("provider_id") != provider_id:
                raise ResourceNotFoundError("Provider service not found")

            image_keys = list(current_data.get("image_keys", []))
            if image_key not in image_keys:
                raise ResourceNotFoundError("Service image not found")

            payload = {
                "main_image_key": image_key,
                "updated_at": datetime.now(tz=timezone.utc),
            }
            document_ref.update(payload)

            updated_document = document_ref.get()
            updated_data = updated_document.to_dict() or {}
            if "id" not in updated_data:
                updated_data["id"] = updated_document.id
            return updated_data
        except ResourceNotFoundError:
            raise
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def reorder_images(self, provider_id: str, service_id: str, image_keys: list[str]) -> dict:
        try:
            document_ref = self._services_collection().document(service_id)
            document = document_ref.get()
            if not document.exists:
                raise ResourceNotFoundError("Provider service not found")

            current_data = document.to_dict() or {}
            if current_data.get("provider_id") != provider_id:
                raise ResourceNotFoundError("Provider service not found")

            current_image_keys = list(current_data.get("image_keys", []))
            if sorted(image_keys) != sorted(current_image_keys):
                raise ResourceNotFoundError("Image reorder payload does not match current images")

            payload = {
                "image_keys": image_keys,
                "updated_at": datetime.now(tz=timezone.utc),
            }

            current_main_key = str(current_data.get("main_image_key") or "")
            if current_main_key and current_main_key not in image_keys:
                payload["main_image_key"] = image_keys[0] if image_keys else ""

            document_ref.update(payload)

            updated_document = document_ref.get()
            updated_data = updated_document.to_dict() or {}
            if "id" not in updated_data:
                updated_data["id"] = updated_document.id
            return updated_data
        except ResourceNotFoundError:
            raise
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def delete_image(self, provider_id: str, service_id: str, image_key: str) -> tuple[dict, str]:
        try:
            document_ref = self._services_collection().document(service_id)
            document = document_ref.get()
            if not document.exists:
                raise ResourceNotFoundError("Provider service not found")

            current_data = document.to_dict() or {}
            if current_data.get("provider_id") != provider_id:
                raise ResourceNotFoundError("Provider service not found")

            current_image_keys = list(current_data.get("image_keys", []))
            if image_key not in current_image_keys:
                raise ResourceNotFoundError("Service image not found")

            current_image_keys.remove(image_key)
            payload = {
                "image_keys": current_image_keys,
                "updated_at": datetime.now(tz=timezone.utc),
            }

            if current_data.get("main_image_key") == image_key:
                payload["main_image_key"] = current_image_keys[0] if current_image_keys else ""

            document_ref.update(payload)
            updated_document = document_ref.get()
            updated_data = updated_document.to_dict() or {}
            if "id" not in updated_data:
                updated_data["id"] = updated_document.id
            return updated_data, image_key
        except ResourceNotFoundError:
            raise
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def delete(self, provider_id: str, service_id: str) -> tuple[bool, list[str]]:
        try:
            document_ref = self._services_collection().document(service_id)
            document = document_ref.get()
            if not document.exists:
                raise ResourceNotFoundError("Provider service not found")

            data = document.to_dict() or {}
            if data.get("provider_id") != provider_id:
                raise ResourceNotFoundError("Provider service not found")

            storage_paths = list(dict.fromkeys([
                str(data.get("main_image_key") or ""),
                *list(data.get("image_keys", [])),
            ]))
            storage_paths = [item for item in storage_paths if item]
            document_ref.delete()
            return True, storage_paths
        except ResourceNotFoundError:
            raise
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def _services_collection(self):
        return self.db.collection(self.services_collection)
