import logging
from time import perf_counter

from app.core.exceptions import ResourceNotFoundError
from app.repositories.client_repository import ClientRepository
from app.repositories.provider_product_repository import ProviderProductRepository
from app.schemas.client import (
    HomeServicesResponse,
    ServiceCategory,
    ServiceItem,
    ServiceListResponse,
)
from app.services.client_category_normalizer import (
    CANONICAL_CLIENT_CATEGORIES,
    normalize_client_category,
)
from app.services.client_cache import client_cache, home_cache_key
from app.services.product_catalog_projection_service import ProductCatalogProjectionService
from app.services.performance_logging import estimate_payload_bytes
from app.services.service_catalog_projection_service import ServiceCatalogProjectionService

logger = logging.getLogger(__name__)


class ClientServicesService:
    def __init__(self) -> None:
        self.repository = ClientRepository()
        self.product_repository = ProviderProductRepository()
        self.projection_service = ServiceCatalogProjectionService()
        self.product_projection_service = ProductCatalogProjectionService()

    def home(
        self,
        request_id: str | None = None,
        *,
        user_id: str | None = None,
        include_products: bool = True,
        image_mode: str = "full",
        include_all_images: bool = True,
        include_metrics: bool = False,
    ) -> HomeServicesResponse | tuple[HomeServicesResponse, dict]:
        start_ts = perf_counter()
        cache_ms = 0.0
        db_ms = 0.0
        mapping_ms = 0.0
        image_sign_ms = 0.0
        cache_variant = (
            f"products:{int(include_products)}:mode:{image_mode}:all_images:{int(include_all_images)}"
        )
        if user_id:
            cache_start = perf_counter()
            cached = client_cache.get(home_cache_key(user_id, variant=cache_variant))
            cache_ms = (perf_counter() - cache_start) * 1000
            if cached is not None:
                response = HomeServicesResponse.model_validate(cached)
                metrics = {
                    "total_ms": (perf_counter() - start_ts) * 1000,
                    "db_ms": 0.0,
                    "mapping_ms": 0.0,
                    "image_sign_ms": 0.0,
                    "cache_ms": cache_ms,
                    "db_reads": 0,
                    "items_count": sum(len(v) for v in response.model_dump(by_alias=True).values()),
                    "payload_bytes": estimate_payload_bytes(response.model_dump(by_alias=True)),
                    "cache_hit": True,
                    "images_signed_count": 0,
                }
                return (response, metrics) if include_metrics else response
        db_start = perf_counter()
        services = self.repository.list_published_services()
        db_ms += (perf_counter() - db_start) * 1000
        grouped: dict[str, list[ServiceItem]] = {
            category: [] for category in CANONICAL_CLIENT_CATEGORIES
        }
        signing_errors_count = 0
        images_signed_count = 0

        def on_image_error(context: dict) -> None:
            nonlocal signing_errors_count
            signing_errors_count += 1
            logger.warning(
                "client_services_home_image_fallback %s",
                {
                    "request_id": request_id,
                    "service_id": context.get("service_id"),
                    "category": context.get("category"),
                    "image_key": context.get("image_key"),
                    "error_type": context.get("error_type"),
                },
            )

        for item in services:
            category = normalize_client_category(str(item.get("category") or ""))
            image_sign_holder = [0.0]
            image_signed_count_holder = [0]
            grouped[category].append(
                self._build_service_item(
                    item,
                    include_products=include_products,
                    image_mode=image_mode,
                    include_all_images=include_all_images,
                    on_image_error=on_image_error,
                    image_sign_ms_accumulator=image_sign_holder,
                    image_signed_count_accumulator=image_signed_count_holder,
                )
            )
            image_sign_ms += image_sign_holder[0]
            images_signed_count += image_signed_count_holder[0]

        mapping_ms += (perf_counter() - start_ts) * 1000 - db_ms

        duration_ms = round((perf_counter() - start_ts) * 1000, 2)
        logger.info(
            "client_services_home_summary %s",
            {
                "request_id": request_id,
                "duration_ms": duration_ms,
                "total_services": sum(len(items) for items in grouped.values()),
                "counts_by_category": {key: len(value) for key, value in grouped.items()},
                "image_signing_errors": signing_errors_count,
                "images_signed_count": images_signed_count,
            },
        )

        response = HomeServicesResponse(
            **{
                "salones-sociales": grouped["salones-sociales"],
                "mobiliario": grouped["mobiliario"],
                "banquetes": grouped["banquetes"],
                "dj": grouped["dj"],
                "decoracion": grouped["decoracion"],
                "fotografia": grouped["fotografia"],
                "entretenimiento": grouped["entretenimiento"],
                "otros": grouped["otros"],
            }
        )
        if user_id:
            client_cache.set(
                home_cache_key(user_id, variant=cache_variant),
                response.model_dump(by_alias=True),
                ttl_seconds=15,
            )

        metrics = {
            "total_ms": (perf_counter() - start_ts) * 1000,
            "db_ms": db_ms,
            "mapping_ms": max(0.0, mapping_ms),
            "image_sign_ms": image_sign_ms,
            "cache_ms": cache_ms,
            "db_reads": 1,
            "items_count": sum(len(v) for v in response.model_dump(by_alias=True).values()),
            "payload_bytes": estimate_payload_bytes(response.model_dump(by_alias=True)),
            "cache_hit": False,
            "images_signed_count": images_signed_count,
        }
        return (response, metrics) if include_metrics else response

    def by_category(
        self,
        category: ServiceCategory,
        q: str | None,
        min_price_cents: int | None,
        max_price_cents: int | None,
        sort: str,
        page: int,
        page_size: int,
        include_metrics: bool = False,
    ) -> ServiceListResponse | tuple[ServiceListResponse, dict]:
        start_ts = perf_counter()
        db_ms = 0.0
        mapping_ms = 0.0
        normalized_query_category = normalize_client_category(
            category,
            fallback_to_others=False,
        )
        if normalized_query_category is None:
            response = ServiceListResponse(
                items=[],
                total=0,
                page=page,
                page_size=page_size,
                has_next=False,
            )
            metrics = {
                "total_ms": (perf_counter() - start_ts) * 1000,
                "db_ms": db_ms,
                "mapping_ms": mapping_ms,
                "image_sign_ms": 0.0,
                "db_reads": 0,
                "items_count": 0,
                "payload_bytes": estimate_payload_bytes(response.model_dump()),
            }
            return (response, metrics) if include_metrics else response
        db_start = perf_counter()
        items = self.repository.list_published_services()
        db_ms += (perf_counter() - db_start) * 1000
        image_sign_ms = 0.0
        projected = []
        for item in items:
            if normalize_client_category(
                str(item.get("category") or ""),
                fallback_to_others=True,
            ) != normalized_query_category:
                continue
            image_sign_holder = [0.0]
            projected_item = self._build_service_item(
                item,
                include_products=True,
                image_sign_ms_accumulator=image_sign_holder,
            )
            image_sign_ms += image_sign_holder[0]
            projected.append(projected_item)

        if q:
            lookup = q.strip().lower()
            projected = [
                item
                for item in projected
                if lookup in item.name.lower()
                or lookup in item.subtitle.lower()
                or lookup in item.description.lower()
            ]

        if min_price_cents is not None:
            projected = [item for item in projected if item.unit_price_cents >= min_price_cents]
        if max_price_cents is not None:
            projected = [item for item in projected if item.unit_price_cents <= max_price_cents]

        projected = self._sort_items(projected, sort)

        total = len(projected)
        offset = (page - 1) * page_size
        end = offset + page_size
        paged = projected[offset:end]
        response = ServiceListResponse(
            items=paged,
            total=total,
            page=page,
            page_size=page_size,
            has_next=end < total,
        )
        mapping_ms += (perf_counter() - start_ts) * 1000 - db_ms
        metrics = {
            "total_ms": (perf_counter() - start_ts) * 1000,
            "db_ms": db_ms,
            "mapping_ms": max(0.0, mapping_ms),
            "image_sign_ms": image_sign_ms,
            "db_reads": 1,
            "items_count": len(response.items),
            "payload_bytes": estimate_payload_bytes(response.model_dump()),
        }
        return (response, metrics) if include_metrics else response

    def detail(
        self,
        service_id: str,
        category: ServiceCategory,
        *,
        include_metrics: bool = False,
    ) -> ServiceItem | tuple[ServiceItem, dict]:
        start_ts = perf_counter()
        db_ms = 0.0
        mapping_ms = 0.0
        db_start = perf_counter()
        item = self.repository.visible_service_by_id(service_id)
        db_ms += (perf_counter() - db_start) * 1000
        normalized_query_category = normalize_client_category(
            category,
            fallback_to_others=False,
        )
        if normalized_query_category is None:
            raise ResourceNotFoundError("Service not found", code="NOT_FOUND")
        normalized_item_category = normalize_client_category(
            str(item.get("category") or "") if item else "",
            fallback_to_others=True,
        )
        if not item or normalized_item_category != normalized_query_category:
            raise ResourceNotFoundError("Service not found", code="NOT_FOUND")
        image_sign_holder = [0.0]
        response = self._build_service_item(
            item,
            include_products=True,
            image_sign_ms_accumulator=image_sign_holder,
        )
        image_sign_ms = image_sign_holder[0]
        mapping_ms += (perf_counter() - start_ts) * 1000 - db_ms
        metrics = {
            "total_ms": (perf_counter() - start_ts) * 1000,
            "db_ms": db_ms,
            "mapping_ms": max(0.0, mapping_ms),
            "image_sign_ms": image_sign_ms,
            "db_reads": 1,
            "items_count": 1,
            "payload_bytes": estimate_payload_bytes(response.model_dump()),
        }
        return (response, metrics) if include_metrics else response

    def _build_service_item(
        self,
        item: dict,
        *,
        include_products: bool = False,
        image_mode: str = "full",
        include_all_images: bool = True,
        on_image_error=None,
        image_sign_ms_accumulator: list[float] | None = None,
        image_signed_count_accumulator: list[int] | None = None,
    ) -> ServiceItem:
        projected = self.projection_service.build_service_projection(
            item,
            on_image_error=on_image_error,
            image_mode=image_mode,
            include_all_images=include_all_images,
        )
        image_sign_ms = float(projected.get("_image_sign_ms", 0.0) or 0.0)
        image_signed_count = int(projected.get("_images_signed_count", 0) or 0)
        if image_sign_ms_accumulator is not None and image_sign_ms_accumulator:
            image_sign_ms_accumulator[0] += image_sign_ms
        if image_signed_count_accumulator is not None and image_signed_count_accumulator:
            image_signed_count_accumulator[0] += image_signed_count
        products = self._build_client_products(projected) if include_products else []

        payload = {
            "id": projected.get("id", ""),
            "name": str(projected.get("name", "")),
            "subtitle": str(projected.get("subtitle", "")),
            "description": str(projected.get("description", "")),
            "price_label": str(projected.get("price_label", "")),
            "unit_price_cents": int(projected.get("unit_price_cents", 0) or 0),
            "badge": str(projected.get("badge", "")),
            "category": normalize_client_category(str(projected.get("category") or "")),
            "image": projected.get("image"),
            "image_url": str(projected.get("image_url", "")),
            "images": list(projected.get("images") or []),
            "image_urls": list(projected.get("image_urls") or []),
            "products": products,
        }
        return ServiceItem(**payload)

    def _build_client_products(self, service: dict) -> list[dict]:
        provider_id = str(service.get("provider_id") or "")
        service_id = str(service.get("id") or "")
        if not provider_id or not service_id:
            return []

        items = self.product_repository.list_published_by_service(provider_id, service_id)
        return [
            {
                "id": projected.get("id", ""),
                "service_id": service_id,
                "name": str(projected.get("name", "")),
                "description": str(projected.get("description", "")),
                "price_label": str(projected.get("price_label", "")),
                "unit_price_cents": int(projected.get("unit_price_cents", 0) or 0),
                "category": service.get("category", ""),
                "image": projected.get("image"),
                "image_url": str(projected.get("image_url", "")),
            }
            for projected in (
                self.product_projection_service.build_product_projection(item) for item in items
            )
        ]

    @staticmethod
    def _sort_items(items: list[ServiceItem], sort: str) -> list[ServiceItem]:
        if sort == "price_asc":
            return sorted(items, key=lambda item: item.unit_price_cents)
        if sort == "price_desc":
            return sorted(items, key=lambda item: item.unit_price_cents, reverse=True)
        if sort == "name_asc":
            return sorted(items, key=lambda item: item.name.lower())
        if sort == "name_desc":
            return sorted(items, key=lambda item: item.name.lower(), reverse=True)
        return items
