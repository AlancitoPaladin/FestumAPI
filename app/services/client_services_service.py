from app.core.exceptions import ResourceNotFoundError
from app.repositories.client_repository import ClientRepository
from app.repositories.provider_product_repository import ProviderProductRepository
from app.schemas.client import (
    HomeServicesResponse,
    ServiceCategory,
    ServiceItem,
    ServiceListResponse,
)
from app.services.product_catalog_projection_service import ProductCatalogProjectionService
from app.services.service_catalog_projection_service import ServiceCatalogProjectionService


class ClientServicesService:
    def __init__(self) -> None:
        self.repository = ClientRepository()
        self.product_repository = ProviderProductRepository()
        self.projection_service = ServiceCatalogProjectionService()
        self.product_projection_service = ProductCatalogProjectionService()

    def home(self) -> HomeServicesResponse:
        services = self.repository.list_published_services()
        grouped: dict[str, list[ServiceItem]] = {}
        for item in services:
            category = str(item.get("category") or "uncategorized")
            grouped.setdefault(category, []).append(self._build_service_item(item, include_products=True))
        return HomeServicesResponse(grouped)

    def by_category(
        self,
        category: ServiceCategory,
        q: str | None,
        min_price_cents: int | None,
        max_price_cents: int | None,
        sort: str,
        page: int,
        page_size: int,
    ) -> ServiceListResponse:
        items = self.repository.services_by_category(category)
        projected = [self._build_service_item(item, include_products=True) for item in items]

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
        start = (page - 1) * page_size
        end = start + page_size
        paged = projected[start:end]
        return ServiceListResponse(
            items=paged,
            total=total,
            page=page,
            page_size=page_size,
            has_next=end < total,
        )

    def detail(self, service_id: str, category: ServiceCategory) -> ServiceItem:
        item = self.repository.visible_service_by_id(service_id)
        if not item or item.get("category") != category:
            raise ResourceNotFoundError("Service not found", code="NOT_FOUND")
        return self._build_service_item(item, include_products=True)

    def _build_service_item(self, item: dict, *, include_products: bool = False) -> ServiceItem:
        projected = self.projection_service.build_service_projection(item)
        products = self._build_client_products(projected) if include_products else []

        payload = {
            "id": projected.get("id", ""),
            "name": str(projected.get("name", "")),
            "subtitle": str(projected.get("subtitle", "")),
            "description": str(projected.get("description", "")),
            "price_label": str(projected.get("price_label", "")),
            "unit_price_cents": int(projected.get("unit_price_cents", 0) or 0),
            "badge": str(projected.get("badge", "")),
            "category": projected.get("category", ""),
            "image": projected.get("image"),
            "image_url": str(projected.get("image_url", "")),
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
