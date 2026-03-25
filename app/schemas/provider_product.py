from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.asset import SignedAssetResponse
from app.schemas.provider_service import ProviderServiceCategory

ProviderProductStatus = Literal["draft", "published", "inactive"]
ProviderProductPublishableStatus = Literal["published", "inactive"]

PRODUCT_DETAIL_FIELDS = (
    "approx_photos",
    "delivery_time",
    "min_duration",
    "extra_hour_allowed",
    "extra_hour_price",
    "min_guests",
    "max_guests",
    "banquet_type",
    "menu_included",
    "stock",
    "dimensions",
    "weight",
    "color_material",
    "venue_capacity",
    "is_price_per_hour",
    "decoration_type",
    "setup_time",
)


def _normalize_text_value(value: str | None) -> str | None:
    if value is None:
        return None
    return " ".join(str(value).split()).strip()


def _normalize_string_boolean_map(value: Any) -> dict[str, bool]:
    if value is None:
        return {}

    if isinstance(value, dict):
        normalized: dict[str, bool] = {}
        for key, item in value.items():
            normalized_key = _normalize_text_value(str(key))
            if not normalized_key:
                continue
            normalized[normalized_key] = bool(item)
        return normalized

    if isinstance(value, list):
        normalized = {}
        for item in value:
            normalized_key = _normalize_text_value(str(item))
            if not normalized_key:
                continue
            normalized[normalized_key] = True
        return normalized

    normalized_key = _normalize_text_value(str(value))
    return {normalized_key: True} if normalized_key else {}


