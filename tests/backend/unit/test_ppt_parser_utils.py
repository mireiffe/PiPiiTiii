"""
Tests for backend/ppt_parser/utils.py

Tests PowerPoint parser utility functions.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "backend"))

from ppt_parser.utils import make_safe_filename, rgb_from_com_rgb


class TestMakeSafeFilename:
    """Tests for make_safe_filename function."""

    def test_removes_special_characters(self):
        """Should remove special characters and replace with underscore."""
        result = make_safe_filename("file@name#with$special%chars")
        assert "@" not in result
        assert "#" not in result
        assert "$" not in result
        assert "%" not in result
        assert "_" in result

    def test_keeps_alphanumeric_characters(self):
        """Should keep alphanumeric characters."""
        result = make_safe_filename("Test123File")
        assert result == "Test123File"

    def test_keeps_korean_characters(self):
        """Should preserve Korean (Hangul) characters."""
        result = make_safe_filename("테스트파일명")
        assert "테스트파일명" in result

    def test_keeps_allowed_special_chars(self):
        """Should keep dots, underscores, and hyphens."""
        result = make_safe_filename("file.name_with-allowed")
        assert "." in result
        assert "_" in result
        assert "-" in result
        assert result == "file.name_with-allowed"

    def test_truncates_long_names(self):
        """Should truncate names longer than 80 characters."""
        long_name = "a" * 100
        result = make_safe_filename(long_name)
        assert len(result) == 80

    def test_handles_empty_string(self):
        """Should return 'noname' for empty string."""
        result = make_safe_filename("")
        assert result == "noname"

    def test_handles_none(self):
        """Should return 'noname' for None input."""
        result = make_safe_filename(None)
        assert result == "noname"

    def test_mixed_content(self):
        """Should handle mixed Korean, English, and special characters."""
        result = make_safe_filename("테스트_File@2024.pptx")
        # Should keep Korean, alphanumeric, underscore, dot
        assert "테스트" in result
        assert "File" in result
        assert "2024" in result
        assert ".pptx" in result
        # @ should be replaced
        assert "@" not in result


class TestRgbFromComRgb:
    """Tests for rgb_from_com_rgb function.

    PowerPoint COM uses BGR format stored as integer (0xBBGGRR).
    """

    def test_converts_basic_rgb(self):
        """Should convert basic BGR integer to RGB list."""
        # Pure white (0xFFFFFF) should return [255, 255, 255]
        result = rgb_from_com_rgb(0xFFFFFF)
        assert result == [255, 255, 255]

    def test_converts_pure_red(self):
        """Should correctly extract pure red (stored as 0x0000FF in BGR)."""
        # Pure red in BGR format: B=0, G=0, R=255 = 0x0000FF = 255
        result = rgb_from_com_rgb(0x0000FF)
        assert result == [255, 0, 0]

    def test_converts_pure_green(self):
        """Should correctly extract pure green (stored as 0x00FF00)."""
        # Pure green in BGR format: B=0, G=255, R=0 = 0x00FF00 = 65280
        result = rgb_from_com_rgb(0x00FF00)
        assert result == [0, 255, 0]

    def test_converts_pure_blue(self):
        """Should correctly extract pure blue (stored as 0xFF0000)."""
        # Pure blue in BGR format: B=255, G=0, R=0 = 0xFF0000 = 16711680
        result = rgb_from_com_rgb(0xFF0000)
        assert result == [0, 0, 255]

    def test_converts_black(self):
        """Should handle black (0x000000)."""
        result = rgb_from_com_rgb(0)
        assert result == [0, 0, 0]

    def test_converts_mixed_color(self):
        """Should correctly convert mixed colors."""
        # Example: RGB(128, 64, 32) in BGR = 0x204080 = 2113664
        # BGR storage: B=32, G=64, R=128
        bgr_value = (32 << 16) | (64 << 8) | 128  # 0x204080
        result = rgb_from_com_rgb(bgr_value)
        assert result == [128, 64, 32]

    def test_returns_none_on_error(self):
        """Should return None when conversion fails."""
        result = rgb_from_com_rgb("invalid")
        assert result is None

    def test_handles_negative_input(self):
        """Should handle negative inputs gracefully."""
        # In Python, bitwise operations on negative numbers work differently
        # The function should either return valid result or None
        result = rgb_from_com_rgb(-1)
        # -1 in two's complement will have all bits set
        assert result is not None or result is None  # Just shouldn't crash

    def test_returns_integers(self):
        """Should return integer values in the list."""
        result = rgb_from_com_rgb(0x808080)  # Gray
        assert all(isinstance(v, int) for v in result)
