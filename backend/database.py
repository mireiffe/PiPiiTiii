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

    def update_project_database(
        self,
        project_id: str,
        slide_count: int,
        title: str = "",
        author: str = "",
        subject: str = "",
        last_modified_by: str = "",
        revision_number: str = "",
        status: str = "done",
    ):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE projects
            SET status = ?,
                slide_count = ?,
                title = ?,
                author = ?,
                subject = ?,
                last_modified_by = ?,
                revision_number = ?
            WHERE id = ?
            """,
            (
                status,
                slide_count,
                title,
                author,
                subject,
                last_modified_by,
                revision_number,
                project_id,
            ),
        )
        conn.commit()
        conn.close()

    def delete_project(self, project_id):
        """
        projects 테이블에서 주어진 project_id를 가진 행을 삭제한다.
        필요한 경우, 관련된 다른 테이블도 여기에서 같이 삭제하도록 확장하세요.
        """
        conn = self.get_connection()
        with conn:
            conn.execute(
                "DELETE FROM projects WHERE id = ?",
                (str(project_id),),
            )

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
