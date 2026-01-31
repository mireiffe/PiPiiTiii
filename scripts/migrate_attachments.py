#!/usr/bin/env python3
"""
Migration script to move base64 image attachments from projects.db to attachments.db.

Usage:
    python migrate_attachments.py

This script:
1. Reads all workflows from projects.db
2. Finds image attachments with base64 data (no imageId)
3. Saves images to attachments.db
4. Updates workflow data with imageId references
5. Removes base64 data from workflow_data
"""

import os
import sys

# Add backend directory to path for imports
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))

from database import Database
from attachments_db import AttachmentsDatabase


def migrate_attachments():
    # Database paths
    db_path = os.path.join(BASE_DIR, "backend", "data", "projects.db")
    attachments_db_path = os.path.join(BASE_DIR, "backend", "data", "attachments.db")

    print(f"Projects DB: {db_path}")
    print(f"Attachments DB: {attachments_db_path}")

    # Initialize databases
    db = Database(db_path)
    attachments_db = AttachmentsDatabase(attachments_db_path)

    # Get all workflows
    all_workflows = db.get_all_workflows()
    print(f"\nFound {len(all_workflows)} projects to check")

    total_migrated = 0
    total_skipped = 0
    projects_updated = 0

    for project in all_workflows:
        project_id = project["id"]
        workflow = project.get("workflow")

        if not workflow:
            continue

        steps = workflow.get("steps", [])
        if not steps:
            continue

        workflow_modified = False
        project_migrated = 0

        for step in steps:
            attachments = step.get("attachments", [])

            for attachment in attachments:
                # Skip if not an image
                if attachment.get("type") != "image":
                    continue

                # Skip if already has imageId (already migrated)
                if attachment.get("imageId"):
                    total_skipped += 1
                    continue

                # Check if has base64 data
                base64_data = attachment.get("data")
                if not base64_data:
                    continue

                # Use attachment id as imageId
                image_id = attachment.get("id")
                if not image_id:
                    print(f"  [WARN] Attachment without id in project {project_id}")
                    continue

                # Save to attachments.db
                print(f"  Migrating image {image_id} from project {project_id}...")
                success = attachments_db.save_image(image_id, project_id, base64_data)

                if success:
                    # Update attachment: add imageId, remove data
                    attachment["imageId"] = image_id
                    del attachment["data"]
                    workflow_modified = True
                    project_migrated += 1
                    total_migrated += 1
                    print("    -> Saved to attachments.db")
                else:
                    print(f"    [ERROR] Failed to save image {image_id}")

        # Update workflow in projects.db if modified
        if workflow_modified:
            db.update_project_workflow(project_id, workflow)
            projects_updated += 1
            print(f"  Updated workflow for project {project_id} ({project_migrated} images)")

    print("\n" + "=" * 50)
    print("Migration Summary:")
    print(f"  Projects checked: {len(all_workflows)}")
    print(f"  Projects updated: {projects_updated}")
    print(f"  Images migrated: {total_migrated}")
    print(f"  Images skipped (already migrated): {total_skipped}")
    print("=" * 50)

    # Show database sizes
    projects_db_size = os.path.getsize(db_path) / 1024 / 1024
    attachments_db_size = attachments_db.get_database_size() / 1024 / 1024
    print("\nDatabase sizes:")
    print(f"  projects.db: {projects_db_size:.2f} MB")
    print(f"  attachments.db: {attachments_db_size:.2f} MB")


if __name__ == "__main__":
    print("=" * 50)
    print("Attachment Migration Script")
    print("Base64 -> attachments.db")
    print("=" * 50)

    response = input("\nThis will modify your database. Continue? (y/N): ")
    if response.lower() != "y":
        print("Aborted.")
        sys.exit(0)

    migrate_attachments()
    print("\nDone!")
