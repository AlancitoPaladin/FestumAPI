from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


ProviderAvailabilityStatus = Literal["available", "reserved", "blocked"]


class ProviderAvailabilityBookingSummary(BaseModel):
    booking_id: str | None = None
    customer_name: str = ""
    customer_image_url: str = ""
    event_type: str = ""
    guests: int = 0


class ProviderAvailabilityDayResponse(BaseModel):
    date: date
    status: ProviderAvailabilityStatus
    booking: ProviderAvailabilityBookingSummary | None = None


class ProviderAvailabilityMonthResponse(BaseModel):
    product_id: str
    product_name: str
    year: int
    month: int
    days: list[ProviderAvailabilityDayResponse]


class ProviderAvailabilityStatusResponse(BaseModel):
    product_id: str
    date: date
    status: ProviderAvailabilityStatus

