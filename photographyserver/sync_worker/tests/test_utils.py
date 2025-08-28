"""Tests for utility functions in the sync worker."""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pgs_sync.sync_types import ImageMetadata
from pgs_sync.utils import (
    extract_image_metadata,
    generate_title_from_filename,
    is_supported_image_file,
)


class TestExtractImageMetadata:
    """Test the extract_image_metadata function."""

    @pytest.mark.unit
    def test_extract_metadata_from_valid_image(self, sample_image_file: Path):
        """Test extracting metadata from a valid image file."""
        metadata = extract_image_metadata(sample_image_file)

        assert isinstance(metadata, ImageMetadata)
        assert metadata.file_size > 0
        assert metadata.width == 100  # From fixture
        assert metadata.height == 100  # From fixture
        assert isinstance(metadata.file_modified_at, datetime)
        assert metadata.file_modified_at.tzinfo is not None

    @pytest.mark.unit
    def test_extract_metadata_file_not_found(self):
        """Test behavior when a file doesn't exist."""
        non_existent_file = Path("/nonexistent/file.jpg")

        with pytest.raises(OSError):
            extract_image_metadata(non_existent_file)

    @pytest.mark.unit
    @patch("pgs_sync.utils.Image.open")
    def test_extract_metadata_invalid_image(self, mock_open, temp_photos_dir: Path):
        """Test handling of files that aren't valid images."""
        # Create a text file with image extension
        invalid_image = temp_photos_dir / "landscapes" / "not_image.jpg"
        invalid_image.write_text("This is not an image")

        # Mock PIL to raise an exception
        mock_open.side_effect = Exception("Cannot identify image file")

        metadata = extract_image_metadata(invalid_image)

        # Should still return metadata with file info, but no dimensions
        assert isinstance(metadata, ImageMetadata)
        assert metadata.file_size > 0
        assert metadata.width is None
        assert metadata.height is None
        assert isinstance(metadata.file_modified_at, datetime)

    @pytest.mark.unit
    @patch("pgs_sync.utils.Image.open")
    def test_extract_metadata_unsupported_format(self, mock_open, sample_image_file: Path):
        """Test handling of unsupported image formats."""
        # Mock PIL to raise unsupported format exception
        mock_open.side_effect = Exception("Unsupported image format")

        metadata = extract_image_metadata(sample_image_file)

        # Should return metadata without dimensions
        assert metadata.width is None
        assert metadata.height is None
        assert metadata.file_size > 0

    @pytest.mark.unit
    def test_metadata_timestamp_timezone(self, sample_image_file: Path):
        """Test that timestamps are in UTC timezone."""
        metadata = extract_image_metadata(sample_image_file)

        assert metadata.file_modified_at.tzinfo == timezone.utc

    @pytest.mark.unit
    @patch("pgs_sync.utils.Image.open")
    def test_extract_metadata_with_context_manager(self, mock_open, sample_image_file: Path):
        """Test that Image.open is used as a context manager."""
        mock_image = MagicMock()
        mock_image.size = (1920, 1080)
        mock_image.__enter__ = MagicMock(return_value=mock_image)
        mock_image.__exit__ = MagicMock(return_value=None)
        mock_open.return_value = mock_image

        metadata = extract_image_metadata(sample_image_file)

        # Verify context manager was used
        mock_image.__enter__.assert_called_once()
        mock_image.__exit__.assert_called_once()
        assert metadata.width == 1920
        assert metadata.height == 1080


