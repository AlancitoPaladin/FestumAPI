from app.services.client_services_service import ClientServicesService


class _FakeClientRepository:
    def __init__(self, service: dict) -> None:
        self.service = service

    def list_published_services(self) -> list[dict]:
        return [dict(self.service)]

    def services_by_category(self, category: str) -> list[dict]:
        if self.service.get("category") == category:
            return [dict(self.service)]
        return []

    def visible_service_by_id(self, service_id: str) -> dict | None:
        if self.service.get("id") == service_id:
            return dict(self.service)
        return None


class _FakeProductRepository:
    def list_published_by_service(self, provider_id: str, service_id: str) -> list[dict]:
        return [
            {
                "id": "prod-1",
                "name": "Paquete basico",
                "description": "Producto base",
                "unit_price_cents": 200000,
                "price_label": "Desde $2,000 MXN",
            }
        ]


class _FakeServiceProjection:
    def build_service_projection(self, item: dict) -> dict:
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
            "image_url": "",
        }


class _FakeProductProjection:
    def build_product_projection(self, item: dict) -> dict:
        return dict(item)


def _build_service() -> dict:
    return {
        "id": "svc-1",
        "provider_id": "provider-1",
        "name": "Salon BJ",
        "subtitle": "Eventos",
        "description": "Salon para eventos",
        "unit_price_cents": 200000,
        "price_label": "Desde $2,000 MXN",
        "badge": "Popular",
        "category": "salones-sociales",
    }


def _build_service_under_test() -> ClientServicesService:
    service = ClientServicesService()
    service.repository = _FakeClientRepository(_build_service())
    service.product_repository = _FakeProductRepository()
    service.projection_service = _FakeServiceProjection()
    service.product_projection_service = _FakeProductProjection()
    return service


def _assert_products_contract(items: list) -> None:
    assert items
    assert items[0].products
    product = items[0].products[0]
    assert product.id == "prod-1"
    assert product.name == "Paquete basico"
    assert product.unit_price_cents == 200000
    assert product.price_label == "Desde $2,000 MXN"


def test_home_includes_products_contract() -> None:
    service = _build_service_under_test()
    response = service.home()
    _assert_products_contract(response.root["salones-sociales"])


def test_by_category_includes_products_contract() -> None:
    service = _build_service_under_test()
    response = service.by_category(
        category="salones-sociales",
        q=None,
        min_price_cents=None,
        max_price_cents=None,
        sort="relevance",
        page=1,
        page_size=20,
    )
    _assert_products_contract(response.items)


def test_detail_includes_products_contract() -> None:
    service = _build_service_under_test()
    response = service.detail("svc-1", "salones-sociales")
    assert response.products
    assert response.products[0].id == "prod-1"
    assert response.products[0].name == "Paquete basico"
    assert response.products[0].unit_price_cents == 200000
