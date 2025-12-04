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
                revision_number TEXT
            )
        """)
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