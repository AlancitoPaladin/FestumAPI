from datetime import date

from pydantic import BaseModel, Field

from app.schemas.provider_service import ProviderServiceCategory


class ProviderReservationNextBookingResponse(BaseModel):
    booking_id: str
    customer_name: str = ""
    customer_image_url: str = ""
    date: date
    status: str = ""


class ProviderReservationProductSummaryResponse(BaseModel):
    id: str
    service_id: str
    product_name: str = ""
    category: ProviderServiceCategory
    image_url: str = ""
    next_booking: ProviderReservationNextBookingResponse | None = None


class ProviderReservationProductSummaryListResponse(BaseModel):
    items: list[ProviderReservationProductSummaryResponse] = Field(default_factory=list)
    total: int = 0
