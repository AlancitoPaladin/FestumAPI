from datetime import date

from pydantic import BaseModel, Field

from app.schemas.asset import SignedAssetResponse
from app.schemas.provider_service import ProviderServiceCategory


class ProviderReservationProductImageResponse(SignedAssetResponse):
    is_main: bool = False


class ProviderReservationNextBookingResponse(BaseModel):
    booking_id: str
    customer_name: str = ""
    customer_image_url: str = ""
    avatar_url: str = ""
    customer_image: SignedAssetResponse | None = None
    date: date
    status: str = ""


class ProviderReservationProductSummaryResponse(BaseModel):
    id: str
    service_id: str
    product_name: str = ""
    category: ProviderServiceCategory
    image_url: str = ""
    main_image_url: str = ""
    image: SignedAssetResponse | None = None
    main_image: SignedAssetResponse | None = None
    images: list[ProviderReservationProductImageResponse] = Field(default_factory=list)
    image_urls: list[str] = Field(default_factory=list)
    next_booking: ProviderReservationNextBookingResponse | None = None


class ProviderReservationProductSummaryListResponse(BaseModel):
    items: list[ProviderReservationProductSummaryResponse] = Field(default_factory=list)
    total: int = 0
