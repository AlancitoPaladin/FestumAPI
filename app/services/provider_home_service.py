from datetime import date, datetime

from app.repositories.provider_booking_repository import ProviderBookingRepository
from app.repositories.provider_home_repository import ProviderHomeRepository
from app.repositories.provider_repository import ProviderRepository
from app.repositories.provider_service_repository import ProviderServiceRepository
from app.schemas.provider_home import (
    ProviderFeaturedServiceResponse,
    ProviderHomeDashboardResponse,
    ProviderNotificationListResponse,
    ProviderNotificationResponse,
    ProviderNotificationsBulkActionResponse,
    ProviderQuickStatsResponse,
)
from app.schemas.user import UserResponse
from app.services.provider_storage_service import ProviderStorageService
from app.services.service_catalog_projection_service import ServiceCatalogProjectionService


class ProviderHomeService:
    def __init__(self) -> None:
        self.provider_repository = ProviderRepository()
        self.home_repository = ProviderHomeRepository()
        self.booking_repository = ProviderBookingRepository()
        self.provider_service_repository = ProviderServiceRepository()
        self.storage_service = ProviderStorageService()
        self.projection_service = ServiceCatalogProjectionService()

    def get_dashboard(self, current_provider: UserResponse) -> ProviderHomeDashboardResponse:
        profile = self.provider_repository.get_by_provider_id(current_provider.id)
        services = self.provider_service_repository.list_by_provider(current_provider.id)
        business_name = ""
        avatar_asset = None
        avatar_url = ""
        if profile:
            business_name = str(profile.get("business_name", "") or "")
            avatar_key = self.storage_service.extract_storage_key(
                str(
                    profile.get("logo_storage_path")
                    or profile.get("logo_url")
                    or ""
                )
            )
            if avatar_key:
                avatar_asset = self.storage_service.build_signed_asset(avatar_key)
                avatar_url = avatar_asset.url

        active_services = [item for item in services if item.get("status") == "published"]
        featured_services = [
            self._build_featured_service(item)
            for item in active_services[:3]
        ]

        return ProviderHomeDashboardResponse(
            provider_id=current_provider.id,
            display_name=current_provider.first_name,
            business_name=business_name,
            avatar=avatar_asset,
            avatar_url=avatar_url,
            quick_stats=ProviderQuickStatsResponse(
                reservations_this_month=self.booking_repository.count_confirmed_for_month(
                    current_provider.id,
                    year=date.today().year,
                    month=date.today().month,
                ),
                active_services=len(active_services),
            ),
            featured_services=featured_services,
        )

    def _build_featured_service(self, item: dict) -> ProviderFeaturedServiceResponse:
        projected = self.projection_service.build_service_projection(item)

        return ProviderFeaturedServiceResponse(
            id=item["id"],
            title=str(item.get("name", "")),
            category=self._format_category(item.get("category")),
            status="Activo" if item.get("status") == "published" else "Inactivo",
            price_label=str(projected.get("price_label", "")),
            reservations=0,
            image=projected.get("image"),
            image_url=str(projected.get("image_url", "")),
        )

    def list_notifications(self, provider_id: str) -> ProviderNotificationListResponse:
        self._sync_automatic_notifications(provider_id)
        items = [
            ProviderNotificationResponse(**item)
            for item in self.home_repository.list_notifications(provider_id)
        ]
        unread_count = sum(1 for item in items if item.is_unread)
        return ProviderNotificationListResponse(items=items, unread_count=unread_count)

    def mark_notification_as_read(
        self, provider_id: str, notification_id: str
    ) -> ProviderNotificationResponse:
        notification = self.home_repository.mark_notification_as_read(provider_id, notification_id)
        return ProviderNotificationResponse(**notification)

    def mark_all_notifications_as_read(
        self, provider_id: str
    ) -> ProviderNotificationsBulkActionResponse:
        affected_count = self.home_repository.mark_all_notifications_as_read(provider_id)
        return ProviderNotificationsBulkActionResponse(affected_count=affected_count)

    def clear_notifications(self, provider_id: str) -> ProviderNotificationsBulkActionResponse:
        affected_count = self.home_repository.clear_notifications(provider_id)
        return ProviderNotificationsBulkActionResponse(affected_count=affected_count)

    @staticmethod
    def _format_category(category: str | None) -> str:
        if not category:
            return ""
        return str(category).replace("-", " ").replace("_", " ").title()

    def _sync_automatic_notifications(self, provider_id: str) -> None:
        bookings = self.booking_repository.list_by_provider(provider_id)
        today = date.today()

        desired_notifications: dict[str, dict] = {}
        for booking in bookings:
            for notification_id, payload in self._build_booking_notifications(booking, today).items():
                desired_notifications[notification_id] = payload

        existing_notifications = self.home_repository.list_notifications(provider_id)
        existing_auto_ids = {
            str(item.get("id", ""))
            for item in existing_notifications
            if str(item.get("source", "")) == "booking_automation"
        }

        for notification_id, payload in desired_notifications.items():
            self.home_repository.upsert_notification(provider_id, notification_id, payload)

        obsolete_ids = sorted(existing_auto_ids - set(desired_notifications))
        if obsolete_ids:
            self.home_repository.delete_notifications_by_ids(provider_id, obsolete_ids)

    def _build_booking_notifications(self, booking: dict, today: date) -> dict[str, dict]:
        event_date = self._parse_date(booking.get("event_date"))
        if event_date is None:
            return {}

        booking_id = str(booking.get("id", "") or "")
        service_id = str(booking.get("service_id", "") or "")
        product_id = str(booking.get("product_id", "") or "")
        customer_name = str(booking.get("customer_name", "") or "Cliente")
        product_name = str(booking.get("product_name", "") or "tu producto")
        status = str(booking.get("status", "") or "")
        source = str(booking.get("source", "") or "")
        days_until_event = (event_date - today).days
        pending_amount = max(
            float(booking.get("total_amount", 0) or 0) - float(booking.get("paid_amount", 0) or 0),
            0,
        )

        notifications: dict[str, dict] = {}
        date_label = self._format_date_label(event_date)

        if status in {"pending", "confirmed"} and self._is_recent_booking(booking, today):
            booking_created_title = (
                "Nueva reserva confirmada"
                if status == "confirmed"
                else "Nueva solicitud de reserva"
            )
            booking_created_subtitle = (
                f"{customer_name} aparto {product_name} para el {date_label}."
                if source != "manual"
                else f"Registraste a {customer_name} para {product_name} el {date_label}."
            )
            notifications[f"booking_created_{booking_id}"] = self._notification_payload(
                title=booking_created_title,
                subtitle=booking_created_subtitle,
                notification_type="booking_created",
                booking=booking,
            )

        if status != "confirmed":
            return notifications

        if days_until_event == 3:
            notifications[f"booking_reminder_3d_{booking_id}"] = self._notification_payload(
                title="Reserva cercana",
                subtitle=f"Faltan 3 dias para {product_name} con {customer_name} ({date_label}).",
                notification_type="booking_reminder",
                booking=booking,
            )

        if days_until_event == 1:
            notifications[f"booking_reminder_1d_{booking_id}"] = self._notification_payload(
                title="Reserva manana",
                subtitle=f"Manana atiendes a {customer_name} en {product_name}.",
                notification_type="booking_reminder",
                booking=booking,
            )

        if days_until_event == 0:
            notifications[f"booking_today_{booking_id}"] = self._notification_payload(
                title="Reserva de hoy",
                subtitle=f"Hoy tienes {product_name} con {customer_name}.",
                notification_type="booking_today",
                booking=booking,
            )

        if pending_amount > 0 and days_until_event in {0, 1}:
            notifications[f"booking_payment_due_{booking_id}"] = self._notification_payload(
                title="Pago pendiente por cobrar",
                subtitle=(
                    f"A {customer_name} le faltan {self._format_currency(pending_amount)} "
                    f"para liquidar {product_name}."
                ),
                notification_type="payment_due",
                booking=booking,
            )

        return notifications

    def _notification_payload(
        self,
        *,
        title: str,
        subtitle: str,
        notification_type: str,
        booking: dict,
    ) -> dict:
        return {
            "title": title,
            "subtitle": subtitle,
            "type": notification_type,
            "source": "booking_automation",
            "booking_id": str(booking.get("id", "") or ""),
            "service_id": str(booking.get("service_id", "") or ""),
            "product_id": str(booking.get("product_id", "") or ""),
            "event_date": self._date_key(booking.get("event_date")),
        }

    @staticmethod
    def _parse_date(value: object) -> date | None:
        if isinstance(value, date):
            return value
        if not value:
            return None
        normalized = str(value)
        if "T" in normalized:
            normalized = normalized.split("T", maxsplit=1)[0]
        try:
            return date.fromisoformat(normalized)
        except ValueError:
            return None

    @staticmethod
    def _parse_datetime(value: object) -> datetime | None:
        if isinstance(value, datetime):
            return value
        if not value:
            return None
        normalized = str(value).strip()
        if normalized.endswith("Z"):
            normalized = normalized.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None

    def _is_recent_booking(self, booking: dict, today: date) -> bool:
        created_at = self._parse_datetime(booking.get("created_at"))
        if created_at is None:
            return False
        created_date = created_at.date()
        days_since_created = (today - created_date).days
        return 0 <= days_since_created <= 7

    @staticmethod
    def _format_date_label(value: date) -> str:
        months = [
            "",
            "enero",
            "febrero",
            "marzo",
            "abril",
            "mayo",
            "junio",
            "julio",
            "agosto",
            "septiembre",
            "octubre",
            "noviembre",
            "diciembre",
        ]
        return f"{value.day} de {months[value.month]}"

    @staticmethod
    def _format_currency(amount: float) -> str:
        if amount.is_integer():
            return f"${int(amount):,} MXN"
        return f"${amount:,.2f} MXN"

    @staticmethod
    def _date_key(value: object) -> str:
        if isinstance(value, date):
            return value.isoformat()
        return str(value or "")
