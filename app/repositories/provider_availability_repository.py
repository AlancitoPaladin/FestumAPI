from datetime import datetime, timezone

from google.api_core.exceptions import GoogleAPICallError, PermissionDenied, RetryError

from app.core.exceptions import ResourceConflictError, ResourceNotFoundError, ServiceUnavailableError
from app.core.firebase import get_firestore_client


class ProviderAvailabilityRepository:
    provider_profiles_collection = "provider_profiles"
    services_collection = "services"
    products_collection = "products"
    availability_collection = "availability"

    def __init__(self) -> None:
        self.db = get_firestore_client()

    @staticmethod
    def _raise_firestore_unavailable(exc: Exception) -> None:
        raise ServiceUnavailableError(
            "Firestore is unavailable or not configured correctly. Verify Firebase credentials and Cloud Firestore API."
        ) from exc

    def list_by_month(
        self, provider_id: str, service_id: str, product_id: str, year: int, month: int
    ) -> list[dict]:
        try:
            collection = self._availability_collection(provider_id, service_id, product_id)
            documents = list(collection.stream())
            prefix = f"{year:04d}-{month:02d}-"
            items = []
            for document in documents:
                data = document.to_dict()
                if not str(data.get("date", "")).startswith(prefix):
                    continue
                items.append({"id": document.id, **data})
            return items
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def block_date(
        self, provider_id: str, service_id: str, product_id: str, date_key: str
    ) -> dict:
        try:
            document_ref = self._availability_collection(provider_id, service_id, product_id).document(date_key)
            document = document_ref.get()
            if document.exists:
                current_data = document.to_dict()
                if current_data.get("status") == "reserved":
                    raise ResourceConflictError("Reserved dates cannot be blocked manually")

            payload = {
                "date": date_key,
                "status": "blocked",
                "updated_at": datetime.now(tz=timezone.utc),
            }
            if not document.exists:
                payload["created_at"] = datetime.now(tz=timezone.utc)

            document_ref.set(payload, merge=True)
            updated_document = document_ref.get()
            return {"id": updated_document.id, **updated_document.to_dict()}
        except ResourceConflictError:
            raise
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def unblock_date(
        self, provider_id: str, service_id: str, product_id: str, date_key: str
    ) -> dict:
        try:
            document_ref = self._availability_collection(provider_id, service_id, product_id).document(date_key)
            document = document_ref.get()
            if not document.exists:
                return {"date": date_key, "status": "available"}

            data = document.to_dict()
            if data.get("status") == "reserved":
                raise ResourceConflictError("Reserved dates cannot be unblocked manually")

            document_ref.delete()
            return {"date": date_key, "status": "available"}
        except ResourceConflictError:
            raise
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def reserve_date(
        self,
        provider_id: str,
        service_id: str,
        product_id: str,
        date_key: str,
        booking_summary: dict,
    ) -> dict:
        try:
            document_ref = self._availability_collection(provider_id, service_id, product_id).document(date_key)
            document = document_ref.get()
            if document.exists:
                current_data = document.to_dict()
                current_booking = current_data.get("booking", {})
                current_booking_id = current_booking.get("booking_id")
                if (
                    current_data.get("status") == "reserved"
                    and current_booking_id
                    and current_booking_id != booking_summary.get("booking_id")
                ):
                    raise ResourceConflictError("Date is already reserved for another booking")

            payload = {
                "date": date_key,
                "status": "reserved",
                "booking": booking_summary,
                "updated_at": datetime.now(tz=timezone.utc),
            }
            if not document.exists:
                payload["created_at"] = datetime.now(tz=timezone.utc)

            document_ref.set(payload, merge=True)
            updated_document = document_ref.get()
            return {"id": updated_document.id, **updated_document.to_dict()}
        except ResourceConflictError:
            raise
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def clear_reserved_date(
        self,
        provider_id: str,
        service_id: str,
        product_id: str,
        date_key: str,
        booking_id: str,
    ) -> dict:
        try:
            document_ref = self._availability_collection(provider_id, service_id, product_id).document(date_key)
            document = document_ref.get()
            if not document.exists:
                return {"date": date_key, "status": "available"}

            data = document.to_dict()
            booking = data.get("booking", {})
            if data.get("status") != "reserved":
                return {"date": date_key, "status": data.get("status", "available")}

            if booking.get("booking_id") and booking.get("booking_id") != booking_id:
                raise ResourceConflictError("Reserved date belongs to another booking")

            document_ref.delete()
            return {"date": date_key, "status": "available"}
        except ResourceConflictError:
            raise
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def delete_all_by_product(self, provider_id: str, service_id: str, product_id: str) -> int:
        try:
            collection = self._availability_collection(provider_id, service_id, product_id)
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

    def _availability_collection(self, provider_id: str, service_id: str, product_id: str):
        return (
            self.db.collection(self.provider_profiles_collection)
            .document(provider_id)
            .collection(self.services_collection)
            .document(service_id)
            .collection(self.products_collection)
            .document(product_id)
            .collection(self.availability_collection)
        )
