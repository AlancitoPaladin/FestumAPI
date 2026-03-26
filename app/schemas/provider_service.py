from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.asset import SignedAssetResponse


ProviderServiceCategory = Literal[
    "dj",
    "photography",
    "entertainment",
    "banquet",
    "furniture",
    "equipment",
    "venue",
    "decoration",
    "salones-sociales",
    "mobiliario",
    "banquetes",
]
ProviderServiceStatus = Literal["draft", "published", "inactive"]
ProviderServicePublishableStatus = Literal["published", "inactive"]


class ProviderServiceDocument(BaseModel):
    category: ProviderServiceCategory
    name: str = Field(default="", max_length=120)
    subtitle: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=4000)
    unit_price_cents: int = Field(default=0, ge=0)
    price_label: str = Field(default="", max_length=80)
    badge: str = Field(default="", max_length=40)
    status: ProviderServiceStatus = "draft"
    main_image_key: str = Field(default="", max_length=1024)
    image_keys: list[str] = Field(default_factory=list, max_length=10)

    @field_validator(
        "name",
        "subtitle",
        "description",
        "price_label",
        "badge",
        "main_image_key",
        mode="before",
    )
    @classmethod
    def normalize_text(cls, value: str | None) -> str:
        if value is None:
            return ""
        return " ".join(str(value).split()).strip()

    @field_validator("image_keys", mode="before")
    @classmethod
    def normalize_image_keys(cls, value: list[str] | None) -> list[str]:
        if value is None:
            return []
        return [str(item).strip().lstrip("/") for item in value if str(item).strip()]


class ProviderServiceCreate(BaseModel):
    category: ProviderServiceCategory
    name: str = Field(..., min_length=1, max_length=120)
    subtitle: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=4000)
    main_image_key: str = Field(default="", max_length=1024)
    image_keys: list[str] = Field(default_factory=list, max_length=10)

    @field_validator(
        "name",
        "subtitle",
        "description",
        "main_image_key",
        mode="before",
    )
    @classmethod
    def normalize_text(cls, value: str | None) -> str:
        if value is None:
            return ""
        return " ".join(str(value).split()).strip()

    @field_validator("image_keys", mode="before")
    @classmethod
    def normalize_image_keys(cls, value: list[str] | None) -> list[str]:
        if value is None:
            return []
        return [str(item).strip().lstrip("/") for item in value if str(item).strip()]

    @model_validator(mode="after")
    def ensure_main_image_is_in_image_keys(self) -> "ProviderServiceCreate":
        if self.main_image_key and self.main_image_key not in self.image_keys:
            self.image_keys.insert(0, self.main_image_key)
        return self


class ProviderServiceDraftCreate(BaseModel):
    category: ProviderServiceCategory
    name: str = Field(..., min_length=1, max_length=120)
    description: str = Field(default="", max_length=4000)

    @field_validator("name", "description", mode="before")
    @classmethod
    def normalize_text(cls, value: str | None) -> str:
        if value is None:
            return ""
        return " ".join(str(value).split()).strip()


class ProviderServiceUpdate(BaseModel):
    category: ProviderServiceCategory | None = None
    name: str | None = Field(default=None, max_length=120)
    subtitle: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    main_image_key: str | None = Field(default=None, max_length=1024)
    image_keys: list[str] | None = None

    @field_validator(
        "name",
        "subtitle",
        "description",
        "main_image_key",
        mode="before",
    )
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(str(value).split()).strip()
        return normalized

    @field_validator("image_keys", mode="before")
    @classmethod
    def normalize_optional_image_keys(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return [str(item).strip().lstrip("/") for item in value if str(item).strip()]

    @model_validator(mode="after")
    def validate_has_at_least_one_field(self) -> "ProviderServiceUpdate":
        if not self.model_dump(exclude_none=True):
            raise ValueError("At least one field is required for update")
        return self


class ProviderServiceStatusUpdate(BaseModel):
    status: ProviderServicePublishableStatus


class ProviderServiceStatusUpdateResponse(BaseModel):
    ok: bool = True


class ProviderServiceImageResponse(SignedAssetResponse):
    is_main: bool = False


class ProviderServiceResponse(ProviderServiceDocument):
    id: str
    provider_id: str
    image: SignedAssetResponse | None = None
    main_image: SignedAssetResponse | None = None
    image_url: str = ""
    main_image_url: str = ""
    image_urls: list[str] = Field(default_factory=list)
    images: list[ProviderServiceImageResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ProviderServiceListResponse(BaseModel):
    items: list[ProviderServiceResponse]
    total: int


class ProviderServiceImageUploadResponse(BaseModel):
    service_id: str
    key: str
    image: SignedAssetResponse
    image_url: str = ""
    is_main: bool


class ProviderServiceImageReferenceRequest(BaseModel):
    image_key: str = Field(..., min_length=1, max_length=1024)

    @field_validator("image_key", mode="before")
    @classmethod
    def normalize_image_key(cls, value: str) -> str:
        return str(value).strip().lstrip("/")


class ProviderServiceImageReorderRequest(BaseModel):
    image_keys: list[str] = Field(..., min_length=1, max_length=10)

    @field_validator("image_keys", mode="before")
    @classmethod
    def normalize_image_keys(cls, value: list[str] | None) -> list[str]:
        if value is None:
            return []
        return [str(item).strip().lstrip("/") for item in value if str(item).strip()]


class ProviderServiceDeleteResponse(BaseModel):
    deleted: bool = True
