from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from google.api_core.exceptions import GoogleAPICallError, PermissionDenied, RetryError

from app.core.exceptions import ServiceUnavailableError
from app.core.firebase import get_firestore_client


class NotificationTokenRepository:
    def __init__(self) -> None:
        self.db = get_firestore_client()

    @staticmethod
    def _raise_firestore_unavailable(exc: Exception) -> None:
        raise ServiceUnavailableError(
            "Firestore is unavailable or not configured correctly. Verify Firebase credentials and Cloud Firestore API."
        ) from exc

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def upsert_token(self, *, user_id: str, token: str, platform: str) -> dict:
        try:
            now = datetime.now(tz=timezone.utc)
            token_id = self._token_hash(token)
            doc_ref = self._tokens_collection(user_id).document(token_id)
            existing = doc_ref.get()
            base_payload = {
                "token": token,
                "platform": platform,
                "user_id": user_id,
                "is_active": True,
                "updated_at": now,
                "last_seen_at": now,
            }
            if existing.exists:
                doc_ref.set(base_payload, merge=True)
            else:
                doc_ref.set({**base_payload, "created_at": now}, merge=False)
            updated = doc_ref.get().to_dict() or {}
            return {"id": token_id, **updated}
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def delete_token(self, *, user_id: str, token: str) -> bool:
        try:
            token_id = self._token_hash(token)
            doc_ref = self._tokens_collection(user_id).document(token_id)
            doc = doc_ref.get()
            if not doc.exists:
                return False
            doc_ref.delete()
            return True
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def list_active_tokens(self, *, user_id: str) -> list[dict]:
        try:
            docs = list(self._tokens_collection(user_id).where("is_active", "==", True).stream())
            return [{"id": doc.id, **(doc.to_dict() or {})} for doc in docs]
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def delete_token_document(self, *, user_id: str, token_id: str) -> bool:
        try:
            doc_ref = self._tokens_collection(user_id).document(token_id)
            doc = doc_ref.get()
            if not doc.exists:
                return False
            doc_ref.delete()
            return True
        except (PermissionDenied, GoogleAPICallError, RetryError) as exc:
            self._raise_firestore_unavailable(exc)

    def _tokens_collection(self, user_id: str):
        return self.db.collection("user_notification_tokens").document(user_id).collection("items")
