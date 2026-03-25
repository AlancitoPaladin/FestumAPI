from app.core.exceptions import ResourceNotFoundError
from app.repositories.client_repository import ClientRepository
from app.repositories.provider_product_repository import ProviderProductRepository
from app.schemas.client import HomeServicesResponse, ServiceCategory, ServiceItem
from app.services.product_catalog_projection_service import ProductCatalogProjectionService
from app.services.service_catalog_projection_service import ServiceCatalogProjectionService


class ClientServicesService:
    home_categories = (
        "dj",
        "photography",
        "entertainment",
        "banquet",
        "furniture",
        "equipment",
        "venue",
        "decoration",
        "salones-sociales",
        "mobiliario",
        "banquetes",
    )

    def __init__(self) -> None:
        self.repository = ClientRepository()
        self.product_repository = ProviderProductRepository()
        self.projection_service = ServiceCatalogProjectionService()
        self.product_projection_service = ProductCatalogProjectionService()

    def home(self) -> HomeServicesResponse:
        payload = {
            category: [
                self._build_service_item(item)
                for item in self.repository.services_by_category(category)
            ]
            for category in self.home_categories
        }
        return HomeServicesResponse(**payload)

    def by_category(self, category: ServiceCategory) -> list[ServiceItem]:
        items = self.repository.services_by_category(category)
        return [self._build_service_item(item) for item in items]

    def detail(self, service_id: str, category: ServiceCategory) -> ServiceItem:
        item = self.repository.service_by_id(service_id)
        if (
            not item
            or item.get("category") != category
            or item.get("status") != "published"
        ):
            raise ResourceNotFoundError("Service not found")
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
