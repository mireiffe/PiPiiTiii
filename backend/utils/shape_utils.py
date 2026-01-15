"""
Shape Tree Utilities

This module provides utilities for navigating and manipulating hierarchical shape trees
in parsed PowerPoint data structures.
"""

from typing import Dict, List, Any, Optional, Tuple


def find_shape_by_index(
    shapes: List[Dict[str, Any]], target_id: str
) -> Optional[Dict[str, Any]]:
    """
    Find a shape in the shape tree by its shape_index.

    Args:
        shapes: List of shape dictionaries (may contain nested children)
        target_id: Target shape_index to find

    Returns:
        Shape dictionary if found, None otherwise
    """
    for shape in shapes:
        # shape_index can be integer or string, normalize to string for comparison
        if str(shape.get("shape_index")) == str(target_id):
            return shape

        # Recursively search in children
        if "children" in shape:
            found = find_shape_by_index(shape["children"], target_id)
            if found:
                return found

    return None


def update_shape_property(
    shapes: List[Dict[str, Any]], target_id: str, updates: Dict[str, Any]
) -> bool:
    """
    Update properties of a shape in the tree.

    Args:
        shapes: List of shape dictionaries (may contain nested children)
        target_id: Target shape_index to update
        updates: Dictionary of properties to update (e.g., {"left": 10, "top": 20})

    Returns:
        True if shape was found and updated, False otherwise
    """
    for shape in shapes:
        # shape_index can be integer or string, normalize to string for comparison
        if str(shape.get("shape_index")) == str(target_id):
            shape.update(updates)
            return True

        # Recursively search in children
        if "children" in shape:
            if update_shape_property(shape["children"], target_id, updates):
                return True

    return False


def extract_preserved_descriptions(
    shapes: List[Dict[str, Any]],
    slide_index: int,
    preserved_data: Dict[Tuple[int, str], str],
):
    """
    Recursively extract descriptions from shapes to preserve them during reparse.

    Args:
        shapes: List of shape dictionaries
        slide_index: Index of the slide containing these shapes
        preserved_data: Output dictionary mapping (slide_index, name) to description
    """
    for shape in shapes:
        name = shape.get("name")
        desc = shape.get("description")

        if name and desc:
            preserved_data[(slide_index, name)] = desc

        if "children" in shape:
            extract_preserved_descriptions(
                shape["children"], slide_index, preserved_data
            )
