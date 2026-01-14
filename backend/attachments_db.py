"""
Separate SQLite database for storing attachment images as BLOBs.
This keeps binary data out of the main projects.db to improve performance.
"""

import sqlite3
import base64
from typing import Optional
from datetime import datetime


class AttachmentsDatabase:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS images (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                data BLOB NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        # Index for faster project-based lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_images_project_id
            ON images(project_id)
        """)
        conn.commit()
        conn.close()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def save_image(self, image_id: str, project_id: str, base64_data: str) -> bool:
        """
        Save an image to the database.

        Args:
            image_id: Unique identifier for the image (e.g., att_xxx)
            project_id: The project this image belongs to
            base64_data: Base64-encoded image data (with or without data URL prefix)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Remove data URL prefix if present (e.g., "data:image/png;base64,")
            if "," in base64_data:
                base64_data = base64_data.split(",", 1)[1]

            # Decode base64 to binary
            binary_data = base64.b64decode(base64_data)

            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO images (id, project_id, data, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (image_id, project_id, binary_data, datetime.now().isoformat()),
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving image {image_id}: {e}")
            return False

    def get_image(self, image_id: str) -> Optional[bytes]:
        """
        Retrieve an image from the database.

        Args:
            image_id: The unique identifier of the image

        Returns:
            Binary image data or None if not found
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT data FROM images WHERE id = ?", (image_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return row[0]
        return None

    def delete_image(self, image_id: str) -> bool:
        """
        Delete a single image from the database.

        Args:
            image_id: The unique identifier of the image

        Returns:
            True if deleted, False otherwise
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM images WHERE id = ?", (image_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            conn.close()
            return deleted
        except Exception as e:
            print(f"Error deleting image {image_id}: {e}")
            return False

    def delete_project_images(self, project_id: str) -> int:
        """
        Delete all images belonging to a project.

        Args:
            project_id: The project ID

        Returns:
            Number of images deleted
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM images WHERE project_id = ?", (project_id,))
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            return deleted_count
        except Exception as e:
            print(f"Error deleting images for project {project_id}: {e}")
            return 0

    def get_image_count(self, project_id: Optional[str] = None) -> int:
        """
        Get the count of images, optionally filtered by project.

        Args:
            project_id: Optional project ID to filter by

        Returns:
            Number of images
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        if project_id:
            cursor.execute(
                "SELECT COUNT(*) FROM images WHERE project_id = ?",
                (project_id,)
            )
        else:
            cursor.execute("SELECT COUNT(*) FROM images")

        count = cursor.fetchone()[0]
        conn.close()
        return count

    def get_database_size(self) -> int:
        """
        Get the size of the database file in bytes.

        Returns:
            Size in bytes
        """
        import os
        try:
            return os.path.getsize(self.db_path)
        except OSError:
            return 0
