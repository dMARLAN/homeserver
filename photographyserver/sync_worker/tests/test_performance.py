"""Performance and load tests for the sync worker."""

import asyncio
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from queue import Queue
from unittest.mock import AsyncMock, patch

import psutil
import pytest
from PIL import Image

from pgs_sync.sync_engine import SyncEngine
from pgs_sync.sync_types import FileEvent, FileEventType
from pgs_sync.utils import extract_image_metadata, generate_title_from_filename
from pgs_sync.watcher import PhotoDirectoryEventHandler


class TestPerformanceMetrics:
    """Test performance characteristics and timing."""

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_single_event_processing_time(self, mock_db_session_factory):
        """Test processing time for single events."""
        sync_engine = SyncEngine(mock_db_session_factory)

        event = FileEvent(
            event_type=FileEventType.CREATED,
            file_path=Path("/test/image.jpg"),
            category="test",
            timestamp=datetime.now(timezone.utc),
        )

        with (
            patch.object(sync_engine, "_is_supported_file", return_value=True),
            patch.object(sync_engine, "_handle_file_created", new_callable=AsyncMock),
        ):

            start_time = time.time()
            await sync_engine.process_file_event(event)
            processing_time = time.time() - start_time

            # Single event should process quickly (under 100ms in ideal conditions)
            assert processing_time < 0.1

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_batch_processing_efficiency(self, mock_db_session_factory):
        """Test that batch processing is more efficient than individual processing."""
        sync_engine = SyncEngine(mock_db_session_factory)

        # Create multiple events
        num_events = 20
        events = [
            FileEvent(
                event_type=FileEventType.CREATED,
                file_path=Path(f"/test/image_{i}.jpg"),
                category="test",
                timestamp=datetime.now(timezone.utc),
            )
            for i in range(num_events)
        ]

        with (
            patch.object(sync_engine, "_is_supported_file", return_value=True),
            patch.object(sync_engine, "_handle_file_created", new_callable=AsyncMock),
        ):

            # Time individual processing
            start_time = time.time()
            for event in events:
                await sync_engine.process_file_event(event)
            individual_time = time.time() - start_time

            # Time batch processing
            start_time = time.time()
            await sync_engine.process_event_batch(events)
            batch_time = time.time() - start_time

            # Batch processing should be faster (or at least not significantly slower)
            # Allow some tolerance for test environment variations
            assert batch_time <= individual_time * 1.5

    @pytest.mark.slow
    def test_event_queue_performance(self):
        """Test event queue performance under load."""
        event_queue = Queue()
        event_handler = PhotoDirectoryEventHandler(event_queue)

        num_events = 1000

        # Time event queuing
        start_time = time.time()
        for i in range(num_events):
            event_handler._queue_event(FileEventType.CREATED, f"/test/image_{i}.jpg")
        queuing_time = time.time() - start_time

        # Should queue 1000 events quickly (under 1 second)
        assert queuing_time < 1.0
        assert event_queue.qsize() == num_events

        # Time event retrieval
        start_time = time.time()
        retrieved_events = []
        while not event_queue.empty():
            retrieved_events.append(event_queue.get())
        retrieval_time = time.time() - start_time

        # Should retrieve all events quickly
        assert retrieval_time < 0.5
        assert len(retrieved_events) == num_events

    @pytest.mark.slow
    def test_memory_usage_under_load(self, temp_photos_dir):
        """Test memory usage characteristics under load."""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Create many events and objects
        events = []
        num_events = 1000

        for i in range(num_events):
            event = FileEvent(
                event_type=FileEventType.CREATED,
                file_path=temp_photos_dir / f"image_{i}.jpg",
                category="test",
                timestamp=datetime.now(timezone.utc),
            )
            events.append(event)

        peak_memory = process.memory_info().rss
        memory_increase = peak_memory - initial_memory

        # Memory increase should be reasonable (less than 50MB for 1000 events)
        assert memory_increase < 50 * 1024 * 1024  # 50MB

        # Clear events and check memory is released
        del events
        import gc

        gc.collect()

        final_memory = process.memory_info().rss
        # Memory should be released (within 10MB of initial)
        assert abs(final_memory - initial_memory) < 10 * 1024 * 1024


