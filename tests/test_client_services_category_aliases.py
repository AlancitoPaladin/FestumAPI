import pytest

from app.core.exceptions import ResourceNotFoundError
from app.services.client_services_service import ClientServicesService


class _FakeClientRepository:
    def __init__(self, services: list[dict]) -> None:
        self.services = services

    def list_published_services(self) -> list[dict]:
        return [dict(item) for item in self.services]

    def services_by_category(self, category: str) -> list[dict]:
        return [dict(item) for item in self.services if item.get("category") == category]

    def visible_service_by_id(self, service_id: str) -> dict | None:
        for item in self.services:
            if item.get("id") == service_id:
                return dict(item)
        return None


class _FakeProductRepository:
    def list_published_by_service(self, provider_id: str, service_id: str) -> list[dict]:
        return []


class _FakeServiceProjection:
    def build_service_projection(
        self,
        item: dict,
        on_image_error=None,
        *,
        image_mode: str = "full",
        include_all_images: bool = True,
    ) -> dict:
        return {
            "id": item["id"],
            "provider_id": item["provider_id"],
            "name": item["name"],
            "subtitle": item["subtitle"],
            "description": item["description"],
            "unit_price_cents": item["unit_price_cents"],
            "price_label": item["price_label"],
            "badge": item["badge"],
            "category": item["category"],
            "image": None,
            "image_url": item.get("image_url", ""),
            "images": [],
            "image_urls": [],
        }


class _FakeProductProjection:
    def build_product_projection(self, item: dict) -> dict:
        return dict(item)


def _build_service_under_test(services: list[dict]) -> ClientServicesService:
    service = ClientServicesService()
    service.repository = _FakeClientRepository(services)
    service.product_repository = _FakeProductRepository()
    service.projection_service = _FakeServiceProjection()
    service.product_projection_service = _FakeProductProjection()
    return service


def _service_doc(service_id: str, category: str) -> dict:
    return {
        "id": service_id,
        "provider_id": "provider-1",
        "name": "Servicio",
        "subtitle": "Sub",
        "description": "Desc",
        "unit_price_cents": 100000,
        "price_label": "Desde $1,000 MXN",
        "badge": "Popular",
        "category": category,
    }


def test_detail_alias_entretenimiento_matches_entertainment() -> None:
    service = _build_service_under_test([_service_doc("svc-1", "entertainment")])
    result = service.detail("svc-1", "entretenimiento")
    assert result.id == "svc-1"
    assert result.category == "entretenimiento"


def test_detail_alias_salones_sociales_matches_venue() -> None:
    service = _build_service_under_test([_service_doc("svc-2", "venue")])
    result = service.detail("svc-2", "salones-sociales")
    assert result.id == "svc-2"
    assert result.category == "salones-sociales"


def test_list_with_legacy_alias_returns_results() -> None:
    services = [
        _service_doc("svc-3", "furniture"),
        _service_doc("svc-4", "venue"),
    ]
    service = _build_service_under_test(services)
    result = service.by_category(
        category="equipment",
        q=None,
        min_price_cents=None,
        max_price_cents=None,
        sort="relevance",
        page=1,
        page_size=20,
    )
    assert len(result.items) == 1
    assert result.items[0].id == "svc-3"
    assert result.items[0].category == "mobiliario"


def test_really_wrong_category_behavior() -> None:
    service = _build_service_under_test([_service_doc("svc-5", "dj")])

    list_result = service.by_category(
        category="invalid-category",
        q=None,
        min_price_cents=None,
        max_price_cents=None,
        sort="relevance",
        page=1,
        page_size=20,
    )
    assert list_result.items == []
    assert list_result.total == 0

    with pytest.raises(ResourceNotFoundError):
        service.detail("svc-5", "invalid-category")
