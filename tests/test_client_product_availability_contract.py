from app.schemas.client import ClientProductAvailabilityResponse
from app.services.provider_availability_service import ProviderAvailabilityService


class _FakeAvailabilityRepository:
    def list_by_month(self, provider_id: str, service_id: str, product_id: str, year: int, month: int) -> list[dict]:
        return [
            {"date": "2026-03-26", "status": "reserved"},
            {"date": "2026-03-27", "status": "blocked"},
            {"date": "2026-03-28", "status": "unexpected"},
        ]


def test_client_availability_contract_uses_valid_enum_and_date_string() -> None:
    service = ProviderAvailabilityService.__new__(ProviderAvailabilityService)
    service.repository = _FakeAvailabilityRepository()

    payload = service.client_month(
        provider_id="provider-1",
        service_id="svc-1",
        product_id="prod-1",
        year=2026,
        month=3,
    )

    response = ClientProductAvailabilityResponse(**payload)

    assert response.product_id == "prod-1"
    assert response.year == 2026
    assert response.month == 3
    target = {day.date: day.status for day in response.days}
    assert target["2026-03-26"] == "reserved"
    assert target["2026-03-27"] == "blocked"
    assert target["2026-03-28"] == "blocked"
