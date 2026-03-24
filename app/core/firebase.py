from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore, storage
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
    if settings.firebase_storage_bucket:
        options["storageBucket"] = settings.firebase_storage_bucket

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


def get_storage_bucket():
    settings = get_settings()
    if not settings.firebase_storage_bucket:
        raise ServiceUnavailableError(
            "Firebase Storage bucket is not configured. Verify FIREBASE_STORAGE_BUCKET."
        )

    try:
        _initialize_firebase()
        return storage.bucket()
    except ServiceUnavailableError:
        raise
    except Exception as exc:
        raise ServiceUnavailableError(
            "Failed to initialize Firebase Storage bucket. Verify Firebase configuration."
        ) from exc
