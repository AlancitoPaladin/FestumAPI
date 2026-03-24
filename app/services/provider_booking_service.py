from datetime import date

from app.core.exceptions import ResourceNotFoundError
from app.repositories.provider_availability_repository import ProviderAvailabilityRepository
from app.repositories.provider_booking_repository import ProviderBookingRepository
from app.repositories.provider_product_repository import ProviderProductRepository
from app.repositories.provider_service_repository import ProviderServiceRepository
from app.schemas.provider_availability import ProviderAvailabilityBookingSummary
from app.schemas.provider_booking import (
    ProviderBookingBase,
    ProviderBookingListResponse,
    ProviderBookingResponse,
    ProviderBookingUpdate,
    ProviderBookingStatusUpdate,
    ProviderManualBookingCreate,
)


class ProviderBookingService:
    def __init__(self) -> None:
        self.booking_repository = ProviderBookingRepository()
        self.product_repository = ProviderProductRepository()
        self.service_repository = ProviderServiceRepository()
        self.availability_repository = ProviderAvailabilityRepository()

    def create_manual_booking(
        self,
        provider_id: str,
        product_id: str,
        payload: ProviderManualBookingCreate,
    ) -> ProviderBookingResponse:
        product = self.product_repository.get_by_product_id(provider_id, product_id)
        if not product:
            raise ResourceNotFoundError("Provider product not found")

        parent_service = self.service_repository.get_by_id(provider_id, product["service_id"])
        if not parent_service:
            raise ResourceNotFoundError("Provider service not found")

        booking_id = self.booking_repository.generate_id(provider_id)
        booking_data = {
            "service_id": product["service_id"],
            "service_name": str(parent_service.get("name", "")),
            "product_id": product_id,
            "product_name": str(product.get("name", "")),
            "customer_name": payload.customer_name,
            "customer_image_url": payload.customer_image_url,
            "event_date": payload.event_date.isoformat(),
            "has_specific_schedule": payload.has_specific_schedule,
            "start_time": payload.start_time.strftime("%H:%M:%S") if payload.start_time else "",
            "end_time": payload.end_time.strftime("%H:%M:%S") if payload.end_time else "",
            "event_type": payload.event_type,
            "guests": payload.guests,
            "contact_phone": payload.contact_phone,
            "contact_email": payload.contact_email,
            "event_location": payload.event_location,
            "payment_details": payload.payment_details,
            "total_amount": payload.total_amount,
            "paid_amount": payload.paid_amount,
            "notes": payload.notes,
            "source": "manual",
            "status": "confirmed",
        }

        booking = self.booking_repository.create(provider_id, booking_id, booking_data)
        try:
            self.availability_repository.reserve_date(
                provider_id=provider_id,
                service_id=product["service_id"],
                product_id=product_id,
                date_key=payload.event_date.isoformat(),
                booking_summary=self._build_availability_summary(booking_id, booking),
            )
        except Exception:
            self.booking_repository.delete(provider_id, booking_id)
            raise

        return self._to_response(booking)

    def list_bookings(
        self,
        provider_id: str,
        *,
        status: str | None = None,
        year: int | None = None,
        month: int | None = None,
        product_id: str | None = None,
    ) -> ProviderBookingListResponse:
        items = [
            self._to_response(item)
            for item in self.booking_repository.list_by_provider(
                provider_id,
                status=status,
                year=year,
                month=month,
                product_id=product_id,
            )
        ]
        return ProviderBookingListResponse(items=items, total=len(items))

    def get_booking(self, provider_id: str, booking_id: str) -> ProviderBookingResponse:
        booking = self.booking_repository.get_by_id(provider_id, booking_id)
        if not booking:
            raise ResourceNotFoundError("Provider booking not found")
        return self._to_response(booking)

    def update_booking(
        self,
        provider_id: str,
        booking_id: str,
        payload: ProviderBookingUpdate,
    ) -> ProviderBookingResponse:
        current_booking = self.booking_repository.get_by_id(provider_id, booking_id)
        if not current_booking:
            raise ResourceNotFoundError("Provider booking not found")

        merged_payload = self._merge_booking_payload(current_booking, payload)
        validated_payload = ProviderBookingBase(**merged_payload)
        update_data = self._serialize_booking_fields(validated_payload)

        if current_booking.get("status") == "confirmed":
            old_date_key = self._date_key(current_booking.get("event_date"))
            new_date_key = validated_payload.event_date.isoformat()
            date_changed = old_date_key != new_date_key

            if date_changed:
                self.availability_repository.clear_reserved_date(
                    provider_id=provider_id,
                    service_id=current_booking["service_id"],
                    product_id=current_booking["product_id"],
                    date_key=old_date_key,
                    booking_id=booking_id,
                )
                try:
                    updated_booking = self.booking_repository.update(
                        provider_id=provider_id,
                        booking_id=booking_id,
                        data=update_data,
                    )
                    self.availability_repository.reserve_date(
                        provider_id=provider_id,
                        service_id=current_booking["service_id"],
                        product_id=current_booking["product_id"],
                        date_key=new_date_key,
                        booking_summary=self._build_availability_summary(booking_id, updated_booking),
                    )
                    return self._to_response(updated_booking)
                except Exception:
                    self.availability_repository.reserve_date(
                        provider_id=provider_id,
                        service_id=current_booking["service_id"],
                        product_id=current_booking["product_id"],
                        date_key=old_date_key,
                        booking_summary=self._build_availability_summary(booking_id, current_booking),
                    )
                    raise

        updated_booking = self.booking_repository.update(
            provider_id=provider_id,
            booking_id=booking_id,
            data=update_data,
        )
        return self._to_response(updated_booking)

    def update_booking_status(
        self,
        provider_id: str,
        booking_id: str,
        payload: ProviderBookingStatusUpdate,
    ) -> ProviderBookingResponse:
        current_booking = self.booking_repository.get_by_id(provider_id, booking_id)
        if not current_booking:
            raise ResourceNotFoundError("Provider booking not found")

        updated_booking = self.booking_repository.update(
            provider_id=provider_id,
            booking_id=booking_id,
            data={"status": payload.status},
        )

        try:
            if current_booking.get("status") != "confirmed" and payload.status == "confirmed":
                self.availability_repository.reserve_date(
                    provider_id=provider_id,
                    service_id=current_booking["service_id"],
                    product_id=current_booking["product_id"],
                    date_key=self._date_key(current_booking.get("event_date")),
                    booking_summary=self._build_availability_summary(booking_id, updated_booking),
                )
            elif current_booking.get("status") == "confirmed" and payload.status != "confirmed":
                self.availability_repository.clear_reserved_date(
                    provider_id=provider_id,
                    service_id=current_booking["service_id"],
                    product_id=current_booking["product_id"],
                    date_key=self._date_key(current_booking.get("event_date")),
                    booking_id=booking_id,
                )
        except Exception:
            self.booking_repository.update(
                provider_id=provider_id,
                booking_id=booking_id,
                data={"status": current_booking["status"]},
            )
            raise

        return self._to_response(updated_booking)

    def count_confirmed_for_month(self, provider_id: str, target_date: date) -> int:
        return self.booking_repository.count_confirmed_for_month(
            provider_id,
            year=target_date.year,
            month=target_date.month,
        )

    @staticmethod
    def _build_availability_summary(booking_id: str, booking: dict) -> dict:
        summary = ProviderAvailabilityBookingSummary(
            booking_id=booking_id,
            customer_name=str(booking.get("customer_name", "")),
            customer_image_url=str(booking.get("customer_image_url", "")),
            event_type=str(booking.get("event_type", "")),
            guests=int(booking.get("guests", 0) or 0),
        )
        return summary.model_dump()

    @staticmethod
    def _serialize_booking_fields(payload: ProviderBookingBase) -> dict:
        return {
            "customer_name": payload.customer_name,
            "customer_image_url": payload.customer_image_url,
            "event_date": payload.event_date.isoformat(),
            "has_specific_schedule": payload.has_specific_schedule,
            "start_time": payload.start_time.strftime("%H:%M:%S") if payload.start_time else "",
            "end_time": payload.end_time.strftime("%H:%M:%S") if payload.end_time else "",
            "event_type": payload.event_type,
            "guests": payload.guests,
            "contact_phone": payload.contact_phone,
            "contact_email": payload.contact_email,
            "event_location": payload.event_location,
            "payment_details": payload.payment_details,
            "total_amount": payload.total_amount,
            "paid_amount": payload.paid_amount,
            "notes": payload.notes,
        }

    @staticmethod
    def _merge_booking_payload(current_booking: dict, payload: ProviderBookingUpdate) -> dict:
        raw = payload.model_dump(exclude_none=True)
        return {
            "customer_name": raw.get("customer_name", current_booking.get("customer_name", "")),
            "customer_image_url": raw.get("customer_image_url", current_booking.get("customer_image_url", "")),
            "event_date": raw.get("event_date", current_booking.get("event_date", "")),
            "has_specific_schedule": raw.get(
                "has_specific_schedule",
                bool(current_booking.get("has_specific_schedule", False)),
            ),
            "start_time": raw.get("start_time", current_booking.get("start_time", "")),
            "end_time": raw.get("end_time", current_booking.get("end_time", "")),
            "event_type": raw.get("event_type", current_booking.get("event_type", "")),
            "guests": raw.get("guests", int(current_booking.get("guests", 0) or 0)),
            "contact_phone": raw.get("contact_phone", current_booking.get("contact_phone", "")),
            "contact_email": raw.get("contact_email", current_booking.get("contact_email", "")),
            "event_location": raw.get("event_location", current_booking.get("event_location", "")),
            "payment_details": raw.get("payment_details", current_booking.get("payment_details", "")),
            "total_amount": raw.get("total_amount", float(current_booking.get("total_amount", 0) or 0)),
            "paid_amount": raw.get("paid_amount", float(current_booking.get("paid_amount", 0) or 0)),
            "notes": raw.get("notes", current_booking.get("notes", "")),
        }

    @staticmethod
    def _to_response(booking: dict) -> ProviderBookingResponse:
        total_amount = float(booking.get("total_amount", 0) or 0)
        paid_amount = float(booking.get("paid_amount", 0) or 0)
        status = str(booking.get("status", "pending"))
        booking_payload = {
            **booking,
            "total_amount": total_amount,
            "paid_amount": paid_amount,
            "pending_amount": max(total_amount - paid_amount, 0),
            "time_label": ProviderBookingService._time_label(booking),
            "status_label": ProviderBookingService._status_label(status),
        }
        return ProviderBookingResponse(
            **booking_payload,
        )

    @staticmethod
    def _time_label(booking: dict) -> str:
        has_specific_schedule = bool(booking.get("has_specific_schedule", False))
        if not has_specific_schedule:
            return "Todo el dia"

        start_time = str(booking.get("start_time", "") or "")
        end_time = str(booking.get("end_time", "") or "")
        if start_time and end_time:
            return f"{start_time[:5]} - {end_time[:5]}"
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

    @staticmethod
    def _date_key(event_date: object) -> str:
        if isinstance(event_date, date):
            return event_date.isoformat()
        return str(event_date)
