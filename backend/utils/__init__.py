"""Backend utility modules."""

from .file_resolver import PPTFileResolver, create_file_resolver
from .shape_utils import (
    find_shape_by_index,
    update_shape_property,
    extract_preserved_descriptions,
)

__all__ = [
    "PPTFileResolver",
    "create_file_resolver",
    "find_shape_by_index",
    "update_shape_property",
    "extract_preserved_descriptions",
]
