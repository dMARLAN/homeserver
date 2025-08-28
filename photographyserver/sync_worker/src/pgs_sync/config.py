"""Configuration management for the sync worker."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class SyncConfig(BaseSettings):
    """Configuration for the sync worker."""

    model_config = SettingsConfigDict(env_prefix="SYNC_", env_file=".env")

    # Database configuration (inherited from pgs_db config)
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "photography_server"
    db_user: str = "postgres"
    db_password: str = "postgres"

    # Storage configuration
    photos_base_path: Path = Path("/app/photos")
    supported_extensions: set[str] = {
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".bmp",
        ".tiff",
        ".tif",
        ".raw",
        ".cr2",
        ".nef",
        ".arw",
        ".dng",
        ".orf",
        ".rw2",
        ".pef",
        ".srw",
    }

    # Worker configuration
    initial_sync_on_startup: bool = True
    periodic_sync_interval: int = 3600  # 1 hour in seconds
    event_debounce_delay: float = 2.0  # 2 seconds
    max_batch_size: int = 100
    retry_attempts: int = 3
    retry_delay: float = 5.0

    # Health monitoring
    health_check_port: int = 8001
    health_check_host: str = "0.0.0.0"
    log_level: str = "INFO"
    access_log: bool = True


# Global configuration instance
sync_config = SyncConfig()
