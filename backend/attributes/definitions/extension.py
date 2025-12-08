import os
from typing import Any, Dict
from attributes.base import BaseAttribute
from attributes.types import FilteringAttributeType


class ExtensionAttribute(BaseAttribute):
    @property
    def key(self) -> str:
        return "file_extension"

    @property
    def display_name(self) -> str:
        return "File Extension"

    @property
    def attr_type(self) -> FilteringAttributeType:
        return FilteringAttributeType(variant="multi_select")

    def extract(self, project_data: Dict[str, Any]) -> Any:
        filename = project_data.get("original_filename", "")
        if not filename:
            return "Unknown"

        _, ext = os.path.splitext(filename)
        return ext.lower().lstrip(".") if ext else "None"
