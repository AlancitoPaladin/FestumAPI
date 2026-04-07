from app.services.provider_product_service import ProviderProductService


def test_next_booking_includes_explicit_event_date_and_status_raw() -> None:
    booking = {
        "id": "FST-2B1990642F-R1",
        "customer_name": "Alan Carlos",
        "event_date": "2026-04-02",
        "has_specific_schedule": True,
        "start_time": "18:00:00",
        "end_time": "23:00:00",
        "status": "pending",
    }

    payload = ProviderProductService._build_next_booking(booking)
    assert payload is not None
    assert payload.event_date == "2026-04-02"
    assert payload.date == "2026-04-02"
    assert payload.start_date == "2026-04-02"
    assert payload.scheduled_date == "2026-04-02"
    assert payload.time_label == "18:00 - 23:00"
    assert payload.status == "pending"