class TestGenerateTitleFromFilename:
    """Test the generate_title_from_filename function."""

    @pytest.mark.unit
    def test_simple_filename(self):
        """Test generating title from simple filename."""
        title = generate_title_from_filename("beautiful_sunset.jpg")
        assert title == "Beautiful Sunset"

    @pytest.mark.unit
    def test_filename_with_extension(self):
        """Test that file extension is removed."""
        title = generate_title_from_filename("mountain_view.jpeg")
        assert title == "Mountain View"

    @pytest.mark.unit
    def test_filename_without_extension(self):
        """Test filename without extension."""
        title = generate_title_from_filename("city_lights")
        assert title == "City Lights"

    @pytest.mark.unit
    def test_remove_common_prefixes(self):
        """Test removal of common camera prefixes."""
        test_cases = [
            ("IMG_1234.jpg", "1234"),
            ("DSC_5678.jpg", "5678"),
            ("DSCN_9012.jpg", "9012"),
            ("P_3456.jpg", "3456"),
            ("PIC_7890.jpg", "7890"),
            ("PHOTO_1111.jpg", "1111"),
            ("IMAGE_2222.jpg", "2222"),
        ]

        for filename, expected in test_cases:
            title = generate_title_from_filename(filename)
            assert expected in title

    @pytest.mark.unit
    def test_remove_timestamps(self):
        """Test removal of timestamp patterns."""
        test_cases = [
            "vacation_20230615_sunset.jpg",
            "party_2023-06-15_group.jpg",
            "wedding_20230615.jpg",
        ]

        for filename in test_cases:
            title = generate_title_from_filename(filename)
            # Timestamp should be removed
            assert "2023" not in title
            assert "06" not in title
            assert "15" not in title

    @pytest.mark.unit
    def test_remove_time_patterns(self):
        """Test removal of time patterns."""
        test_cases = [
            "event_142530_photo.jpg",
            "meeting_14-25-30_notes.jpg",
            "concert_14:25:30_stage.jpg",
        ]

        for filename in test_cases:
            title = generate_title_from_filename(filename)
            # Time should be removed
            assert "14" not in title or "25" not in title or "30" not in title

    @pytest.mark.unit
    def test_remove_sequential_numbers(self):
        """Test removal of sequential numbers."""
        test_cases = [
            ("001_sunset.jpg", "Sunset"),
            ("photo_123.jpg", "Photo"),
            ("_456_landscape.jpg", "Landscape"),
        ]

        for filename, expected_word in test_cases:
            title = generate_title_from_filename(filename)
            assert expected_word.lower() in title.lower()

    @pytest.mark.unit
    def test_replace_separators(self):
        """Test replacement of underscores and hyphens with spaces."""
        test_cases = [
            ("beach_vacation_2023.jpg", "Beach Vacation"),
            ("mountain-hiking-trail.jpg", "Mountain Hiking Trail"),
            ("city___lights___night.jpg", "City Lights Night"),
        ]

        for filename, expected in test_cases:
            title = generate_title_from_filename(filename)
            assert expected.lower() in title.lower()

    @pytest.mark.unit
    def test_capitalize_words(self):
        """Test that words are properly capitalized."""
        title = generate_title_from_filename("beautiful_mountain_view.jpg")

        words = title.split()
        for word in words:
            assert word[0].isupper()

    @pytest.mark.unit
    def test_empty_result_fallback(self):
        """Test fallback when title generation results in empty string."""
        # Filename with only patterns that get removed
        title = generate_title_from_filename("IMG_20230615_142530.jpg")

        # Should fall back to a cleaned version of original stem
        assert title != ""
        assert "Img" in title

    @pytest.mark.unit
    def test_case_insensitive_prefix_removal(self):
        """Test that prefix removal is case-insensitive."""
        test_cases = [
            "img_sunset.jpg",
            "IMG_sunset.jpg",
            "Img_sunset.jpg",
            "dsc_photo.jpg",
            "DSC_photo.jpg",
        ]

        for filename in test_cases:
            title = generate_title_from_filename(filename)
            # Prefix should be removed regardless of case
            assert "sunset" in title.lower() or "photo" in title.lower()

    @pytest.mark.unit
    def test_multiple_spaces_cleanup(self):
        """Test that multiple consecutive spaces are cleaned up."""
        title = generate_title_from_filename("beach___vacation___2023.jpg")

        # Should not contain multiple consecutive spaces
        assert "  " not in title

    @pytest.mark.unit
    def test_path_object_input(self):
        """Test that Path objects are handled correctly."""
        path = Path("/photos/landscapes/sunset_view.jpg")
        title = generate_title_from_filename(str(path))

        assert title == "Sunset View"


class TestIsSupportedImageFile:
    """Test the is_supported_image_file function."""

    @pytest.mark.unit
    def test_supported_extensions(self):
        """Test that supported file extensions return True."""
        supported_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

        test_cases = [
            Path("/test/image.jpg"),
            Path("/test/image.jpeg"),
            Path("/test/image.png"),
            Path("/test/image.gif"),
            Path("/test/image.webp"),
        ]

        for file_path in test_cases:
            assert is_supported_image_file(file_path, supported_extensions)

    @pytest.mark.unit
    def test_unsupported_extensions(self):
        """Test that unsupported file extensions return False."""
        supported_extensions = {".jpg", ".jpeg", ".png"}

        test_cases = [
            Path("/test/document.txt"),
            Path("/test/archive.zip"),
            Path("/test/video.mp4"),
            Path("/test/audio.mp3"),
        ]

        for file_path in test_cases:
            assert not is_supported_image_file(file_path, supported_extensions)

    @pytest.mark.unit
    def test_case_insensitive_matching(self):
        """Test that extension matching is case-insensitive."""
        supported_extensions = {".jpg", ".png"}

        test_cases = [
            Path("/test/image.JPG"),
            Path("/test/image.Jpg"),
            Path("/test/image.PNG"),
            Path("/test/image.Png"),
        ]

        for file_path in test_cases:
            assert is_supported_image_file(file_path, supported_extensions)

    @pytest.mark.unit
    def test_no_extension(self):
        """Test files without extensions."""
        supported_extensions = {".jpg", ".png"}

        file_path = Path("/test/image_without_extension")
        assert not is_supported_image_file(file_path, supported_extensions)

    @pytest.mark.unit
    def test_empty_extension_set(self):
        """Test behavior with empty supported extensions set."""
        supported_extensions = set()

        file_path = Path("/test/image.jpg")
        assert not is_supported_image_file(file_path, supported_extensions)

    @pytest.mark.unit
    def test_multiple_dots_in_filename(self):
        """Test files with multiple dots in filename."""
        supported_extensions = {".jpg"}

        file_path = Path("/test/image.backup.jpg")
        assert is_supported_image_file(file_path, supported_extensions)

        file_path = Path("/test/image.backup.txt")
        assert not is_supported_image_file(file_path, supported_extensions)
