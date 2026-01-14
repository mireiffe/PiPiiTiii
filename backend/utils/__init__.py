"""Backend utility modules."""

from .file_resolver import PPTFileResolver, create_file_resolver
from .shape_utils import (
    find_shape_by_index,
    update_shape_property,
    traverse_shapes,
    extract_shape_properties,
    extract_preserved_descriptions,
    restore_preserved_descriptions,
    map_all_shapes,
    count_shapes,
    filter_shapes,
)
from .llm_utils import (
    extract_json_from_response,
    validate_workflow_schema,
    validate_workflow_actions,
    parse_workflow_from_llm_response,
)

__all__ = [
    "PPTFileResolver",
    "create_file_resolver",
    "find_shape_by_index",
    "update_shape_property",
    "traverse_shapes",
    "extract_shape_properties",
    "extract_preserved_descriptions",
    "restore_preserved_descriptions",
    "map_all_shapes",
    "count_shapes",
    "filter_shapes",
    "extract_json_from_response",
    "validate_workflow_schema",
    "validate_workflow_actions",
    "parse_workflow_from_llm_response",
]
