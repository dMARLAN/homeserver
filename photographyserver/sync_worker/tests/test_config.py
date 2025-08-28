"""Tests for the sync configuration module."""

from pathlib import Path

import pytest

from pgs_sync.config import SyncConfig


class TestSyncConfig:
    """Test the SyncConfig class."""

    @pytest.mark.unit
    def test_default_values(self):
        """Test that default configuration values are set correctly."""
        config = SyncConfig()

        # Database defaults
        assert config.db_host == "localhost"
        assert config.db_port == 5432
        assert config.db_name == "photography_server"
        assert config.db_user == "postgres"
        assert config.db_password == "postgres"

        # Storage defaults
        assert config.photos_base_path == Path("/app/photos")
        assert ".jpg" in config.supported_extensions
        assert ".jpeg" in config.supported_extensions
        assert ".png" in config.supported_extensions
        assert ".gif" in config.supported_extensions
        assert ".webp" in config.supported_extensions
        assert ".raw" in config.supported_extensions

        # Worker defaults
        assert config.initial_sync_on_startup is True
        assert config.periodic_sync_interval == 3600
        assert config.event_debounce_delay == 2.0
        assert config.max_batch_size == 100
        assert config.retry_attempts == 3
        assert config.retry_delay == 5.0

        # Health monitoring defaults
        assert config.health_check_port == 8001
        assert config.health_check_host == "0.0.0.0"
        assert config.log_level == "INFO"

    @pytest.mark.unit
    def test_environment_variable_override(self, monkeypatch):
        """Test that environment variables override default values."""
        # Set environment variables with SYNC_ prefix
        monkeypatch.setenv("SYNC_DB_HOST", "custom_host")
        monkeypatch.setenv("SYNC_DB_PORT", "3306")
        monkeypatch.setenv("SYNC_DB_NAME", "custom_db")
        monkeypatch.setenv("SYNC_DB_USER", "custom_user")
        monkeypatch.setenv("SYNC_DB_PASSWORD", "custom_password")
        monkeypatch.setenv("SYNC_PHOTOS_BASE_PATH", "/custom/photos")
        monkeypatch.setenv("SYNC_INITIAL_SYNC_ON_STARTUP", "false")
        monkeypatch.setenv("SYNC_PERIODIC_SYNC_INTERVAL", "7200")
        monkeypatch.setenv("SYNC_EVENT_DEBOUNCE_DELAY", "3.5")
        monkeypatch.setenv("SYNC_MAX_BATCH_SIZE", "50")
        monkeypatch.setenv("SYNC_RETRY_ATTEMPTS", "5")
        monkeypatch.setenv("SYNC_RETRY_DELAY", "10.0")
        monkeypatch.setenv("SYNC_HEALTH_CHECK_PORT", "9001")
        monkeypatch.setenv("SYNC_HEALTH_CHECK_HOST", "127.0.0.1")
        monkeypatch.setenv("SYNC_LOG_LEVEL", "DEBUG")

        config = SyncConfig()

        # Check that environment variables were used
        assert config.db_host == "custom_host"
        assert config.db_port == 3306
        assert config.db_name == "custom_db"
        assert config.db_user == "custom_user"
        assert config.db_password == "custom_password"
        assert config.photos_base_path == Path("/custom/photos")
        assert config.initial_sync_on_startup is False
        assert config.periodic_sync_interval == 7200
        assert config.event_debounce_delay == 3.5
        assert config.max_batch_size == 50
        assert config.retry_attempts == 5
        assert config.retry_delay == 10.0
        assert config.health_check_port == 9001
        assert config.health_check_host == "127.0.0.1"
        assert config.log_level == "DEBUG"

    @pytest.mark.unit
    def test_path_type_conversion(self, monkeypatch):
        """Test that string paths are converted to Path objects."""
        monkeypatch.setenv("SYNC_PHOTOS_BASE_PATH", "/test/path/string")

        config = SyncConfig()

        assert isinstance(config.photos_base_path, Path)
        assert config.photos_base_path == Path("/test/path/string")

    @pytest.mark.unit
    def test_boolean_conversion(self, monkeypatch):
        """Test that string boolean values are converted correctly."""
        # Test various boolean representations
        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("0", False),
            ("no", False),
        ]

        for string_value, expected_bool in test_cases:
            monkeypatch.setenv("SYNC_INITIAL_SYNC_ON_STARTUP", string_value)
            config = SyncConfig()
            assert config.initial_sync_on_startup is expected_bool

    @pytest.mark.unit
    def test_supported_extensions_immutable(self):
        """Test that supported extensions is a set and contains expected formats."""
        config = SyncConfig()

        # Check it's a set
        assert isinstance(config.supported_extensions, set)

        # Check common image formats are included
        expected_extensions = {
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

        for ext in expected_extensions:
            assert ext in config.supported_extensions

    @pytest.mark.unit
    def test_numeric_type_conversion(self, monkeypatch):
        """Test that string numeric values are converted to correct types."""
        monkeypatch.setenv("SYNC_DB_PORT", "5433")
        monkeypatch.setenv("SYNC_PERIODIC_SYNC_INTERVAL", "1800")
        monkeypatch.setenv("SYNC_EVENT_DEBOUNCE_DELAY", "1.5")
        monkeypatch.setenv("SYNC_MAX_BATCH_SIZE", "200")
        monkeypatch.setenv("SYNC_RETRY_ATTEMPTS", "2")
        monkeypatch.setenv("SYNC_RETRY_DELAY", "3.0")

        config = SyncConfig()

        # Check integer conversions
        assert isinstance(config.db_port, int)
        assert config.db_port == 5433
        assert isinstance(config.periodic_sync_interval, int)
        assert config.periodic_sync_interval == 1800
        assert isinstance(config.max_batch_size, int)
        assert config.max_batch_size == 200
        assert isinstance(config.retry_attempts, int)
        assert config.retry_attempts == 2

        # Check float conversions
        assert isinstance(config.event_debounce_delay, float)
        assert config.event_debounce_delay == 1.5
        assert isinstance(config.retry_delay, float)
        assert config.retry_delay == 3.0

    @pytest.mark.unit
    def test_invalid_numeric_values(self, monkeypatch):
        """Test behavior with invalid numeric environment variables."""
        # Set invalid numeric values
        monkeypatch.setenv("SYNC_DB_PORT", "invalid")

        # Should raise validation error
        with pytest.raises(Exception):  # Pydantic will raise validation error
            SyncConfig()

    @pytest.mark.unit
    def test_global_config_instance(self):
        """Test that the global sync_config instance is accessible."""
        from pgs_sync.config import sync_config

        assert isinstance(sync_config, SyncConfig)
        assert sync_config.db_host is not None
        assert sync_config.photos_base_path is not None

    @pytest.mark.unit
    def test_config_model_validation(self):
        """Test that Pydantic model validation works correctly."""
        # Test that we can create config with valid values
        config = SyncConfig(
            db_port=5432,
            photos_base_path=Path("/valid/path"),
            event_debounce_delay=1.0,
            max_batch_size=50,
        )

        assert config.db_port == 5432
        assert config.photos_base_path == Path("/valid/path")
        assert config.event_debounce_delay == 1.0
        assert config.max_batch_size == 50

    @pytest.mark.unit
    def test_env_prefix_isolation(self, monkeypatch):
        """Test that only SYNC_ prefixed variables are used."""
        # Set variables without SYNC_ prefix
        monkeypatch.setenv("DB_HOST", "should_not_be_used")
        monkeypatch.setenv("DB_PORT", "9999")

        # Set variable with SYNC_ prefix
        monkeypatch.setenv("SYNC_DB_HOST", "should_be_used")

        config = SyncConfig()

        # Only SYNC_ prefixed variable should be used
        assert config.db_host == "should_be_used"
        assert config.db_port == 5432  # Should use default, not the non-prefixed value
