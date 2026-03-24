from datetime import datetime, timezone

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
                created_at=now,
                updated_at=now,
            )
        return ProviderBusinessProfileResponse(
            **profile,
            is_onboarding_completed=self._is_onboarding_completed(profile),
        )

    def upsert_business_profile(
        self, provider_id: str, payload: ProviderBusinessProfileUpsert
    ) -> ProviderBusinessProfileResponse:
        profile = self.repository.upsert(
            provider_id=provider_id,
            data=payload.model_dump(),
        )
        return ProviderBusinessProfileResponse(
            **profile,
            is_onboarding_completed=self._is_onboarding_completed(profile),
        )

    def upload_logo(self, provider_id: str, file) -> ProviderBusinessAssetUploadResponse:
        storage_path, asset_url = self.storage_service.upload_logo(provider_id, file)
        self.repository.set_logo(provider_id, asset_url, storage_path)
        return ProviderBusinessAssetUploadResponse(
            provider_id=provider_id,
            asset_type="logo",
            storage_path=storage_path,
            asset_url=asset_url,
        )

    def upload_photo(self, provider_id: str, file) -> ProviderBusinessAssetUploadResponse:
        storage_path, asset_url = self.storage_service.upload_photo(provider_id, file)
        self.repository.add_photo(provider_id, asset_url, storage_path)
        return ProviderBusinessAssetUploadResponse(
            provider_id=provider_id,
            asset_type="photo",
            storage_path=storage_path,
            asset_url=asset_url,
        )

    @staticmethod
    def _is_onboarding_completed(profile: dict) -> bool:
        return all(
            str(profile.get(field_name, "") or "").strip()
            for field_name in ("business_name", "location", "contact_number")
        )
