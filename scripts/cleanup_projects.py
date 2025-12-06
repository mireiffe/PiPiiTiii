"""Utility to validate result folders and reconcile them with the projects database.

This script consolidates the behaviors of `cleanup_storage.py` and
`cleanup_database.py` into a single entry point:

1) Health check for each result folder (JSON existence, basic metadata, slides).
2) Consistency check with the SQLite database (`projects.db`).
3) Dry-run by default; use `--delete` to apply removals.
"""

import argparse
import json
import os
import shutil
import sys
from dataclasses import dataclass
from typing import Dict, List, Tuple

# Add backend to path to import Database
sys.path.append(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
)

from database import Database

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULT_DIR = os.path.join(BASE_DIR, "results")
DB_PATH = os.path.join(BASE_DIR, "backend", "data", "projects.db")


@dataclass
class FolderIssue:
    project_id: str
    reason: str
    path: str


@dataclass
class DbIssue:
    project_id: str
    reason: str


def validate_result_folder(project_id: str, folder_path: str) -> Tuple[bool, str]:
    """Perform simple health checks on a result folder."""

    json_path = os.path.join(folder_path, f"{project_id}.json")
    if not os.path.exists(json_path):
        return False, "Missing JSON file"

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:  # noqa: BLE001 - surface exact parsing errors for troubleshooting
        return False, f"Invalid JSON ({exc})"

    metadata = data.get("metadata")
    if not metadata or not isinstance(metadata, dict):
        return False, "Missing metadata section"

    slides = data.get("slides")
    if not isinstance(slides, list) or len(slides) == 0:
        return False, "No slides found"

    slides_count = data.get("slides_count")
    if isinstance(slides_count, int) and slides_count > 0:
        if slides_count != len(slides):
            return False, "Slide count does not match slides length"

    return True, ""


def collect_folder_issues() -> Tuple[Dict[str, str], List[FolderIssue]]:
    """Return healthy folders and the list of folders that failed validation."""

    if not os.path.exists(RESULT_DIR):
        print(f"Result directory not found: {RESULT_DIR}")
        return {}, []

    healthy: Dict[str, str] = {}
    issues: List[FolderIssue] = []

    for entry in sorted(os.listdir(RESULT_DIR)):
        folder_path = os.path.join(RESULT_DIR, entry)
        if not os.path.isdir(folder_path):
            continue

        ok, reason = validate_result_folder(entry, folder_path)
        if ok:
            healthy[entry] = folder_path
        else:
            issues.append(FolderIssue(project_id=entry, reason=reason, path=folder_path))

    return healthy, issues


def collect_db_state() -> List[Dict]:
    if not os.path.exists(DB_PATH):
        print(f"Database not found: {DB_PATH}")
        return []

    db = Database(DB_PATH)
    return db.list_projects()


def plan_cleanup(
    healthy_folders: Dict[str, str],
    invalid_folders: List[FolderIssue],
    db_projects: List[Dict],
) -> Tuple[List[FolderIssue], List[DbIssue]]:
    """Determine which folders/DB rows should be removed."""

    folders_to_delete: List[FolderIssue] = list(invalid_folders)
    db_to_delete: List[DbIssue] = []

    db_ids = {str(p["id"]): p for p in db_projects}

    # Folders that are healthy but not tracked in the DB
    for project_id, folder_path in healthy_folders.items():
        if project_id not in db_ids:
            folders_to_delete.append(
                FolderIssue(
                    project_id=project_id,
                    reason="Not present in database",
                    path=folder_path,
                )
            )

    # DB rows whose folders are missing or invalid
    invalid_ids = {issue.project_id for issue in invalid_folders}
    for project_id in db_ids:
        if project_id not in healthy_folders:
            reason = "Folder missing" if project_id not in invalid_ids else "Folder invalid"
            db_to_delete.append(DbIssue(project_id=project_id, reason=reason))

    return folders_to_delete, db_to_delete


def delete_folders(folders: List[FolderIssue]):
    for issue in folders:
        try:
            shutil.rmtree(issue.path)
            print(f"Deleted folder: {issue.project_id} ({issue.path})")
        except Exception as exc:  # noqa: BLE001 - surface exact deletion errors for troubleshooting
            print(f"Failed to delete folder {issue.project_id}: {exc}")


def delete_db_rows(db: Database, db_issues: List[DbIssue]):
    for issue in db_issues:
        try:
            db.delete_project(issue.project_id)
            print(f"Deleted DB entry: {issue.project_id}")
        except Exception as exc:  # noqa: BLE001 - surface exact deletion errors for troubleshooting
            print(f"Failed to delete DB entry {issue.project_id}: {exc}")


def print_summary(
    healthy_folders: Dict[str, str],
    invalid_folders: List[FolderIssue],
    folders_to_delete: List[FolderIssue],
    db_issues: List[DbIssue],
    delete: bool,
):
    print("\n=== Health Check ===")
    print(f"Healthy folders: {len(healthy_folders)}")
    if invalid_folders:
        print("Invalid folders:")
        for issue in invalid_folders:
            print(f" - {issue.project_id}: {issue.reason}")
    else:
        print("No invalid folders found.")

    print("\n=== Database Consistency ===")
    if db_issues:
        print("Entries to remove from database:")
        for issue in db_issues:
            print(f" - {issue.project_id}: {issue.reason}")
    else:
        print("No database entries require removal.")

    print("\n=== Cleanup Plan ===")
    if folders_to_delete:
        print("Folders marked for deletion:")
        for issue in folders_to_delete:
            print(f" - {issue.project_id}: {issue.reason}")
    else:
        print("No folders need deletion.")

    action = "Applying deletions" if delete else "Dry run (no deletions performed)"
    print(f"\n{action}.")


def main(delete: bool):
    healthy_folders, invalid_folders = collect_folder_issues()
    db_projects = collect_db_state()

    if not healthy_folders and not invalid_folders:
        return

    folders_to_delete, db_issues = plan_cleanup(healthy_folders, invalid_folders, db_projects)
    print_summary(healthy_folders, invalid_folders, folders_to_delete, db_issues, delete)

    if delete:
        db = Database(DB_PATH)
        delete_folders(folders_to_delete)
        delete_db_rows(db, db_issues)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Validate result folders, compare them with projects.db, and clean up"
            " inconsistencies."
        )
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Apply deletions. Without this flag, the script runs in dry-run mode.",
    )
    args = parser.parse_args()

    main(delete=args.delete)
