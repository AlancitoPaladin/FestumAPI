from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.asset import SignedAssetResponse


ServiceCategory = Literal[
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
OrderStatus = Literal["pending_payment", "confirmed", "in_progress", "completed", "cancelled"]


class OkResponse(BaseModel):
    ok: bool = True


class CartItem(BaseModel):
    id: str
    name: str = Field(..., min_length=1, max_length=120)
    quantity: int = Field(default=1, ge=1)
    unit_price_cents: int = Field(..., ge=0)


class AddCartItemRequest(BaseModel):
    service_id: str = Field(..., min_length=1, max_length=120)
    name: str = Field(..., min_length=1, max_length=120)
    unit_price_cents: int = Field(..., ge=0)


class RestoreCartItemRequest(BaseModel):
    item: CartItem
    index: int = Field(..., ge=0)


class CartItemsResponse(BaseModel):
    items: list[CartItem]


class CartContainsResponse(BaseModel):
    contains: bool


class RemovedCartItemResponse(BaseModel):
    item: CartItem


class OrderItem(BaseModel):
    id: str
    title: str = Field(..., min_length=3, max_length=180)
    status: OrderStatus
    total_label: str = Field(..., min_length=1, max_length=80)
    created_at: datetime | None = None


class OrdersResponse(BaseModel):
    items: list[OrderItem]


class CreateOrderRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=180)
    status: OrderStatus
    total_label: str = Field(..., min_length=1, max_length=80)


class UpdateOrderStatusRequest(BaseModel):
    status: OrderStatus


class ClientProductItem(BaseModel):
    id: str
    service_id: str
    name: str = Field(..., min_length=1, max_length=120)
    description: str = Field(default="", max_length=4000)
    price_label: str = Field(..., min_length=1, max_length=80)
    unit_price_cents: int = Field(..., ge=0)
    category: ServiceCategory
    image: SignedAssetResponse | None = None
    image_url: str = ""


class ClientAvailabilityDay(BaseModel):
    date: str
    status: Literal["available", "reserved", "blocked"]


class ClientProductAvailabilityResponse(BaseModel):
    product_id: str
    year: int
    month: int
    days: list[ClientAvailabilityDay] = Field(default_factory=list)


class ServiceItem(BaseModel):
    id: str
    name: str = Field(..., min_length=1, max_length=120)
    subtitle: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=4000)
    price_label: str = Field(..., min_length=1, max_length=80)
    unit_price_cents: int = Field(..., ge=0)
    badge: str = Field(..., min_length=1, max_length=40)
    category: ServiceCategory
    short_title: str | None = None
    short_subtitle: str | None = None
    image: SignedAssetResponse | None = None
    image_url: str = ""
    products: list[ClientProductItem] = Field(default_factory=list)


class HomeServicesResponse(BaseModel):
    dj: list[ServiceItem] = Field(default_factory=list)
    photography: list[ServiceItem] = Field(default_factory=list)
    entertainment: list[ServiceItem] = Field(default_factory=list)
    banquet: list[ServiceItem] = Field(default_factory=list)
    furniture: list[ServiceItem] = Field(default_factory=list)
    equipment: list[ServiceItem] = Field(default_factory=list)
    venue: list[ServiceItem] = Field(default_factory=list)
    decoration: list[ServiceItem] = Field(default_factory=list)
    salones_sociales: list[ServiceItem] = Field(alias="salones-sociales", default_factory=list)
    mobiliario: list[ServiceItem] = Field(default_factory=list)
    banquetes: list[ServiceItem] = Field(default_factory=list)

    model_config = {
        "populate_by_name": True,
    }
