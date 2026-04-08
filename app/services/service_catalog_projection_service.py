from collections.abc import Callable
from time import perf_counter

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

    def build_service_projection(
        self,
        service: dict,
        on_image_error: Callable[[dict], None] | None = None,
        *,
        image_mode: str = "full",
        include_all_images: bool = True,
    ) -> dict:
        unit_price_cents = self._resolve_unit_price_cents(service)
        price_label = self._resolve_price_label(service, unit_price_cents)
        images, image_sign_ms, images_signed_count = self._resolve_signed_images(
            service,
            on_image_error=on_image_error,
            image_mode=image_mode,
            include_all_images=include_all_images,
        )
        image = next((item for item in images if item["is_main"]), images[0] if images else None)
        legacy_image_url = str(
            service.get("image_url")
            or service.get("main_image_url")
            or ""
        )
        resolved_image_url = image["url"] if image else legacy_image_url
        return {
            **service,
            "unit_price_cents": unit_price_cents,
            "price_label": price_label,
            "badge": self._build_badge(service),
            "image": image,
            "main_image": image,
            "image_url": resolved_image_url,
            "main_image_url": resolved_image_url,
            "image_urls": [item["url"] for item in images] or list(service.get("image_urls") or []),
            "images": images,
            "_image_sign_ms": image_sign_ms,
            "_images_signed_count": images_signed_count,
        }

    def _resolve_unit_price_cents(self, service: dict) -> int:
        persisted_price = service.get("unit_price_cents")
        if isinstance(persisted_price, int) and persisted_price >= 0:
            return persisted_price
        if isinstance(persisted_price, str):
            stripped = persisted_price.strip()
            if stripped.isdigit():
                return int(stripped)

        provider_id = str(service.get("provider_id") or "")
        service_id = str(service.get("id") or "")
        if not provider_id or not service_id:
            return 0

        derived_price = self.product_repository.get_min_published_price_cents(provider_id, service_id)
        if derived_price is None:
            return 0
        return derived_price

    def _resolve_price_label(self, service: dict, unit_price_cents: int) -> str:
        persisted_label = str(service.get("price_label") or "").strip()
        if persisted_label:
            return persisted_label
        return self._build_price_label(unit_price_cents)

    def _resolve_signed_images(
        self,
        service: dict,
        on_image_error: Callable[[dict], None] | None = None,
        *,
        image_mode: str = "full",
        include_all_images: bool = True,
    ) -> tuple[list[dict], float, int]:
        main_key = self.storage_service.extract_storage_key(str(service.get("main_image_key") or ""))
        normalized_keys = self._normalize_ordered_image_keys(
            image_keys=list(service.get("image_keys") or []),
            main_key=main_key,
        )

        images: list[dict] = []
        image_sign_ms = 0.0
        target_keys = normalized_keys
        if not include_all_images and normalized_keys:
            primary = main_key if main_key and main_key in normalized_keys else normalized_keys[0]
            target_keys = [primary]

        for index, key in enumerate(target_keys):
            try:
                sign_start = perf_counter()
                if image_mode == "lite":
                    signed_asset = self.storage_service.build_signed_asset_lite(
                        key,
                        preferred_variant="thumb",
                    )
                else:
                    signed_asset = self.storage_service.build_signed_asset(key)
                image_sign_ms += (perf_counter() - sign_start) * 1000
                images.append(
                    {
                        **signed_asset.model_dump(mode="json"),
                        "is_main": key == main_key if main_key else index == 0,
                    }
                )
            except Exception as exc:
                if on_image_error:
                    on_image_error(
                        {
                            "service_id": str(service.get("id") or ""),
                            "category": str(service.get("category") or ""),
                            "image_key": key,
                            "error_type": type(exc).__name__,
                            "error_message": str(exc),
                        }
                    )

        if images and not any(item["is_main"] for item in images):
            images[0]["is_main"] = True
        return images, image_sign_ms, len(images)

    def _normalize_ordered_image_keys(self, *, image_keys: list, main_key: str | None) -> list[str]:
        ordered: list[str] = []
        seen: set[str] = set()

        def _push(raw: str | None) -> None:
            key = self.storage_service.extract_storage_key(str(raw or ""))
            if not key or key in seen:
                return
            seen.add(key)
            ordered.append(key)

        _push(main_key)
        for raw in image_keys:
            _push(str(raw))
        return ordered

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