def _normalize_details_map(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        return {}

    normalized: dict[str, Any] = {}
    for key, item in value.items():
        normalized_key = _normalize_text_value(str(key))
        if not normalized_key:
            continue
        if isinstance(item, str):
            normalized_item = _normalize_text_value(item)
            if normalized_item == "":
                continue
            normalized[normalized_key] = normalized_item
            continue
        normalized[normalized_key] = item
    return normalized


class ProviderProductImageResponse(SignedAssetResponse):
    is_main: bool = False


class ProviderProductFields(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    description: str = Field(default="", max_length=1500)
    price: float | None = Field(default=None, ge=0)
    pricing_unit: str | None = Field(default=None, max_length=50)
    details: dict[str, Any] = Field(default_factory=dict)
    inclusions: dict[str, bool] = Field(default_factory=dict)
    policies: dict[str, bool] = Field(default_factory=dict)
    approx_photos: int | None = Field(default=None, ge=0)
    delivery_time: str | None = Field(default=None, max_length=80)
    min_duration: str | None = Field(default=None, max_length=80)
    extra_hour_allowed: bool = False
    extra_hour_price: float | None = Field(default=None, ge=0)
    min_guests: int | None = Field(default=None, ge=0)
    max_guests: int | None = Field(default=None, ge=0)
    banquet_type: str | None = Field(default=None, max_length=50)
    menu_included: str | None = Field(default=None, max_length=1000)
    stock: int | None = Field(default=None, ge=0)
    dimensions: str | None = Field(default=None, max_length=80)
    weight: str | None = Field(default=None, max_length=80)
    color_material: str | None = Field(default=None, max_length=120)
    venue_capacity: int | None = Field(default=None, ge=0)
    is_price_per_hour: bool = False
    decoration_type: str | None = Field(default=None, max_length=50)
    setup_time: str | None = Field(default=None, max_length=80)
    main_image_url: str = Field(default="", max_length=500)
    image_urls: list[str] = Field(default_factory=list, max_length=10)
    status: ProviderProductStatus = "draft"

    @field_validator(
        "name",
        "description",
        "pricing_unit",
        "delivery_time",
        "min_duration",
        "banquet_type",
        "menu_included",
        "dimensions",
        "weight",
        "color_material",
        "decoration_type",
        "setup_time",
        mode="before",
    )
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        return _normalize_text_value(value)

    @field_validator("details", mode="before")
    @classmethod
    def normalize_details(cls, value: Any) -> dict[str, Any]:
        return _normalize_details_map(value)

    @field_validator("inclusions", "policies", mode="before")
    @classmethod
    def normalize_boolean_maps(cls, value: Any) -> dict[str, bool]:
        return _normalize_string_boolean_map(value)

    @field_validator("image_urls", mode="before")
    @classmethod
    def normalize_image_urls(cls, value: list[str] | None) -> list[str]:
        if value is None:
            return []
        return [str(item).strip() for item in value if str(item).strip()]


class ProviderProductCreate(ProviderProductFields):
    category: ProviderServiceCategory


class ProviderProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=1500)
    price: float | None = Field(default=None, ge=0)
    pricing_unit: str | None = Field(default=None, max_length=50)
    details: dict[str, Any] | None = None
    inclusions: dict[str, bool] | None = None
    policies: dict[str, bool] | None = None
    approx_photos: int | None = Field(default=None, ge=0)
    delivery_time: str | None = Field(default=None, max_length=80)
    min_duration: str | None = Field(default=None, max_length=80)
    extra_hour_allowed: bool | None = None
    extra_hour_price: float | None = Field(default=None, ge=0)
    min_guests: int | None = Field(default=None, ge=0)
    max_guests: int | None = Field(default=None, ge=0)
    banquet_type: str | None = Field(default=None, max_length=50)
    menu_included: str | None = Field(default=None, max_length=1000)
    stock: int | None = Field(default=None, ge=0)
    dimensions: str | None = Field(default=None, max_length=80)
    weight: str | None = Field(default=None, max_length=80)
    color_material: str | None = Field(default=None, max_length=120)
    venue_capacity: int | None = Field(default=None, ge=0)
    is_price_per_hour: bool | None = None
    decoration_type: str | None = Field(default=None, max_length=50)
    setup_time: str | None = Field(default=None, max_length=80)

    @field_validator(
        "name",
        "description",
        "pricing_unit",
        "delivery_time",
        "min_duration",
        "banquet_type",
        "menu_included",
        "dimensions",
        "weight",
        "color_material",
        "decoration_type",
        "setup_time",
        mode="before",
    )
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        return _normalize_text_value(value)

    @field_validator("details", mode="before")
    @classmethod
    def normalize_details(cls, value: Any) -> dict[str, Any] | None:
        if value is None:
            return None
        return _normalize_details_map(value)

    @field_validator("inclusions", "policies", mode="before")
    @classmethod
    def normalize_boolean_maps(cls, value: Any) -> dict[str, bool] | None:
        if value is None:
            return None
        return _normalize_string_boolean_map(value)

    @model_validator(mode="after")
    def validate_has_at_least_one_field(self) -> "ProviderProductUpdate":
        if not self.model_dump(exclude_none=True):
            raise ValueError("At least one field is required for update")
        return self


class ProviderProductValidated(ProviderProductFields):
    category: ProviderServiceCategory

    @model_validator(mode="after")
    def validate_category_rules(self) -> "ProviderProductValidated":
        self._require_fields("price", "pricing_unit")
        price_value = self._value("price")
        if price_value is None or float(price_value) <= 0:
            raise ValueError("price must be greater than 0")

        if self.category in {"dj", "photography", "entertainment"}:
            self._require_fields("min_duration")
            if self._value("extra_hour_allowed") and self._value("extra_hour_price") is None:
                raise ValueError("extra_hour_price is required when extra_hour_allowed is true")
            if self.category == "photography":
                self._require_fields("approx_photos", "delivery_time")

        if self.category in {"banquet", "banquetes"}:
            self._require_fields("min_guests", "max_guests", "banquet_type", "menu_included")

        if self.category in {"furniture", "equipment", "mobiliario"}:
            self._require_fields("stock", "dimensions", "weight", "color_material")

        if self.category in {"venue", "salones-sociales"}:
            self._require_fields("venue_capacity")

        if self.category == "decoration":
            self._require_fields("decoration_type", "setup_time")

        min_guests = self._value("min_guests")
        max_guests = self._value("max_guests")
        if min_guests is not None and max_guests is not None and min_guests > max_guests:
            raise ValueError("min_guests cannot be greater than max_guests")

        return self

    def _value(self, field_name: str) -> Any:
        value = getattr(self, field_name, None)
        if value is not None and value != "":
            return value
        return self.details.get(field_name)

    def _require_fields(self, *field_names: str) -> None:
        missing_fields = []
        for field_name in field_names:
            value = self._value(field_name)
            if value is None or value == "":
                missing_fields.append(field_name)
        if missing_fields:
            raise ValueError(
                f"Missing required fields for category {self.category}: {', '.join(missing_fields)}"
            )


class ProviderProductResponse(ProviderProductFields):
    id: str
    provider_id: str
    service_id: str
    category: ProviderServiceCategory
    image_storage_paths: list[str] = Field(default_factory=list)
    main_image_storage_path: str = Field(default="", max_length=1024)
    image: SignedAssetResponse | None = None
    images: list[ProviderProductImageResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ProviderProductListResponse(BaseModel):
    items: list[ProviderProductResponse]
    total: int


class ProviderProductStatusUpdate(BaseModel):
    status: ProviderProductPublishableStatus


class ProviderProductStatusUpdateResponse(BaseModel):
    ok: bool = True


class ProviderProductImageUploadResponse(BaseModel):
    product_id: str
    key: str
    image: SignedAssetResponse
    image_url: str = ""
    is_main: bool


class ProviderProductImageReferenceRequest(BaseModel):
    image_key: str = Field(..., min_length=1, max_length=1024)

    @field_validator("image_key", mode="before")
    @classmethod
    def normalize_image_key(cls, value: str) -> str:
        return str(value).strip().lstrip("/")


class ProviderProductImageReorderRequest(BaseModel):
    image_keys: list[str] = Field(..., min_length=1, max_length=10)

    @field_validator("image_keys", mode="before")
    @classmethod
    def normalize_image_keys(cls, value: list[str] | None) -> list[str]:
        if value is None:
            return []
        return [str(item).strip().lstrip("/") for item in value if str(item).strip()]


class ProviderProductDeleteResponse(BaseModel):
    deleted: bool = True
