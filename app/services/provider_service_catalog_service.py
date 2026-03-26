from fastapi import UploadFile

from app.core.exceptions import ApiError, ResourceNotFoundError
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
    ProviderServiceStatusUpdate,
    ProviderServiceStatusUpdateResponse,
    ProviderServiceUpdate,
)
from app.services.service_catalog_projection_service import ServiceCatalogProjectionService
from app.services.provider_storage_service import ProviderStorageService


class ProviderServiceCatalogService:
    def __init__(self) -> None:
        self.repository = ProviderServiceRepository()
        self.product_repository = ProviderProductRepository()
        self.booking_repository = ProviderBookingRepository()
        self.availability_repository = ProviderAvailabilityRepository()
        self.storage_service = ProviderStorageService()
        self.projection_service = ServiceCatalogProjectionService()

    def create_service(
        self, provider_id: str, payload: ProviderServiceCreate
    ) -> ProviderServiceResponse:
        service = self.repository.create(
            provider_id,
            {
                "category": payload.category,
                "name": payload.name,
                "subtitle": payload.subtitle,
                "description": payload.description,
                "main_image_key": payload.main_image_key,
                "image_keys": payload.image_keys,
                "unit_price_cents": payload.unit_price_cents or 0,
                "price_label": self._build_price_label(payload.unit_price_cents or 0),
                "badge": "",
                "status": "draft",
            },
        )
        return self._to_response(service)

    def create_draft_service(
        self, provider_id: str, payload: ProviderServiceDraftCreate
    ) -> ProviderServiceResponse:
        service = self.repository.create(
            provider_id,
            {
                "category": payload.category,
                "name": payload.name,
                "subtitle": "",
                "description": payload.description,
                "unit_price_cents": payload.unit_price_cents or 0,
                "price_label": self._build_price_label(payload.unit_price_cents or 0),
                "badge": "",
                "status": "draft",
                "main_image_key": "",
                "image_keys": [],
            },
        )
        return self._to_response(service)

    def list_services(self, provider_id: str) -> ProviderServiceListResponse:
        items = [self._to_response(item) for item in self.repository.list_by_provider(provider_id)]
        return ProviderServiceListResponse(items=items, total=len(items))

    def get_service(self, provider_id: str, service_id: str) -> ProviderServiceResponse:
        service = self.repository.get_by_id(provider_id, service_id)
        if not service:
            raise ResourceNotFoundError("Provider service not found")
        return self._to_response(service)

    def update_service(
        self, provider_id: str, service_id: str, payload: ProviderServiceUpdate
    ) -> ProviderServiceResponse:
        current_service = self.repository.get_by_id(provider_id, service_id)
        if not current_service:
            raise ResourceNotFoundError("Provider service not found")

        update_data = payload.model_dump(exclude_none=True)
        normalized = self._normalize_image_fields(current_service, update_data)
        if "unit_price_cents" in normalized:
            normalized["price_label"] = self._build_price_label(
                int(normalized["unit_price_cents"] or 0)
            )
        service = self.repository.update(
            provider_id=provider_id,
            service_id=service_id,
            data=normalized,
        )
        return self._to_response(service)

    def update_service_status(
        self,
        provider_id: str,
        service_id: str,
        payload: ProviderServiceStatusUpdate,
    ) -> ProviderServiceStatusUpdateResponse:
        current_service = self.repository.get_by_id(provider_id, service_id)
        if not current_service:
            raise ResourceNotFoundError("Provider service not found")

        self._validate_status_transition(str(current_service.get("status", "draft")), payload.status)
        if payload.status == "published":
            self._ensure_publishable(current_service)

        self.repository.update(
            provider_id=provider_id,
            service_id=service_id,
            data={"status": payload.status},
        )
        return ProviderServiceStatusUpdateResponse(ok=True)

    def upload_service_image(
        self,
        provider_id: str,
        service_id: str,
        file: UploadFile,
        is_main: bool,
    ) -> ProviderServiceImageUploadResponse:
        if not self.repository.get_by_id(provider_id, service_id):
            raise ResourceNotFoundError("Provider service not found")

        storage_path, _ = self.storage_service.upload_service_image(
            provider_id=provider_id,
            service_id=service_id,
            file=file,
        )
        try:
            self.repository.add_image(
                provider_id=provider_id,
                service_id=service_id,
                image_key=storage_path,
                is_main=is_main,
            )
        except Exception:
            self.storage_service.delete_file(storage_path)
            raise

        image = self.storage_service.build_signed_asset(storage_path)
        return ProviderServiceImageUploadResponse(
            service_id=service_id,
            key=storage_path,
            image=image,
            image_url=image.url,
            is_main=is_main,
        )

    def set_main_service_image(
        self,
        provider_id: str,
        service_id: str,
        payload: ProviderServiceImageReferenceRequest,
    ) -> ProviderServiceResponse:
        service = self.repository.set_main_image(provider_id, service_id, payload.image_key)
        return self._to_response(service)

    def reorder_service_images(
        self,
        provider_id: str,
        service_id: str,
        payload: ProviderServiceImageReorderRequest,
    ) -> ProviderServiceResponse:
        service = self.repository.reorder_images(provider_id, service_id, payload.image_keys)
        return self._to_response(service)

    def delete_service_image(
        self,
        provider_id: str,
        service_id: str,
        payload: ProviderServiceImageReferenceRequest,
    ) -> ProviderServiceResponse:
        service, deleted_storage_path = self.repository.delete_image(
            provider_id=provider_id,
            service_id=service_id,
            image_key=payload.image_key,
        )
        self.storage_service.delete_file(deleted_storage_path)
        return self._to_response(service)

    def delete_service(self, provider_id: str, service_id: str) -> ProviderServiceDeleteResponse:
        if not self.repository.get_by_id(provider_id, service_id):
            raise ResourceNotFoundError("Provider service not found")

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

    def _to_response(self, service: dict) -> ProviderServiceResponse:
        projected = self.projection_service.build_service_projection(service)
        return ProviderServiceResponse(
            **projected,
        )

    @staticmethod
    def _normalize_image_fields(current_service: dict, update_data: dict) -> dict:
        normalized = dict(update_data)
        if "main_image_key" in normalized and normalized["main_image_key"]:
            image_keys = list(normalized.get("image_keys") or current_service.get("image_keys", []))
            if normalized["main_image_key"] not in image_keys:
                image_keys.insert(0, normalized["main_image_key"])
            normalized["image_keys"] = list(dict.fromkeys(image_keys))

        if "image_keys" in normalized and "main_image_key" not in normalized:
            current_main = str(current_service.get("main_image_key") or "")
            if current_main and current_main not in normalized["image_keys"]:
                normalized["main_image_key"] = normalized["image_keys"][0] if normalized["image_keys"] else ""
        return normalized

    @staticmethod
    def _validate_status_transition(current_status: str, next_status: str) -> None:
        transitions = {
            "draft": {"published", "inactive"},
            "published": {"inactive"},
            "inactive": {"published"},
        }
        allowed_targets = transitions.get(current_status, set())
        if next_status not in allowed_targets:
            raise ApiError(
                f"Invalid status transition from {current_status} to {next_status}"
            )

    @staticmethod
    def _ensure_publishable(service: dict) -> None:
        required_text_fields = {
            "name": str(service.get("name", "") or "").strip(),
            "subtitle": str(service.get("subtitle", "") or "").strip(),
        }
        missing = [field_name for field_name, value in required_text_fields.items() if not value]
        if missing:
            raise ApiError(
                "Service must be completed before publishing. Missing: "
                + ", ".join(missing)
            )

    @staticmethod
    def _build_price_label(unit_price_cents: int) -> str:
        if unit_price_cents <= 0:
            return "Cotiza"
        amount = unit_price_cents / 100
        if unit_price_cents % 100 == 0:
            return f"Desde ${amount:,.0f} MXN"
        return f"Desde ${amount:,.2f} MXN"
