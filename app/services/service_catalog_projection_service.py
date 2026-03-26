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
        images = self._resolve_signed_images(service)
        image = next((item for item in images if item["is_main"]), images[0] if images else None)
        return {
            **service,
            "unit_price_cents": unit_price_cents,
            "price_label": self._build_price_label(unit_price_cents),
            "badge": self._build_badge(service),
            "image": image,
            "main_image": image,
            "image_url": image["url"] if image else "",
            "main_image_url": image["url"] if image else "",
            "image_urls": [item["url"] for item in images],
            "images": images,
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

    def _resolve_signed_images(self, service: dict) -> list[dict]:
        raw_keys = list(service.get("image_keys") or [])
        if not raw_keys:
            main_key = str(service.get("main_image_key") or "")
            if main_key:
                raw_keys = [main_key]

        normalized_keys: list[str] = []
        for raw_key in raw_keys:
            key = self.storage_service.extract_storage_key(str(raw_key))
            if key and key not in normalized_keys:
                normalized_keys.append(key)

        main_key = self.storage_service.extract_storage_key(str(service.get("main_image_key") or ""))

        images: list[dict] = []
        for index, key in enumerate(normalized_keys):
            signed_asset = self.storage_service.build_signed_asset(key)
            images.append(
                {
                    "key": signed_asset.key,
                    "url": signed_asset.url,
                    "expires_at": signed_asset.expires_at,
                    "is_main": key == main_key if main_key else index == 0,
                }
            )

        if images and not any(item["is_main"] for item in images):
            images[0]["is_main"] = True
        return images

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
