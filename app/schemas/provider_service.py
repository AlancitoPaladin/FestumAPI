from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


ProviderServiceCategory = Literal[
    "dj",
    "photography",
    "entertainment",
    "banquet",
    "furniture",
    "equipment",
    "venue",
    "decoration",
]

ProviderServiceStatus = Literal["draft", "active", "inactive"]


class ProviderServiceBase(BaseModel):
    category: ProviderServiceCategory
    name: str = Field(..., min_length=2, max_length=120)
    description: str = Field(default="", max_length=1500)
    status: ProviderServiceStatus = "draft"
    main_image_url: str = Field(default="", max_length=500)
    image_urls: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("name", "description", mode="before")
    @classmethod
    def normalize_text(cls, value: str | None) -> str:
        if value is None:
            return ""
        return " ".join(str(value).split()).strip()

    @field_validator("image_urls", mode="before")
    @classmethod
    def normalize_image_urls(cls, value: list[str] | None) -> list[str]:
        if value is None:
            return []
        return [str(item).strip() for item in value if str(item).strip()]


class ProviderServiceCreate(ProviderServiceBase):
    pass


class ProviderServiceDraftCreate(BaseModel):
    category: ProviderServiceCategory
    name: str = Field(..., min_length=2, max_length=120)
    description: str = Field(default="", max_length=1500)

    @field_validator("name", "description", mode="before")
    @classmethod
    def normalize_text(cls, value: str | None) -> str:
        if value is None:
            return ""
        return " ".join(str(value).split()).strip()


class ProviderServiceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=1500)
    status: ProviderServiceStatus | None = None

    @field_validator("name", "description", mode="before")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return " ".join(str(value).split()).strip()

    @model_validator(mode="after")
    def validate_has_at_least_one_field(self) -> "ProviderServiceUpdate":
        if not self.model_dump(exclude_none=True):
            raise ValueError("At least one field is required for update")
        return self


class ProviderServiceResponse(ProviderServiceBase):
    id: str
    provider_id: str
    image_storage_paths: list[str] = Field(default_factory=list)
    main_image_storage_path: str = Field(default="", max_length=500)
    created_at: datetime
    updated_at: datetime


class ProviderServiceListResponse(BaseModel):
    items: list[ProviderServiceResponse]
    total: int


class ProviderServiceImageUploadResponse(BaseModel):
    service_id: str
    storage_path: str
    image_url: str
    is_main: bool


class ProviderServiceImageReferenceRequest(BaseModel):
    image_url: str = Field(..., min_length=1, max_length=500)

    @field_validator("image_url", mode="before")
    @classmethod
    def normalize_image_url(cls, value: str) -> str:
        return str(value).strip()


class ProviderServiceImageReorderRequest(BaseModel):
    image_urls: list[str] = Field(..., min_length=1, max_length=10)

    @field_validator("image_urls", mode="before")
    @classmethod
    def normalize_image_urls(cls, value: list[str] | None) -> list[str]:
        if value is None:
            return []
        return [str(item).strip() for item in value if str(item).strip()]


class ProviderServiceDeleteResponse(BaseModel):
    deleted: bool = True
