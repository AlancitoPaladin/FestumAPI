from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from app.core.config import BASE_DIR, get_settings
from app.core.exceptions import ApiError


class ProviderStorageService:
    allowed_content_types = {"image/webp", "image/png", "image/jpeg"}
    uploads_dir = BASE_DIR / "uploads"

    def upload_logo(self, provider_id: str, file: UploadFile) -> tuple[str, str]:
        storage_path = f"providers/{provider_id}/logo/logo.webp"
        return self._upload_file(file=file, storage_path=storage_path)

    def upload_photo(self, provider_id: str, file: UploadFile) -> tuple[str, str]:
        file_id = uuid4().hex
        storage_path = f"providers/{provider_id}/photos/{file_id}.webp"
        return self._upload_file(file=file, storage_path=storage_path)

    def upload_service_image(
        self,
        provider_id: str,
        service_id: str,
        file: UploadFile,
    ) -> tuple[str, str]:
        file_id = uuid4().hex
        storage_path = f"providers/{provider_id}/services/{service_id}/images/{file_id}.webp"
        return self._upload_file(file=file, storage_path=storage_path)

    def upload_product_image(
        self,
        provider_id: str,
        service_id: str,
        product_id: str,
        file: UploadFile,
    ) -> tuple[str, str]:
        file_id = uuid4().hex
        storage_path = (
            f"providers/{provider_id}/services/{service_id}/products/{product_id}/images/{file_id}.webp"
        )
        return self._upload_file(file=file, storage_path=storage_path)

    def _upload_file(self, file: UploadFile, storage_path: str) -> tuple[str, str]:
        self._validate_file(file)

        content = file.file.read()
        if not content:
            raise ApiError("Image file is empty")

        webp_content = self._convert_to_webp(content)
        local_path = self.uploads_dir / storage_path
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(webp_content)
        asset_url = self._build_asset_url(storage_path)
        return storage_path, asset_url

    def delete_file(self, storage_path: str) -> None:
        if not storage_path:
            return

        file_path = self.uploads_dir / storage_path
        if file_path.exists():
            file_path.unlink()
            self._cleanup_empty_directories(file_path.parent)

    def _validate_file(self, file: UploadFile) -> None:
        if not file.filename:
            raise ApiError("Image file name is required")
        if file.content_type not in self.allowed_content_types:
            raise ApiError("Only JPG, PNG or WEBP images are allowed")

    def _convert_to_webp(self, content: bytes) -> bytes:
        try:
            with Image.open(BytesIO(content)) as image:
                converted_image = image.copy()
                if converted_image.mode not in {"RGB", "RGBA"}:
                    converted_image = converted_image.convert("RGBA")

                output = BytesIO()
                converted_image.save(output, format="WEBP", quality=80, method=6)
                return output.getvalue()
        except UnidentifiedImageError as exc:
            raise ApiError("Invalid image file") from exc

    def _build_asset_url(self, storage_path: str) -> str:
        relative_path = f"/uploads/{storage_path.replace('\\', '/')}"
        uploads_base_url = get_settings().uploads_base_url
        if uploads_base_url:
            return f"{uploads_base_url}{relative_path}"
        return relative_path

    def _cleanup_empty_directories(self, directory: Path) -> None:
        current_directory = directory
        while current_directory != self.uploads_dir and current_directory.exists():
            if any(current_directory.iterdir()):
                return
            current_directory.rmdir()
            current_directory = current_directory.parent
