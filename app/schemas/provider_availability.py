from datetime import date as date_type
from typing import Literal

from pydantic import BaseModel, Field


ProviderAvailabilityStatus = Literal["available", "reserved", "blocked"]


class ProviderAvailabilityBlockRequest(BaseModel):
    date: date_type


class ProviderAvailabilityBookingSummary(BaseModel):
    id: str | None = None
    booking_id: str | None = None
    customer_name: str = ""
    customer_image_url: str = ""
    date: date_type | None = None
    time: str = ""
    event_type: str = ""
    guests: int = 0
    total_amount: float = 0
    paid_amount: float = 0
    status: str = ""
    notes: str = ""


class ProviderAvailabilityDayResponse(BaseModel):
    date: date_type
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
    date: date_type
    status: ProviderAvailabilityStatus
