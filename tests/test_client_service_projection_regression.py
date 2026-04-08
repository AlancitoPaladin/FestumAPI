from app.services.service_catalog_projection_service import ServiceCatalogProjectionService
from app.schemas.asset import SignedAssetResponse


class _FakeProductRepository:
    def __init__(self, price: int | None) -> None:
        self.price = price

    def get_min_published_price_cents(self, provider_id: str, service_id: str) -> int | None:
        return self.price


class _FakeStorage:
    @staticmethod
    def extract_storage_key(value: str | None) -> str | None:
        raw = str(value or "").strip().lstrip("/")
        return raw or None

    @staticmethod
    def build_signed_asset(key: str) -> SignedAssetResponse:
        return SignedAssetResponse(
            key=key,
            url=f"https://cdn.example.com/{key}",
            expires_at="2026-12-31T00:00:00Z",
        )


def test_projection_keeps_persisted_service_price_and_label() -> None:
    service = ServiceCatalogProjectionService()
    service.product_repository = _FakeProductRepository(price=None)

    source = {
        "id": "03KLjn7esy53NA0arf9m",
        "provider_id": "provider-1",
        "category": "salones-sociales",
        "name": "Salon BJ",
        "subtitle": "Eventos",
        "description": "Salon para eventos",
        "unit_price_cents": 200000,
        "price_label": "Desde $2,000 MXN",
        "image_keys": [],
        "main_image_key": "",
    }

    projected = service.build_service_projection(source)

    assert projected["unit_price_cents"] == 200000
    assert projected["price_label"] == "Desde $2,000 MXN"


def test_projection_uses_derived_price_only_when_service_price_missing() -> None:
    service = ServiceCatalogProjectionService()
    service.product_repository = _FakeProductRepository(price=345000)

    source = {
        "id": "svc-2",
        "provider_id": "provider-1",
        "category": "banquetes",
        "name": "Banquete Plus",
        "subtitle": "Catering",
        "description": "Detalle",
        "image_keys": [],
        "main_image_key": "",
    }

    projected = service.build_service_projection(source)

    assert projected["unit_price_cents"] == 345000
    assert projected["price_label"] == "Desde $3,450 MXN"


def test_projection_gallery_dedupes_and_orders_main_first() -> None:
    service = ServiceCatalogProjectionService()
    service.product_repository = _FakeProductRepository(price=None)
    service.storage_service = _FakeStorage()

    source = {
        "id": "svc-gallery",
        "provider_id": "provider-1",
        "category": "salones-sociales",
        "name": "Salon Galeria",
        "subtitle": "Eventos",
        "description": "Galeria completa",
        "unit_price_cents": 200000,
        "price_label": "Desde $2,000 MXN",
        "main_image_key": "providers/p1/services/svc-gallery/images/main.webp",
        "image_keys": [
            "providers/p1/services/svc-gallery/images/second.webp",
            "providers/p1/services/svc-gallery/images/main.webp",
            "providers/p1/services/svc-gallery/images/third.webp",
            "providers/p1/services/svc-gallery/images/second.webp",
        ],
    }

    projected = service.build_service_projection(source)
    keys = [item["key"] for item in projected["images"]]

    assert keys == [
        "providers/p1/services/svc-gallery/images/main.webp",
        "providers/p1/services/svc-gallery/images/second.webp",
        "providers/p1/services/svc-gallery/images/third.webp",
    ]
    assert len(set(keys)) == 3
    assert projected["image"]["key"] == "providers/p1/services/svc-gallery/images/main.webp"


def test_projection_gallery_fallback_to_main_when_image_keys_empty() -> None:
    service = ServiceCatalogProjectionService()
    service.product_repository = _FakeProductRepository(price=None)
    service.storage_service = _FakeStorage()

    source = {
        "id": "svc-main-only",
        "provider_id": "provider-1",
        "category": "salones-sociales",
        "name": "Salon Main",
        "subtitle": "Eventos",
        "description": "Main image",
        "unit_price_cents": 200000,
        "price_label": "Desde $2,000 MXN",
        "main_image_key": "providers/p1/services/svc-main-only/images/main.webp",
        "image_keys": [],
    }

    projected = service.build_service_projection(source)
    keys = [item["key"] for item in projected["images"]]

    assert keys == ["providers/p1/services/svc-main-only/images/main.webp"]
