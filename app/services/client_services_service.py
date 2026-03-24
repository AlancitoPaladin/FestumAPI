from app.core.exceptions import ResourceNotFoundError
from app.repositories.client_repository import ClientRepository
from app.schemas.client import HomeServicesResponse, ServiceCategory, ServiceItem
from app.services.provider_storage_service import ProviderStorageService


class ClientServicesService:
    def __init__(self) -> None:
        self.repository = ClientRepository()
        self.storage_service = ProviderStorageService()

    def home(self) -> HomeServicesResponse:
        salones = self.repository.services_by_category("salones-sociales")
        mobiliario = self.repository.services_by_category("mobiliario")
        banquetes = self.repository.services_by_category("banquetes")
        return HomeServicesResponse(
            **{
                "salones-sociales": [self._build_service_item(item) for item in salones],
                "mobiliario": [self._build_service_item(item) for item in mobiliario],
                "banquetes": [self._build_service_item(item) for item in banquetes],
            }
        )

    def by_category(self, category: ServiceCategory) -> list[ServiceItem]:
        items = self.repository.services_by_category(category)
        return [self._build_service_item(item) for item in items]

    def detail(self, service_id: str, category: ServiceCategory) -> ServiceItem:
        item = self.repository.service_by_id(service_id)
        if not item or item.get("category") != category:
            raise ResourceNotFoundError("Service not found")
        return self._build_service_item(item)

    def _build_service_item(self, item: dict) -> ServiceItem:
        image_value = (
            item.get("main_image_storage_path")
            or (item.get("image_storage_paths") or [""])[0]
            or item.get("main_image_url")
            or (item.get("image_urls") or [""])[0]
            or item.get("image_url")
            or ""
        )
        image_key = self.storage_service.extract_storage_key(str(image_value))
        signed_image = self.storage_service.build_signed_asset(image_key) if image_key else None
        legacy_image_url = str(item.get("image_url") or item.get("main_image_url") or "")

        payload = {
            **item,
            "image": signed_image,
            "image_url": legacy_image_url,
        }
        return ServiceItem(**payload)
