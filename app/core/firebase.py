from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore
from google.auth.exceptions import DefaultCredentialsError

from app.core.config import BASE_DIR, get_settings
from app.core.exceptions import ServiceUnavailableError


def _initialize_firebase() -> None:
    if firebase_admin._apps:
        return

    settings = get_settings()
    options: dict[str, str] = {}
    if settings.firebase_project_id:
        options["projectId"] = settings.firebase_project_id
    if settings.firebase_database_url:
        options["databaseURL"] = settings.firebase_database_url

    try:
        if settings.firebase_credentials_path:
            credential_path = Path(settings.firebase_credentials_path)
            if not credential_path.is_absolute():
                credential_path = BASE_DIR / credential_path
            if not credential_path.exists():
                raise ServiceUnavailableError(
                    "Firebase credentials file was not found. Verify FIREBASE_CREDENTIALS_PATH."
                )
            cred = credentials.Certificate(credential_path)
        else:
            cred = credentials.ApplicationDefault()

        firebase_admin.initialize_app(cred, options=options)
    except (DefaultCredentialsError, ValueError) as exc:
        raise ServiceUnavailableError(
            "Firebase credentials are not configured correctly. Verify FIREBASE_CREDENTIALS_PATH or ADC."
        ) from exc


def get_firestore_client() -> firestore.Client:
    try:
        _initialize_firebase()
        return firestore.client()
    except ServiceUnavailableError:
        raise
    except Exception as exc:
        raise ServiceUnavailableError(
            "Failed to initialize Firestore client. Verify Firebase configuration."
        ) from exc


def get_firebase_app() -> firebase_admin.App:
    try:
        _initialize_firebase()
        return firebase_admin.get_app()
    except ServiceUnavailableError:
        raise
    except Exception as exc:
        raise ServiceUnavailableError(
            "Failed to initialize Firebase app. Verify Firebase configuration."
        ) from exc
