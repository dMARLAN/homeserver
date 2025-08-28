"""Simple health check server for the sync worker."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.responses import JSONResponse


class HealthMonitor:
    """Simple health monitor for the sync worker."""

    def __init__(self) -> None:
        self.app = FastAPI(title="PGS Sync Worker Health Monitor")
        self.start_time = datetime.now(timezone.utc)
        self._setup_routes()

    def _setup_routes(self) -> None:
        """Set up health check endpoint."""

        @self.app.get("/health")
        async def health_check() -> JSONResponse:
            """Basic health check endpoint."""
            return JSONResponse(content={"status": "healthy"})

    def get_app(self) -> FastAPI:
        """Get the FastAPI application for the health monitor."""
        return self.app
