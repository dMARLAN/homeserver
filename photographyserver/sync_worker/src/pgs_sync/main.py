"""Application entry point for the sync worker."""

import asyncio
import logging

from pgs_db.database import db_manager
from pgs_sync.config import sync_config
from pgs_sync.worker import SyncWorker


def setup_logging() -> None:
    """Configure logging for the application."""
    logging.basicConfig(
        level=getattr(logging, sync_config.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


async def main() -> None:
    """Main application entry point."""
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Starting PGS Sync Worker")
    logger.info(f"Photos directory: {sync_config.photos_base_path}")
    logger.info(f"Health check port: {sync_config.health_check_port}")

    db_manager.initialize()

    try:
        await SyncWorker().start()
    finally:
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
