import os
from pathlib import Path
from typing import Literal


class DatabaseConfig:
    """Database configuration settings for the photography server."""

    def __init__(self) -> None:
        # Database connection settings
        self.db_host = os.getenv("DB_HOST", "localhost")
        self.db_port = int(os.getenv("DB_PORT", "5432"))
        self.db_name = os.getenv("DB_NAME", "photography_server")
        self.db_user = os.getenv("DB_USER", "postgres")
        self.db_password = os.getenv("DB_PASSWORD", "postgres")

        # Connection pool settings
        self.pool_size = int(os.getenv("DB_POOL_SIZE", "10"))
        self.max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "20"))
        self.pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", "30"))
        self.pool_recycle = int(os.getenv("DB_POOL_RECYCLE", "3600"))

        # Application settings
        self.echo_sql = os.getenv("DB_ECHO_SQL", "false").lower() == "true"
        env_value = os.getenv("ENVIRONMENT", "development")
        if env_value not in ("development", "production", "test"):
            env_value = "development"
        self.environment: Literal["development", "production", "test"] = env_value

        # Storage path settings
        self.photos_base_path = self._get_photos_path()

    def _get_photos_path(self) -> Path:
        """Get the photos storage path based on environment."""
        explicit_path = os.getenv("PHOTOS_BASE_PATH")
        if explicit_path:
            return Path(explicit_path)

        if self.environment == "production":
            return Path("/photoserver/photos")
        else:
            project_root = Path(__file__).parent.parent.parent.parent.parent
            return project_root / "photos"

    @property
    def database_url(self) -> str:
        """Construct the async PostgreSQL database URL."""
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def sync_database_url(self) -> str:
        """Construct the sync PostgreSQL database URL for Alembic migrations."""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


# Global configuration instance
db_config = DatabaseConfig()
