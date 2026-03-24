from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


ProviderBookingSource = Literal["manual", "client"]
ProviderBookingStatus = Literal["pending", "confirmed", "rejected", "cancelled"]


class ProviderBookingBase(BaseModel):
    customer_name: str = Field(..., min_length=2, max_length=120)
    customer_image_url: str = Field(default="", max_length=500)
    event_date: date
    has_specific_schedule: bool = False
    start_time: time | None = None
    end_time: time | None = None
    event_type: str = Field(..., min_length=2, max_length=120)
    guests: int = Field(default=0, ge=0)
    contact_phone: str = Field(default="", max_length=40)
    contact_email: str = Field(default="", max_length=120)
    event_location: str = Field(default="", max_length=200)
    payment_details: str = Field(default="", max_length=500)
    total_amount: float = Field(default=0, ge=0)
    paid_amount: float = Field(default=0, ge=0)
    notes: str = Field(default="", max_length=1500)

    @field_validator(
        "customer_name",
        "event_type",
        "notes",
        "customer_image_url",
        "contact_phone",
        "contact_email",
        "event_location",
        "payment_details",
        mode="before",
    )
    @classmethod
    def normalize_text(cls, value: str | None) -> str:
        if value is None:
            return ""
        return " ".join(str(value).split()).strip()

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def normalize_time(cls, value: time | str | None) -> time | None:
        if value is None or value == "":
            return None
        if isinstance(value, time):
            return value.replace(second=0, microsecond=0)

        normalized = str(value).strip()
        if len(normalized) == 5:
            normalized = f"{normalized}:00"
        return time.fromisoformat(normalized).replace(second=0, microsecond=0)

    @model_validator(mode="after")
    def validate_schedule(self) -> "ProviderBookingBase":
        if self.has_specific_schedule:
            if self.start_time is None or self.end_time is None:
                raise ValueError("start_time and end_time are required when has_specific_schedule is true")
            if self.end_time <= self.start_time:
                raise ValueError("end_time must be later than start_time")
        else:
            self.start_time = None
            self.end_time = None
        if self.paid_amount > self.total_amount:
            raise ValueError("paid_amount cannot be greater than total_amount")
        return self


class ProviderManualBookingCreate(ProviderBookingBase):
    @model_validator(mode="after")
    def validate_event_date(self) -> "ProviderManualBookingCreate":
        if self.event_date < date.today():
            raise ValueError("event_date cannot be in the past")
        return self


class ProviderBookingStatusUpdate(BaseModel):
    status: ProviderBookingStatus


class ProviderBookingUpdate(BaseModel):
    customer_name: str | None = Field(default=None, min_length=2, max_length=120)
    customer_image_url: str | None = Field(default=None, max_length=500)
    event_date: date | None = None
    has_specific_schedule: bool | None = None
    start_time: time | None = None
    end_time: time | None = None
    event_type: str | None = Field(default=None, min_length=2, max_length=120)
    guests: int | None = Field(default=None, ge=0)
    contact_phone: str | None = Field(default=None, max_length=40)
    contact_email: str | None = Field(default=None, max_length=120)
    event_location: str | None = Field(default=None, max_length=200)
    payment_details: str | None = Field(default=None, max_length=500)
    total_amount: float | None = Field(default=None, ge=0)
    paid_amount: float | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=1500)

    @field_validator(
        "customer_name",
        "event_type",
        "notes",
        "customer_image_url",
        "contact_phone",
        "contact_email",
        "event_location",
        "payment_details",
        mode="before",
    )
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return " ".join(str(value).split()).strip()

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def normalize_time(cls, value: time | str | None) -> time | None:
        if value is None or value == "":
            return None
        if isinstance(value, time):
            return value.replace(second=0, microsecond=0)

        normalized = str(value).strip()
        if len(normalized) == 5:
            normalized = f"{normalized}:00"
        return time.fromisoformat(normalized).replace(second=0, microsecond=0)

    @model_validator(mode="after")
    def validate_has_at_least_one_field(self) -> "ProviderBookingUpdate":
        if not self.model_dump(exclude_none=True):
            raise ValueError("At least one field is required for update")
        return self


class ProviderBookingResponse(ProviderBookingBase):
    id: str
    provider_id: str
    service_id: str
    service_name: str = ""
    product_id: str
    product_name: str = ""
    source: ProviderBookingSource
    status: ProviderBookingStatus
    status_label: str = ""
    time_label: str = ""
    pending_amount: float = 0
    created_at: datetime
    updated_at: datetime


class ProviderBookingListResponse(BaseModel):
    items: list[ProviderBookingResponse]
    total: int
