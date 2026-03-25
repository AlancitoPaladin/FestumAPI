from app.core.exceptions import ResourceNotFoundError
from app.repositories.client_repository import ClientRepository
from app.schemas.client import ClientProductAvailabilityResponse
from app.services.provider_availability_service import ProviderAvailabilityService


class ClientProductAvailabilityService:
    def __init__(self) -> None:
        self.client_repository = ClientRepository()
        self.provider_availability_service = ProviderAvailabilityService()

    def get_month(self, product_id: str, year: int, month: int) -> ClientProductAvailabilityResponse:
        match = self.client_repository.published_service_by_product_id(product_id)
        if not match:
            raise ResourceNotFoundError("Product not found")

        service, _product = match
        payload = self.provider_availability_service.client_month(
            provider_id=str(service.get("provider_id") or ""),
            service_id=str(service.get("id") or ""),
            product_id=product_id,
            year=year,
            month=month,
        )
        return ClientProductAvailabilityResponse(**payload)
