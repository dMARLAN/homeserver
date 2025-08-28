from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

from pgs_db.config import db_config


class APIConfig(BaseSettings):
    """API configuration settings for the photography server."""

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    workers: int = 1

    # Application settings
    title: str = "Photography Server API"
    description: str = "API for serving photography portfolio images and metadata"
    version: str = "1.0.0"
    environment: Literal["development", "production", "test"] = "development"

    # CORS settings
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    cors_allow_headers: list[str] = ["*"]

    # File serving settings
    max_file_size_mb: int = 50
    allowed_image_types: set[str] = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/bmp", "image/tiff"}

    # API settings
    api_v1_prefix: str = "/api/v1"
    enable_docs: bool = True
    enable_redoc: bool = True

    # Logging settings
    log_level: str = "INFO"
    enable_access_logs: bool = True

    model_config = SettingsConfigDict(env_prefix="API_", case_sensitive=False)

    @property
    def storage_path(self) -> Path:
        """Get the photos storage path from database configuration."""
        return db_config.photos_base_path


# Global configuration instance
api_config = APIConfig()


def get_api_config() -> APIConfig:
    """Get the API configuration instance."""
    return api_config
