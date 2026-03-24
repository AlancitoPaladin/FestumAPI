from fastapi import UploadFile

from app.core.exceptions import ResourceNotFoundError
from app.repositories.provider_availability_repository import ProviderAvailabilityRepository
from app.repositories.provider_product_repository import ProviderProductRepository
from app.repositories.provider_service_repository import ProviderServiceRepository
from app.schemas.provider_product import (
    ProviderProductCreate,
    ProviderProductDeleteResponse,
    ProviderProductImageReferenceRequest,
    ProviderProductImageReorderRequest,
    ProviderProductImageUploadResponse,
    ProviderProductListResponse,
    ProviderProductResponse,
    ProviderProductUpdate,
    ProviderProductValidated,
)
from app.schemas.provider_reservation import (
    ProviderReservationNextBookingResponse,
    ProviderReservationProductSummaryListResponse,
    ProviderReservationProductSummaryResponse,
)
from app.repositories.provider_booking_repository import ProviderBookingRepository
from app.services.provider_storage_service import ProviderStorageService


class ProviderProductService:
    def __init__(self) -> None:
        self.service_repository = ProviderServiceRepository()
        self.repository = ProviderProductRepository()
        self.booking_repository = ProviderBookingRepository()
        self.availability_repository = ProviderAvailabilityRepository()
        self.storage_service = ProviderStorageService()

    def create_product(
        self, provider_id: str, service_id: str, payload: ProviderProductCreate
    ) -> ProviderProductResponse:
        parent_service = self._get_parent_service(provider_id, service_id)
        category = parent_service["category"]
        validated_payload = ProviderProductValidated(category=category, **payload.model_dump())
        product = self.repository.create(
            provider_id=provider_id,
            service_id=service_id,
            category=category,
            data=validated_payload.model_dump(exclude={"category"}),
        )
        return ProviderProductResponse(**product)

    def list_products(self, provider_id: str, service_id: str) -> ProviderProductListResponse:
        self._get_parent_service(provider_id, service_id)
        items = [
            ProviderProductResponse(**item)
            for item in self.repository.list_by_service(provider_id, service_id)
        ]
        return ProviderProductListResponse(items=items, total=len(items))

    def list_products_by_service_name(
        self, provider_id: str, service_name: str
    ) -> ProviderProductListResponse:
        parent_service = self.service_repository.get_by_name(provider_id, service_name)
        if not parent_service:
            raise ResourceNotFoundError("Provider service not found")
        return self.list_products(provider_id, parent_service["id"])

    def get_product(
        self, provider_id: str, service_id: str, product_id: str
    ) -> ProviderProductResponse:
        self._get_parent_service(provider_id, service_id)
        product = self.repository.get_by_id(provider_id, service_id, product_id)
        if not product:
            raise ResourceNotFoundError("Provider product not found")
        return ProviderProductResponse(**product)

    def update_product(
        self,
        provider_id: str,
        service_id: str,
        product_id: str,
        payload: ProviderProductUpdate,
    ) -> ProviderProductResponse:
        parent_service = self._get_parent_service(provider_id, service_id)
        current_product = self.repository.get_by_id(provider_id, service_id, product_id)
        if not current_product:
            raise ResourceNotFoundError("Provider product not found")

        merged_payload = {
            **current_product,
            **payload.model_dump(exclude_none=True),
        }
        ProviderProductValidated(category=parent_service["category"], **merged_payload)

        product = self.repository.update(
            provider_id=provider_id,
            service_id=service_id,
            product_id=product_id,
            data=payload.model_dump(exclude_none=True),
        )
        return ProviderProductResponse(**product)

    def upload_product_image(
        self,
        provider_id: str,
        service_id: str,
        product_id: str,
        file: UploadFile,
        is_main: bool,
    ) -> ProviderProductImageUploadResponse:
        self._get_parent_service(provider_id, service_id)
        storage_path, image_url = self.storage_service.upload_product_image(
            provider_id=provider_id,
            service_id=service_id,
            product_id=product_id,
            file=file,
        )
        try:
            self.repository.add_image(
                provider_id=provider_id,
                service_id=service_id,
                product_id=product_id,
                image_url=image_url,
                storage_path=storage_path,
                is_main=is_main,
            )
        except Exception:
            self.storage_service.delete_file(storage_path)
            raise
        return ProviderProductImageUploadResponse(
            product_id=product_id,
            storage_path=storage_path,
            image_url=image_url,
            is_main=is_main,
        )

    def set_main_product_image(
        self,
        provider_id: str,
        service_id: str,
        product_id: str,
        payload: ProviderProductImageReferenceRequest,
    ) -> ProviderProductResponse:
        self._get_parent_service(provider_id, service_id)
        product = self.repository.set_main_image(
            provider_id=provider_id,
            service_id=service_id,
            product_id=product_id,
            image_url=payload.image_url,
        )
        return ProviderProductResponse(**product)

    def reorder_product_images(
        self,
        provider_id: str,
        service_id: str,
        product_id: str,
        payload: ProviderProductImageReorderRequest,
    ) -> ProviderProductResponse:
        self._get_parent_service(provider_id, service_id)
        product = self.repository.reorder_images(
            provider_id=provider_id,
            service_id=service_id,
            product_id=product_id,
            image_urls=payload.image_urls,
        )
        return ProviderProductResponse(**product)

    def delete_product_image(
        self,
        provider_id: str,
        service_id: str,
        product_id: str,
        payload: ProviderProductImageReferenceRequest,
    ) -> ProviderProductResponse:
        self._get_parent_service(provider_id, service_id)
        product, deleted_storage_path = self.repository.delete_image(
            provider_id=provider_id,
            service_id=service_id,
            product_id=product_id,
            image_url=payload.image_url,
        )
        self.storage_service.delete_file(deleted_storage_path)
        return ProviderProductResponse(**product)

    def delete_product(
        self, provider_id: str, service_id: str, product_id: str
    ) -> ProviderProductDeleteResponse:
        self._get_parent_service(provider_id, service_id)
        self.booking_repository.delete_all_by_product(provider_id, product_id)
        self.availability_repository.delete_all_by_product(provider_id, service_id, product_id)
        deleted, storage_paths = self.repository.delete(provider_id, service_id, product_id)
        for storage_path in storage_paths:
            self.storage_service.delete_file(storage_path)
        return ProviderProductDeleteResponse(deleted=deleted)

    def list_products_for_reservations(
        self, provider_id: str
    ) -> ProviderReservationProductSummaryListResponse:
        products = self.repository.list_by_provider(provider_id)
        next_booking_by_product = self.booking_repository.get_next_booking_map(provider_id)

        items = []
        for product in products:
            next_booking = next_booking_by_product.get(product["id"])
            items.append(
                ProviderReservationProductSummaryResponse(
                    id=product["id"],
                    service_id=product["service_id"],
                    product_name=str(product.get("name", "")),
                    category=product["category"],
                    image_url=str(
                        product.get("main_image_url")
                        or (product.get("image_urls") or [""])[0]
                    ),
                    next_booking=self._build_next_booking(next_booking),
                )
            )

        return ProviderReservationProductSummaryListResponse(items=items, total=len(items))

    def delete_product_by_id(self, provider_id: str, product_id: str) -> ProviderProductDeleteResponse:
        product = self.repository.get_by_product_id(provider_id, product_id)
        if not product:
            raise ResourceNotFoundError("Provider product not found")

        self.booking_repository.delete_all_by_product(provider_id, product_id)
        self.availability_repository.delete_all_by_product(provider_id, product["service_id"], product_id)
        deleted, storage_paths = self.repository.delete(provider_id, product["service_id"], product_id)
        for storage_path in storage_paths:
            self.storage_service.delete_file(storage_path)
        return ProviderProductDeleteResponse(deleted=deleted)

    def _get_parent_service(self, provider_id: str, service_id: str) -> dict:
        service = self.service_repository.get_by_id(provider_id, service_id)
        if not service:
            raise ResourceNotFoundError("Provider service not found")
        return service

    @staticmethod
    def _build_next_booking(booking: dict | None) -> ProviderReservationNextBookingResponse | None:
        if not booking:
            return None

        status_map = {
            "confirmed": "Confirmada",
            "pending": "Pendiente",
            "cancelled": "Cancelada",
            "rejected": "Rechazada",
        }
        return ProviderReservationNextBookingResponse(
            booking_id=booking["id"],
            customer_name=str(booking.get("customer_name", "")),
            customer_image_url=str(booking.get("customer_image_url", "")),
            date=str(booking.get("event_date", "")),
            status=status_map.get(str(booking.get("status", "")), str(booking.get("status", "")).title()),
        )
