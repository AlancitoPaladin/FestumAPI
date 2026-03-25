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
