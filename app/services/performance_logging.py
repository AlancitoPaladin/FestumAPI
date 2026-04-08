from __future__ import annotations

import hashlib
import json
import logging
from typing import Any


def mask_user_id(user_id: str | None) -> str:
    raw = str(user_id or "")
    if not raw:
        return ""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def estimate_payload_bytes(payload: Any) -> int:
    try:
        return len(json.dumps(payload, default=str, ensure_ascii=False).encode("utf-8"))
    except Exception:
        return -1


def log_endpoint_metrics(
    logger: logging.Logger,
    *,
    endpoint: str,
    request_id: str | None,
    user_id: str | None,
    total_ms: float,
    db_ms: float,
    mapping_ms: float,
    image_sign_ms: float = 0.0,
    items_count: int = 0,
    payload_bytes: int = -1,
    extra: dict[str, Any] | None = None,
) -> None:
    payload = {
        "endpoint": endpoint,
        "request_id": request_id or "",
        "user_id_masked": mask_user_id(user_id),
        "total_ms": round(float(total_ms), 2),
        "db_ms": round(float(db_ms), 2),
        "mapping_ms": round(float(mapping_ms), 2),
        "image_sign_ms": round(float(image_sign_ms), 2),
        "items_count": int(items_count),
        "payload_bytes": int(payload_bytes),
    }
    if extra:
        payload.update(extra)
    logger.info("client_endpoint_metrics %s", payload)

