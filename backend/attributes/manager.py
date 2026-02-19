import os
import importlib.util
import inspect
from typing import Dict, List, Any
from attributes.base import BaseAttribute
from database import Database


class AttributeManager:
    def __init__(self, db: Database, definitions_dir: str):
        self.db = db
        self.definitions_dir = definitions_dir
        self.attributes: Dict[str, BaseAttribute] = {}
        self.load_attributes()

    def load_attributes(self):
        """Load attribute definitions from the definitions directory."""
        self.attributes = {}

        if not os.path.exists(self.definitions_dir):
            os.makedirs(self.definitions_dir)

        for filename in os.listdir(self.definitions_dir):
            if filename.endswith(".py") and not filename.startswith("_"):
                self._load_attribute_from_file(
                    os.path.join(self.definitions_dir, filename)
                )

        self._sync_db_schema()

    def _load_attribute_from_file(self, filepath: str):
        try:
            module_name = os.path.splitext(os.path.basename(filepath))[0]
            spec = importlib.util.spec_from_file_location(module_name, filepath)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                for name, obj in inspect.getmembers(module):
                    if (
                        inspect.isclass(obj)
                        and issubclass(obj, BaseAttribute)
                        and obj is not BaseAttribute
                    ):
                        instance = obj()
                        self.attributes[instance.key] = instance
                        print(
                            f"[INFO] Loaded attribute: {instance.key} ({instance.display_name})"
                        )
        except Exception as e:
            print(f"[ERROR] Failed to load attribute from {filepath}: {e}")

    def _sync_db_schema(self):
        """Ensure DB has columns for all active attributes."""
        # 1. Update attributes table
        active_attrs = [
            {
                "key": attr.key,
                "display_name": attr.display_name,
                "attr_type": attr.attr_type.asdict(),
            }
            for attr in self.attributes.values()
        ]
        self.db.sync_active_attributes(active_attrs)

        # 2. Add missing columns to projects table
        # We need to check existing columns first.
        # SQLite pragma table_info gives us columns.
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(projects)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        conn.close()

        for key in self.attributes.keys():
            if key not in existing_columns:
                print(f"[INFO] Adding column '{key}' to projects table.")
                # Default to TEXT for simplicity, or we could infer type from extract() return hint?
                # For now, TEXT is safest for flexible attributes.
                self.db.execute_ddl(f"ALTER TABLE projects ADD COLUMN {key} TEXT")

    def calculate_attributes(
        self, project_data: Dict[str, Any], *, use_llm: bool = False
    ) -> Dict[str, Any]:
        """Calculate all active attributes for a project.

        Args:
            project_data: Project metadata dictionary.
            use_llm: If True, use extract_with_llm() which refines results via
                     LLM for attributes that define an llm_extract_config.
                     Attributes without config fall back to plain extract().
        """
        results = {}
        for key, attr in self.attributes.items():
            try:
                if use_llm:
                    results[key] = attr.extract_with_llm(project_data)
                else:
                    results[key] = attr.extract(project_data)
            except Exception as e:
                print(f"[ERROR] Failed to calculate attribute {key}: {e}")
                results[key] = None
        return results

    def get_active_attributes(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": attr.key,
                "display_name": attr.display_name,
                "attr_type": attr.attr_type.asdict(),
            }
            for attr in self.attributes.values()
        ]
