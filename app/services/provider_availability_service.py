from datetime import date

from app.core.exceptions import ResourceNotFoundError
from app.repositories.provider_availability_repository import ProviderAvailabilityRepository
from app.repositories.provider_product_repository import ProviderProductRepository
from app.schemas.provider_availability import (
    ProviderAvailabilityBookingSummary,
    ProviderAvailabilityDayResponse,
    ProviderAvailabilityMonthResponse,
    ProviderAvailabilityStatusResponse,
)


class ProviderAvailabilityService:
    def __init__(self) -> None:
        self.product_repository = ProviderProductRepository()
        self.repository = ProviderAvailabilityRepository()

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
                booking = ProviderAvailabilityBookingSummary(**booking_data)

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

    def block_date(self, provider_id: str, product_id: str, target_date: date) -> ProviderAvailabilityStatusResponse:
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

    @staticmethod
    def _days_in_month(year: int, month: int) -> int:
        if month == 12:
            return 31
        return (date(year, month + 1, 1) - date(year, month, 1)).days
