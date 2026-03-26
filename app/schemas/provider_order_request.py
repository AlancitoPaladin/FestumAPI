from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


ProviderOrderRequestStatus = Literal["pending_provider_approval", "accepted", "rejected"]


class ProviderOrderRequestItemResponse(BaseModel):
    service_id: str
    service_name: str = ""
    product_id: str | None = None
    product_name: str | None = None
    selected_product_ids: list[str] = Field(default_factory=list)
    selected_products_snapshot: list[dict] = Field(default_factory=list)
    unit_price_cents: int = Field(default=0, ge=0)
    total_item_cents: int = Field(default=0, ge=0)


class ProviderOrderRequestResponse(BaseModel):
    id: str
    order_id: str
    client_id: str
    client_name: str = ""
    event_date: str
    notes: str = ""
    title: str
    status: ProviderOrderRequestStatus
    subtotal_cents: int = Field(default=0, ge=0)
    service_fee_cents: int = Field(default=0, ge=0)
    tax_cents: int = Field(default=0, ge=0)
    total_cents: int = Field(default=0, ge=0)
    currency: str = "MXN"
    fee_rate: float = 0
    tax_rate: float = 0
    total_label: str
    items: list[ProviderOrderRequestItemResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ProviderOrderRequestListResponse(BaseModel):
    items: list[ProviderOrderRequestResponse] = Field(default_factory=list)
    total: int = 0


class ProviderOrderRequestDecisionPayload(BaseModel):
    decision: Literal["accepted", "rejected"]


class ProviderOrderSummaryResponse(BaseModel):
    id: str
    title: str
    status: str
    subtotal_cents: int = Field(default=0, ge=0)
    service_fee_cents: int = Field(default=0, ge=0)
    tax_cents: int = Field(default=0, ge=0)
    total_cents: int = Field(default=0, ge=0)
    currency: str = "MXN"
    fee_rate: float = 0
    tax_rate: float = 0
    total_label: str
    created_at: datetime


class ProviderOrderRequestDecisionResponse(BaseModel):
    order: ProviderOrderSummaryResponse
