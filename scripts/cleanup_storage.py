import os
import sys
import shutil
import argparse
import json
from datetime import datetime

# Add backend to path to import Database
sys.path.append(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
)

from database import Database

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULT_DIR = os.path.join(BASE_DIR, "results")
DB_PATH = os.path.join(BASE_DIR, "backend", "data", "projects.db")


def cleanup(delete=False):
    if not os.path.exists(RESULT_DIR):
        print(f"Result directory not found: {RESULT_DIR}")
        return

    if not os.path.exists(DB_PATH):
        print(f"Database not found: {DB_PATH}")
        return

    print(f"Checking {RESULT_DIR} against {DB_PATH}...")

    db = Database(DB_PATH)
    projects = db.list_projects()
    # Create a set of valid project IDs
    valid_ids = {p["id"] for p in projects}

    # List directories in results
    found_folders = os.listdir(RESULT_DIR)

    orphans = []
    for folder in found_folders:
        folder_path = os.path.join(RESULT_DIR, folder)
        if not os.path.isdir(folder_path):
            continue

        if folder not in valid_ids:
            orphans.append(folder)

    if not orphans:
        print("No orphaned folders found. All clean!")
        return

    print(f"Found {len(orphans)} orphaned folders:")
    for orphan in orphans:
        folder_path = os.path.join(RESULT_DIR, orphan)
        json_path = os.path.join(folder_path, f"{orphan}.json")

        details = ""
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                stats = os.stat(json_path)
                created_at = datetime.fromtimestamp(stats.st_ctime).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

                metadata = data.get("metadata", {})
                builtin = metadata.get("builtin_properties", {})
                title = builtin.get("Title") or "No Title"
                author = builtin.get("Author") or "Unknown Author"

                details = f" | {created_at} | {title} | {author}"
            except Exception:
                details = " | (Error reading JSON)"
        else:
            details = " | (No JSON found)"

        print(f" - {orphan}{details}")

    if delete:
        print("\nDeleting orphaned folders...")
        for orphan in orphans:
            folder_path = os.path.join(RESULT_DIR, orphan)
            try:
                shutil.rmtree(folder_path)
                print(f"Deleted: {orphan}")
            except Exception as e:
                print(f"Failed to delete {orphan}: {e}")
        print("Cleanup complete.")
    else:
        print("\nRun with --delete to remove these folders.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Cleanup orphaned project folders in results directory."
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete orphaned folders instead of just listing them.",
    )
    args = parser.parse_args()

    cleanup(delete=args.delete)
