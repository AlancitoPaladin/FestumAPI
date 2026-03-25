from datetime import datetime, timezone

from google.api_core.exceptions import GoogleAPICallError, PermissionDenied, RetryError

from app.core.exceptions import ResourceNotFoundError, ServiceUnavailableError
from app.core.firebase import get_firestore_client


class ProviderProductRepository:
    provider_profiles_collection = "provider_profiles"
    services_collection = "services"
    products_collection = "products"
    root_services_collection = "services"

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

    def list_published_by_service(self, provider_id: str, service_id: str) -> list[dict]:
        items = self.list_by_service(provider_id, service_id)
        published_items: list[dict] = []
        for item in items:
            status = str(item.get("status") or "").strip().lower()
            if status and status not in {"published", "active"}:
                continue
            published_items.append(item)
        return published_items

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
            for service_id in self._provider_service_ids(provider_id):
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
            for service_id in self._provider_service_ids(provider_id):
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
        image_key: str,
        image_url: str,
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
            current_image_storage_paths.append(image_key)

            payload = {
                "image_urls": current_image_urls,
                "image_storage_paths": current_image_storage_paths,
                "updated_at": datetime.now(tz=timezone.utc),
            }
            if is_main or not current_data.get("main_image_url"):
                payload["main_image_url"] = image_url
                payload["main_image_storage_path"] = image_key

            document_ref.update(payload)
            updated_document = document_ref.get()
            return {"id": updated_document.id, **updated_document.to_dict()}
        except ResourceNotFoundError:
            raise
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def set_main_image(
        self, provider_id: str, service_id: str, product_id: str, image_key: str
    ) -> dict:
        try:
            document_ref = self._products_collection(provider_id, service_id).document(product_id)
            document = document_ref.get()
            if not document.exists:
                raise ResourceNotFoundError("Provider product not found")

            current_data = document.to_dict()
            current_image_urls = list(current_data.get("image_urls", []))
            current_image_storage_paths = list(current_data.get("image_storage_paths", []))

            normalized_image_keys = [str(item).strip().lstrip("/") for item in current_image_storage_paths]
            if image_key not in normalized_image_keys:
                raise ResourceNotFoundError("Product image not found")

            image_index = normalized_image_keys.index(image_key)
            payload = {
                "main_image_url": current_image_urls[image_index] if image_index < len(current_image_urls) else "",
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
        self, provider_id: str, service_id: str, product_id: str, image_keys: list[str]
    ) -> dict:
        try:
            document_ref = self._products_collection(provider_id, service_id).document(product_id)
            document = document_ref.get()
            if not document.exists:
                raise ResourceNotFoundError("Provider product not found")

            current_data = document.to_dict()
            current_image_urls = list(current_data.get("image_urls", []))
            current_image_storage_paths = list(current_data.get("image_storage_paths", []))

            normalized_image_keys = [str(item).strip().lstrip("/") for item in current_image_storage_paths]
            if sorted(image_keys) != sorted(normalized_image_keys):
                raise ResourceNotFoundError("Image reorder payload does not match current images")

            url_by_key = dict(zip(normalized_image_keys, current_image_urls))
            reordered_storage_paths = [key for key in image_keys]
            reordered_image_urls = [url_by_key.get(item, "") for item in image_keys]

            payload = {
                "image_urls": reordered_image_urls,
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
        self, provider_id: str, service_id: str, product_id: str, image_key: str
    ) -> tuple[dict, str]:
        try:
            document_ref = self._products_collection(provider_id, service_id).document(product_id)
            document = document_ref.get()
            if not document.exists:
                raise ResourceNotFoundError("Provider product not found")

            current_data = document.to_dict()
            current_image_urls = list(current_data.get("image_urls", []))
            current_image_storage_paths = list(current_data.get("image_storage_paths", []))

            normalized_image_keys = [str(item).strip().lstrip("/") for item in current_image_storage_paths]
            if image_key not in normalized_image_keys:
                raise ResourceNotFoundError("Product image not found")

            image_index = normalized_image_keys.index(image_key)
            deleted_storage_path = current_image_storage_paths.pop(image_index)
            current_image_urls.pop(image_index)

            payload = {
                "image_urls": current_image_urls,
                "image_storage_paths": current_image_storage_paths,
                "updated_at": datetime.now(tz=timezone.utc),
            }

            current_main_key = str(current_data.get("main_image_storage_path") or "").strip().lstrip("/")
            if current_main_key == image_key:
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

    def get_min_published_price_cents(self, provider_id: str, service_id: str) -> int | None:
        try:
            documents = list(self._products_collection(provider_id, service_id).stream())
            prices: list[int] = []
            for document in documents:
                data = document.to_dict() or {}
                status = str(data.get("status") or "").strip().lower()
                if status and status not in {"published", "active"}:
                    continue

                raw_price = data.get("price")
                if raw_price is None:
                    continue

                try:
                    price_value = float(raw_price)
                except (TypeError, ValueError):
                    continue

                if price_value <= 0:
                    continue
                prices.append(int(round(price_value * 100)))

            if not prices:
                return None
            return min(prices)
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

    def _provider_service_ids(self, provider_id: str) -> list[str]:
        documents = list(self.db.collection(self.root_services_collection).stream())
        service_ids: list[str] = []
        for document in documents:
            data = document.to_dict() or {}
            if data.get("provider_id") == provider_id:
                service_ids.append(document.id)
        return service_ids
