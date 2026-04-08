import logging

from fastapi import APIRouter, Depends, Query, Request

from app.api.dependencies.auth import get_current_user
from app.schemas.client import ClientBootstrapResponse
from app.schemas.user import UserResponse
from app.services.client_bootstrap_service import ClientBootstrapService
from app.services.performance_logging import mask_user_id

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/bootstrap", response_model=ClientBootstrapResponse, response_model_by_alias=True)
def get_client_bootstrap(
    request: Request,
    images: str = Query(default="lite", pattern="^(lite|full)$"),
    current_user: UserResponse = Depends(get_current_user),
    service: ClientBootstrapService = Depends(ClientBootstrapService),
) -> ClientBootstrapResponse:
    request_id = request.headers.get("X-Request-ID") or request.headers.get("x-request-id")
    response, metrics = service.get_bootstrap(
        current_user.id,
        request_id=request_id,
        images=images,
        include_metrics=True,
    )
    logger.info(
        "client_bootstrap_metrics %s",
        {
            "endpoint": "/api/v1/client/bootstrap",
            "request_id": request_id or "",
            "user_id_masked": mask_user_id(current_user.id),
            "total_ms": round(float(metrics["total_ms"]), 2),
            "home_ms": round(float(metrics["home_ms"]), 2),
            "home_db_ms": round(float(metrics.get("home_db_ms", 0.0)), 2),
            "home_image_sign_ms": round(float(metrics.get("home_image_sign_ms", 0.0)), 2),
            "cart_ms": round(float(metrics["cart_ms"]), 2),
            "orders_ms": round(float(metrics["orders_ms"]), 2),
            "locks_ms": round(float(metrics["locks_ms"]), 2),
            "payload_bytes": int(metrics["payload_bytes"]),
            "services_count_total": int(metrics.get("services_count_total", 0)),
            "images_signed_count": int(metrics.get("images_signed_count", 0)),
            "images_mode": images,
            "cache_hit": bool(metrics.get("cache_hit", False)),
        },
    )
    return response
