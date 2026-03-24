from datetime import datetime, timezone

from fastapi import UploadFile

from app.repositories.provider_repository import ProviderRepository
from app.schemas.provider import (
    ProviderBusinessAssetUploadResponse,
    ProviderBusinessProfileResponse,
    ProviderBusinessProfileUpsert,
)
from app.services.provider_storage_service import ProviderStorageService


class ProviderService:
    def __init__(self) -> None:
        self.repository = ProviderRepository()
        self.storage_service = ProviderStorageService()

    def get_business_profile(self, provider_id: str) -> ProviderBusinessProfileResponse:
        profile = self.repository.get_by_provider_id(provider_id)
        if not profile:
            now = datetime.now(tz=timezone.utc)
            return ProviderBusinessProfileResponse(
                id=provider_id,
                provider_id=provider_id,
                is_onboarding_completed=False,
                business_name="",
                location="",
                coverage_area="",
                contact_number="",
                whatsapp="",
                instagram="",
                facebook="",
                website="",
                logo_url="",
                photo_urls=[],
                logo=None,
                photos=[],
                created_at=now,
                updated_at=now,
            )
        return self._build_business_profile_response(
            provider_id=provider_id,
            profile=profile,
        )

    def upsert_business_profile(
        self, provider_id: str, payload: ProviderBusinessProfileUpsert
    ) -> ProviderBusinessProfileResponse:
        profile = self.repository.upsert(
            provider_id=provider_id,
            data=payload.model_dump(),
        )
        return self._build_business_profile_response(
            provider_id=provider_id,
            profile=profile,
        )

    def upload_logo(self, provider_id: str, file: UploadFile) -> ProviderBusinessAssetUploadResponse:
        storage_path, asset_url = self.storage_service.upload_logo(provider_id, file)
        try:
            self.repository.set_logo(provider_id, asset_url, storage_path)
        except Exception:
            self.storage_service.delete_file(storage_path)
            raise
        signed_asset = self.storage_service.build_signed_asset(storage_path)
        return ProviderBusinessAssetUploadResponse(
            provider_id=provider_id,
            asset_type="logo",
            storage_path=storage_path,
            asset=signed_asset,
            asset_url=asset_url,
        )

    def upload_photo(self, provider_id: str, file: UploadFile) -> ProviderBusinessAssetUploadResponse:
        storage_path, asset_url = self.storage_service.upload_photo(provider_id, file)
        try:
            self.repository.add_photo(provider_id, asset_url, storage_path)
        except Exception:
            self.storage_service.delete_file(storage_path)
            raise
        signed_asset = self.storage_service.build_signed_asset(storage_path)
        return ProviderBusinessAssetUploadResponse(
            provider_id=provider_id,
            asset_type="photo",
            storage_path=storage_path,
            asset=signed_asset,
            asset_url=asset_url,
        )

    def _build_business_profile_response(
        self,
        provider_id: str,
        profile: dict,
    ) -> ProviderBusinessProfileResponse:
        normalized_profile = {**profile}
        normalized_profile.pop("provider_id", None)

        logo_key = self.storage_service.extract_storage_key(
            str(
                normalized_profile.get("logo_storage_path")
                or normalized_profile.get("logo_url")
                or ""
            )
        )
        photo_values = (
            normalized_profile.get("photo_storage_paths")
            or normalized_profile.get("photo_urls")
            or []
        )
        photo_keys = [
            key
            for key in (
                self.storage_service.extract_storage_key(str(item))
                for item in photo_values
            )
            if key
        ]

        logo_asset = self.storage_service.build_signed_asset(logo_key) if logo_key else None
        photo_assets = [self.storage_service.build_signed_asset(key) for key in photo_keys]

        return ProviderBusinessProfileResponse(
            id=provider_id,
            provider_id=provider_id,
            **normalized_profile,
            is_onboarding_completed=self._is_onboarding_completed(normalized_profile),
            logo=logo_asset,
            photos=photo_assets,
        )

    @staticmethod
    def _is_onboarding_completed(profile: dict) -> bool:
        return all(
            str(profile.get(field_name, "") or "").strip()
            for field_name in ("business_name", "location", "contact_number")
        )
