from app.services.client_services_service import ClientServicesService
from app.services.service_catalog_projection_service import ServiceCatalogProjectionService


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


class _FakeProductsRepo:
    def list_published_by_service(self, provider_id: str, service_id: str) -> list[dict]:
        return []


class _FakeFailingStorage:
    @staticmethod
    def extract_storage_key(raw: str) -> str:
        return raw.strip().lstrip("/")

    @staticmethod
    def build_signed_asset(key: str):
        raise RuntimeError("signing failed")


def _build_service_under_test(services: list[dict], failing_signing: bool = False) -> ClientServicesService:
    service = ClientServicesService()
    service.repository = _FakeClientRepository(services)
    service.product_repository = _FakeProductsRepo()
    service.product_projection_service = _FakeProductsRepo()
    if failing_signing:
        projection = ServiceCatalogProjectionService()
        projection.storage_service = _FakeFailingStorage()
        service.projection_service = projection
    return service


def test_home_returns_exact_three_keys() -> None:
    services = [
        {
            "id": "svc-venue",
            "provider_id": "p1",
            "name": "Salon BJ",
            "subtitle": "Eventos",
            "description": "Desc",
            "unit_price_cents": 200000,
            "price_label": "Desde $2,000 MXN",
            "badge": "Popular",
            "category": "venue",
        },
        {
            "id": "svc-furn",
            "provider_id": "p1",
            "name": "Sillas",
            "subtitle": "Mobiliario",
            "description": "Desc",
            "unit_price_cents": 50000,
            "price_label": "Desde $500 MXN",
            "badge": "Popular",
            "category": "furniture",
        },
        {
            "id": "svc-banq",
            "provider_id": "p1",
            "name": "Banquete",
            "subtitle": "Comida",
            "description": "Desc",
            "unit_price_cents": 150000,
            "price_label": "Desde $1,500 MXN",
            "badge": "Popular",
            "category": "banquet",
        },
    ]
    service = _build_service_under_test(services)

    response = service.home()
    payload = response.model_dump(by_alias=True)

    assert set(payload.keys()) == {
        "salones-sociales",
        "mobiliario",
        "banquetes",
        "dj",
        "decoracion",
        "fotografia",
        "entretenimiento",
        "otros",
    }
    assert len(payload["salones-sociales"]) == 1
    assert len(payload["mobiliario"]) == 1
    assert len(payload["banquetes"]) == 1


def test_home_falls_back_when_image_signing_fails() -> None:
    services = [
        {
            "id": "svc-1",
            "provider_id": "p1",
            "name": "Salon BJ",
            "subtitle": "Eventos",
            "description": "Desc",
            "unit_price_cents": 200000,
            "price_label": "Desde $2,000 MXN",
            "badge": "Popular",
            "category": "salones-sociales",
            "main_image_key": "providers/p1/services/svc-1/main.jpg",
            "image_url": "https://legacy.example.com/main.jpg",
        }
    ]
    service = _build_service_under_test(services, failing_signing=True)

    response = service.home()
    payload = response.model_dump(by_alias=True)
    items = payload["salones-sociales"]

    assert len(items) == 1
    assert items[0]["id"] == "svc-1"
    assert items[0]["image"] is None
    assert items[0]["image_url"] == "https://legacy.example.com/main.jpg"


def test_home_returns_empty_arrays_when_no_services() -> None:
    service = _build_service_under_test([])

    response = service.home()
    payload = response.model_dump(by_alias=True)

    assert payload == {
        "salones-sociales": [],
        "mobiliario": [],
        "banquetes": [],
        "dj": [],
        "decoracion": [],
        "fotografia": [],
        "entretenimiento": [],
        "otros": [],
    }


def test_home_includes_dj_category_items() -> None:
    services = [
        {
            "id": "svc-dj-1",
            "provider_id": "p1",
            "name": "DJ Premium",
            "subtitle": "Musica en vivo",
            "description": "DJ con audio profesional",
            "unit_price_cents": 350000,
            "price_label": "Desde $3,500 MXN",
            "badge": "Popular",
            "category": "dj",
        }
    ]
    service = _build_service_under_test(services)

    response = service.home()
    payload = response.model_dump(by_alias=True)

    assert len(payload["dj"]) == 1
    assert payload["dj"][0]["id"] == "svc-dj-1"
    assert payload["otros"] == []
