from __future__ import annotations

import logging

from firebase_admin import messaging

from app.core.firebase import get_firebase_app
from app.repositories.notification_token_repository import NotificationTokenRepository

logger = logging.getLogger(__name__)


class PushNotificationService:
    def __init__(self, token_repository: NotificationTokenRepository | None = None) -> None:
        self._token_repository = token_repository

    @property
    def token_repository(self) -> NotificationTokenRepository:
        if self._token_repository is None:
            self._token_repository = NotificationTokenRepository()
        return self._token_repository

    def send_to_user(
        self,
        *,
        user_id: str,
        title: str,
        body: str,
        data: dict[str, str] | None = None,
        context: dict[str, str] | None = None,
    ) -> dict:
        tokens = self.token_repository.list_active_tokens(user_id=user_id)
        if not tokens:
            logger.info(
                "push_send_skipped_no_tokens",
                extra={
                    "user_id": user_id,
                    **{k: str(v) for k, v in (context or {}).items()},
                },
            )
            return {"sent": 0, "failed": 0, "removed": 0, "total": 0}

        get_firebase_app()
        payload_data = {k: str(v) for k, v in (data or {}).items() if v is not None}

        sent = 0
        failed = 0
        removed = 0
        for token_doc in tokens:
            token = str(token_doc.get("token") or "")
            if not token:
                continue

            message = messaging.Message(
                token=token,
                notification=messaging.Notification(title=title, body=body),
                data=payload_data,
            )
            try:
                messaging.send(message)
                sent += 1
            except Exception as exc:  # noqa: BLE001
                failed += 1
                if self._is_unregistered_token_error(exc):
                    if self.token_repository.delete_token_document(user_id=user_id, token_id=str(token_doc.get("id") or "")):
                        removed += 1
                logger.warning(
                    "push_send_failed",
                    extra={
                        "user_id": user_id,
                        "token_id": str(token_doc.get("id") or ""),
                        "error": str(exc),
                        **{k: str(v) for k, v in (context or {}).items()},
                    },
                )

        logger.info(
            "push_send_summary",
            extra={
                "user_id": user_id,
                "sent": sent,
                "failed": failed,
                "removed": removed,
                "total": len(tokens),
                **{k: str(v) for k, v in (context or {}).items()},
            },
        )

        return {
            "sent": sent,
            "failed": failed,
            "removed": removed,
            "total": len(tokens),
        }

    @staticmethod
    def _is_unregistered_token_error(exc: Exception) -> bool:
        code = str(getattr(exc, "code", "") or "").lower()
        text = str(exc).lower()
        return (
            "registration-token-not-registered" in code
            or "unregistered" in code
            or "invalid-registration-token" in code
            or "registration token is not a valid fcm registration token" in text
            or "requested entity was not found" in text
            or "not registered" in text
        )
