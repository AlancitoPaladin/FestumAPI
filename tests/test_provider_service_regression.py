from datetime import datetime, timezone

from app.schemas.provider_service import ProviderServiceStatusUpdate, ProviderServiceUpdate
from app.services.provider_service_catalog_service import ProviderServiceCatalogService


class _FakeProviderServiceRepository:
    def __init__(self, seed: dict) -> None:
        self.doc = dict(seed)
        self.last_update_data: dict | None = None

    def get_by_id(self, provider_id: str, service_id: str) -> dict | None:
        if self.doc.get("provider_id") != provider_id or self.doc.get("id") != service_id:
            return None
        return dict(self.doc)

    def update(self, provider_id: str, service_id: str, data: dict) -> dict:
        self.last_update_data = dict(data)
        self.doc.update(data)
        self.doc["updated_at"] = datetime.now(tz=timezone.utc)
        return dict(self.doc)


def _build_service_under_test(seed: dict) -> tuple[ProviderServiceCatalogService, _FakeProviderServiceRepository]:
    service = ProviderServiceCatalogService()
    fake_repo = _FakeProviderServiceRepository(seed)
    service.repository = fake_repo
    return service, fake_repo


def test_publish_status_does_not_override_price_fields() -> None:
    seed = {
        "id": "svc-1",
        "provider_id": "prov-1",
        "category": "banquetes",
        "name": "Banquete Premium",
        "subtitle": "Para eventos grandes",
        "description": "Incluye catering completo",
        "unit_price_cents": 4120000,
        "price_label": "Desde $41,200 MXN",
        "status": "draft",
        "created_at": datetime.now(tz=timezone.utc),
        "updated_at": datetime.now(tz=timezone.utc),
    }
    service, repo = _build_service_under_test(seed)

    service.update_service_status("prov-1", "svc-1", ProviderServiceStatusUpdate(status="published"))

    assert repo.last_update_data == {"status": "published"}
    assert repo.doc["unit_price_cents"] == 4120000
    assert repo.doc["price_label"] == "Desde $41,200 MXN"


def test_update_service_keeps_existing_price_when_omitted() -> None:
    seed = {
        "id": "svc-2",
        "provider_id": "prov-1",
        "category": "mobiliario",
        "name": "Mobiliario Base",
        "subtitle": "Sillas y mesas",
        "description": "Paquete base",
        "unit_price_cents": 150000,
        "price_label": "Desde $1,500 MXN",
        "status": "draft",
        "created_at": datetime.now(tz=timezone.utc),
        "updated_at": datetime.now(tz=timezone.utc),
    }
    service, repo = _build_service_under_test(seed)

    service.update_service(
        "prov-1",
        "svc-2",
        ProviderServiceUpdate(name="Mobiliario Plus"),
    )

    assert "unit_price_cents" not in (repo.last_update_data or {})
    assert repo.doc["unit_price_cents"] == 150000
    assert repo.doc["price_label"] == "Desde $1,500 MXN"


def test_update_service_persists_unit_price_when_provided() -> None:
    seed = {
        "id": "svc-3",
        "provider_id": "prov-1",
        "category": "salones-sociales",
        "name": "Salón Aurora",
        "subtitle": "Evento social",
        "description": "Incluye iluminación",
        "unit_price_cents": 900000,
        "price_label": "Desde $9,000 MXN",
        "status": "draft",
        "created_at": datetime.now(tz=timezone.utc),
        "updated_at": datetime.now(tz=timezone.utc),
    }
    service, repo = _build_service_under_test(seed)

    service.update_service(
        "prov-1",
        "svc-3",
        ProviderServiceUpdate(unit_price_cents=1200000),
    )

    assert repo.doc["unit_price_cents"] == 1200000
    assert repo.doc["price_label"] == "Desde $12,000 MXN"
