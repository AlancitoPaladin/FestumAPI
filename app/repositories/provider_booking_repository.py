from datetime import date, datetime, timezone

from google.api_core.exceptions import GoogleAPICallError, PermissionDenied, RetryError
from google.cloud.firestore_v1.base_query import FieldFilter

from app.core.exceptions import ResourceNotFoundError, ServiceUnavailableError
from app.core.firebase import get_firestore_client


class ProviderBookingRepository:
    provider_profiles_collection = "provider_profiles"
    bookings_collection = "bookings"

    def __init__(self) -> None:
        self.db = get_firestore_client()

    @staticmethod
    def _raise_firestore_unavailable(exc: Exception) -> None:
        raise ServiceUnavailableError(
            "Firestore is unavailable or not configured correctly. Verify Firebase credentials and Cloud Firestore API."
        ) from exc

    def generate_id(self, provider_id: str) -> str:
        return self._bookings_collection(provider_id).document().id

    def create(self, provider_id: str, booking_id: str, data: dict) -> dict:
        try:
            now = datetime.now(tz=timezone.utc)
            payload = {
                **data,
                "provider_id": provider_id,
                "created_at": now,
                "updated_at": now,
            }
            document_ref = self._bookings_collection(provider_id).document(booking_id)
            document_ref.set(payload)
            return {"id": booking_id, **payload}
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def list_by_provider(
        self,
        provider_id: str,
        *,
        status: str | None = None,
        year: int | None = None,
        month: int | None = None,
        product_id: str | None = None,
    ) -> list[dict]:
        try:
            documents = list(self._bookings_collection(provider_id).stream())
            items = [{"id": document.id, **document.to_dict()} for document in documents]

            if status:
                items = [item for item in items if item.get("status") == status]
            if product_id:
                items = [item for item in items if item.get("product_id") == product_id]
            if year is not None:
                items = [
                    item
                    for item in items
                    if self._event_date_parts(item.get("event_date"))[0] == year
                ]
            if month is not None:
                items = [
                    item
                    for item in items
                    if self._event_date_parts(item.get("event_date"))[1] == month
                ]

            items.sort(
                key=lambda item: (
                    str(item.get("event_date") or ""),
                    str(item.get("start_time") or ""),
                    item.get("created_at"),
                ),
                reverse=True,
            )
            return items
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def get_by_id(self, provider_id: str, booking_id: str) -> dict | None:
        try:
            document = self._bookings_collection(provider_id).document(booking_id).get()
            if not document.exists:
                return None
            return {"id": document.id, **document.to_dict()}
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def update(self, provider_id: str, booking_id: str, data: dict) -> dict:
        try:
            document_ref = self._bookings_collection(provider_id).document(booking_id)
            document = document_ref.get()
            if not document.exists:
                raise ResourceNotFoundError("Provider booking not found")

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

    def delete(self, provider_id: str, booking_id: str) -> None:
        try:
            self._bookings_collection(provider_id).document(booking_id).delete()
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def delete_all_by_product(self, provider_id: str, product_id: str) -> int:
        try:
            documents = list(
                self._bookings_collection(provider_id).where(
                    filter=FieldFilter("product_id", "==", product_id)
                ).stream()
            )
            if not documents:
                return 0

            batch = self.db.batch()
            for document in documents:
                batch.delete(self._bookings_collection(provider_id).document(document.id))
            batch.commit()
            return len(documents)
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def count_confirmed_for_month(self, provider_id: str, year: int, month: int) -> int:
        items = self.list_by_provider(provider_id, status="confirmed", year=year, month=month)
        return len(items)

    def get_next_booking_map(self, provider_id: str) -> dict[str, dict]:
        try:
            today = date.today().isoformat()
            items = self.list_by_provider(provider_id)
            upcoming_items = [
                item
                for item in items
                if item.get("status") in {"pending", "confirmed"}
                and str(item.get("event_date") or "") >= today
                and item.get("product_id")
            ]
            upcoming_items.sort(
                key=lambda item: (
                    str(item.get("event_date") or ""),
                    str(item.get("start_time") or ""),
                    str(item.get("created_at") or ""),
                )
            )

            next_by_product: dict[str, dict] = {}
            for item in upcoming_items:
                product_id = str(item.get("product_id") or "")
                if product_id and product_id not in next_by_product:
                    next_by_product[product_id] = item
            return next_by_product
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    @staticmethod
    def _event_date_parts(event_date: object) -> tuple[int | None, int | None]:
        if not event_date:
            return None, None

        normalized = str(event_date)
        if "T" in normalized:
            normalized = normalized.split("T", maxsplit=1)[0]
        parts = normalized.split("-")
        if len(parts) != 3:
            return None, None

        try:
            return int(parts[0]), int(parts[1])
        except ValueError:
            return None, None

    def _bookings_collection(self, provider_id: str):
        return (
            self.db.collection(self.provider_profiles_collection)
            .document(provider_id)
            .collection(self.bookings_collection)
        )
