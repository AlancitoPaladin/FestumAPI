from __future__ import annotations

import json
import statistics
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from app.services.client_cart_service import ClientCartService
from app.services.client_orders_service import ClientOrdersService
from app.services.client_services_service import ClientServicesService


def _pct(values: list[float], p: int) -> float:
    if not values:
        return 0.0
    index = max(0, min(len(values) - 1, round((p / 100) * (len(values) - 1))))
    return sorted(values)[index]


@dataclass
class BenchmarkRow:
    endpoint: str
    p50_ms: float
    p95_ms: float
    p99_ms: float
    avg_payload_bytes: int


class FakeClientRepo:
    def __init__(self, orders_count: int = 120) -> None:
        now = datetime.now(tz=timezone.utc)
        self.orders = [
            {
                "id": f"FST-{1000+i}",
                "title": "Salón Aurora +1 servicios",
                "status": "pending_payment",
                "subtotal_cents": 200000,
                "service_fee_cents": 10000,
                "tax_cents": 33600,
                "total_cents": 243600,
                "total_label": "$2,436 MXN",
                "created_at": now,
                "items": [{"service_id": "svc-1", "service_name": "Salón Aurora", "total_item_cents": 243600}],
            }
            for i in range(orders_count)
        ]
        self.services = [
            {
                "id": "svc-1",
                "provider_id": "prov-1",
                "name": "Salón Aurora",
                "subtitle": "Evento",
                "description": "Desc",
                "unit_price_cents": 200000,
                "price_label": "Desde $2,000 MXN",
                "badge": "Popular",
                "category": "salones-sociales",
            },
            {
                "id": "svc-2",
                "provider_id": "prov-1",
                "name": "DJ Premium",
                "subtitle": "Música",
                "description": "Desc",
                "unit_price_cents": 100000,
                "price_label": "Desde $1,000 MXN",
                "badge": "Popular",
                "category": "dj",
            },
        ]
        self.cart = [
            {
                "id": "svc-1",
                "name": "Salón Aurora",
                "service_name": "Salón Aurora",
                "quantity": 1,
                "unit_price_cents": 200000,
            }
        ]

    def order_list(self, user_id: str) -> list[dict]:
        return self.orders

    def order_get(self, user_id: str, order_id: str) -> dict | None:
        for item in self.orders:
            if item["id"] == order_id:
                return item
        return None

    def cart_list(self, user_id: str) -> list[dict]:
        return self.cart

    def list_published_services(self) -> list[dict]:
        return self.services

    def services_by_category(self, category: str) -> list[dict]:
        return [item for item in self.services if item.get("category") == category]

    def visible_service_by_id(self, service_id: str) -> dict | None:
        for item in self.services:
            if item["id"] == service_id:
                return item
        return None


class FakeProductsRepo:
    def list_published_by_service(self, provider_id: str, service_id: str) -> list[dict]:
        return []


def run_benchmark(iterations: int = 120) -> list[BenchmarkRow]:
    repo = FakeClientRepo()

    orders_service = ClientOrdersService()
    orders_service.repository = repo

    cart_service = ClientCartService()
    cart_service.repository = repo

    services_service = ClientServicesService()
    services_service.repository = repo
    services_service.product_repository = FakeProductsRepo()

    rows: list[BenchmarkRow] = []
    specs = [
        ("GET /client/orders (include_items=false)", lambda: orders_service.list_orders("client-1", include_items=False)),
        ("GET /client/orders (include_items=true)", lambda: orders_service.list_orders("client-1", include_items=True)),
        ("GET /client/orders/{id}", lambda: orders_service.get_order_detail("client-1", "FST-1000")),
        ("GET /client/services/home", lambda: services_service.home(user_id="client-1")),
        ("GET /client/services", lambda: services_service.by_category("salones-sociales", None, None, None, "relevance", 1, 20)),
        ("GET /client/services/{id}", lambda: services_service.detail("svc-1", "salones-sociales")),
        ("GET /client/cart", lambda: cart_service.list_items("client-1")),
    ]

    for endpoint, fn in specs:
        latencies: list[float] = []
        payload_sizes: list[int] = []
        for _ in range(iterations):
            start = time.perf_counter()
            response = fn()
            latencies.append((time.perf_counter() - start) * 1000)
            payload_sizes.append(len(json.dumps(response.model_dump(), default=str).encode("utf-8")))
        rows.append(
            BenchmarkRow(
                endpoint=endpoint,
                p50_ms=_pct(latencies, 50),
                p95_ms=_pct(latencies, 95),
                p99_ms=_pct(latencies, 99),
                avg_payload_bytes=round(statistics.mean(payload_sizes)),
            )
        )
    return rows


if __name__ == "__main__":
    results = run_benchmark()
    print("endpoint,p50_ms,p95_ms,p99_ms,avg_payload_bytes")
    for row in results:
        print(
            f"{row.endpoint},{row.p50_ms:.2f},{row.p95_ms:.2f},{row.p99_ms:.2f},{row.avg_payload_bytes}"
        )
