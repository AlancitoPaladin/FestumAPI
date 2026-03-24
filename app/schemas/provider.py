from datetime import datetime

from pydantic import BaseModel, Field, field_validator


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
        "contact_number",
        "whatsapp",
        "instagram",
        "facebook",
        "website",
        "logo_url",
        mode="before",
    )
    @classmethod
    def normalize_text(cls, value: str | None) -> str:
        if value is None:
            return ""
        return " ".join(str(value).split()).strip()

    @field_validator("photo_urls", mode="before")
    @classmethod
    def normalize_photo_urls(cls, value: list[str] | None) -> list[str]:
        if value is None:
            return []
        return [" ".join(str(item).split()).strip() for item in value if str(item).strip()]


class ProviderBusinessProfileUpsert(ProviderBusinessProfileBase):
    pass


class ProviderBusinessProfileResponse(ProviderBusinessProfileBase):
    provider_id: str
    is_onboarding_completed: bool = False
    created_at: datetime
    updated_at: datetime


class ProviderBusinessAssetUploadResponse(BaseModel):
    provider_id: str
    asset_type: str
    storage_path: str
    asset_url: str
