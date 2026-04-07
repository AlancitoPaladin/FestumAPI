from fastapi import UploadFile
from pydantic import ValidationError

from app.core.exceptions import ApiError, ResourceNotFoundError
from app.core.config import get_settings
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
    ProviderProductStatusUpdate,
    ProviderProductStatusUpdateResponse,
    ProviderProductFields,
    ProviderProductUpdate,
    ProviderProductValidated,
)
from app.schemas.provider_reservation import (
    ProviderReservationNextBookingResponse,
    ProviderReservationProductSummaryListResponse,
    ProviderReservationProductSummaryResponse,
)
from app.repositories.provider_booking_repository import ProviderBookingRepository
from app.services.product_catalog_projection_service import ProductCatalogProjectionService
from app.services.provider_storage_service import ProviderStorageService


class ProviderProductService:
    def __init__(self) -> None:
        self.service_repository = ProviderServiceRepository()
        self.repository = ProviderProductRepository()
        self.booking_repository = ProviderBookingRepository()
        self.availability_repository = ProviderAvailabilityRepository()
        self.storage_service = ProviderStorageService()
        self.projection_service = ProductCatalogProjectionService()

    def create_product(
        self, provider_id: str, service_id: str, payload: ProviderProductCreate
    ) -> ProviderProductResponse:
        parent_service = self._get_parent_service(provider_id, service_id)
        category = parent_service["category"]
        if payload.category != category:
            raise ApiError("Product category must match the parent service category")

        validated_payload = ProviderProductValidated(category=category, **payload.model_dump(exclude={"category"}))
        product = self.repository.create(
            provider_id=provider_id,
            service_id=service_id,
            category=category,
            data=self._normalize_payload_for_storage(
                {
                    **validated_payload.model_dump(exclude={"category"}),
                    "status": "draft",
                }
            ),
        )
        return self._build_product_response(product)

    def list_products(self, provider_id: str, service_id: str) -> ProviderProductListResponse:
        self._get_parent_service(provider_id, service_id)
        items = [
            self._build_product_response(item)
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
        return self._build_product_response(product)

    def get_product_by_id(self, provider_id: str, product_id: str) -> ProviderProductResponse:
        product = self.repository.get_by_product_id(provider_id, product_id)
        if not product:
            raise ResourceNotFoundError("Provider product not found")
        return self._build_product_response(product)

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

        normalized_update = self._normalize_update_payload(current_product, payload.model_dump(exclude_none=True))

        product = self.repository.update(
            provider_id=provider_id,
            service_id=service_id,
            product_id=product_id,
            data={
                **normalized_update,
                "category": parent_service["category"],
            },
        )
        return self._build_product_response(product)

    def update_product_by_id(
        self,
        provider_id: str,
        product_id: str,
        payload: ProviderProductUpdate,
    ) -> ProviderProductResponse:
        product = self.repository.get_by_product_id(provider_id, product_id)
        if not product:
            raise ResourceNotFoundError("Provider product not found")
        return self.update_product(
            provider_id=provider_id,
            service_id=product["service_id"],
            product_id=product_id,
            payload=payload,
        )

    def update_product_status(
        self,
        provider_id: str,
        product_id: str,
        payload: ProviderProductStatusUpdate,
    ) -> ProviderProductStatusUpdateResponse:
        product = self.repository.get_by_product_id(provider_id, product_id)
        if not product:
            raise ResourceNotFoundError("Provider product not found")

        parent_service = self._get_parent_service(provider_id, product["service_id"])
        self._validate_status_transition(str(product.get("status", "draft")), payload.status)
        if payload.status == "published":
            self._ensure_publishable(
                product=product,
                category=parent_service["category"],
            )
        self.repository.update(
            provider_id=provider_id,
            service_id=product["service_id"],
            product_id=product_id,
            data={
                "status": payload.status,
                "category": parent_service["category"],
            },
        )
        return ProviderProductStatusUpdateResponse(ok=True)

    def upload_product_image(
        self,
        provider_id: str,
        service_id: str,
        product_id: str,
        file: UploadFile,
        is_main: bool,
    ) -> ProviderProductImageUploadResponse:
        self._get_parent_service(provider_id, service_id)
        product = self.repository.get_by_id(provider_id, service_id, product_id)
        if not product:
            raise ResourceNotFoundError("Provider product not found")

        image_key, raw_image_url = self.storage_service.upload_product_image(
            provider_id=provider_id,
            service_id=service_id,
            product_id=product_id,
            file=file,
        )
        try:
            product = self.repository.add_image(
                provider_id=provider_id,
                service_id=service_id,
                product_id=product_id,
                image_key=image_key,
                image_url=raw_image_url,
                is_main=is_main,
            )
        except Exception:
            self.storage_service.delete_file(image_key)
            raise
        signed_asset = self.storage_service.build_signed_asset(image_key)
        return ProviderProductImageUploadResponse(
            product_id=product_id,
            key=image_key,
            image=signed_asset,
            image_url=signed_asset.url,
            is_main=is_main,
        )

    def upload_product_image_by_id(
        self,
        provider_id: str,
        product_id: str,
        file: UploadFile,
        is_main: bool,
    ) -> ProviderProductImageUploadResponse:
        product = self.repository.get_by_product_id(provider_id, product_id)
        if not product:
            raise ResourceNotFoundError("Provider product not found")
        return self.upload_product_image(
            provider_id=provider_id,
            service_id=product["service_id"],
            product_id=product_id,
            file=file,
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
            image_key=payload.image_key,
        )
        return self._build_product_response(product)

    def set_main_product_image_by_id(
        self,
        provider_id: str,
        product_id: str,
        payload: ProviderProductImageReferenceRequest,
    ) -> ProviderProductResponse:
        product = self.repository.get_by_product_id(provider_id, product_id)
        if not product:
            raise ResourceNotFoundError("Provider product not found")
        return self.set_main_product_image(
            provider_id=provider_id,
            service_id=product["service_id"],
            product_id=product_id,
            payload=payload,
        )

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
            image_keys=payload.image_keys,
        )
        return self._build_product_response(product)

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
            image_key=payload.image_key,
        )
        self.storage_service.delete_file(deleted_storage_path)
        return self._build_product_response(product)

    def delete_product_image_by_id(
        self,
        provider_id: str,
        product_id: str,
        payload: ProviderProductImageReferenceRequest,
    ) -> ProviderProductResponse:
        product = self.repository.get_by_product_id(provider_id, product_id)
        if not product:
            raise ResourceNotFoundError("Provider product not found")
        return self.delete_product_image(
            provider_id=provider_id,
            service_id=product["service_id"],
            product_id=product_id,
            payload=payload,
        )

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
            projected = self.projection_service.build_product_projection(product)
            items.append(
                ProviderReservationProductSummaryResponse(
                    id=product["id"],
                    service_id=product["service_id"],
                    product_name=str(product.get("name", "")),
                    category=product["category"],
                    image_url=str(projected.get("image_url", "")),
                    main_image_url=str(projected.get("main_image_url", "")),
                    image=projected.get("image"),
                    main_image=projected.get("image"),
                    images=projected.get("images", []),
                    image_urls=list(projected.get("image_urls", [])),
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

    def _build_product_response(self, product: dict) -> ProviderProductResponse:
        projected = self.projection_service.build_product_projection(product)
        return ProviderProductResponse(**projected)

    def _normalize_update_payload(self, current_product: dict, payload: dict) -> dict:
        normalized = dict(payload)

        detail_fields = (
            "approx_photos",
            "delivery_time",
            "min_duration",
            "extra_hour_allowed",
            "extra_hour_price",
            "min_guests",
            "max_guests",
            "banquet_type",
            "menu_included",
            "stock",
            "dimensions",
            "weight",
            "color_material",
            "venue_capacity",
            "is_price_per_hour",
            "decoration_type",
            "setup_time",
        )
        details_changed = "details" in payload or any(field in payload for field in detail_fields)
        if details_changed:
            merged_details = dict(current_product.get("details") or {})
            if "details" in payload:
                merged_details.update(payload.get("details") or {})
            for field_name in detail_fields:
                if field_name in payload:
                    merged_details[field_name] = payload[field_name]
            normalized["details"] = {
                key: value
                for key, value in merged_details.items()
                if value is not None and value != ""
            }

        if "inclusions" in payload:
            normalized["inclusions"] = dict(payload.get("inclusions") or {})
        if "policies" in payload:
            normalized["policies"] = dict(payload.get("policies") or {})

        return normalized

    @staticmethod
    def _normalize_payload_for_storage(payload: dict) -> dict:
        normalized = dict(payload)
        details = dict(normalized.get("details") or {})
        for field_name in (
            "approx_photos",
            "delivery_time",
            "min_duration",
            "extra_hour_allowed",
            "extra_hour_price",
            "min_guests",
            "max_guests",
            "banquet_type",
            "menu_included",
            "stock",
            "dimensions",
            "weight",
            "color_material",
            "venue_capacity",
            "is_price_per_hour",
            "decoration_type",
            "setup_time",
        ):
            if field_name in normalized and normalized[field_name] is not None:
                details.setdefault(field_name, normalized[field_name])
            elif field_name in details:
                normalized[field_name] = details[field_name]

        normalized["details"] = {
            key: value
            for key, value in details.items()
            if value is not None and value != ""
        }
        normalized["inclusions"] = dict(normalized.get("inclusions") or {})
        normalized["policies"] = dict(normalized.get("policies") or {})
        return normalized

    def _get_parent_service(self, provider_id: str, service_id: str) -> dict:
        service = self.service_repository.get_by_id(provider_id, service_id)
        if not service:
            raise ResourceNotFoundError("Provider service not found")
        return service

    def _ensure_publishable(self, product: dict, category: str) -> None:
        validation_payload = {
            field_name: product[field_name]
            for field_name in ProviderProductFields.model_fields
            if field_name in product
        }

        try:
            ProviderProductValidated(category=category, **validation_payload)
        except ValidationError as exc:
            raise ApiError(self._format_validation_error(exc)) from exc

    @staticmethod
    def _validate_status_transition(current_status: str, next_status: str) -> None:
        transitions = {
            "draft": {"published", "inactive"},
            "published": {"inactive"},
            "inactive": {"published"},
        }
        allowed_targets = transitions.get(current_status, set())
        if next_status not in allowed_targets:
            raise ApiError(f"Invalid status transition from {current_status} to {next_status}")

    @staticmethod
    def _build_next_booking(booking: dict | None) -> ProviderReservationNextBookingResponse | None:
        if not booking:
            return None

        customer_asset = ProviderProductService._build_optional_signed_asset(
            str(booking.get("customer_image_url", ""))
        )
        customer_image_url = customer_asset.url if customer_asset else str(
            booking.get("customer_image_url", "")
        )
        status_map = {
            "confirmed": "Confirmada",
            "pending": "Pendiente",
            "cancelled": "Cancelada",
            "rejected": "Rechazada",
        }
        return ProviderReservationNextBookingResponse(
            booking_id=booking["id"],
            customer_name=str(booking.get("customer_name", "")),
            customer_image_url=customer_image_url,
            avatar_url=customer_image_url,
            customer_image=customer_asset,
            date=str(booking.get("event_date", "")),
            status=status_map.get(str(booking.get("status", "")), str(booking.get("status", "")).title()),
        )

    @staticmethod
    def _build_optional_signed_asset(value: str):
        raw_value = str(value or "").strip()
        if not raw_value:
            return None

        settings = get_settings()
        bucket_name = str(settings.s3_bucket_name or "").strip()
        if not (
            raw_value.startswith("providers/")
            or raw_value.startswith("users/")
            or raw_value.startswith("s3://")
            or (bucket_name and bucket_name in raw_value)
        ):
            return None

        storage_service = ProviderStorageService()
        storage_key = storage_service.extract_storage_key(raw_value)
        if not storage_key:
            return None
        return storage_service.build_signed_asset(storage_key)

    @staticmethod
    def _format_validation_error(exc: ValidationError) -> str:
        messages: list[str] = []
        for error in exc.errors():
            raw_message = str(error.get("msg", "Invalid product payload"))
            message = raw_message.removeprefix("Value error, ").strip()
            location = ".".join(str(part) for part in error.get("loc", ()) if part != "__root__")
            messages.append(f"{location}: {message}" if location else message)
        return "; ".join(dict.fromkeys(messages)) or "Invalid product payload"
