from fastapi import UploadFile

from app.core.exceptions import ResourceNotFoundError
from app.repositories.provider_availability_repository import ProviderAvailabilityRepository
from app.repositories.provider_booking_repository import ProviderBookingRepository
from app.repositories.provider_product_repository import ProviderProductRepository
from app.repositories.provider_service_repository import ProviderServiceRepository
from app.schemas.provider_service import (
    ProviderServiceCreate,
    ProviderServiceDeleteResponse,
    ProviderServiceDraftCreate,
    ProviderServiceImageReferenceRequest,
    ProviderServiceImageReorderRequest,
    ProviderServiceImageUploadResponse,
    ProviderServiceListResponse,
    ProviderServiceResponse,
    ProviderServiceUpdate,
)
from app.services.provider_storage_service import ProviderStorageService


class ProviderServiceCatalogService:
    def __init__(self) -> None:
        self.repository = ProviderServiceRepository()
        self.product_repository = ProviderProductRepository()
        self.booking_repository = ProviderBookingRepository()
        self.availability_repository = ProviderAvailabilityRepository()
        self.storage_service = ProviderStorageService()

    def create_service(
        self, provider_id: str, payload: ProviderServiceCreate
    ) -> ProviderServiceResponse:
        service = self.repository.create(provider_id, payload.model_dump())
        return ProviderServiceResponse(**service)

    def create_draft_service(
        self, provider_id: str, payload: ProviderServiceDraftCreate
    ) -> ProviderServiceResponse:
        draft_payload = ProviderServiceCreate(
            category=payload.category,
            name=payload.name,
            description=payload.description,
            status="draft",
        )
        service = self.repository.create(provider_id, draft_payload.model_dump())
        return ProviderServiceResponse(**service)

    def list_services(self, provider_id: str) -> ProviderServiceListResponse:
        items = [
            ProviderServiceResponse(**item)
            for item in self.repository.list_by_provider(provider_id)
        ]
        return ProviderServiceListResponse(items=items, total=len(items))

    def get_service(self, provider_id: str, service_id: str) -> ProviderServiceResponse:
        service = self.repository.get_by_id(provider_id, service_id)
        if not service:
            raise ResourceNotFoundError("Provider service not found")
        return ProviderServiceResponse(**service)

    def update_service(
        self, provider_id: str, service_id: str, payload: ProviderServiceUpdate
    ) -> ProviderServiceResponse:
        current_service = self.repository.get_by_id(provider_id, service_id)
        if not current_service:
            raise ResourceNotFoundError("Provider service not found")

        merged_payload = {
            **current_service,
            **payload.model_dump(exclude_none=True),
        }
        ProviderServiceCreate(**merged_payload)

        service = self.repository.update(
            provider_id=provider_id,
            service_id=service_id,
            data=payload.model_dump(exclude_none=True),
        )
        return ProviderServiceResponse(**service)

    def upload_service_image(
        self,
        provider_id: str,
        service_id: str,
        file: UploadFile,
        is_main: bool,
    ) -> ProviderServiceImageUploadResponse:
        storage_path, image_url = self.storage_service.upload_service_image(
            provider_id=provider_id,
            service_id=service_id,
            file=file,
        )
        self.repository.add_image(
            provider_id=provider_id,
            service_id=service_id,
            image_url=image_url,
            storage_path=storage_path,
            is_main=is_main,
        )
        return ProviderServiceImageUploadResponse(
            service_id=service_id,
            storage_path=storage_path,
            image_url=image_url,
            is_main=is_main,
        )

    def set_main_service_image(
        self,
        provider_id: str,
        service_id: str,
        payload: ProviderServiceImageReferenceRequest,
    ) -> ProviderServiceResponse:
        service = self.repository.set_main_image(provider_id, service_id, payload.image_url)
        return ProviderServiceResponse(**service)

    def reorder_service_images(
        self,
        provider_id: str,
        service_id: str,
        payload: ProviderServiceImageReorderRequest,
    ) -> ProviderServiceResponse:
        service = self.repository.reorder_images(provider_id, service_id, payload.image_urls)
        return ProviderServiceResponse(**service)

    def delete_service_image(
        self,
        provider_id: str,
        service_id: str,
        payload: ProviderServiceImageReferenceRequest,
    ) -> ProviderServiceResponse:
        service, deleted_storage_path = self.repository.delete_image(
            provider_id=provider_id,
            service_id=service_id,
            image_url=payload.image_url,
        )
        self.storage_service.delete_file(deleted_storage_path)
        return ProviderServiceResponse(**service)

    def delete_service(self, provider_id: str, service_id: str) -> ProviderServiceDeleteResponse:
        products = self.product_repository.list_by_service(provider_id, service_id)
        for product in products:
            self.booking_repository.delete_all_by_product(provider_id, product["id"])
            self.availability_repository.delete_all_by_product(
                provider_id,
                service_id,
                product["id"],
            )

        product_storage_paths = self.product_repository.delete_all_by_service(provider_id, service_id)
        deleted, service_storage_paths = self.repository.delete(provider_id, service_id)

        for storage_path in [*product_storage_paths, *service_storage_paths]:
            self.storage_service.delete_file(storage_path)

        return ProviderServiceDeleteResponse(deleted=deleted)
