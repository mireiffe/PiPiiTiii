import json
import sqlite3
from typing import List, Dict, Optional, Any


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                original_filename TEXT,
                created_at TEXT,
                status TEXT,
                slide_count INTEGER,
                title TEXT,
                subject TEXT,
                author TEXT,
                last_modified_by TEXT,
                revision_number TEXT,
                summary_data TEXT
            )
        """)

        # Migration: Add summary_data column if it doesn't exist
        cursor.execute("PRAGMA table_info(projects)")
        columns = [row[1] for row in cursor.fetchall()]
        if "summary_data" not in columns:
            cursor.execute("ALTER TABLE projects ADD COLUMN summary_data TEXT")
            print("Added summary_data column to projects table")

        # Migration: Add summary_data_llm column for LLM-generated content
        if "summary_data_llm" not in columns:
            cursor.execute("ALTER TABLE projects ADD COLUMN summary_data_llm TEXT")
            print("Added summary_data_llm column to projects table")

        # Migration: Add summary_prompt_version column for tracking prompt version
        if "summary_prompt_version" not in columns:
            cursor.execute("ALTER TABLE projects ADD COLUMN summary_prompt_version TEXT")
            print("Added summary_prompt_version column to projects table")

        # Migration: Add workflow_data column for Behavior Tree workflow
        if "workflow_data" not in columns:
            cursor.execute("ALTER TABLE projects ADD COLUMN workflow_data TEXT")
            print("Added workflow_data column to projects table")

        # Migration: Add kept column for archiving projects
        if "kept" not in columns:
            cursor.execute("ALTER TABLE projects ADD COLUMN kept INTEGER DEFAULT 0")
            print("Added kept column to projects table")

        # Migration: Add key_info_data column for 핵심정보 data
        if "key_info_data" not in columns:
            cursor.execute("ALTER TABLE projects ADD COLUMN key_info_data TEXT")
            print("Added key_info_data column to projects table")

        # Migration: Add key_info_completed column for 핵심정보 완료 상태
        if "key_info_completed" not in columns:
            cursor.execute("ALTER TABLE projects ADD COLUMN key_info_completed INTEGER DEFAULT 0")
            print("Added key_info_completed column to projects table")

        # Migration: Remove phenomenon_data column (deprecated, data moved to workflow_data)
        if "phenomenon_data" in columns:
            try:
                cursor.execute("ALTER TABLE projects DROP COLUMN phenomenon_data")
                print("Removed deprecated phenomenon_data column from projects table")
            except sqlite3.OperationalError:
                print("WARNING: Could not remove phenomenon_data column (SQLite version < 3.35.0)")
                print("The column is unused and can be safely ignored.")

        conn.commit()
        conn.close()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def add_project(self, project_data: Dict[str, Any]):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO projects (
                id, original_filename, created_at, status, slide_count,
                title, subject, author, last_modified_by, revision_number
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                project_data["id"],
                project_data["original_filename"],
                project_data["created_at"],
                project_data["status"],
                project_data.get("slide_count", 0),
                project_data.get("title", ""),
                project_data.get("subject", ""),
                project_data.get("author", "Unknown"),
                project_data.get("last_modified_by", ""),
                project_data.get("revision_number", ""),
            ),
        )
        conn.commit()
        conn.close()

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return dict(row)
        return None

    def list_projects(self) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM projects ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def update_project_status(self, project_id: str, status: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE projects SET status = ? WHERE id = ?", (status, project_id)
        )
        conn.commit()
        conn.close()

    def execute_ddl(self, sql: str):
        """Execute Data Definition Language (DDL) statements."""
        conn = self.get_connection()
        try:
            conn.execute(sql)
            conn.commit()
        except Exception as e:
            print(f"DDL Execution Error: {e}")
            raise
        finally:
            conn.close()

    def get_active_attributes(self) -> List[str]:
        """Get list of active attribute keys."""
        conn = self.get_connection()
        cursor = conn.cursor()
        # Ensure table exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attributes (
                key TEXT PRIMARY KEY,
                display_name TEXT,
                attr_type TEXT
            )
        """)
        self._ensure_attribute_type_column(cursor)
        cursor.execute("SELECT key FROM attributes")
        rows = cursor.fetchall()
        conn.close()
        return [row[0] for row in rows]

    def sync_active_attributes(self, attributes: List[Dict[str, Any]]):
        """
        Sync the attributes table with the provided list of active attributes.
        attributes: List of dicts with 'key', 'display_name', and 'attr_type'
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        # Ensure table exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attributes (
                key TEXT PRIMARY KEY,
                display_name TEXT,
                attr_type TEXT
            )
        """)
        self._ensure_attribute_type_column(cursor)

        # Get current keys
        cursor.execute("SELECT key FROM attributes")
        current_keys = {row[0] for row in cursor.fetchall()}

        new_keys = {attr["key"] for attr in attributes}

        # Insert new ones
        for attr in attributes:
            attr_type_json = json.dumps(attr.get("attr_type", {}))
            if attr["key"] not in current_keys:
                cursor.execute(
                    "INSERT INTO attributes (key, display_name, attr_type) VALUES (?, ?, ?)",
                    (attr["key"], attr["display_name"], attr_type_json),
                )
            else:
                cursor.execute(
                    "UPDATE attributes SET display_name = ?, attr_type = ? WHERE key = ?",
                    (attr["display_name"], attr_type_json, attr["key"]),
                )

        # Remove old ones
        for key in current_keys:
            if key not in new_keys:
                cursor.execute("DELETE FROM attributes WHERE key = ?", (key,))

        conn.commit()
        conn.close()

    @staticmethod
    def _ensure_attribute_type_column(cursor):
        cursor.execute("PRAGMA table_info(attributes)")
        columns = {row[1] for row in cursor.fetchall()}
        if "attr_type" not in columns:
            cursor.execute("ALTER TABLE attributes ADD COLUMN attr_type TEXT")

    def update_project_attributes(self, project_id: str, attributes: Dict[str, Any]):
        """Update dynamic attribute columns for a project."""
        if not attributes:
            return

        set_clause = ", ".join([f"{key} = ?" for key in attributes.keys()])
        values = list(attributes.values())
        values.append(project_id)

        sql = f"UPDATE projects SET {set_clause} WHERE id = ?"

        conn = self.get_connection()
        try:
            conn.execute(sql, values)
            conn.commit()
        except Exception as e:
            print(f"Error updating attributes for {project_id}: {e}")
        finally:
            conn.close()

    def get_distinct_values(self, column: str) -> List[Any]:
        """Get distinct values for a specific column (used for filters)."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"SELECT DISTINCT {column} FROM projects WHERE {column} IS NOT NULL ORDER BY {column}"
            )
            rows = cursor.fetchall()
            return [row[0] for row in rows]
        except Exception:
            # Column might not exist yet
            return []
        finally:
            conn.close()

    def get_numeric_range(self, column: str) -> Optional[Dict[str, float]]:
        """Return min/max numeric values for a column if available."""

        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"SELECT MIN(CAST({column} AS REAL)), MAX(CAST({column} AS REAL)) "
                f"FROM projects WHERE {column} IS NOT NULL"
            )
            min_val, max_val = cursor.fetchone()
            if min_val is None or max_val is None:
                return None
            return {"min": float(min_val), "max": float(max_val)}
        except Exception:
            return None
        finally:
            conn.close()

    def get_project_summary(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get summary data for a project (both user and LLM versions)."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT summary_data, summary_data_llm FROM projects WHERE id = ?",
            (project_id,),
        )
        row = cursor.fetchone()
        conn.close()
        result = {"user": {}, "llm": {}}
        if row:
            if row[0]:
                result["user"] = json.loads(row[0])
            if row[1]:
                result["llm"] = json.loads(row[1])
        return result

    def update_project_summary(self, project_id: str, summary_data: Dict[str, Any]):
        """Update user summary data for a project."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE projects SET summary_data = ? WHERE id = ?",
            (json.dumps(summary_data, ensure_ascii=False), project_id),
        )
        conn.commit()
        conn.close()

    def update_project_summary_llm(self, project_id: str, field_id: str, content: str):
        """Update LLM-generated summary for a specific field."""
        conn = self.get_connection()
        cursor = conn.cursor()
        # Get existing LLM data
        cursor.execute(
            "SELECT summary_data_llm FROM projects WHERE id = ?", (project_id,)
        )
        row = cursor.fetchone()
        llm_data = {}
        if row and row[0]:
            llm_data = json.loads(row[0])
        # Update specific field
        llm_data[field_id] = content
        cursor.execute(
            "UPDATE projects SET summary_data_llm = ? WHERE id = ?",
            (json.dumps(llm_data, ensure_ascii=False), project_id),
        )
        conn.commit()
        conn.close()

    def update_project_summary_prompt_version(self, project_id: str, prompt_version: str):
        """Update the prompt version used for summary generation."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE projects SET summary_prompt_version = ? WHERE id = ?",
            (prompt_version, project_id),
        )
        conn.commit()
        conn.close()

    def get_projects_summary_status(self) -> List[Dict[str, Any]]:
        """Get summary status for all projects (id, has_summary, prompt_version)."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, summary_data_llm, summary_prompt_version FROM projects"
        )
        rows = cursor.fetchall()
        conn.close()
        result = []
        for row in rows:
            has_summary = bool(row[1] and row[1] != '{}')
            result.append({
                "id": row[0],
                "has_summary": has_summary,
                "prompt_version": row[2] or None
            })
        return result

    def get_project_workflow(self, project_id: str, workflow_id: str = None) -> Optional[Dict[str, Any]]:
        """Get workflow data for a project.

        Args:
            project_id: The project ID
            workflow_id: Optional workflow ID. If provided, returns that specific workflow's data.
                        If not provided, returns all workflows data.

        Returns:
            If workflow_id is provided: The specific workflow data or None
            If workflow_id is None: Dict with 'workflows' key containing all workflow data
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT workflow_data FROM projects WHERE id = ?",
            (project_id,),
        )
        row = cursor.fetchone()
        conn.close()

        if not row or not row[0]:
            return {"workflows": {}} if workflow_id is None else None

        data = json.loads(row[0])

        # Migration: convert old single-workflow format to new multi-workflow format
        if isinstance(data, dict) and 'steps' in data and 'workflows' not in data:
            # Old format: { steps: [], ... }
            # Convert to new format: { workflows: { "default": { steps: [], ... } } }
            data = {"workflows": {"default": data}}

        # Ensure workflows key exists
        if not isinstance(data, dict) or 'workflows' not in data:
            data = {"workflows": {}}

        if workflow_id is not None:
            # Return specific workflow data
            return data.get("workflows", {}).get(workflow_id)

        return data

    def update_project_workflow(self, project_id: str, workflow_data: Dict[str, Any], workflow_id: str = None):
        """Update workflow data for a project.

        Args:
            project_id: The project ID
            workflow_data: The workflow data to save
            workflow_id: Optional workflow ID. If provided, updates only that workflow's data.
                        If not provided, replaces all workflow data (expects { workflows: {...} } format).
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        if workflow_id is not None:
            # Update specific workflow - first get existing data
            cursor.execute(
                "SELECT workflow_data FROM projects WHERE id = ?",
                (project_id,),
            )
            row = cursor.fetchone()

            existing_data = {"workflows": {}}
            if row and row[0]:
                existing_data = json.loads(row[0])
                # Migration from old format
                if isinstance(existing_data, dict) and 'steps' in existing_data and 'workflows' not in existing_data:
                    existing_data = {"workflows": {"default": existing_data}}
                elif not isinstance(existing_data, dict) or 'workflows' not in existing_data:
                    existing_data = {"workflows": {}}

            # Update or delete specific workflow
            if workflow_data is None:
                # Delete the workflow if data is None
                existing_data["workflows"].pop(workflow_id, None)
            else:
                existing_data["workflows"][workflow_id] = workflow_data
            workflow_data = existing_data

        cursor.execute(
            "UPDATE projects SET workflow_data = ? WHERE id = ?",
            (json.dumps(workflow_data, ensure_ascii=False), project_id),
        )
        conn.commit()
        conn.close()

    def update_project_kept(self, project_id: str, kept: bool):
        """Update the kept (archived) status of a project."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE projects SET kept = ? WHERE id = ?",
            (1 if kept else 0, project_id),
        )
        conn.commit()
        conn.close()

    def get_all_workflows(self) -> List[Dict[str, Any]]:
        """Get workflow data for all projects (for validation).

        Returns list of { id, workflows: { workflowId: ProjectWorkflowData, ... } }
        Handles migration from old single-workflow format.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, workflow_data FROM projects")
        rows = cursor.fetchall()
        conn.close()
        result = []
        for row in rows:
            workflows = {}
            if row[1]:
                try:
                    data = json.loads(row[1])
                    # Migration from old format
                    if isinstance(data, dict) and 'steps' in data and 'workflows' not in data:
                        workflows = {"default": data}
                    elif isinstance(data, dict) and 'workflows' in data:
                        workflows = data.get("workflows", {})
                except json.JSONDecodeError:
                    workflows = {}
            result.append({
                "id": row[0],
                "workflows": workflows
            })
        return result

    # ========== Key Info (핵심정보) Methods ==========

    def get_project_key_info(self, project_id: str) -> Dict[str, Any]:
        """Get key info data for a project (핵심정보 데이터 조회).

        Returns:
            Dict with 'instances' array containing key info instances
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT key_info_data FROM projects WHERE id = ?",
            (project_id,),
        )
        row = cursor.fetchone()
        conn.close()

        if not row or not row[0]:
            return {"instances": []}

        try:
            data = json.loads(row[0])
            # Ensure instances key exists
            if not isinstance(data, dict) or 'instances' not in data:
                data = {"instances": []}
            return data
        except json.JSONDecodeError:
            return {"instances": []}

    def update_project_key_info(self, project_id: str, key_info_data: Dict[str, Any]):
        """Update key info data for a project (핵심정보 데이터 저장)."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE projects SET key_info_data = ? WHERE id = ?",
            (json.dumps(key_info_data, ensure_ascii=False), project_id),
        )
        conn.commit()
        conn.close()

    def update_project_key_info_completed(self, project_id: str, completed: bool):
        """Update the key_info_completed status of a project."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE projects SET key_info_completed = ? WHERE id = ?",
            (1 if completed else 0, project_id),
        )
        conn.commit()
        conn.close()

    def get_all_keyinfo_status(self) -> List[Dict[str, Any]]:
        """Get keyinfo instance status for all projects.

        Returns list of { id, has_instances: bool }
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, key_info_data, key_info_completed FROM projects")
        rows = cursor.fetchall()
        conn.close()
        result = []
        for row in rows:
            has_instances = False
            if row[1]:
                try:
                    data = json.loads(row[1])
                    instances = data.get("instances", [])
                    has_instances = len(instances) > 0
                except (json.JSONDecodeError, AttributeError):
                    pass
            result.append({
                "id": row[0],
                "has_instances": has_instances,
                "completed": bool(row[2]) if row[2] is not None else False,
            })
        return result
