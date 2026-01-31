"""
Tests for backend/utils/shape_utils.py

Tests shape tree navigation and manipulation utilities.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "backend"))

from utils.shape_utils import (
    find_shape_by_index,
    update_shape_property,
    extract_preserved_descriptions,
)


class TestFindShapeByIndex:
    """Tests for find_shape_by_index function."""

    def test_find_shape_at_root_level(self, sample_shapes):
        """Should find a shape at the root level by its index."""
        result = find_shape_by_index(sample_shapes, "1")
        assert result is not None
        assert result["name"] == "Title"
        assert result["shape_index"] == 1

    def test_find_shape_in_nested_children(self, sample_shapes):
        """Should find a shape nested inside children."""
        result = find_shape_by_index(sample_shapes, "3")
        assert result is not None
        assert result["name"] == "Nested Shape"
        assert result["type"] == "Rectangle"

    def test_find_shape_with_string_id(self, sample_shapes):
        """Should find a shape when shape_index is stored as string."""
        result = find_shape_by_index(sample_shapes, "4")
        assert result is not None
        assert result["name"] == "Image"
        assert result["type"] == "Picture"

    def test_find_shape_with_integer_lookup(self, sample_shapes):
        """Should find a shape when searching with integer (converted to string)."""
        result = find_shape_by_index(sample_shapes, 1)
        assert result is not None
        assert result["name"] == "Title"

    def test_returns_none_for_nonexistent_shape(self, sample_shapes):
        """Should return None when shape is not found."""
        result = find_shape_by_index(sample_shapes, "999")
        assert result is None

    def test_returns_none_for_empty_list(self):
        """Should return None for empty shape list."""
        result = find_shape_by_index([], "1")
        assert result is None


class TestUpdateShapeProperty:
    """Tests for update_shape_property function."""

    def test_update_root_level_shape(self, sample_shapes):
        """Should update properties of a root level shape."""
        result = update_shape_property(sample_shapes, "1", {"left": 200, "top": 100})
        assert result is True
        shape = find_shape_by_index(sample_shapes, "1")
        assert shape["left"] == 200
        assert shape["top"] == 100

    def test_update_nested_shape(self, sample_shapes):
        """Should update properties of a nested shape."""
        result = update_shape_property(sample_shapes, "3", {"width": 100, "height": 100})
        assert result is True
        shape = find_shape_by_index(sample_shapes, "3")
        assert shape["width"] == 100
        assert shape["height"] == 100

    def test_update_multiple_properties(self, sample_shapes):
        """Should update multiple properties at once."""
        updates = {"left": 50, "top": 50, "description": "Updated description"}
        result = update_shape_property(sample_shapes, "1", updates)
        assert result is True
        shape = find_shape_by_index(sample_shapes, "1")
        assert shape["left"] == 50
        assert shape["top"] == 50
        assert shape["description"] == "Updated description"

    def test_returns_false_for_nonexistent_shape(self, sample_shapes):
        """Should return False when shape is not found."""
        result = update_shape_property(sample_shapes, "999", {"left": 100})
        assert result is False

    def test_does_not_modify_other_shapes(self, sample_shapes):
        """Should not affect other shapes when updating one."""
        original_left = sample_shapes[1]["left"]
        update_shape_property(sample_shapes, "1", {"left": 999})
        assert sample_shapes[1]["left"] == original_left


class TestExtractPreservedDescriptions:
    """Tests for extract_preserved_descriptions function."""

    def test_extracts_descriptions_from_shapes(self, sample_shapes):
        """Should extract description from shapes with name and description."""
        preserved = {}
        extract_preserved_descriptions(sample_shapes, 0, preserved)

        assert (0, "Title") in preserved
        assert preserved[(0, "Title")] == "Main title"
        assert (0, "Content") in preserved
        assert preserved[(0, "Content")] == "Main content"

    def test_extracts_nested_descriptions(self, sample_shapes):
        """Should extract descriptions from nested children."""
        preserved = {}
        extract_preserved_descriptions(sample_shapes, 0, preserved)

        assert (0, "Nested Shape") in preserved
        assert preserved[(0, "Nested Shape")] == "Nested element"

    def test_skips_shapes_without_description(self, sample_shapes):
        """Should skip shapes that don't have a description."""
        preserved = {}
        extract_preserved_descriptions(sample_shapes, 0, preserved)

        # Image shape has no description
        assert (0, "Image") not in preserved

    def test_uses_correct_slide_index(self, sample_shapes):
        """Should use the provided slide index in the key tuple."""
        preserved = {}
        extract_preserved_descriptions(sample_shapes, 5, preserved)

        assert (5, "Title") in preserved
        assert (0, "Title") not in preserved

    def test_handles_empty_shape_list(self):
        """Should handle empty shape list without errors."""
        preserved = {}
        extract_preserved_descriptions([], 0, preserved)
        assert len(preserved) == 0

    def test_accumulates_to_existing_dict(self, sample_shapes):
        """Should add to existing preserved data dict."""
        preserved = {(0, "Existing"): "existing description"}
        extract_preserved_descriptions(sample_shapes, 1, preserved)

        assert (0, "Existing") in preserved
        assert (1, "Title") in preserved