class TestLoadTesting:
    """Load testing scenarios."""

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_concurrent_event_processing(self, mock_db_session_factory):
        """Test processing events concurrently."""
        sync_engine = SyncEngine(mock_db_session_factory)

        # Create multiple batches to process concurrently
        num_batches = 5
        events_per_batch = 10

        batches = []
        for batch_idx in range(num_batches):
            batch = [
                FileEvent(
                    event_type=FileEventType.CREATED,
                    file_path=Path(f"/test/batch_{batch_idx}_image_{i}.jpg"),
                    category="test",
                    timestamp=datetime.now(timezone.utc),
                )
                for i in range(events_per_batch)
            ]
            batches.append(batch)

        with (
            patch.object(sync_engine, "_is_supported_file", return_value=True),
            patch.object(sync_engine, "_handle_file_created", new_callable=AsyncMock),
        ):

            # Process batches concurrently
            start_time = time.time()
            tasks = [sync_engine.process_event_batch(batch) for batch in batches]
            await asyncio.gather(*tasks)
            processing_time = time.time() - start_time

            # Should complete all batches in reasonable time (under 5 seconds)
            assert processing_time < 5.0

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_large_file_metadata_extraction(self, temp_photos_dir):
        """Test metadata extraction from large files."""
        # Create a large test image with noise to make it less compressible
        large_image_path = temp_photos_dir / "large_image.jpg"
        import random

        large_image = Image.new("RGB", (6000, 4000))
        # Fill with random colors to make it harder to compress
        pixels = [(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)) for _ in range(6000 * 4000)]
        large_image.putdata(pixels)
        large_image.save(large_image_path, "JPEG", quality=98)

        # Time metadata extraction
        start_time = time.time()
        metadata = extract_image_metadata(large_image_path)
        extraction_time = time.time() - start_time

        # Should extract metadata quickly even for large files (under 1 second)
        assert extraction_time < 1.0
        assert metadata.width == 6000
        assert metadata.height == 4000
        assert metadata.file_size > 1024 * 1024  # Should be at least 1MB

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_rapid_event_generation(self, temp_photos_dir):
        """Test handling rapid succession of events."""
        event_queue = Queue()
        event_handler = PhotoDirectoryEventHandler(event_queue)

        # Generate events rapidly
        num_events = 500
        event_types = [FileEventType.CREATED, FileEventType.MODIFIED, FileEventType.DELETED]

        start_time = time.time()
        for i in range(num_events):
            event_type = event_types[i % len(event_types)]
            event_handler._queue_event(event_type, f"/test/rapid_image_{i}.jpg")
        generation_time = time.time() - start_time

        # Should handle rapid event generation (under 2 seconds for 500 events)
        assert generation_time < 2.0
        assert event_queue.qsize() == num_events

        # Verify events are properly formed
        sample_event = event_queue.get()
        assert isinstance(sample_event, FileEvent)
        assert sample_event.event_type in event_types
        assert isinstance(sample_event.timestamp, datetime)

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_sustained_throughput(self, mock_db_session_factory):
        """Test sustained event processing throughput."""
        sync_engine = SyncEngine(mock_db_session_factory)

        # Process events continuously for a sustained period
        duration_seconds = 5
        events_processed = 0

        with (
            patch.object(sync_engine, "_is_supported_file", return_value=True),
            patch.object(sync_engine, "_handle_file_created", new_callable=AsyncMock),
        ):

            start_time = time.time()

            while time.time() - start_time < duration_seconds:
                # Create a batch of events
                batch = [
                    FileEvent(
                        event_type=FileEventType.CREATED,
                        file_path=Path(f"/test/sustained_{events_processed + i}.jpg"),
                        category="test",
                        timestamp=datetime.now(timezone.utc),
                    )
                    for i in range(10)
                ]

                await sync_engine.process_event_batch(batch)
                events_processed += len(batch)

            actual_duration = time.time() - start_time
            throughput = events_processed / actual_duration

            # Should maintain reasonable throughput (at least 50 events/second)
            assert throughput >= 50


class TestScalabilityLimits:
    """Test scalability limits and edge cases."""

    @pytest.mark.slow
    def test_maximum_queue_size(self):
        """Test behavior with very large event queues."""
        event_queue = Queue()
        event_handler = PhotoDirectoryEventHandler(event_queue)

        # Fill the queue with many events
        max_events = 10000

        start_time = time.time()
        for i in range(max_events):
            if i % 1000 == 0:  # Check time periodically
                elapsed = time.time() - start_time
                if elapsed > 30:  # Stop if taking too long
                    break

            event_handler._queue_event(FileEventType.CREATED, f"/test/max_queue_{i}.jpg")

        final_queue_size = event_queue.qsize()

        # Should handle large queues (at least 5000 events)
        assert final_queue_size >= 5000

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_error_rate_under_load(self, mock_db_session_factory):
        """Test error handling under load conditions."""
        sync_engine = SyncEngine(mock_db_session_factory)

        # Create events, some of which will cause errors
        num_events = 100
        events = []

        for i in range(num_events):
            # Every 10th event will be unsupported (causing it to be skipped)
            filename = f"/test/load_image_{i}.{'txt' if i % 10 == 0 else 'jpg'}"
            event = FileEvent(
                event_type=FileEventType.CREATED,
                file_path=Path(filename),
                category="test",
                timestamp=datetime.now(timezone.utc),
            )
            events.append(event)

        # Process with some events causing "errors" (unsupported files)
        processed_count = 0
        skipped_count = 0

        for event in events:
            if sync_engine._is_supported_file(event.file_path):
                with patch.object(sync_engine, "_handle_file_created", new_callable=AsyncMock):
                    await sync_engine.process_file_event(event)
                    processed_count += 1
            else:
                skipped_count += 1

        # Should handle mixed supported/unsupported files correctly
        assert processed_count == num_events - (num_events // 10)  # 90% processed
        assert skipped_count == num_events // 10  # 10% skipped

    @pytest.mark.slow
    def test_title_generation_performance(self):
        """Test performance of title generation with various filename patterns."""
        # Test various filename patterns
        test_filenames = [
            "IMG_20230615_142530.jpg",
            "DSC_1234.jpg",
            "beautiful_sunset_at_beach.jpg",
            "vacation-photos-2023-summer.jpg",
            "P1010001.jpg",
            "DSCN_5678_edited.jpg",
            "landscape_photography_mountains_2023_06_15.jpg",
            "wedding_ceremony_bride_groom_kiss.jpg",
        ] * 100  # Repeat to get meaningful timing

        start_time = time.time()
        titles = [generate_title_from_filename(filename) for filename in test_filenames]
        processing_time = time.time() - start_time

        # Should process all titles quickly (under 1 second for 800 filenames)
        assert processing_time < 1.0
        assert len(titles) == len(test_filenames)

        # Verify titles are reasonable
        for title in titles[:8]:  # Check the first few
            assert isinstance(title, str)
            assert len(title) > 0
            # Should be properly capitalized (first character is upper if it's a letter)
            if title[0].isalpha():
                assert title[0].isupper()
