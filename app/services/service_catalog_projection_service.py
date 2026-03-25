from app.repositories.provider_product_repository import ProviderProductRepository
from app.services.provider_storage_service import ProviderStorageService


class ServiceCatalogProjectionService:
    _badge_by_category = {
        "dj": "DJ",
        "photography": "Fotografia",
        "entertainment": "Entretenimiento",
        "banquet": "Banquetes",
        "furniture": "Mobiliario",
        "equipment": "Equipo",
        "venue": "Salon",
        "decoration": "Decoracion",
        "salones-sociales": "Salones",
        "mobiliario": "Mobiliario",
        "banquetes": "Banquetes",
    }

    def __init__(self) -> None:
        self.product_repository = ProviderProductRepository()
        self.storage_service = ProviderStorageService()

    def build_service_projection(self, service: dict) -> dict:
        unit_price_cents = self._resolve_unit_price_cents(service)
        image = self._resolve_primary_image(service)
        return {
            **service,
            "unit_price_cents": unit_price_cents,
            "price_label": self._build_price_label(unit_price_cents),
            "badge": self._build_badge(service),
            "image": image,
            "image_url": image.url if image else "",
        }

    def _resolve_unit_price_cents(self, service: dict) -> int:
        provider_id = str(service.get("provider_id") or "")
        service_id = str(service.get("id") or "")
        if not provider_id or not service_id:
            return 0

        derived_price = self.product_repository.get_min_published_price_cents(provider_id, service_id)
        if derived_price is None:
            return 0
        return derived_price

    def _resolve_primary_image(self, service: dict):
        image_source = str(service.get("main_image_key") or "")
        if not image_source:
            image_keys = list(service.get("image_keys") or [])
            image_source = str(image_keys[0]) if image_keys else ""

        image_key = self.storage_service.extract_storage_key(image_source)
        if not image_key:
            return None
        return self.storage_service.build_signed_asset(image_key)

    def _build_badge(self, service: dict) -> str:
        category = str(service.get("category") or "")
        return self._badge_by_category.get(category, "Servicio")

    @staticmethod
    def _build_price_label(unit_price_cents: int) -> str:
        if unit_price_cents <= 0:
            return "Cotiza"

        amount = unit_price_cents / 100
        if unit_price_cents % 100 == 0:
            formatted_amount = f"${amount:,.0f} MXN"
        else:
            formatted_amount = f"${amount:,.2f} MXN"
        return f"Desde {formatted_amount}"
