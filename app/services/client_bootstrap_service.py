from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from app.repositories.client_repository import ClientRepository
from app.schemas.client import (
    BootstrapCartSummary,
    BootstrapLocksSummary,
    BootstrapMeta,
    BootstrapOrdersSummary,
    ClientBootstrapResponse,
    HomeServicesResponse,
)
from app.services.client_cache import (
    bootstrap_cart_cache_key,
    bootstrap_home_cache_key,
    bootstrap_locks_cache_key,
    bootstrap_orders_cache_key,
    client_cache,
)
from app.services.client_orders_service import ACTIVE_ORDER_STATUSES
from app.services.client_services_service import ClientServicesService
from app.services.performance_logging import estimate_payload_bytes


class ClientBootstrapService:
    def __init__(self) -> None:
        self.repository = ClientRepository()
        self.home_service = ClientServicesService()

    def get_bootstrap(
        self,
        user_id: str,
        *,
        request_id: str | None = None,
        images: str = "lite",
        include_metrics: bool = False,
    ) -> ClientBootstrapResponse | tuple[ClientBootstrapResponse, dict[str, Any]]:
        start_ts = perf_counter()
        image_mode = "full" if images == "full" else "lite"

        with ThreadPoolExecutor(max_workers=3) as executor:
            home_future = executor.submit(
                self._timed_cached_home,
                request_id=request_id,
                user_id=user_id,
                image_mode=image_mode,
            )
            cart_future = executor.submit(self._timed_cached_cart_summary, user_id)
            orders_future = executor.submit(self._timed_cached_orders_summary, user_id)

            home_result, home_ms, home_metrics, home_cache_hit = home_future.result()
            cart_summary, cart_ms, cart_cache_hit = cart_future.result()
            orders_summary, orders_ms, orders_cache_hit, orders_for_locks = orders_future.result()

        locks_summary, locks_ms, locks_cache_hit = self._timed_cached_locks_summary(
            user_id=user_id,
            fallback_orders=orders_for_locks,
        )

        response = ClientBootstrapResponse(
            home=home_result,
            cart=cart_summary,
            orders=orders_summary,
            locks=locks_summary,
            meta=BootstrapMeta(generated_at=datetime.now(tz=timezone.utc)),
        )

        metrics = {
            "total_ms": (perf_counter() - start_ts) * 1000,
            "home_ms": home_ms,
            "home_db_ms": float(home_metrics.get("db_ms", 0.0)),
            "home_image_sign_ms": float(home_metrics.get("image_sign_ms", 0.0)),
            "cart_ms": cart_ms,
            "orders_ms": orders_ms,
            "locks_ms": locks_ms,
            "payload_bytes": estimate_payload_bytes(response.model_dump(by_alias=True)),
            "services_count_total": sum(len(v) for v in response.home.model_dump(by_alias=True).values()),
            "images_signed_count": int(home_metrics.get("images_signed_count", 0)),
            "cache_hit": bool(home_cache_hit and cart_cache_hit and orders_cache_hit and locks_cache_hit),
        }
        return (response, metrics) if include_metrics else response

    def _timed_cached_home(
        self,
        *,
        request_id: str | None,
        user_id: str,
        image_mode: str,
    ) -> tuple[Any, float, dict[str, Any], bool]:
        cache_key = bootstrap_home_cache_key(user_id, image_mode)
        cached = client_cache.get(cache_key)
        if cached is not None:
            response = HomeServicesResponse.model_validate(cached)
            return response, 0.0, {"db_ms": 0.0, "image_sign_ms": 0.0, "images_signed_count": 0}, True

        start = perf_counter()
        home_response, home_metrics = self.home_service.home(
            request_id=request_id,
            user_id=user_id,
            include_products=False,
            image_mode=image_mode,
            include_all_images=False,
            include_metrics=True,
        )
        home_response = self._trim_home_for_bootstrap(home_response, image_mode=image_mode)
        elapsed_ms = (perf_counter() - start) * 1000
        client_cache.set(
            cache_key,
            home_response.model_dump(by_alias=True, mode="json"),
            ttl_seconds=15,
        )
        return home_response, elapsed_ms, home_metrics, False

    def _timed_cached_cart_summary(self, user_id: str) -> tuple[BootstrapCartSummary, float, bool]:
        cache_key = bootstrap_cart_cache_key(user_id)
        cached = client_cache.get(cache_key)
        if cached is not None:
            return BootstrapCartSummary.model_validate(cached), 0.0, True
        start = perf_counter()
        cart_items = self.repository.cart_list(user_id)
        service_ids = self._extract_cart_service_ids(cart_items)
        response = BootstrapCartSummary(
            count=len(service_ids),
            service_ids=service_ids,
        )
        elapsed_ms = (perf_counter() - start) * 1000
        client_cache.set(cache_key, response.model_dump(mode="json"), ttl_seconds=7)
        return response, elapsed_ms, False

    def _timed_cached_orders_summary(
        self,
        user_id: str,
    ) -> tuple[BootstrapOrdersSummary, float, bool, list[dict] | None]:
        cache_key = bootstrap_orders_cache_key(user_id)
        cached = client_cache.get(cache_key)
        if cached is not None:
            return BootstrapOrdersSummary.model_validate(cached), 0.0, True, None
        start = perf_counter()
        orders = self.repository.order_list(user_id)
        response = BootstrapOrdersSummary(count=len(orders))
        elapsed_ms = (perf_counter() - start) * 1000
        client_cache.set(cache_key, response.model_dump(mode="json"), ttl_seconds=7)
        return response, elapsed_ms, False, orders

    def _timed_cached_locks_summary(
        self,
        *,
        user_id: str,
        fallback_orders: list[dict] | None = None,
    ) -> tuple[BootstrapLocksSummary, float, bool]:
        cache_key = bootstrap_locks_cache_key(user_id)
        cached = client_cache.get(cache_key)
        if cached is not None:
            return BootstrapLocksSummary.model_validate(cached), 0.0, True
        start = perf_counter()
        if hasattr(self.repository, "list_order_status_and_items_by_statuses"):
            orders = self.repository.list_order_status_and_items_by_statuses(
                user_id,
                sorted(ACTIVE_ORDER_STATUSES),
            )
        else:
            orders = fallback_orders if fallback_orders is not None else self.repository.order_list(user_id)
        active_service_ids = self._extract_active_service_ids(orders)
        response = BootstrapLocksSummary(active_service_ids=active_service_ids)
        elapsed_ms = (perf_counter() - start) * 1000
        client_cache.set(cache_key, response.model_dump(mode="json"), ttl_seconds=7)
        return response, elapsed_ms, False

    @staticmethod
    def _extract_active_service_ids(orders: list[dict]) -> list[str]:
        seen: set[str] = set()
        service_ids: list[str] = []
        for order in orders:
            status = str(order.get("status") or "")
            if status not in ACTIVE_ORDER_STATUSES:
                continue
            for item in list(order.get("items") or []):
                service_id = str(item.get("service_id") or item.get("id") or "").strip()
                if not service_id or service_id in seen:
                    continue
                seen.add(service_id)
                service_ids.append(service_id)
        return service_ids

    @staticmethod
    def _extract_cart_service_ids(cart_items: list[dict]) -> list[str]:
        seen: set[str] = set()
        service_ids: list[str] = []
        for item in cart_items:
            service_id = str(item.get("id") or item.get("service_id") or "").strip()
            if not service_id or service_id in seen:
                continue
            seen.add(service_id)
            service_ids.append(service_id)
        return service_ids

    @staticmethod
    def _trim_home_for_bootstrap(
        home: HomeServicesResponse,
        *,
        image_mode: str,
    ) -> HomeServicesResponse:
        payload = home.model_dump(by_alias=True)
        for category, items in payload.items():
            if not isinstance(items, list):
                continue
            for item in items:
                item["description"] = ""
                item["products"] = []
                image = item.get("image")
                if not image:
                    continue
                if image_mode == "lite":
                    image["medium"] = None
                    image["original"] = None
                    if not image.get("thumb"):
                        image["thumb"] = {
                            "key": image.get("key", ""),
                            "url": image.get("url", ""),
                            "expires_at": image.get("expires_at", ""),
                        }
        return HomeServicesResponse.model_validate(payload)
