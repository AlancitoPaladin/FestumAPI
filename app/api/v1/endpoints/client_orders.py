import logging

from fastapi import APIRouter, Depends, Header, Query, Request, status

from app.api.dependencies.auth import get_current_user
from app.schemas.client import (
    ActiveServiceIdsResponse,
    CheckoutResponse,
    CheckoutRequestPayload,
    CreateOrderRequestPayload,
    CreateOrderRequest,
    OrdersListResponse,
    OrderRequestCreateResponse,
    OkResponse,
    OrderItem,
    OrdersResponse,
    UpdateOrderStatusRequest,
)
from app.schemas.user import UserResponse
from app.services.client_orders_service import ClientOrdersService
from app.services.performance_logging import log_endpoint_metrics

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/orders", response_model=OrdersListResponse | OrdersResponse)
def get_orders(
    request: Request,
    include_items: bool = Query(default=False),
    current_user: UserResponse = Depends(get_current_user),
    service: ClientOrdersService = Depends(ClientOrdersService),
) -> OrdersListResponse | OrdersResponse:
    request_id = request.headers.get("X-Request-ID") or request.headers.get("x-request-id")
    response, metrics = service.list_orders(
        current_user.id,
        include_items=include_items,
        include_metrics=True,
    )
    log_endpoint_metrics(
        logger,
        endpoint="/api/v1/client/orders",
        request_id=request_id,
        user_id=current_user.id,
        total_ms=metrics["total_ms"],
        db_ms=metrics["db_ms"],
        mapping_ms=metrics["mapping_ms"],
        items_count=metrics["items_count"],
        payload_bytes=metrics["payload_bytes"],
        extra={
            "cache_hit": metrics.get("cache_hit", False),
            "include_items": include_items,
            "db_reads": metrics.get("db_reads", 0),
        },
    )
    return response


@router.get("/orders/active-service-ids", response_model=ActiveServiceIdsResponse)
def get_active_service_ids(
    request: Request,
    current_user: UserResponse = Depends(get_current_user),
    service: ClientOrdersService = Depends(ClientOrdersService),
) -> ActiveServiceIdsResponse:
    request_id = request.headers.get("X-Request-ID") or request.headers.get("x-request-id")
    response, metrics = service.list_active_service_ids(
        current_user.id,
        include_metrics=True,
    )
    log_endpoint_metrics(
        logger,
        endpoint="/api/v1/client/orders/active-service-ids",
        request_id=request_id,
        user_id=current_user.id,
        total_ms=metrics["total_ms"],
        db_ms=metrics["db_ms"],
        mapping_ms=metrics["mapping_ms"],
        items_count=metrics["items_count"],
        payload_bytes=metrics["payload_bytes"],
        extra={
            "db_reads": metrics.get("db_reads", 0),
            "service_ids_count": metrics.get("service_ids_count", response.total),
            "cache_hit": metrics.get("cache_hit", False),
        },
    )
    return response


@router.get("/orders/{orderId}", response_model=OrderItem)
def get_order_detail(
    orderId: str,
    request: Request,
    current_user: UserResponse = Depends(get_current_user),
    service: ClientOrdersService = Depends(ClientOrdersService),
) -> OrderItem:
    request_id = request.headers.get("X-Request-ID") or request.headers.get("x-request-id")
    response, metrics = service.get_order_detail(
        current_user.id,
        orderId,
        include_metrics=True,
    )
    log_endpoint_metrics(
        logger,
        endpoint="/api/v1/client/orders/{orderId}",
        request_id=request_id,
        user_id=current_user.id,
        total_ms=metrics["total_ms"],
        db_ms=metrics["db_ms"],
        mapping_ms=metrics["mapping_ms"],
        items_count=metrics["items_count"],
        payload_bytes=metrics["payload_bytes"],
        extra={"db_reads": metrics.get("db_reads", 0)},
    )
    return response


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
