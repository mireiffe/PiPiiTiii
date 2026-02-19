"""Swap PPT-derived data between two projects.

When two PPT files are registered to the wrong project IDs (swapped),
this script exchanges only the PPT-originated data while keeping
user-defined attributes (file_extension, file_source, db_no, etc.) in place.

Usage:
    python scripts/swap_projects.py <project_id_1> <project_id_2>           # dry-run (default)
    python scripts/swap_projects.py <project_id_1> <project_id_2> --apply   # actually swap
"""

import argparse
import os
import shutil
import sqlite3
import sys
from datetime import datetime

# Add backend to path to import Database
sys.path.append(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
)


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULT_DIR = os.path.join(BASE_DIR, "results")
DB_PATH = os.path.join(BASE_DIR, "backend", "data", "projects.db")
ATTACHMENTS_DB_PATH = os.path.join(BASE_DIR, "backend", "data", "attachments.db")
BACKUP_DIR = os.path.join(BASE_DIR, "backend", "data", "backups")

# Columns that come from the PPT file or are user-entered about that PPT's content.
# These travel with the PPT when swapping.
SWAP_COLUMNS = [
    "original_filename",
    "slide_count",
    "title",
    "subject",
    "author",
    "last_modified_by",
    "revision_number",
    "summary_data",
    "summary_data_llm",
    "summary_prompt_version",
    "workflow_data",
    "key_info_data",
    "key_info_completed",
]


