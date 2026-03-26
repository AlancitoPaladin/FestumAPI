from app.services.service_catalog_projection_service import ServiceCatalogProjectionService


class _FakeProductRepository:
    def __init__(self, price: int | None) -> None:
        self.price = price

    def get_min_published_price_cents(self, provider_id: str, service_id: str) -> int | None:
        return self.price


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
