import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from pgs_api.config import api_config
from pgs_api.routes import photos, categories
from pgs_db.database import db_manager

# Configure logging
logging.basicConfig(
    level=getattr(logging, api_config.log_level.upper()), format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown tasks."""
    logger.info("Starting Photography Server API")

    db_manager.initialize()

    await db_manager.create_tables()

    api_config.storage_path.mkdir(exist_ok=True)

    logger.info(f"Storage path: {api_config.storage_path.absolute()}")
    logger.info(f"API running on {api_config.host}:{api_config.port}")

    yield

    logger.info("Shutting down Photography Server API")
    await db_manager.close()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title=api_config.title,
        description=api_config.description,
        version=api_config.version,
        docs_url="/docs" if api_config.enable_docs else None,
        redoc_url="/redoc" if api_config.enable_redoc else None,
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=api_config.cors_origins,
        allow_credentials=api_config.cors_allow_credentials,
        allow_methods=api_config.cors_allow_methods,
        allow_headers=api_config.cors_allow_headers,
    )

    # Mount static files for direct image serving
    if api_config.storage_path.exists():
        app.mount("/static", StaticFiles(directory=api_config.storage_path), name="static")

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    # Health check endpoint
    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint to verify API and database connectivity."""
        db_health = await db_manager.health_check()
        return {"status": db_health["status"]}

    # Include API routes with versioning
    include_api_routes(app)

    return app


def include_api_routes(app: FastAPI) -> None:
    """Include all API routes with proper versioning."""

    # Include all API v1 route modules
    app.include_router(photos.router, prefix=api_config.api_v1_prefix)
    app.include_router(categories.router, prefix=api_config.api_v1_prefix)


# Create the application instance
app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=api_config.host,
        port=api_config.port,
        reload=api_config.reload,
        workers=api_config.workers if not api_config.reload else None,
        access_log=api_config.enable_access_logs,
        log_level=api_config.log_level.lower(),
    )
