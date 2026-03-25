from typing import Any

from app.schemas.provider_product import PRODUCT_DETAIL_FIELDS
from app.services.provider_storage_service import ProviderStorageService


class ProductCatalogProjectionService:
    def __init__(self) -> None:
        self.storage_service = ProviderStorageService()

    def build_product_projection(self, product: dict) -> dict:
        unit_price_cents = self._resolve_unit_price_cents(product)
        images = self._resolve_signed_images(product)
        primary_image = next((item for item in images if item["is_main"]), images[0] if images else None)
        details = self._build_details(product)
        inclusions = self._build_boolean_map(product.get("inclusions"))
        policies = self._build_boolean_map(product.get("policies"))

        return {
            **product,
            "unit_price_cents": unit_price_cents,
            "price_label": self._build_price_label(unit_price_cents, product),
            "details": details,
            "inclusions": inclusions,
            "policies": policies,
            "image": primary_image,
            "images": images,
            "main_image_url": primary_image["url"] if primary_image else "",
            "image_urls": [item["url"] for item in images],
        }

    @staticmethod
    def _resolve_unit_price_cents(product: dict) -> int:
        raw_price = product.get("price")
        if raw_price is None:
            return 0
        try:
            price_value = float(raw_price)
        except (TypeError, ValueError):
            return 0
        if price_value <= 0:
            return 0
        return int(round(price_value * 100))

    def _resolve_signed_images(self, product: dict) -> list[dict]:
        raw_keys = list(product.get("image_storage_paths") or [])
        if not raw_keys:
            image_urls = list(product.get("image_urls") or [])
            raw_keys = [
                key
                for key in (
                    self.storage_service.extract_storage_key(image_url) for image_url in image_urls
                )
                if key
            ]

        normalized_keys: list[str] = []
        for raw_key in raw_keys:
            key = self.storage_service.extract_storage_key(str(raw_key))
            if key and key not in normalized_keys:
                normalized_keys.append(key)

        main_key = self.storage_service.extract_storage_key(
            str(product.get("main_image_storage_path") or product.get("main_image_url") or "")
        )

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

    @staticmethod
    def _build_price_label(unit_price_cents: int, product: dict) -> str:
        if unit_price_cents <= 0:
            return "Cotiza"

        amount = unit_price_cents / 100
        if unit_price_cents % 100 == 0:
            formatted_amount = f"${amount:,.0f}"
        else:
            formatted_amount = f"${amount:,.2f}"

        pricing_unit = str(product.get("pricing_unit") or "").strip()
        if pricing_unit:
            return f"{formatted_amount} {pricing_unit}"
        return formatted_amount

    @staticmethod
    def _build_boolean_map(value: Any) -> dict[str, bool]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return {
                " ".join(str(key).split()).strip(): bool(item)
                for key, item in value.items()
                if " ".join(str(key).split()).strip()
            }
        if isinstance(value, list):
            return {
                " ".join(str(item).split()).strip(): True
                for item in value
                if " ".join(str(item).split()).strip()
            }
        normalized = " ".join(str(value).split()).strip()
        return {normalized: True} if normalized else {}

    @staticmethod
    def _build_details(product: dict) -> dict[str, Any]:
        details = {}
        raw_details = product.get("details")
        if isinstance(raw_details, dict):
            details.update(raw_details)

        for field_name in PRODUCT_DETAIL_FIELDS:
            value = product.get(field_name)
            if value is None or value == "":
                continue
            details.setdefault(field_name, value)

        return details
