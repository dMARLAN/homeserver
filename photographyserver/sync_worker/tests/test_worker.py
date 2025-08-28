"""Tests for the main sync worker functionality."""

import signal
from datetime import datetime, timezone
from pathlib import Path
from queue import Queue
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pgs_sync.sync_types import FileEvent, FileEventType, SyncStats
from pgs_sync.worker import SyncWorker


class TestSyncWorker:
    """Test the SyncWorker class."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for SyncWorker."""
        with (
            patch("pgs_sync.worker.db_manager") as mock_db_manager,
            patch("pgs_sync.worker.sync_config") as mock_config,
            patch("pgs_sync.worker.PhotoDirectoryWatcher") as mock_watcher_class,
            patch("pgs_sync.worker.SyncEngine") as mock_engine_class,
            patch("pgs_sync.worker.HealthMonitor") as mock_health_class,
        ):

            # Configure mocks
            mock_config.photos_base_path = "/test/photos"
            mock_config.initial_sync_on_startup = True
            mock_config.max_batch_size = 10
            mock_config.event_debounce_delay = 1.0
            mock_config.retry_attempts = 3
            mock_config.retry_delay = 1.0
            mock_config.periodic_sync_interval = 3600
            mock_config.health_check_host = "localhost"
            mock_config.health_check_port = 8001
            mock_config.log_level = "INFO"

            mock_db_manager.session_factory = MagicMock()

            mock_watcher = MagicMock()
            mock_watcher.observer = MagicMock()
            mock_watcher.start_watching = AsyncMock()
            mock_watcher.stop_watching = AsyncMock()
            mock_watcher_class.return_value = mock_watcher

            mock_engine = MagicMock()
            mock_engine.perform_initial_sync = AsyncMock()
            mock_engine.process_event_batch = AsyncMock()
            mock_engine.perform_periodic_sync = AsyncMock()
            mock_engine_class.return_value = mock_engine

            mock_health = MagicMock()
            mock_health.get_app = MagicMock()
            mock_health_class.return_value = mock_health

            yield {
                "db_manager": mock_db_manager,
                "config": mock_config,
                "watcher_class": mock_watcher_class,
                "watcher": mock_watcher,
                "engine_class": mock_engine_class,
                "engine": mock_engine,
                "health_class": mock_health_class,
                "health": mock_health,
            }

    @pytest.fixture
    def sync_worker(self, mock_dependencies) -> SyncWorker:
        """Create a SyncWorker for testing."""
        return SyncWorker()

    @pytest.mark.unit
    def test_initialization(self, sync_worker: SyncWorker, mock_dependencies):
        """Test that SyncWorker is initialized correctly."""
        mocks = mock_dependencies

        assert sync_worker.config is not None
        assert sync_worker.db_manager is not None
        assert isinstance(sync_worker.event_queue, Queue)
        assert sync_worker.watcher is not None
        assert sync_worker.sync_engine is not None
        assert sync_worker.health_monitor is not None
        assert sync_worker.running is False

        # Check that components were created with correct parameters
        mocks["watcher_class"].assert_called_once()
        mocks["engine_class"].assert_called_once()
        mocks["health_class"].assert_called_once()

    @pytest.mark.unit
    def test_get_db_session(self, sync_worker: SyncWorker, mock_dependencies):
        """Test getting database session."""
        # Call the method to get a session
        session = sync_worker._get_db_session()

        # Should call the session factory
        mock_dependencies["db_manager"].session_factory.assert_called_once()

        # Should return the session
        assert session == mock_dependencies["db_manager"].session_factory()

    @pytest.mark.unit
    def test_setup_signal_handlers(self, sync_worker: SyncWorker):
        """Test that signal handlers are set up correctly."""
        with patch("signal.signal") as mock_signal:
            sync_worker._setup_signal_handlers()

            # Should set up handlers for SIGTERM and SIGINT
            calls = mock_signal.call_args_list
            signal_types = [call[0][0] for call in calls]

            assert signal.SIGTERM in signal_types
            assert signal.SIGINT in signal_types

    @pytest.mark.unit
    def test_signal_handler_function(self, sync_worker: SyncWorker):
        """Test the signal handler function."""
        sync_worker.running = True

        # Get the signal handler function
        with patch("signal.signal") as mock_signal:
            sync_worker._setup_signal_handlers()
            handler = mock_signal.call_args_list[0][0][1]

        # Call the handler
        handler(signal.SIGTERM, None)

        # Worker should be stopped
        assert sync_worker.running is False

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_start_with_initial_sync(self, sync_worker: SyncWorker, mock_dependencies):
        """Test starting worker with initial sync enabled."""
        mocks = mock_dependencies

        # Mock initial sync to return stats
        mock_stats = SyncStats(files_scanned=100, files_added=10, files_updated=5, files_removed=2, errors=1)
        mocks["engine"].perform_initial_sync.return_value = mock_stats

        # Mock the long-running tasks to complete quickly
        with (
            patch.object(sync_worker, "_start_health_server", new_callable=AsyncMock),
            patch.object(sync_worker, "_process_events", new_callable=AsyncMock),
            patch.object(sync_worker, "_periodic_sync", new_callable=AsyncMock),
            patch("asyncio.gather", new_callable=AsyncMock),
        ):

            sync_worker.running = False  # Ensure it stops quickly
            await sync_worker.start()

            # Initial sync should be performed
            mocks["engine"].perform_initial_sync.assert_called_once()

            # Watcher should be started
            mocks["watcher"].start_watching.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_start_without_initial_sync(self, sync_worker: SyncWorker, mock_dependencies):
        """Test starting worker with initial sync disabled."""
        mocks = mock_dependencies
        mocks["config"].initial_sync_on_startup = False

        with (
            patch.object(sync_worker, "_start_health_server", new_callable=AsyncMock),
            patch.object(sync_worker, "_process_events", new_callable=AsyncMock),
            patch.object(sync_worker, "_periodic_sync", new_callable=AsyncMock),
            patch("asyncio.gather", new_callable=AsyncMock),
        ):

            sync_worker.running = False
            await sync_worker.start()

            # Initial sync should not be performed
            mocks["engine"].perform_initial_sync.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_shutdown(self, sync_worker: SyncWorker, mock_dependencies):
        """Test graceful shutdown of worker."""
        mocks = mock_dependencies
        sync_worker.running = True

        await sync_worker.shutdown()

        assert sync_worker.running is False
        mocks["watcher"].stop_watching.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_start_health_server(self, sync_worker: SyncWorker):
        """Test starting the health monitoring server."""
        with patch("uvicorn.Config") as mock_config, patch("uvicorn.Server") as mock_server:

            mock_server_instance = MagicMock()
            mock_server_instance.serve = AsyncMock()
            mock_server.return_value = mock_server_instance

            await sync_worker._start_health_server()

            # Should create uvicorn config and server
            mock_config.assert_called_once()
            mock_server.assert_called_once()
            mock_server_instance.serve.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_process_events_loop(self, sync_worker: SyncWorker):
        """Test the event processing loop."""
        sync_worker.running = True

        # Mock collect_event_batch to return events once, then empty
        call_count = 0

        async def mock_collect_batch():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [MagicMock()]  # First call returns events
            else:
                sync_worker.running = False  # Stop after the second call
                return []

        with (
            patch.object(sync_worker, "_collect_event_batch", side_effect=mock_collect_batch),
            patch.object(sync_worker, "_process_event_batch_with_retry", new_callable=AsyncMock) as mock_process,
        ):

            await sync_worker._process_events()

            # Should process events when available
            mock_process.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_collect_event_batch(self, sync_worker: SyncWorker, sample_file_events):
        """Test collecting events into batches."""
        # Add events to queue
        for event in sample_file_events:
            sync_worker.event_queue.put(event)

        sync_worker.running = True

        # Collect batch with small debounce delay
        with (
            patch.object(sync_worker.config, "event_debounce_delay", 0.1),
            patch.object(sync_worker.config, "max_batch_size", 10),
        ):

            batch = await sync_worker._collect_event_batch()

            assert len(batch) == len(sample_file_events)
            assert all(isinstance(event, FileEvent) for event in batch)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_collect_event_batch_empty_queue(self, sync_worker: SyncWorker):
        """Test collecting events from empty queue."""
        sync_worker.running = True

        # Set very short timeout to avoid long waits
        with patch("time.time", side_effect=[0, 0.5, 1.0, 1.5]):  # Mock time progression
            batch = await sync_worker._collect_event_batch()

            assert len(batch) == 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_collect_event_batch_respects_max_size(self, sync_worker: SyncWorker):
        """Test that batch collection respects max batch size."""
        # Add more events than max batch size
        max_size = 3
        for i in range(5):
            event = FileEvent(
                event_type=FileEventType.CREATED,
                file_path=Path(f"/test/image_{i}.jpg"),
                category="test",
                timestamp=datetime.now(timezone.utc),
            )
            sync_worker.event_queue.put(event)

        sync_worker.running = True

        with (
            patch.object(sync_worker.config, "max_batch_size", max_size),
            patch.object(sync_worker.config, "event_debounce_delay", 0.1),
        ):

            batch = await sync_worker._collect_event_batch()

            assert len(batch) <= max_size

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_process_event_batch_with_retry_success(self, sync_worker: SyncWorker, mock_dependencies):
        """Test successful event batch processing."""
        mocks = mock_dependencies
        events = [MagicMock()]

        await sync_worker._process_event_batch_with_retry(events)

        # Should process the batch
        mocks["engine"].process_event_batch.assert_called_once_with(events)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_process_event_batch_with_retry_failure(self, sync_worker: SyncWorker, mock_dependencies):
        """Test event batch processing with retries on failure."""
        mocks = mock_dependencies
        events = [MagicMock()]

        # Mock engine to fail all attempts
        mocks["engine"].process_event_batch.side_effect = Exception("Processing failed")

        with (
            patch.object(sync_worker.config, "retry_attempts", 2),
            patch.object(sync_worker.config, "retry_delay", 0.1),
        ):

            with pytest.raises(Exception, match="Processing failed"):
                await sync_worker._process_event_batch_with_retry(events)

            # Should retry the configured number of times
            assert mocks["engine"].process_event_batch.call_count == 2

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_process_event_batch_with_retry_partial_success(self, sync_worker: SyncWorker, mock_dependencies):
        """Test event batch processing with success after retries."""
        mocks = mock_dependencies
        events = [MagicMock()]

        # Mock engine to fail the first attempt, then succeed
        call_count = 0

        def mock_process_batch(_):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("First attempt failed")
            # Second attempt succeeds (no exception)

        mocks["engine"].process_event_batch.side_effect = mock_process_batch

        with (
            patch.object(sync_worker.config, "retry_attempts", 3),
            patch.object(sync_worker.config, "retry_delay", 0.1),
        ):

            # Should not raise exception
            await sync_worker._process_event_batch_with_retry(events)

            # Should have retried once
            assert mocks["engine"].process_event_batch.call_count == 2

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_periodic_sync(self, sync_worker: SyncWorker, mock_dependencies):
        """Test periodic sync functionality."""
        mocks = mock_dependencies
        sync_worker.running = True

        # Mock periodic sync to return stats
        mock_stats = SyncStats(files_scanned=50, files_added=2, files_updated=1, files_removed=0, errors=0)
        mocks["engine"].perform_periodic_sync.return_value = mock_stats

        # Mock sleep to exit quickly
        call_count = 0

        async def mock_sleep(_):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                sync_worker.running = False  # Stop after second sleep call

        with patch("asyncio.sleep", side_effect=mock_sleep):
            await sync_worker._periodic_sync()

            # Periodic sync should be performed
            mocks["engine"].perform_periodic_sync.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_periodic_sync_exception_handling(self, sync_worker: SyncWorker, mock_dependencies):
        """Test that periodic sync handles exceptions gracefully."""
        mocks = mock_dependencies
        sync_worker.running = True

        # Mock periodic sync to raise exception
        mocks["engine"].perform_periodic_sync.side_effect = Exception("Sync failed")

        # Mock sleep to exit quickly
        call_count = 0

        async def mock_sleep(_):
            nonlocal call_count
            call_count += 1
            if call_count >= 1:
                sync_worker.running = False

        with patch("asyncio.sleep", side_effect=mock_sleep):
            # Should not raise exception
            await sync_worker._periodic_sync()

    @pytest.mark.unit
    def test_event_queue_integration(self, sync_worker: SyncWorker):
        """Test that event queue is properly integrated."""
        # Should have an empty queue initially
        assert sync_worker.event_queue.qsize() == 0

        # Add an event
        event = FileEvent(
            event_type=FileEventType.CREATED,
            file_path=Path("/test/image.jpg"),
            category="test",
            timestamp=datetime.now(timezone.utc),
        )
        sync_worker.event_queue.put(event)

        assert sync_worker.event_queue.qsize() == 1

        # Event should be retrievable
        retrieved_event = sync_worker.event_queue.get()
        assert retrieved_event == event

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_start_exception_handling(self, sync_worker: SyncWorker, mock_dependencies):
        """Test exception handling in start method."""
        mocks = mock_dependencies

        # Mock initial sync to raise exception
        mocks["engine"].perform_initial_sync.side_effect = Exception("Initial sync failed")

        # Should call shutdown even if start fails
        with patch.object(sync_worker, "shutdown", new_callable=AsyncMock) as mock_shutdown:
            await sync_worker.start()

            mock_shutdown.assert_called_once()

    @pytest.mark.unit
    def test_health_monitor_configuration(self, sync_worker: SyncWorker, mock_dependencies):
        """Test that health monitor is configured correctly."""
        mocks = mock_dependencies

        # Health monitor should be initialized
        mocks["health_class"].assert_called_once()