def backup_databases():
    """Create timestamped backup copies of both DB files."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    backed_up = []
    for src_path, label in [(DB_PATH, "projects"), (ATTACHMENTS_DB_PATH, "attachments")]:
        if os.path.exists(src_path):
            dst = os.path.join(BACKUP_DIR, f"{label}_{ts}.db")
            shutil.copy2(src_path, dst)
            backed_up.append(dst)
            print(f"  Backup: {dst}")
    return backed_up


def get_project_row(conn, project_id):
    """Fetch a full project row as a dict."""
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    row = cur.fetchone()
    if row is None:
        return None
    return dict(row)


def print_project_summary(label, row):
    """Print key fields of a project for visual confirmation."""
    print(f"\n  [{label}] id = {row['id']}")
    for col in SWAP_COLUMNS:
        val = row.get(col)
        if val is not None and isinstance(val, str) and len(val) > 80:
            val = val[:77] + "..."
        print(f"    {col}: {val}")


def swap_db_columns(conn, id1, id2, row1, row2, dry_run):
    """Swap SWAP_COLUMNS values between two project rows."""
    if dry_run:
        print("\n[DRY-RUN] Would swap the following DB columns:")
        for col in SWAP_COLUMNS:
            v1, v2 = row1.get(col), row2.get(col)
            if v1 != v2:
                v1_short = repr(v1)[:60] if v1 is not None else "NULL"
                v2_short = repr(v2)[:60] if v2 is not None else "NULL"
                print(f"    {col}: {v1_short} <-> {v2_short}")
        return

    cur = conn.cursor()

    # Build a single UPDATE per project for atomicity within the transaction
    set_clause = ", ".join(f"{col} = ?" for col in SWAP_COLUMNS)

    # Values from row2 -> project id1
    vals_for_1 = [row2.get(col) for col in SWAP_COLUMNS] + [id1]
    cur.execute(f"UPDATE projects SET {set_clause} WHERE id = ?", vals_for_1)

    # Values from row1 -> project id2
    vals_for_2 = [row1.get(col) for col in SWAP_COLUMNS] + [id2]
    cur.execute(f"UPDATE projects SET {set_clause} WHERE id = ?", vals_for_2)

    print("  DB columns swapped.")


def swap_result_dirs(id1, id2, dry_run):
    """Swap the contents of results/{id1}/ and results/{id2}/ directories."""
    dir1 = os.path.join(RESULT_DIR, id1)
    dir2 = os.path.join(RESULT_DIR, id2)

    dir1_exists = os.path.isdir(dir1)
    dir2_exists = os.path.isdir(dir2)

    if not dir1_exists and not dir2_exists:
        print("  No result directories found for either project. Skipping.")
        return

    if dry_run:
        print("\n[DRY-RUN] Would swap result directories:")
        print(f"    {dir1} (exists={dir1_exists})")
        print(f"    {dir2} (exists={dir2_exists})")
        return

    tmp_dir = os.path.join(RESULT_DIR, f"_swap_tmp_{id1}")

    # Step 1: dir1 -> tmp
    if dir1_exists:
        os.rename(dir1, tmp_dir)

    # Step 2: dir2 -> dir1
    if dir2_exists:
        os.rename(dir2, dir1)

    # Step 3: tmp -> dir2
    if dir1_exists:
        os.rename(tmp_dir, dir2)

    # Step 4: Rename JSON files inside each directory to match their new project ID
    _rename_json(dir1, id2, id1)  # was id2's data, now lives in dir1
    _rename_json(dir2, id1, id2)  # was id1's data, now lives in dir2

    print("  Result directories swapped.")


def _rename_json(directory, old_id, new_id):
    """Rename {old_id}.json -> {new_id}.json inside a directory if it exists."""
    if not os.path.isdir(directory):
        return
    old_json = os.path.join(directory, f"{old_id}.json")
    new_json = os.path.join(directory, f"{new_id}.json")
    if os.path.exists(old_json):
        os.rename(old_json, new_json)
        print(f"    Renamed {old_id}.json -> {new_id}.json in {os.path.basename(directory)}/")


def swap_attachment_project_ids(id1, id2, dry_run):
    """Swap project_id references in the attachments database."""
    if not os.path.exists(ATTACHMENTS_DB_PATH):
        print("  Attachments DB not found. Skipping.")
        return

    conn = sqlite3.connect(ATTACHMENTS_DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT id FROM images WHERE project_id = ?", (id1,))
    imgs_1 = [r[0] for r in cur.fetchall()]

    cur.execute("SELECT id FROM images WHERE project_id = ?", (id2,))
    imgs_2 = [r[0] for r in cur.fetchall()]

    if not imgs_1 and not imgs_2:
        print("  No attachment images for either project. Skipping.")
        conn.close()
        return

    if dry_run:
        print("\n[DRY-RUN] Would swap attachment project_ids:")
        print(f"    Project {id1}: {len(imgs_1)} image(s) -> will become {id2}")
        print(f"    Project {id2}: {len(imgs_2)} image(s) -> will become {id1}")
        conn.close()
        return

    # Use a temporary sentinel to avoid unique-constraint issues
    tmp_id = f"_swap_tmp_{id1}"
    cur.execute("UPDATE images SET project_id = ? WHERE project_id = ?", (tmp_id, id1))
    cur.execute("UPDATE images SET project_id = ? WHERE project_id = ?", (id1, id2))
    cur.execute("UPDATE images SET project_id = ? WHERE project_id = ?", (id2, tmp_id))
    conn.commit()
    conn.close()

    print(f"  Attachment project_ids swapped ({len(imgs_1)} <-> {len(imgs_2)} images).")


def main():
    parser = argparse.ArgumentParser(
        description="Swap PPT-derived data between two projects"
    )
    parser.add_argument("id1", help="First project ID")
    parser.add_argument("id2", help="Second project ID")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually perform the swap (default is dry-run)",
    )
    args = parser.parse_args()

    dry_run = not args.apply
    id1, id2 = args.id1, args.id2

    if id1 == id2:
        print("ERROR: Both project IDs are the same.")
        sys.exit(1)

    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database not found at {DB_PATH}")
        sys.exit(1)

    # ── Read current state ──────────────────────────────────────────
    conn = sqlite3.connect(DB_PATH)
    row1 = get_project_row(conn, id1)
    row2 = get_project_row(conn, id2)

    if row1 is None:
        print(f"ERROR: Project {id1} not found in DB.")
        conn.close()
        sys.exit(1)
    if row2 is None:
        print(f"ERROR: Project {id2} not found in DB.")
        conn.close()
        sys.exit(1)

    mode_label = "DRY-RUN" if dry_run else "APPLY"
    print(f"{'='*60}")
    print(f"  PPT Data Swap [{mode_label}]")
    print(f"{'='*60}")

    print("\n── Current State ──")
    print_project_summary("Project A", row1)
    print_project_summary("Project B", row2)

    # ── Backup ──────────────────────────────────────────────────────
    if not dry_run:
        print("\n── Creating Backups ──")
        backup_databases()

    # ── Swap DB columns ─────────────────────────────────────────────
    print("\n── DB Column Swap ──")
    swap_db_columns(conn, id1, id2, row1, row2, dry_run)

    if not dry_run:
        conn.commit()
    conn.close()

    # ── Swap result directories ─────────────────────────────────────
    print("\n── Result Directory Swap ──")
    swap_result_dirs(id1, id2, dry_run)

    # ── Swap attachment images ──────────────────────────────────────
    print("\n── Attachment Image Swap ──")
    swap_attachment_project_ids(id1, id2, dry_run)

    # ── Verification ────────────────────────────────────────────────
    if not dry_run:
        print("\n── Verification (After Swap) ──")
        conn = sqlite3.connect(DB_PATH)
        new_row1 = get_project_row(conn, id1)
        new_row2 = get_project_row(conn, id2)
        conn.close()
        print_project_summary("Project A (after)", new_row1)
        print_project_summary("Project B (after)", new_row2)

    print(f"\n{'='*60}")
    if dry_run:
        print("  Dry-run complete. No changes were made.")
        print("  Run with --apply to perform the actual swap.")
    else:
        print("  Swap completed successfully!")
        print(f"  Backups saved in: {BACKUP_DIR}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
