import logging

from fastapi import APIRouter, Depends, Query, Request

from app.api.dependencies.auth import get_current_user
from app.schemas.client import HomeServicesResponse, ServiceItem, ServiceListResponse
from app.schemas.user import UserResponse
from app.services.client_services_service import ClientServicesService
from app.services.performance_logging import log_endpoint_metrics

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/services/home", response_model=HomeServicesResponse, response_model_by_alias=True)
def services_home(
    request: Request,
    _: UserResponse = Depends(get_current_user),
    service: ClientServicesService = Depends(ClientServicesService),
) -> HomeServicesResponse:
    request_id = (
        request.headers.get("X-Request-ID")
        or request.headers.get("x-request-id")
        or str(getattr(request.state, "request_id", "") or "")
        or None
    )
    response, metrics = service.home(
        request_id=request_id,
        user_id=_.id,
        include_metrics=True,
    )
    log_endpoint_metrics(
        logger,
        endpoint="/api/v1/client/services/home",
        request_id=request_id,
        user_id=_.id,
        total_ms=metrics["total_ms"],
        db_ms=metrics["db_ms"],
        mapping_ms=metrics["mapping_ms"],
        image_sign_ms=metrics["image_sign_ms"],
        items_count=metrics["items_count"],
        payload_bytes=metrics["payload_bytes"],
        extra={
            "cache_hit": metrics.get("cache_hit", False),
            "db_reads": metrics.get("db_reads", 0),
        },
    )
    return response


@router.get("/services", response_model=ServiceListResponse)
def services_by_category(
    request: Request,
    category: str = Query(..., min_length=1),
    q: str | None = Query(default=None),
    min_price_cents: int | None = Query(default=None, ge=0),
    max_price_cents: int | None = Query(default=None, ge=0),
    sort: str = Query(default="relevance", pattern="^(relevance|price_asc|price_desc|name_asc|name_desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: UserResponse = Depends(get_current_user),
    service: ClientServicesService = Depends(ClientServicesService),
) -> ServiceListResponse:
    request_id = request.headers.get("X-Request-ID") or request.headers.get("x-request-id")
    response, metrics = service.by_category(
        category=category,
        q=q,
        min_price_cents=min_price_cents,
        max_price_cents=max_price_cents,
        sort=sort,
        page=page,
        page_size=page_size,
        include_metrics=True,
    )
    log_endpoint_metrics(
        logger,
        endpoint="/api/v1/client/services",
        request_id=request_id,
        user_id=_.id,
        total_ms=metrics["total_ms"],
        db_ms=metrics["db_ms"],
        mapping_ms=metrics["mapping_ms"],
        image_sign_ms=metrics["image_sign_ms"],
        items_count=metrics["items_count"],
        payload_bytes=metrics["payload_bytes"],
        extra={"db_reads": metrics.get("db_reads", 0)},
    )
    return response


@router.get("/services/{serviceId}", response_model=ServiceItem)
def service_detail(
    serviceId: str,
    request: Request,
    category: str = Query(..., min_length=1),
    _: UserResponse = Depends(get_current_user),
    service: ClientServicesService = Depends(ClientServicesService),
) -> ServiceItem:
    request_id = request.headers.get("X-Request-ID") or request.headers.get("x-request-id")
    response, metrics = service.detail(serviceId, category, include_metrics=True)
    log_endpoint_metrics(
        logger,
        endpoint="/api/v1/client/services/{serviceId}",
        request_id=request_id,
        user_id=_.id,
        total_ms=metrics["total_ms"],
        db_ms=metrics["db_ms"],
        mapping_ms=metrics["mapping_ms"],
        image_sign_ms=metrics["image_sign_ms"],
        items_count=metrics["items_count"],
        payload_bytes=metrics["payload_bytes"],
        extra={"db_reads": metrics.get("db_reads", 0)},
    )
    return response
