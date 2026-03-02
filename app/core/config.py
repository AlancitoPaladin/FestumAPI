from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "Festum API"
    app_version: str = "1.0.0"
    api_v1_prefix: str = "/api/v1"
    environment: Literal["local", "staging", "production"] = "local"
    debug: bool = False
    jwt_secret_key: str = Field(default="change-this-in-production", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=60, alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    firebase_project_id: str | None = Field(default=None, alias="FIREBASE_PROJECT_ID")
    firebase_credentials_path: str | None = Field(
        default=None, alias="FIREBASE_CREDENTIALS_PATH"
    )
    firebase_database_url: str | None = Field(
        default=None, alias="FIREBASE_DATABASE_URL"
    )

    allowed_origins: str = Field(
        default="http://localhost,http://localhost:3000",
        alias="ALLOWED_ORIGINS",
    )

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("allowed_origins")
    @classmethod
    def normalize_allowed_origins(cls, value: str) -> str:
        return ",".join([item.strip() for item in value.split(",") if item.strip()])

    @property
    def allowed_origins_list(self) -> list[str]:
        return [item.strip() for item in self.allowed_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
