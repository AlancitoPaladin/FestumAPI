from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.asset import SignedAssetResponse


ServiceCategory = Literal["salones-sociales", "mobiliario", "banquetes"]
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


class ServiceItem(BaseModel):
    id: str
    name: str = Field(..., min_length=1, max_length=120)
    subtitle: str = Field(..., min_length=1, max_length=200)
    price_label: str = Field(..., min_length=1, max_length=80)
    unit_price_cents: int = Field(..., ge=0)
    badge: str = Field(..., min_length=1, max_length=40)
    category: ServiceCategory
    short_title: str | None = None
    short_subtitle: str | None = None
    image: SignedAssetResponse | None = None
    image_url: str = ""


class HomeServicesResponse(BaseModel):
    salones_sociales: list[ServiceItem] = Field(alias="salones-sociales", default_factory=list)
    mobiliario: list[ServiceItem] = Field(default_factory=list)
    banquetes: list[ServiceItem] = Field(default_factory=list)

    model_config = {
        "populate_by_name": True,
    }
