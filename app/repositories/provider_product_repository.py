from datetime import datetime, timezone

from google.api_core.exceptions import GoogleAPICallError, PermissionDenied, RetryError

from app.core.exceptions import ResourceNotFoundError, ServiceUnavailableError
from app.core.firebase import get_firestore_client


class ProviderProductRepository:
    provider_profiles_collection = "provider_profiles"
    services_collection = "services"
    products_collection = "products"

    def __init__(self) -> None:
        self.db = get_firestore_client()

    @staticmethod
    def _raise_firestore_unavailable(exc: Exception) -> None:
        raise ServiceUnavailableError(
            "Firestore is unavailable or not configured correctly. Verify Firebase credentials and Cloud Firestore API."
        ) from exc

    def create(self, provider_id: str, service_id: str, category: str, data: dict) -> dict:
        try:
            now = datetime.now(tz=timezone.utc)
            payload = {
                **data,
                "provider_id": provider_id,
                "service_id": service_id,
                "category": category,
                "created_at": now,
                "updated_at": now,
            }
            document_ref = self._products_collection(provider_id, service_id).document()
            document_ref.set(payload)
            return {"id": document_ref.id, **payload}
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def list_by_service(self, provider_id: str, service_id: str) -> list[dict]:
        try:
            documents = (
                self._products_collection(provider_id, service_id)
                .order_by("created_at", direction="DESCENDING")
                .stream()
            )
            return [{"id": document.id, **document.to_dict()} for document in documents]
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def get_by_id(self, provider_id: str, service_id: str, product_id: str) -> dict | None:
        try:
            document = self._products_collection(provider_id, service_id).document(product_id).get()
            if not document.exists:
                return None
            return {"id": document.id, **document.to_dict()}
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def get_by_product_id(self, provider_id: str, product_id: str) -> dict | None:
        try:
            service_documents = self._services_collection(provider_id).stream()
            for service_document in service_documents:
                service_id = service_document.id
                document = self._products_collection(provider_id, service_id).document(product_id).get()
                if not document.exists:
                    continue
                return {"id": document.id, "service_id": service_id, **document.to_dict()}
            return None
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def list_by_provider(self, provider_id: str) -> list[dict]:
        try:
            items = []
            service_documents = self._services_collection(provider_id).stream()
            for service_document in service_documents:
                service_id = service_document.id
                product_documents = self._products_collection(provider_id, service_id).stream()
                for document in product_documents:
                    items.append({"id": document.id, "service_id": service_id, **document.to_dict()})

            items.sort(key=lambda item: item.get("created_at"), reverse=True)
            return items
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def update(self, provider_id: str, service_id: str, product_id: str, data: dict) -> dict:
        try:
            document_ref = self._products_collection(provider_id, service_id).document(product_id)
            document = document_ref.get()
            if not document.exists:
                raise ResourceNotFoundError("Provider product not found")

            payload = {
                **data,
                "updated_at": datetime.now(tz=timezone.utc),
            }
            document_ref.update(payload)
            updated_document = document_ref.get()
            return {"id": updated_document.id, **updated_document.to_dict()}
        except ResourceNotFoundError:
            raise
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def add_image(
        self,
        provider_id: str,
        service_id: str,
        product_id: str,
        image_url: str,
        storage_path: str,
        is_main: bool,
    ) -> dict:
        try:
            document_ref = self._products_collection(provider_id, service_id).document(product_id)
            document = document_ref.get()
            if not document.exists:
                raise ResourceNotFoundError("Provider product not found")

            current_data = document.to_dict()
            current_image_urls = list(current_data.get("image_urls", []))
            current_image_storage_paths = list(current_data.get("image_storage_paths", []))

            current_image_urls.append(image_url)
            current_image_storage_paths.append(storage_path)

            payload = {
                "image_urls": current_image_urls,
                "image_storage_paths": current_image_storage_paths,
                "updated_at": datetime.now(tz=timezone.utc),
            }
            if is_main or not current_data.get("main_image_url"):
                payload["main_image_url"] = image_url
                payload["main_image_storage_path"] = storage_path

            document_ref.update(payload)
            updated_document = document_ref.get()
            return {"id": updated_document.id, **updated_document.to_dict()}
        except ResourceNotFoundError:
            raise
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def set_main_image(
        self, provider_id: str, service_id: str, product_id: str, image_url: str
    ) -> dict:
        try:
            document_ref = self._products_collection(provider_id, service_id).document(product_id)
            document = document_ref.get()
            if not document.exists:
                raise ResourceNotFoundError("Provider product not found")

            current_data = document.to_dict()
            current_image_urls = list(current_data.get("image_urls", []))
            current_image_storage_paths = list(current_data.get("image_storage_paths", []))

            if image_url not in current_image_urls:
                raise ResourceNotFoundError("Product image not found")

            image_index = current_image_urls.index(image_url)
            payload = {
                "main_image_url": image_url,
                "main_image_storage_path": current_image_storage_paths[image_index],
                "updated_at": datetime.now(tz=timezone.utc),
            }
            document_ref.update(payload)

            updated_document = document_ref.get()
            return {"id": updated_document.id, **updated_document.to_dict()}
        except ResourceNotFoundError:
            raise
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def reorder_images(
        self, provider_id: str, service_id: str, product_id: str, image_urls: list[str]
    ) -> dict:
        try:
            document_ref = self._products_collection(provider_id, service_id).document(product_id)
            document = document_ref.get()
            if not document.exists:
                raise ResourceNotFoundError("Provider product not found")

            current_data = document.to_dict()
            current_image_urls = list(current_data.get("image_urls", []))
            current_image_storage_paths = list(current_data.get("image_storage_paths", []))

            if sorted(image_urls) != sorted(current_image_urls):
                raise ResourceNotFoundError("Image reorder payload does not match current images")

            storage_by_url = dict(zip(current_image_urls, current_image_storage_paths))
            reordered_storage_paths = [storage_by_url[item] for item in image_urls]

            payload = {
                "image_urls": image_urls,
                "image_storage_paths": reordered_storage_paths,
                "updated_at": datetime.now(tz=timezone.utc),
            }
            document_ref.update(payload)

            updated_document = document_ref.get()
            return {"id": updated_document.id, **updated_document.to_dict()}
        except ResourceNotFoundError:
            raise
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def delete_image(
        self, provider_id: str, service_id: str, product_id: str, image_url: str
    ) -> tuple[dict, str]:
        try:
            document_ref = self._products_collection(provider_id, service_id).document(product_id)
            document = document_ref.get()
            if not document.exists:
                raise ResourceNotFoundError("Provider product not found")

            current_data = document.to_dict()
            current_image_urls = list(current_data.get("image_urls", []))
            current_image_storage_paths = list(current_data.get("image_storage_paths", []))

            if image_url not in current_image_urls:
                raise ResourceNotFoundError("Product image not found")

            image_index = current_image_urls.index(image_url)
            deleted_storage_path = current_image_storage_paths.pop(image_index)
            current_image_urls.pop(image_index)

            payload = {
                "image_urls": current_image_urls,
                "image_storage_paths": current_image_storage_paths,
                "updated_at": datetime.now(tz=timezone.utc),
            }

            if current_data.get("main_image_url") == image_url:
                if current_image_urls:
                    payload["main_image_url"] = current_image_urls[0]
                    payload["main_image_storage_path"] = current_image_storage_paths[0]
                else:
                    payload["main_image_url"] = ""
                    payload["main_image_storage_path"] = ""

            document_ref.update(payload)
            updated_document = document_ref.get()
            return {"id": updated_document.id, **updated_document.to_dict()}, deleted_storage_path
        except ResourceNotFoundError:
            raise
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def delete(self, provider_id: str, service_id: str, product_id: str) -> tuple[bool, list[str]]:
        try:
            document_ref = self._products_collection(provider_id, service_id).document(product_id)
            document = document_ref.get()
            if not document.exists:
                raise ResourceNotFoundError("Provider product not found")

            data = document.to_dict()
            storage_paths = list(data.get("image_storage_paths", []))
            document_ref.delete()
            return True, storage_paths
        except ResourceNotFoundError:
            raise
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def delete_all_by_service(self, provider_id: str, service_id: str) -> list[str]:
        try:
            collection = self._products_collection(provider_id, service_id)
            documents = list(collection.stream())
            if not documents:
                return []

            storage_paths: list[str] = []
            batch = self.db.batch()
            for document in documents:
                data = document.to_dict()
                storage_paths.extend(list(data.get("image_storage_paths", [])))
                batch.delete(collection.document(document.id))
            batch.commit()
            return storage_paths
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def _products_collection(self, provider_id: str, service_id: str):
        return (
            self.db.collection(self.provider_profiles_collection)
            .document(provider_id)
            .collection(self.services_collection)
            .document(service_id)
            .collection(self.products_collection)
        )

    def _services_collection(self, provider_id: str):
        return (
            self.db.collection(self.provider_profiles_collection)
            .document(provider_id)
            .collection(self.services_collection)
        )
