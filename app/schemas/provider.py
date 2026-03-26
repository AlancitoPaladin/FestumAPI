from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.asset import SignedAssetResponse
from app.schemas.common_validators import (
    normalize_phone,
    normalize_social_handle,
    normalize_text,
    normalize_website,
)


class ProviderBusinessProfileBase(BaseModel):
    business_name: str = Field(default="", max_length=120)
    location: str = Field(default="", max_length=120)
    coverage_area: str = Field(default="", max_length=160)
    contact_number: str = Field(default="", max_length=20)
    whatsapp: str = Field(default="", max_length=20)
    instagram: str = Field(default="", max_length=100)
    facebook: str = Field(default="", max_length=100)
    website: str = Field(default="", max_length=255)
    logo_url: str = Field(default="", max_length=500)
    photo_urls: list[str] = Field(default_factory=list, max_length=10)

    @field_validator(
        "business_name",
        "location",
        "coverage_area",
        "logo_url",
        mode="before",
    )
    @classmethod
    def normalize_text(cls, value: str | None) -> str:
        return normalize_text(value)

    @field_validator("contact_number", "whatsapp", mode="before")
    @classmethod
    def normalize_phone_fields(cls, value: str | None) -> str:
        return normalize_phone(value)

    @field_validator("instagram", mode="before")
    @classmethod
    def normalize_instagram(cls, value: str | None) -> str:
        return normalize_social_handle(value)

    @field_validator("facebook", mode="before")
    @classmethod
    def normalize_facebook(cls, value: str | None) -> str:
        return normalize_text(value)

    @field_validator("website", mode="before")
    @classmethod
    def normalize_website_field(cls, value: str | None) -> str:
        return normalize_website(value)

    @field_validator("photo_urls", mode="before")
    @classmethod
    def normalize_photo_urls(cls, value: list[str] | None) -> list[str]:
        if value is None:
            return []
        return [normalize_text(str(item)) for item in value if str(item).strip()]


class ProviderBusinessProfileUpsert(ProviderBusinessProfileBase):
    pass


class ProviderBusinessProfileResponse(ProviderBusinessProfileBase):
    id: str
    provider_id: str
    is_onboarding_completed: bool = False
    logo: SignedAssetResponse | None = None
    photos: list[SignedAssetResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ProviderBusinessAssetUploadResponse(BaseModel):
    provider_id: str
    asset_type: str
    storage_path: str
    asset: SignedAssetResponse
    asset_url: str | None = None
