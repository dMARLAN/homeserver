"""Tests for health monitoring functionality."""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from pgs_sync.health import HealthMonitor


class TestHealthMonitor:
    """Test the HealthMonitor class."""

    @pytest.fixture
    def health_monitor(self) -> HealthMonitor:
        """Create a HealthMonitor for testing."""
        return HealthMonitor()

    @pytest.fixture
    def test_client(self, health_monitor: HealthMonitor) -> TestClient:
        """Create a test client for the health monitor app."""
        return TestClient(health_monitor.get_app())

    @pytest.mark.unit
    def test_initialization(self, health_monitor: HealthMonitor):
        """Test that HealthMonitor is initialized correctly."""
        assert health_monitor.app is not None
        assert health_monitor.start_time is not None
        assert isinstance(health_monitor.start_time, datetime)
        assert health_monitor.start_time.tzinfo == timezone.utc

    @pytest.mark.unit
    def test_health_endpoint(self, test_client: TestClient):
        """Test health endpoint returns healthy status."""
        response = test_client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"

    @pytest.mark.unit
    def test_get_app(self, health_monitor: HealthMonitor):
        """Test getting the FastAPI application."""
        app = health_monitor.get_app()

        assert app is health_monitor.app
        assert app.title == "PGS Sync Worker Health Monitor"
