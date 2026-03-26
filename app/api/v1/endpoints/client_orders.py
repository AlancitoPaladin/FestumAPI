from fastapi import APIRouter, Depends, Header, status

from app.api.dependencies.auth import get_current_user
from app.schemas.client import (
    CheckoutResponse,
    CheckoutRequestPayload,
    CreateOrderRequestPayload,
    CreateOrderRequest,
    OrderRequestCreateResponse,
    OkResponse,
    OrderItem,
    OrdersResponse,
    UpdateOrderStatusRequest,
)
from app.schemas.user import UserResponse
from app.services.client_orders_service import ClientOrdersService

router = APIRouter()


@router.get("/orders", response_model=OrdersResponse)
def get_orders(
    current_user: UserResponse = Depends(get_current_user),
    service: ClientOrdersService = Depends(ClientOrdersService),
) -> OrdersResponse:
    return service.list_orders(current_user.id)


@router.post("/orders", response_model=OrderItem, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: CreateOrderRequest | None = None,
    current_user: UserResponse = Depends(get_current_user),
    service: ClientOrdersService = Depends(ClientOrdersService),
) -> OrderItem:
    return service.create_order(current_user.id, payload)


@router.post("/orders/checkout", response_model=CheckoutResponse, status_code=status.HTTP_201_CREATED)
def checkout_order(
    payload: CheckoutRequestPayload | None = None,
    current_user: UserResponse = Depends(get_current_user),
    service: ClientOrdersService = Depends(ClientOrdersService),
) -> CheckoutResponse:
    return service.checkout(current_user, payload)


@router.post("/orders/requests", response_model=OrderRequestCreateResponse, status_code=status.HTTP_201_CREATED)
def create_order_request(
    payload: CreateOrderRequestPayload,
    current_user: UserResponse = Depends(get_current_user),
    service: ClientOrdersService = Depends(ClientOrdersService),
) -> OrderRequestCreateResponse:
    return service.create_order_request(current_user, payload)


@router.patch("/orders/{orderId}/status", response_model=OkResponse)
def update_order_status(
    orderId: str,
    payload: UpdateOrderStatusRequest,
    trace_id: str | None = Header(default=None, alias="X-Trace-Id"),
    current_user: UserResponse = Depends(get_current_user),
    service: ClientOrdersService = Depends(ClientOrdersService),
) -> OkResponse:
    return service.update_status(
        current_user.id,
        orderId,
        payload,
        actor=current_user.role,
        trace_id=trace_id,
    )
