from datetime import date

from app.core.exceptions import ResourceNotFoundError
from app.repositories.provider_availability_repository import ProviderAvailabilityRepository
from app.repositories.provider_booking_repository import ProviderBookingRepository
from app.repositories.provider_product_repository import ProviderProductRepository
from app.schemas.provider_availability import (
    ProviderAvailabilityBlockRequest,
    ProviderAvailabilityBookingSummary,
    ProviderAvailabilityDayResponse,
    ProviderAvailabilityMonthResponse,
    ProviderAvailabilityStatusResponse,
)


class ProviderAvailabilityService:
    def __init__(self) -> None:
        self.product_repository = ProviderProductRepository()
        self.repository = ProviderAvailabilityRepository()
        self.booking_repository = ProviderBookingRepository()

    def get_month(
        self, provider_id: str, product_id: str, year: int, month: int
    ) -> ProviderAvailabilityMonthResponse:
        product = self.product_repository.get_by_product_id(provider_id, product_id)
        if not product:
            raise ResourceNotFoundError("Provider product not found")

        month_items = self.repository.list_by_month(
            provider_id=provider_id,
            service_id=product["service_id"],
            product_id=product_id,
            year=year,
            month=month,
        )
        status_by_date = {item["date"]: item for item in month_items}

        days_in_month = self._days_in_month(year, month)
        days = []
        for day in range(1, days_in_month + 1):
            current_date = date(year, month, day)
            date_key = current_date.isoformat()
            item = status_by_date.get(date_key)
            if not item:
                days.append(
                    ProviderAvailabilityDayResponse(
                        date=current_date,
                        status="available",
                    )
                )
                continue

            booking = None
            booking_data = item.get("booking")
            if booking_data:
                booking = self._build_booking_summary(provider_id, booking_data, item.get("date"))

            days.append(
                ProviderAvailabilityDayResponse(
                    date=current_date,
                    status=item.get("status", "available"),
                    booking=booking,
                )
            )

        return ProviderAvailabilityMonthResponse(
            product_id=product_id,
            product_name=str(product.get("name", "")),
            year=year,
            month=month,
            days=days,
        )

    def block_date(
        self,
        provider_id: str,
        product_id: str,
        target_date: date,
    ) -> ProviderAvailabilityStatusResponse:
        product = self.product_repository.get_by_product_id(provider_id, product_id)
        if not product:
            raise ResourceNotFoundError("Provider product not found")

        item = self.repository.block_date(
            provider_id=provider_id,
            service_id=product["service_id"],
            product_id=product_id,
            date_key=target_date.isoformat(),
        )
        return ProviderAvailabilityStatusResponse(
            product_id=product_id,
            date=target_date,
            status=item.get("status", "blocked"),
        )

    def unblock_date(
        self, provider_id: str, product_id: str, target_date: date
    ) -> ProviderAvailabilityStatusResponse:
        product = self.product_repository.get_by_product_id(provider_id, product_id)
        if not product:
            raise ResourceNotFoundError("Provider product not found")

        item = self.repository.unblock_date(
            provider_id=provider_id,
            service_id=product["service_id"],
            product_id=product_id,
            date_key=target_date.isoformat(),
        )
        return ProviderAvailabilityStatusResponse(
            product_id=product_id,
            date=target_date,
            status=item.get("status", "available"),
        )

    def block_date_from_request(
        self, provider_id: str, product_id: str, payload: ProviderAvailabilityBlockRequest
    ) -> ProviderAvailabilityStatusResponse:
        return self.block_date(provider_id, product_id, payload.date)

    def unblock_date_from_request(
        self, provider_id: str, product_id: str, payload: ProviderAvailabilityBlockRequest
    ) -> ProviderAvailabilityStatusResponse:
        return self.unblock_date(provider_id, product_id, payload.date)

    def client_month(
        self,
        provider_id: str,
        service_id: str,
        product_id: str,
        year: int,
        month: int,
    ) -> dict:
        month_items = self.repository.list_by_month(
            provider_id=provider_id,
            service_id=service_id,
            product_id=product_id,
            year=year,
            month=month,
        )
        status_by_date = {item["date"]: item.get("status", "available") for item in month_items}

        days = []
        days_in_month = self._days_in_month(year, month)
        for day in range(1, days_in_month + 1):
            current_date = date(year, month, day)
            date_key = current_date.isoformat()
            days.append(
                {
                    "date": date_key,
                    "status": status_by_date.get(date_key, "available"),
                }
            )

        return {
            "product_id": product_id,
            "year": year,
            "month": month,
            "days": days,
        }

    def _build_booking_summary(
        self,
        provider_id: str,
        booking_data: dict,
        fallback_date: str | None,
    ) -> ProviderAvailabilityBookingSummary:
        booking_id = str(
            booking_data.get("booking_id")
            or booking_data.get("id")
            or ""
        )
        if booking_id:
            booking = self.booking_repository.get_by_id(provider_id, booking_id)
            if booking:
                return ProviderAvailabilityBookingSummary(
                    id=booking_id,
                    booking_id=booking_id,
                    customer_name=str(booking.get("customer_name", "")),
                    customer_image_url=str(booking.get("customer_image_url", "")),
                    date=self._normalize_date(booking.get("event_date") or fallback_date),
                    time=self._time_label(booking),
                    event_type=str(booking.get("event_type", "")),
                    guests=int(booking.get("guests", 0) or 0),
                    total_amount=float(booking.get("total_amount", 0) or 0),
                    paid_amount=float(booking.get("paid_amount", 0) or 0),
                    status=self._status_label(str(booking.get("status", "pending"))),
                    notes=str(booking.get("notes", "")),
                )

        return ProviderAvailabilityBookingSummary(
            **{
                **booking_data,
                "id": booking_id or booking_data.get("id"),
                "booking_id": booking_id or booking_data.get("booking_id"),
                "date": self._normalize_date(booking_data.get("date") or fallback_date),
            }
        )

    @staticmethod
    def _days_in_month(year: int, month: int) -> int:
        if month == 12:
            return 31
        return (date(year, month + 1, 1) - date(year, month, 1)).days

    @staticmethod
    def _normalize_date(raw_value: object) -> date | None:
        if raw_value is None or raw_value == "":
            return None
        if isinstance(raw_value, date):
            return raw_value
        normalized = str(raw_value)
        if "T" in normalized:
            normalized = normalized.split("T", maxsplit=1)[0]
        return date.fromisoformat(normalized)

    @staticmethod
    def _time_label(booking: dict) -> str:
        has_specific_schedule = bool(booking.get("has_specific_schedule", False))
        if not has_specific_schedule:
            return "Todo el dia"

        start_time = str(booking.get("start_time", "") or "")
        if start_time:
            return start_time[:5]
        return "Horario por confirmar"

    @staticmethod
    def _status_label(status: str) -> str:
        return {
            "confirmed": "Confirmada",
            "pending": "Pendiente",
            "cancelled": "Cancelada",
            "rejected": "Rechazada",
        }.get(status, status.title())
