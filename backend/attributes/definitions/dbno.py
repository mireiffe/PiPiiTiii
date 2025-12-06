import os
import json
from typing import Any, Dict
from attributes.base import BaseAttribute
from attributes.types import FilteringAttributeType


class SourceAttribute(BaseAttribute):
    info_path = "./backend/genealogy.json"

    @property
    def key(self) -> str:
        return "db_no"

    @property
    def display_name(self) -> str:
        return "DB No."

    @property
    def attr_type(self) -> FilteringAttributeType:
        return FilteringAttributeType(variant="multi_select")

    def extract(self, project_data: Dict[str, Any]) -> Any:
        filename = project_data.get("original_filename", "")
        if not filename:
            return ""

        if not self.info_path or not os.path.exists(self.info_path):
            return ""

        try:
            with open(self.info_path, "r", encoding="utf-8") as f:
                info = json.load(f)
        except (json.JSONDecodeError, OSError):
            return ""

        return info.get(filename, {}).get("idx", "")
