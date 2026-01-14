"""
Shape Tree Utilities

This module provides utilities for navigating and manipulating hierarchical shape trees
in parsed PowerPoint data structures.
"""

from typing import Dict, List, Any, Optional, Callable, Tuple


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


def traverse_shapes(
    shapes: List[Dict[str, Any]], visitor: Callable[[Dict[str, Any]], None]
):
    """
    Traverse all shapes in the tree and apply a visitor function.

    Args:
        shapes: List of shape dictionaries (may contain nested children)
        visitor: Function to call on each shape
    """
    for shape in shapes:
        visitor(shape)

        if "children" in shape:
            traverse_shapes(shape["children"], visitor)


def extract_shape_properties(
    shapes: List[Dict[str, Any]],
    extractor: Callable[[Dict[str, Any]], Optional[Tuple[Any, Any]]],
) -> Dict[Any, Any]:
    """
    Extract properties from all shapes into a dictionary.

    Args:
        shapes: List of shape dictionaries (may contain nested children)
        extractor: Function that takes a shape and returns (key, value) tuple or None

    Returns:
        Dictionary mapping keys to values extracted from shapes
    """
    result = {}

    def visitor(shape):
        extracted = extractor(shape)
        if extracted:
            key, value = extracted
            result[key] = value

    traverse_shapes(shapes, visitor)
    return result


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


def restore_preserved_descriptions(
    shapes: List[Dict[str, Any]],
    slide_index: int,
    preserved_data: Dict[Tuple[int, str], str],
):
    """
    Restore descriptions from preserved data back into shapes.

    Args:
        shapes: List of shape dictionaries
        slide_index: Index of the slide containing these shapes
        preserved_data: Dictionary mapping (slide_index, name) to description
    """
    for shape in shapes:
        name = shape.get("name")

        if name:
            key = (slide_index, name)
            if key in preserved_data:
                shape["description"] = preserved_data[key]

        if "children" in shape:
            restore_preserved_descriptions(
                shape["children"], slide_index, preserved_data
            )


def map_all_shapes(shapes: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Create a flat mapping of all shapes by their shape_index.

    Args:
        shapes: List of shape dictionaries (may contain nested children)

    Returns:
        Dictionary mapping shape_index to shape dictionary
    """
    result = {}

    def visitor(shape):
        shape_index = shape.get("shape_index")
        if shape_index is not None:
            result[str(shape_index)] = shape

    traverse_shapes(shapes, visitor)
    return result


def count_shapes(shapes: List[Dict[str, Any]]) -> int:
    """
    Count total number of shapes including nested children.

    Args:
        shapes: List of shape dictionaries

    Returns:
        Total count of shapes
    """
    count = 0

    def visitor(shape):
        nonlocal count
        count += 1

    traverse_shapes(shapes, visitor)
    return count


def filter_shapes(
    shapes: List[Dict[str, Any]], predicate: Callable[[Dict[str, Any]], bool]
) -> List[Dict[str, Any]]:
    """
    Filter shapes based on a predicate function (flattened list).

    Args:
        shapes: List of shape dictionaries
        predicate: Function that returns True for shapes to include

    Returns:
        Flat list of shapes that match the predicate
    """
    result = []

    def visitor(shape):
        if predicate(shape):
            result.append(shape)

    traverse_shapes(shapes, visitor)
    return result
