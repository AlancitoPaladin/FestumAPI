from google.api_core.exceptions import GoogleAPICallError, PermissionDenied, RetryError

from app.core.exceptions import ServiceUnavailableError
from app.core.firebase import get_firestore_client


class HealthService:
    def check_firestore_connection(self) -> None:
        try:
            db = get_firestore_client()
            list(db.collections())
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            raise ServiceUnavailableError(
                "Firestore is unavailable or not configured correctly. Verify Firebase credentials and Cloud Firestore API."
            ) from exc
