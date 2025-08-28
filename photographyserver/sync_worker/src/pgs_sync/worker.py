"""Main sync worker that orchestrates file watching and database synchronization."""

import asyncio
import logging
import signal
import time
from queue import Empty, Queue
from types import FrameType

from sqlalchemy.ext.asyncio import AsyncSession  # type: ignore[import-untyped]

from pgs_db.database import db_manager
from pgs_sync.config import sync_config
from pgs_sync.health import HealthMonitor
from pgs_sync.sync_engine import SyncEngine
from pgs_sync.sync_types import FileEvent
from pgs_sync.watcher import PhotoDirectoryWatcher

logger = logging.getLogger(__name__)


class SyncWorker:
    """Main sync worker that coordinates all sync operations."""

    def __init__(self) -> None:
        self.config = sync_config
        self.db_manager = db_manager
        self.event_queue: Queue[FileEvent] = Queue()
        self.watcher = PhotoDirectoryWatcher(self.config.photos_base_path, self.event_queue)
        self.sync_engine = SyncEngine(self._get_db_session)

        # Initialize health monitor
        self.health_monitor = HealthMonitor()

        self.running = False
        self._setup_signal_handlers()

    def _get_db_session(self) -> AsyncSession:
        """Get a database session from the session factory."""
        return self.db_manager.session_factory()

    def _setup_signal_handlers(self) -> None:
        """Set up graceful shutdown signal handlers."""

        def signal_handler(signum: int, frame: FrameType | None) -> None:
            logger.info(f"Received signal {signum}, shutting down gracefully...")
            self.running = False

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

    async def start(self) -> None:
        """Start the sync worker and all its components."""
        logger.info("Starting sync worker")
        self.running = True

        try:
            if self.config.initial_sync_on_startup:
                logger.info("Performing initial sync on startup")
                await self.sync_engine.perform_initial_sync()

            await self.watcher.start_watching()

            health_task = asyncio.create_task(self._start_health_server())
            event_task = asyncio.create_task(self._process_events())
            periodic_task = asyncio.create_task(self._periodic_sync())

            await asyncio.gather(health_task, event_task, periodic_task, return_exceptions=True)

        except Exception as e:
            logger.error(f"Error in sync worker: {e}")
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        """Gracefully shutdown the sync worker."""
        logger.info("Shutting down sync worker")
        self.running = False

        await self.watcher.stop_watching()

        logger.info("Sync worker shutdown complete")

    async def _start_health_server(self) -> None:
        """Start the health monitoring HTTP server."""
        import uvicorn

        config = uvicorn.Config(
            app=self.health_monitor.get_app(),
            host=self.config.health_check_host,
            port=self.config.health_check_port,
            log_level=self.config.log_level.lower(),
            access_log=self.config.access_log,
        )
        server = uvicorn.Server(config)
        await server.serve()

    async def _process_events(self) -> None:
        """Process file system events from the queue."""
        logger.info("Starting event processing loop")

        while self.running:
            try:
                events_batch = await self._collect_event_batch()

                if not events_batch:
                    await asyncio.sleep(0.1)
                    continue

                await self._process_event_batch_with_retry(events_batch)

            except Exception as e:
                logger.error(f"Error in event processing loop: {e}")
                await asyncio.sleep(1)

    async def _collect_event_batch(self) -> list[FileEvent]:
        """Collect events from the queue into a batch for processing.

        Returns:
            List of FileEvent objects to process
        """
        events_batch: list[FileEvent] = []
        batch_timeout = 1.0  # 1 second timeout for batching
        batch_start_time = time.time()

        while (
            len(events_batch) < self.config.max_batch_size
            and time.time() - batch_start_time < batch_timeout
            and self.running
        ):

            try:
                # Use a small timeout to allow batching while being responsive
                event = self.event_queue.get(timeout=0.1)
                events_batch.append(event)
                self.event_queue.task_done()

                # If this is the first event in the batch, apply to debounce delay
                if len(events_batch) == 1:
                    await asyncio.sleep(self.config.event_debounce_delay)

            except Empty:
                # No more events available, break if we have some events
                if events_batch:
                    break
                # Otherwise, continue waiting for events
                continue

        if events_batch:
            logger.debug(f"Collected batch of {len(events_batch)} events for processing")

        return events_batch

    async def _process_event_batch_with_retry(self, events: list[FileEvent]) -> None:
        """Process a batch of events with retry logic.

        Args:
            events: List of events to process
        """
        last_exception = None
        start_time = time.time()

        for attempt in range(self.config.retry_attempts):
            try:
                # Process the entire batch
                await self.sync_engine.process_event_batch(events)

                # Calculate processing time
                processing_time_ms = (time.time() - start_time) * 1000

                logger.info(f"Successfully processed batch of {len(events)} events in {processing_time_ms:.1f}ms")
                return

            except Exception as e:
                last_exception = e
                attempt_num = attempt + 1

                if attempt_num < self.config.retry_attempts:
                    logger.warning(
                        f"Failed to process event batch (attempt {attempt_num}/{self.config.retry_attempts}): {e}. "
                        f"Retrying in {self.config.retry_delay} seconds..."
                    )
                    await asyncio.sleep(self.config.retry_delay)
                else:
                    logger.error(f"Failed to process event batch after {self.config.retry_attempts} attempts: {e}")

        # Re-raise the last exception after all retries failed
        if last_exception:
            raise last_exception

    async def _periodic_sync(self) -> None:
        """Perform periodic full syncs as fallback."""
        logger.info("Starting periodic sync loop")

        while self.running:
            try:
                await asyncio.sleep(self.config.periodic_sync_interval)
                if self.running:
                    await self.sync_engine.perform_periodic_sync()

            except Exception as e:
                logger.error(f"Error in periodic sync: {e}")
