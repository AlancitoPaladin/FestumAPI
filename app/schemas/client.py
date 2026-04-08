from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.asset import SignedAssetResponse


ServiceCategory = str
OrderStatus = Literal[
    "pending_payment",
    "pending_provider_approval",
    "confirmed",
    "in_progress",
    "completed",
    "cancelled",
    "rejected",
]


class OkResponse(BaseModel):
    ok: bool = True
    idempotent: bool = False


class CartItem(BaseModel):
    id: str
    name: str = Field(..., min_length=1, max_length=120)
    quantity: int = Field(default=1, ge=1)
    unit_price_cents: int = Field(..., ge=0)
    service_name: str = Field(..., min_length=1, max_length=120)
    product_id: str | None = None
    product_name: str | None = None
    selected_product_ids: list[str] = Field(default_factory=list)


class AddCartItemRequest(BaseModel):
    service_id: str = Field(..., min_length=1, max_length=120)
    name: str = Field(..., min_length=1, max_length=120)
    unit_price_cents: int = Field(..., ge=0)
    product_id: str | None = None
    product_name: str | None = None
    selected_product_ids: list[str] = Field(default_factory=list)


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
    subtotal_cents: int | None = Field(default=None, ge=0)
    service_fee_cents: int | None = Field(default=None, ge=0)
    tax_cents: int | None = Field(default=None, ge=0)
    total_cents: int | None = Field(default=None, ge=0)
    currency: str | None = None
    fee_rate: float | None = None
    tax_rate: float | None = None
    total_label: str = Field(..., min_length=1, max_length=80)
    items: list[dict] = Field(default_factory=list)
    created_at: datetime | None = None


class OrdersResponse(BaseModel):
    items: list[OrderItem]


class OrderListItem(BaseModel):
    id: str
    title: str = Field(..., min_length=3, max_length=180)
    status: OrderStatus
    total_cents: int | None = Field(default=None, ge=0)
    total_label: str = Field(..., min_length=1, max_length=80)
    created_at: datetime | None = None
    service_name: str | None = None


class OrdersListResponse(BaseModel):
    items: list[OrderListItem]


class ActiveServiceIdsResponse(BaseModel):
    service_ids: list[str] = Field(default_factory=list)
    total: int = Field(default=0, ge=0)


class CreateOrderRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=180)
    status: OrderStatus
    total_label: str = Field(..., min_length=1, max_length=80)


class UpdateOrderStatusRequest(BaseModel):
    status: OrderStatus


class CheckoutOrderResponse(BaseModel):
    id: str
    title: str
    status: OrderStatus
    subtotal_cents: int = Field(default=0, ge=0)
    service_fee_cents: int = Field(default=0, ge=0)
    tax_cents: int = Field(default=0, ge=0)
    total_cents: int = Field(default=0, ge=0)
    currency: str = "MXN"
    fee_rate: float = 0
    tax_rate: float = 0
    total_label: str
    created_at: datetime


class SelectedProductSnapshot(BaseModel):
    id: str
    name: str
    unit_price_cents: int = Field(..., ge=0)


class CheckoutItemResponse(BaseModel):
    service_id: str
    service_name: str
    product_id: str | None = None
    product_name: str | None = None
    selected_product_ids: list[str] = Field(default_factory=list)
    selected_products_snapshot: list[SelectedProductSnapshot] = Field(default_factory=list)
    unit_price_cents: int = Field(..., ge=0)
    total_item_cents: int = Field(..., ge=0)


class CheckoutProviderEffectsResponse(BaseModel):
    reservations_created: int = 0
    notifications_created: int = 0


class CheckoutResponse(BaseModel):
    order: CheckoutOrderResponse
    items: list[CheckoutItemResponse]
    provider_effects: CheckoutProviderEffectsResponse


class CheckoutRequestItemPayload(BaseModel):
    service_id: str = Field(..., min_length=1, max_length=120)
    product_id: str | None = None
    selected_product_ids: list[str] | None = None


class CheckoutRequestPayload(BaseModel):
    items: list[CheckoutRequestItemPayload] = Field(default_factory=list)


class OrderRequestItemPayload(BaseModel):
    service_id: str = Field(..., min_length=1, max_length=120)
    product_id: str | None = None
    selected_product_ids: list[str] | None = None
    product_name: str | None = None
    service_name: str | None = None


class CreateOrderRequestPayload(BaseModel):
    event_date: date
    notes: str = Field(default="", max_length=1500)
    items: list[OrderRequestItemPayload] = Field(default_factory=list, min_length=1)


class OrderRequestCreateResponse(BaseModel):
    order: CheckoutOrderResponse


class ClientProductItem(BaseModel):
    id: str
    service_id: str
    name: str = Field(..., min_length=1, max_length=120)
    description: str = Field(default="", max_length=4000)
    price_label: str = Field(..., min_length=1, max_length=80)
    unit_price_cents: int = Field(..., ge=0)
    category: str
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
    category: str
    short_title: str | None = None
    short_subtitle: str | None = None
    image: SignedAssetResponse | None = None
    image_url: str = ""
    images: list[dict] = Field(default_factory=list)
    image_urls: list[str] = Field(default_factory=list)
    products: list[ClientProductItem] = Field(default_factory=list)


class HomeServicesResponse(BaseModel):
    salones_sociales: list[ServiceItem] = Field(default_factory=list, alias="salones-sociales")
    mobiliario: list[ServiceItem] = Field(default_factory=list)
    banquetes: list[ServiceItem] = Field(default_factory=list)
    dj: list[ServiceItem] = Field(default_factory=list)
    decoracion: list[ServiceItem] = Field(default_factory=list)
    fotografia: list[ServiceItem] = Field(default_factory=list)
    entretenimiento: list[ServiceItem] = Field(default_factory=list)
    otros: list[ServiceItem] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class BootstrapCartSummary(BaseModel):
    count: int = Field(default=0, ge=0)
    service_ids: list[str] = Field(default_factory=list)


class BootstrapOrdersSummary(BaseModel):
    count: int = Field(default=0, ge=0)


class BootstrapLocksSummary(BaseModel):
    active_service_ids: list[str] = Field(default_factory=list)


class BootstrapMeta(BaseModel):
    generated_at: datetime


class ClientBootstrapResponse(BaseModel):
    home: HomeServicesResponse
    cart: BootstrapCartSummary
    orders: BootstrapOrdersSummary
    locks: BootstrapLocksSummary
    meta: BootstrapMeta


class ServiceListResponse(BaseModel):
    items: list[ServiceItem]
    total: int
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    has_next: bool
