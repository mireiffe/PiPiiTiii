"""
PPT File Resolution Utilities

This module provides utilities to resolve PPT file paths using multiple fallback strategies.
It handles cases where the stored path may be relative, absolute, or missing.
"""

import os
from typing import Optional
from fastapi import HTTPException


class PPTFileResolver:
    """Resolves PPT file paths using multiple strategies."""

    def __init__(self, base_dir: str, upload_dir: str, db):
        """
        Initialize the file resolver.

        Args:
            base_dir: Base directory for relative path resolution
            upload_dir: Directory where uploaded files are stored
            db: Database instance for metadata lookups
        """
        self.base_dir = base_dir
        self.upload_dir = upload_dir
        self.db = db

    def resolve_ppt_path(
        self, ppt_path: Optional[str], project_id: str, raise_on_not_found: bool = True
    ) -> Optional[str]:
        """
        Resolve PPT file path using multiple fallback strategies.

        Strategy 1: Convert relative to absolute path and check existence
        Strategy 2: Look for file in uploads using basename
        Strategy 3: Legacy fallback - search by project_id prefix
        Strategy 4: Database lookup using original_filename

        Args:
            ppt_path: Initial PPT path (may be None, relative, or absolute)
            project_id: Project ID for fallback strategies
            raise_on_not_found: If True, raises HTTPException when file not found

        Returns:
            Absolute path to PPT file, or None if not found and raise_on_not_found=False

        Raises:
            HTTPException: If file not found and raise_on_not_found=True
        """
        # Convert relative path to absolute path if needed
        if ppt_path and not os.path.isabs(ppt_path):
            ppt_path = os.path.join(self.base_dir, ppt_path)

        # Check if the path exists as-is
        if ppt_path and os.path.exists(ppt_path):
            return ppt_path

        # Try fallback strategies
        found_path = (
            self._strategy_basename(ppt_path)
            or self._strategy_project_prefix(project_id)
            or self._strategy_db_lookup(project_id)
        )

        if found_path:
            return found_path

        if raise_on_not_found:
            raise HTTPException(status_code=404, detail="Original PPT file not found")

        return None

    def _strategy_basename(self, ppt_path: Optional[str]) -> Optional[str]:
        """
        Strategy 1: Check if file exists in uploads with basename of stored path.

        Args:
            ppt_path: Original PPT path

        Returns:
            Resolved path or None
        """
        if not ppt_path:
            return None

        basename = os.path.basename(ppt_path)
        candidate = os.path.join(self.upload_dir, basename)

        if os.path.exists(candidate):
            return candidate

        return None

    def _strategy_project_prefix(self, project_id: str) -> Optional[str]:
        """
        Strategy 2: Legacy fallback - search for files with project_id prefix.

        Args:
            project_id: Project ID to search for

        Returns:
            Resolved path or None
        """
        try:
            for filename in os.listdir(self.upload_dir):
                if filename.startswith(project_id):
                    full_path = os.path.join(self.upload_dir, filename)
                    if os.path.isfile(full_path):
                        return full_path
        except Exception:
            pass

        return None

    def _strategy_db_lookup(self, project_id: str) -> Optional[str]:
        """
        Strategy 3: Look up original filename from database.

        Args:
            project_id: Project ID to query

        Returns:
            Resolved path or None
        """
        try:
            project_info = self.db.get_project(project_id)
            if project_info and project_info.get("original_filename"):
                orig_name = project_info["original_filename"]
                candidate = os.path.join(self.upload_dir, orig_name)

                if os.path.exists(candidate):
                    return candidate
        except Exception as e:
            print(f"DB lookup failed during file resolution: {e}")

        return None


def create_file_resolver(base_dir: str, upload_dir: str, db) -> PPTFileResolver:
    """
    Factory function to create a file resolver instance.

    Args:
        base_dir: Base directory for relative path resolution
        upload_dir: Directory where uploaded files are stored
        db: Database instance

    Returns:
        Configured PPTFileResolver instance
    """
    return PPTFileResolver(base_dir, upload_dir, db)
