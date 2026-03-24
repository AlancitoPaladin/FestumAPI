from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.provider_service import ProviderServiceCategory


class ProviderProductFields(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    description: str = Field(default="", max_length=1500)
    price: float | None = Field(default=None, ge=0)
    pricing_unit: str | None = Field(default=None, max_length=50)
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
    inclusions: list[str] = Field(default_factory=list, max_length=50)
    policies: list[str] = Field(default_factory=list, max_length=50)
    main_image_url: str = Field(default="", max_length=500)
    image_urls: list[str] = Field(default_factory=list, max_length=10)

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
        if value is None:
            return None
        return " ".join(str(value).split()).strip()

    @field_validator("inclusions", "policies", "image_urls", mode="before")
    @classmethod
    def normalize_string_lists(cls, value: list[str] | None) -> list[str]:
        if value is None:
            return []
        return [" ".join(str(item).split()).strip() for item in value if str(item).strip()]


class ProviderProductCreate(ProviderProductFields):
    pass


class ProviderProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=1500)
    price: float | None = Field(default=None, ge=0)
    pricing_unit: str | None = Field(default=None, max_length=50)
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
    inclusions: list[str] | None = None
    policies: list[str] | None = None

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
        if value is None:
            return None
        return " ".join(str(value).split()).strip()

    @field_validator("inclusions", "policies", mode="before")
    @classmethod
    def normalize_string_lists(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return [" ".join(str(item).split()).strip() for item in value if str(item).strip()]

    @model_validator(mode="after")
    def validate_has_at_least_one_field(self) -> "ProviderProductUpdate":
        if not self.model_dump(exclude_none=True):
            raise ValueError("At least one field is required for update")
        return self


class ProviderProductValidated(ProviderProductFields):
    category: ProviderServiceCategory

    @model_validator(mode="after")
    def validate_category_rules(self) -> "ProviderProductValidated":
        if self.category in {"dj", "photography", "entertainment"}:
            self._require_fields("price", "pricing_unit", "min_duration")
            if self.extra_hour_allowed and self.extra_hour_price is None:
                raise ValueError("extra_hour_price is required when extra_hour_allowed is true")
            if self.category == "photography":
                self._require_fields("approx_photos", "delivery_time")

        if self.category == "banquet":
            self._require_fields("price", "min_guests", "max_guests", "banquet_type", "menu_included")

        if self.category in {"furniture", "equipment"}:
            self._require_fields("price", "stock", "dimensions", "weight", "color_material")

        if self.category == "venue":
            self._require_fields("price", "venue_capacity")

        if self.category == "decoration":
            self._require_fields("price", "decoration_type", "setup_time")

        if (
            self.min_guests is not None
            and self.max_guests is not None
            and self.min_guests > self.max_guests
        ):
            raise ValueError("min_guests cannot be greater than max_guests")

        return self

    def _require_fields(self, *field_names: str) -> None:
        missing_fields = []
        for field_name in field_names:
            value = getattr(self, field_name)
            if value is None or value == "":
                missing_fields.append(field_name)
        if missing_fields:
            raise ValueError(f"Missing required fields for category {self.category}: {', '.join(missing_fields)}")


class ProviderProductResponse(ProviderProductFields):
    id: str
    provider_id: str
    service_id: str
    category: ProviderServiceCategory
    image_storage_paths: list[str] = Field(default_factory=list)
    main_image_storage_path: str = Field(default="", max_length=500)
    created_at: datetime
    updated_at: datetime


class ProviderProductListResponse(BaseModel):
    items: list[ProviderProductResponse]
    total: int


class ProviderProductImageUploadResponse(BaseModel):
    product_id: str
    storage_path: str
    image_url: str
    is_main: bool


class ProviderProductImageReferenceRequest(BaseModel):
    image_url: str = Field(..., min_length=1, max_length=500)

    @field_validator("image_url", mode="before")
    @classmethod
    def normalize_image_url(cls, value: str) -> str:
        return str(value).strip()


class ProviderProductImageReorderRequest(BaseModel):
    image_urls: list[str] = Field(..., min_length=1, max_length=10)

    @field_validator("image_urls", mode="before")
    @classmethod
    def normalize_image_urls(cls, value: list[str] | None) -> list[str]:
        if value is None:
            return []
        return [str(item).strip() for item in value if str(item).strip()]


class ProviderProductDeleteResponse(BaseModel):
    deleted: bool = True
