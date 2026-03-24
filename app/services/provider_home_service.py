from datetime import date

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


class ProviderHomeService:
    def __init__(self) -> None:
        self.provider_repository = ProviderRepository()
        self.home_repository = ProviderHomeRepository()
        self.booking_repository = ProviderBookingRepository()
        self.provider_service_repository = ProviderServiceRepository()

    def get_dashboard(self, current_provider: UserResponse) -> ProviderHomeDashboardResponse:
        profile = self.provider_repository.get_by_provider_id(current_provider.id)
        services = self.provider_service_repository.list_by_provider(current_provider.id)
        business_name = ""
        avatar_url = ""
        if profile:
            business_name = str(profile.get("business_name", "") or "")
            avatar_url = str(profile.get("logo_url", "") or "")

        active_services = [item for item in services if item.get("status") == "active"]
        featured_services = [
            ProviderFeaturedServiceResponse(
                id=item["id"],
                title=str(item.get("name", "")),
                category=self._format_category(item.get("category")),
                status="Activo" if item.get("status") == "active" else "Inactivo",
                price_label=self._build_price_label(item),
                reservations=0,
                image_url=str(
                    item.get("main_image_url")
                    or (item.get("image_urls") or [""])[0]
                ),
            )
            for item in active_services[:3]
        ]

        return ProviderHomeDashboardResponse(
            provider_id=current_provider.id,
            display_name=current_provider.first_name,
            business_name=business_name,
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

    def list_notifications(self, provider_id: str) -> ProviderNotificationListResponse:
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
        return str(category).replace("_", " ").title()

    @staticmethod
    def _build_price_label(service: dict) -> str:
        price = service.get("price")
        pricing_unit = str(service.get("pricing_unit") or "").strip()
        if price is None:
            return "Sin precio"

        if float(price).is_integer():
            price_text = str(int(price))
        else:
            price_text = f"{float(price):.2f}".rstrip("0").rstrip(".")

        if pricing_unit:
            return f"${price_text} {pricing_unit}"
        return f"${price_text}"
