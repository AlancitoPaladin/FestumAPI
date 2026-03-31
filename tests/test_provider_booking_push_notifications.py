from datetime import datetime, timezone

from app.schemas.provider_booking import ProviderBookingStatusUpdate
from app.services.provider_booking_service import ProviderBookingService


class _FakeBookingRepository:
    def __init__(self) -> None:
        now = datetime.now(tz=timezone.utc)
        self._booking = {
            "id": "booking-1",
            "provider_id": "provider-1",
            "client_id": "client-1",
            "order_id": "FST-REQ-111111",
            "service_id": "svc-1",
            "service_name": "Salon BJ",
            "product_id": "prod-1",
            "product_name": "Paquete basico",
            "customer_name": "Client User",
            "customer_image_url": "",
            "event_date": "2026-04-02",
            "has_specific_schedule": False,
            "start_time": "",
            "end_time": "",
            "event_type": "Evento",
            "guests": 0,
            "contact_phone": "",
            "contact_email": "",
            "event_location": "",
            "payment_details": "",
            "total_amount": 2000.0,
            "paid_amount": 0.0,
            "notes": "",
            "source": "client",
            "status": "pending",
            "created_at": now,
            "updated_at": now,
        }

    def get_by_id(self, provider_id: str, booking_id: str) -> dict | None:
        return dict(self._booking)

    def update(self, provider_id: str, booking_id: str, data: dict) -> dict:
        self._booking = {**self._booking, **data}
        return dict(self._booking)


class _FakeAvailabilityRepository:
    def reserve_date(self, provider_id: str, service_id: str, product_id: str, date_key: str, booking_summary: dict) -> dict:
        return {}

    def clear_reserved_date(self, provider_id: str, service_id: str, product_id: str, date_key: str, booking_id: str) -> dict:
        return {}


class _FakePushNotificationService:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def send_to_user(self, *, user_id: str, title: str, body: str, data: dict | None = None, context: dict | None = None) -> dict:
        self.calls.append(
            {
                "user_id": user_id,
                "title": title,
                "body": body,
                "data": data or {},
                "context": context or {},
            }
        )
        return {"sent": 1, "failed": 0, "removed": 0, "total": 1}


def test_update_booking_status_sends_client_push_notification() -> None:
    service = ProviderBookingService()
    service.booking_repository = _FakeBookingRepository()
    service.availability_repository = _FakeAvailabilityRepository()
    service.push_notification_service = _FakePushNotificationService()

    response = service.update_booking_status(
        "provider-1",
        "booking-1",
        ProviderBookingStatusUpdate(status="confirmed"),
    )

    assert response.status == "confirmed"
    assert len(service.push_notification_service.calls) == 1
    call = service.push_notification_service.calls[0]
    assert call["user_id"] == "client-1"
    assert call["data"]["type"] == "reservation_updated"
    assert call["data"]["order_id"] == "FST-REQ-111111"
    assert call["data"]["target_screen"] == "client_orders"
