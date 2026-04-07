from datetime import datetime, timezone

import pytest

from app.core.exceptions import ApiError
from app.schemas.provider_product import ProviderProductStatusUpdate, ProviderProductUpdate
from app.services.provider_product_service import ProviderProductService


class _FakeProviderServiceRepository:
    def __init__(self, seed: dict) -> None:
        self.doc = dict(seed)

    def get_by_id(self, provider_id: str, service_id: str) -> dict | None:
        if self.doc.get("provider_id") != provider_id or self.doc.get("id") != service_id:
            return None
        return dict(self.doc)


class _FakeProviderProductRepository:
    def __init__(self, seed: dict) -> None:
        self.doc = dict(seed)
        self.last_update_data: dict | None = None

    def get_by_id(self, provider_id: str, service_id: str, product_id: str) -> dict | None:
        if (
            self.doc.get("provider_id") != provider_id
            or self.doc.get("service_id") != service_id
            or self.doc.get("id") != product_id
        ):
            return None
        return dict(self.doc)

    def get_by_product_id(self, provider_id: str, product_id: str) -> dict | None:
        if self.doc.get("provider_id") != provider_id or self.doc.get("id") != product_id:
            return None
        return dict(self.doc)

    def update(self, provider_id: str, service_id: str, product_id: str, data: dict) -> dict:
        self.last_update_data = dict(data)
        self.doc.update(data)
        self.doc["updated_at"] = datetime.now(tz=timezone.utc)
        return dict(self.doc)


class _FakeProductProjectionService:
    @staticmethod
    def build_product_projection(product: dict) -> dict:
        return dict(product)


def _build_product_service(
    product_seed: dict,
    *,
    service_category: str = "photography",
) -> tuple[ProviderProductService, _FakeProviderProductRepository]:
    service = ProviderProductService.__new__(ProviderProductService)
    service.service_repository = _FakeProviderServiceRepository(
        {
            "id": product_seed["service_id"],
            "provider_id": product_seed["provider_id"],
            "category": service_category,
        }
    )
    fake_repo = _FakeProviderProductRepository(product_seed)
    service.repository = fake_repo
    service.booking_repository = None
    service.availability_repository = None
    service.storage_service = None
    service.projection_service = _FakeProductProjectionService()
    return service, fake_repo


def _build_product_seed(**overrides: object) -> dict:
    now = datetime.now(tz=timezone.utc)
    seed = {
        "id": "prod-1",
        "provider_id": "prov-1",
        "service_id": "svc-1",
        "category": "photography",
        "name": "Cobertura Premium",
        "description": "Cobertura completa del evento",
        "price": 4500.0,
        "pricing_unit": "Por evento",
        "details": {
            "approx_photos": 300,
            "delivery_time": "15 dias",
            "min_duration": "4 horas",
        },
        "inclusions": {"Galeria digital": True},
        "policies": {"50% de anticipo": True},
        "approx_photos": 300,
        "delivery_time": "15 dias",
        "min_duration": "4 horas",
        "extra_hour_allowed": False,
        "extra_hour_price": None,
        "min_guests": None,
        "max_guests": None,
        "banquet_type": None,
        "menu_included": None,
        "stock": None,
        "dimensions": None,
        "weight": None,
        "color_material": None,
        "venue_capacity": None,
        "is_price_per_hour": False,
        "decoration_type": None,
        "setup_time": None,
        "main_image_url": "",
        "image_urls": [],
        "status": "draft",
        "created_at": now,
        "updated_at": now,
    }
    seed.update(overrides)
    return seed


def test_partial_product_update_allows_single_field_change_even_if_draft_is_incomplete() -> None:
    seed = _build_product_seed(
        price=None,
        pricing_unit=None,
        approx_photos=None,
        delivery_time=None,
        min_duration=None,
        details={},
    )
    service, repo = _build_product_service(seed)

    response = service.update_product_by_id(
        "prov-1",
        "prod-1",
        ProviderProductUpdate(name="Cobertura Premium Plus"),
    )

    assert response.name == "Cobertura Premium Plus"
    assert repo.last_update_data == {
        "name": "Cobertura Premium Plus",
        "category": "photography",
    }


def test_partial_product_update_ignores_category_from_payload_and_keeps_parent_category() -> None:
    seed = _build_product_seed(category="photography")
    service, repo = _build_product_service(seed, service_category="photography")
    payload = ProviderProductUpdate.model_validate(
        {
            "name": "Cobertura Deluxe",
            "category": "venue",
        }
    )

    response = service.update_product_by_id("prov-1", "prod-1", payload)

    assert payload.model_dump(exclude_none=True) == {"name": "Cobertura Deluxe"}
    assert response.category == "photography"
    assert repo.last_update_data == {
        "name": "Cobertura Deluxe",
        "category": "photography",
    }


def test_publish_product_status_returns_api_error_for_incomplete_product() -> None:
    seed = _build_product_seed(
        price=None,
        pricing_unit=None,
        approx_photos=None,
        delivery_time=None,
        min_duration=None,
        details={},
    )
    service, repo = _build_product_service(seed)

    with pytest.raises(ApiError) as exc_info:
        service.update_product_status(
            "prov-1",
            "prod-1",
            ProviderProductStatusUpdate(status="published"),
        )

    assert "Missing required fields for category photography" in str(exc_info.value.detail)
    assert repo.last_update_data is None


def test_publish_product_status_succeeds_for_complete_product_and_keeps_canonical_category() -> None:
    seed = _build_product_seed(category="legacy-category")
    service, repo = _build_product_service(seed, service_category="photography")

    response = service.update_product_status(
        "prov-1",
        "prod-1",
        ProviderProductStatusUpdate(status="published"),
    )

    assert response.ok is True
    assert repo.last_update_data == {
        "status": "published",
        "category": "photography",
    }
