#!/usr/bin/env python3
"""
Data consolidation script for PiPiiTiii.

Reads projects.db, attachments.db, settings.json and produces a single
consolidated SQLite database with a normalized, PostgreSQL-ready schema.

Usage:
    python scripts/consolidate_data.py                  # dry-run (default)
    python scripts/consolidate_data.py --execute        # actually create DB
    python scripts/consolidate_data.py --execute --remove-unused-attrs
    python scripts/consolidate_data.py --execute --output-dir ./export
"""

import argparse
import json
import os
import shutil
import sqlite3
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Source paths
PROJECTS_DB_PATH = os.path.join(BASE_DIR, "backend", "data", "projects.db")
ATTACHMENTS_DB_PATH = os.path.join(BASE_DIR, "backend", "data", "attachments.db")
SETTINGS_FILE_PATH = os.path.join(BASE_DIR, "backend", "data", "settings.json")

# Default output directory
DEFAULT_OUTPUT_DIR = os.path.join(BASE_DIR, "scripts", "output")

# Columns that are always part of the projects table (not dynamic attributes)
CORE_PROJECT_COLUMNS = {
    "id",
    "original_filename",
    "created_at",
    "status",
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
    "kept",
    "key_info_data",
    "key_info_completed",
}

# Columns to drop from the consolidated projects table
# (data moved to normalized tables or no longer needed)
COLUMNS_TO_DROP = {
    "key_info_data",           # → key_info_instances, key_info_captures, key_info_images
    "summary_prompt_version",  # operational metadata, not needed in consolidated DB
}


# ---------------------------------------------------------------------------
# Schema definitions
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
-- Projects: core metadata + active dynamic attribute columns
CREATE TABLE IF NOT EXISTS projects (
    id                  TEXT PRIMARY KEY,
    original_filename   TEXT,
    created_at          TEXT,
    status              TEXT,
    slide_count         INTEGER,
    title               TEXT,
    subject             TEXT,
    author              TEXT,
    last_modified_by    TEXT,
    revision_number     TEXT,
    summary_data        TEXT,       -- JSON: user-edited summaries
    summary_data_llm    TEXT,       -- JSON: LLM-generated summaries
    workflow_data       TEXT,       -- JSON: workflow data
    kept                INTEGER DEFAULT 0,
    key_info_completed  INTEGER DEFAULT 0,
    used_key_info_ids   TEXT        -- JSON array: item IDs used by this project
);

-- KeyInfo definitions from settings.json (category + item flattened)
CREATE TABLE IF NOT EXISTS key_info_definitions (
    item_id             TEXT PRIMARY KEY,
    category_id         TEXT NOT NULL,
    category_name       TEXT NOT NULL,
    category_order      INTEGER,
    item_title          TEXT NOT NULL,
    item_description    TEXT,
    item_order          INTEGER,
    system_prompt       TEXT,
    user_prompt         TEXT,
    created_at          TEXT
);

-- KeyInfo instances: one row per (project, category, item) entry
CREATE TABLE IF NOT EXISTS key_info_instances (
    id                  TEXT PRIMARY KEY,
    project_id          TEXT NOT NULL REFERENCES projects(id),
    category_id         TEXT NOT NULL,
    item_id             TEXT NOT NULL,
    text_value          TEXT,
    item_order          INTEGER,
    created_at          TEXT,
    updated_at          TEXT
);
CREATE INDEX IF NOT EXISTS idx_kii_project ON key_info_instances(project_id);
CREATE INDEX IF NOT EXISTS idx_kii_category ON key_info_instances(category_id);
CREATE INDEX IF NOT EXISTS idx_kii_item ON key_info_instances(item_id);

-- Capture regions linked to key_info instances
CREATE TABLE IF NOT EXISTS key_info_captures (
    id                  TEXT PRIMARY KEY,
    instance_id         TEXT NOT NULL REFERENCES key_info_instances(id),
    slide_index         INTEGER,
    x                   REAL,
    y                   REAL,
    width               REAL,
    height              REAL,
    label               TEXT,
    caption             TEXT
);
CREATE INDEX IF NOT EXISTS idx_kic_instance ON key_info_captures(instance_id);

-- Image attachments linked to key_info instances
CREATE TABLE IF NOT EXISTS key_info_images (
    instance_id         TEXT NOT NULL REFERENCES key_info_instances(id),
    image_id            TEXT NOT NULL,
    caption             TEXT,
    PRIMARY KEY (instance_id, image_id)
);
CREATE INDEX IF NOT EXISTS idx_kim_instance ON key_info_images(instance_id);

-- Image BLOBs (from attachments.db)
CREATE TABLE IF NOT EXISTS images (
    id                  TEXT PRIMARY KEY,
    project_id          TEXT NOT NULL REFERENCES projects(id),
    data                BLOB NOT NULL,
    created_at          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_images_project ON images(project_id);
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_settings() -> dict:
    """Load settings.json if it exists."""
    if not os.path.exists(SETTINGS_FILE_PATH):
        return {}
    with open(SETTINGS_FILE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_source_columns(db_path: str, table: str) -> List[str]:
    """Return column names for a table in the source DB."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cursor.fetchall()]
    conn.close()
    return cols


def detect_dynamic_attr_columns(db_path: str) -> List[str]:
    """Return column names in projects that are dynamic attributes."""
    all_cols = get_source_columns(db_path, "projects")
    return [c for c in all_cols if c not in CORE_PROJECT_COLUMNS]


def detect_unused_attr_columns(db_path: str, attr_cols: List[str]) -> List[str]:
    """Return attribute columns where ALL values are NULL."""
    if not attr_cols:
        return []
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    unused = []
    for col in attr_cols:
        cursor.execute(
            f"SELECT COUNT(*) FROM projects WHERE [{col}] IS NOT NULL AND [{col}] != ''"
        )
        count = cursor.fetchone()[0]
        if count == 0:
            unused.append(col)
    conn.close()
    return unused


def get_active_attributes(db_path: str) -> List[Dict[str, Any]]:
    """Read the attributes metadata table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT key, display_name, attr_type FROM attributes")
        rows = cursor.fetchall()
        return [
            {"key": r[0], "display_name": r[1], "attr_type": r[2]}
            for r in rows
        ]
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()


def parse_key_info_instances(key_info_json: Optional[str]) -> Tuple[
    List[Dict], List[Dict], List[Dict]
]:
    """
    Parse key_info_data JSON string into normalized rows.
    Returns (instances, captures, images).
    Handles legacy single-value → array migration.
    """
    instances_out: List[Dict] = []
    captures_out: List[Dict] = []
    images_out: List[Dict] = []

    if not key_info_json:
        return instances_out, captures_out, images_out

    try:
        data = json.loads(key_info_json)
    except json.JSONDecodeError:
        return instances_out, captures_out, images_out

    for inst in data.get("instances", []):
        inst_id = inst.get("id", "")
        if not inst_id:
            continue

        instances_out.append({
            "id": inst_id,
            "category_id": inst.get("categoryId", ""),
            "item_id": inst.get("itemId", ""),
            "text_value": inst.get("textValue"),
            "item_order": inst.get("order", 0),
            "created_at": inst.get("createdAt", ""),
            "updated_at": inst.get("updatedAt"),
        })

        # --- Captures (migrate legacy single → array) ---
        capture_values = inst.get("captureValues") or []
        legacy_capture = inst.get("captureValue")
        if not capture_values and legacy_capture:
            capture_values = [legacy_capture]

        for cap in capture_values:
            cap_id = cap.get("id", "")
            if not cap_id:
                continue
            captures_out.append({
                "id": cap_id,
                "instance_id": inst_id,
                "slide_index": cap.get("slideIndex"),
                "x": cap.get("x"),
                "y": cap.get("y"),
                "width": cap.get("width"),
                "height": cap.get("height"),
                "label": cap.get("label"),
                "caption": cap.get("caption"),
            })

        # --- Images (migrate legacy single → array) ---
        image_ids = inst.get("imageIds") or []
        image_captions: Dict[str, str] = inst.get("imageCaptions") or {}
        legacy_image_id = inst.get("imageId")
        legacy_image_caption = inst.get("imageCaption")
        if not image_ids and legacy_image_id:
            image_ids = [legacy_image_id]
            if legacy_image_caption:
                image_captions[legacy_image_id] = legacy_image_caption

        for img_id in image_ids:
            images_out.append({
                "instance_id": inst_id,
                "image_id": img_id,
                "caption": image_captions.get(img_id),
            })

    return instances_out, captures_out, images_out


def compute_used_key_info_ids(key_info_json: Optional[str]) -> List[str]:
    """Extract unique item IDs used by a project's key_info_data."""
    if not key_info_json:
        return []
    try:
        data = json.loads(key_info_json)
    except json.JSONDecodeError:
        return []
    seen: Set[str] = set()
    for inst in data.get("instances", []):
        item_id = inst.get("itemId", "")
        if item_id:
            seen.add(item_id)
    return sorted(seen)


# ---------------------------------------------------------------------------
# Analysis (dry-run)
# ---------------------------------------------------------------------------

def analyze(remove_unused_attrs: bool) -> Dict[str, Any]:
    """Analyze source data and return a report dict."""
    report: Dict[str, Any] = {"errors": []}

    # --- Check source files ---
    for label, path in [
        ("projects.db", PROJECTS_DB_PATH),
        ("attachments.db", ATTACHMENTS_DB_PATH),
        ("settings.json", SETTINGS_FILE_PATH),
    ]:
        exists = os.path.exists(path)
        size_mb = os.path.getsize(path) / (1024 * 1024) if exists else 0
        report[label] = {"exists": exists, "path": path, "size_mb": round(size_mb, 2)}
        if not exists:
            report["errors"].append(f"{label} not found at {path}")

    if report["errors"]:
        return report

    # --- Projects ---
    conn = sqlite3.connect(PROJECTS_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM projects")
    report["project_count"] = cursor.fetchone()[0]
    conn.close()

    # --- Dynamic attributes ---
    attr_cols = detect_dynamic_attr_columns(PROJECTS_DB_PATH)
    report["dynamic_attr_columns"] = attr_cols
    report["active_attributes"] = get_active_attributes(PROJECTS_DB_PATH)

    unused_attrs = detect_unused_attr_columns(PROJECTS_DB_PATH, attr_cols)
    report["unused_attr_columns"] = unused_attrs
    report["remove_unused_attrs"] = remove_unused_attrs

    if remove_unused_attrs:
        report["kept_attr_columns"] = [c for c in attr_cols if c not in unused_attrs]
    else:
        report["kept_attr_columns"] = attr_cols

    # --- KeyInfo definitions (from settings) ---
    settings = load_settings()
    ki_settings = settings.get("key_info_settings", {})
    categories = ki_settings.get("categories", [])
    definition_count = sum(len(cat.get("items", [])) for cat in categories)
    report["key_info_categories"] = len(categories)
    report["key_info_definitions"] = definition_count

    # --- KeyInfo instances (from projects) ---
    conn = sqlite3.connect(PROJECTS_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, key_info_data FROM projects")
    rows = cursor.fetchall()
    conn.close()

    total_instances = 0
    total_captures = 0
    total_images = 0
    for row in rows:
        instances, captures, images = parse_key_info_instances(row["key_info_data"])
        total_instances += len(instances)
        total_captures += len(captures)
        total_images += len(images)

    report["key_info_instances"] = total_instances
    report["key_info_captures"] = total_captures
    report["key_info_image_refs"] = total_images

    # --- Attachments ---
    conn = sqlite3.connect(ATTACHMENTS_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM images")
    report["attachment_count"] = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(LENGTH(data)) FROM images")
    blob_bytes = cursor.fetchone()[0] or 0
    report["attachment_blob_mb"] = round(blob_bytes / (1024 * 1024), 2)
    conn.close()

    return report


def print_report(report: Dict[str, Any]):
    """Pretty-print the analysis report."""
    print()
    print("=" * 60)
    print("  Data Consolidation — Analysis Report")
    print("=" * 60)

    if report.get("errors"):
        print("\n  [ERRORS]")
        for err in report["errors"]:
            print(f"    - {err}")
        print("\n  Fix the above errors before running with --execute.")
        return

    # Source files
    print("\n  Source Files:")
    for label in ("projects.db", "attachments.db", "settings.json"):
        info = report[label]
        status = "OK" if info["exists"] else "MISSING"
        print(f"    {label:20s}  {status:8s}  {info['size_mb']:>8.2f} MB")

    # Projects
    print(f"\n  Projects:                {report['project_count']}")

    # Dynamic attributes
    print(f"\n  Dynamic Attribute Columns ({len(report['dynamic_attr_columns'])}):")
    for col in report["dynamic_attr_columns"]:
        is_unused = col in report.get("unused_attr_columns", [])
        marker = " [UNUSED — will remove]" if is_unused and report["remove_unused_attrs"] else ""
        marker = " [UNUSED]" if is_unused and not report["remove_unused_attrs"] else marker
        print(f"    - {col}{marker}")

    if report["remove_unused_attrs"] and report["unused_attr_columns"]:
        print(f"    → {len(report['unused_attr_columns'])} column(s) will be removed")

    # KeyInfo
    print(f"\n  KeyInfo Definitions:     {report['key_info_definitions']} items in {report['key_info_categories']} categories")
    print(f"  KeyInfo Instances:       {report['key_info_instances']}")
    print(f"  KeyInfo Captures:        {report['key_info_captures']}")
    print(f"  KeyInfo Image Refs:      {report['key_info_image_refs']}")

    # Attachments
    print(f"\n  Attachment Images:       {report['attachment_count']}  ({report['attachment_blob_mb']:.2f} MB)")

    # Output tables
    print("\n  Output Tables:")
    print("    - projects              (core metadata + active attrs + used_key_info_ids)")
    print("    - key_info_definitions  (category/item definitions from settings)")
    print("    - key_info_instances    (per-project key_info entries)")
    print("    - key_info_captures     (capture regions per instance)")
    print("    - key_info_images       (image refs per instance)")
    print("    - images                (BLOB data from attachments.db)")
    print()
    print("=" * 60)
    print("  This is a DRY RUN. Use --execute to create the consolidated DB.")
    print("=" * 60)
    print()


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

def execute(report: Dict[str, Any], output_dir: str):
    """Create the consolidated database."""

    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_db_path = os.path.join(output_dir, f"consolidated_{timestamp}.db")
    print(f"\n  Creating: {output_db_path}")

    # --- Create schema ---
    out_conn = sqlite3.connect(output_db_path)
    out_conn.executescript(SCHEMA_SQL)

    # --- 1) key_info_definitions from settings.json ---
    settings = load_settings()
    ki_settings = settings.get("key_info_settings", {})
    categories = ki_settings.get("categories", [])

    def_count = 0
    for cat in categories:
        cat_id = cat.get("id", "")
        cat_name = cat.get("name", "")
        cat_order = cat.get("order", 0)
        system_prompt = cat.get("systemPrompt")
        user_prompt = cat.get("userPrompt")
        created_at = cat.get("createdAt", "")

        for item in cat.get("items", []):
            out_conn.execute(
                """INSERT INTO key_info_definitions
                   (item_id, category_id, category_name, category_order,
                    item_title, item_description, item_order,
                    system_prompt, user_prompt, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    item.get("id", ""),
                    cat_id,
                    cat_name,
                    cat_order,
                    item.get("title", ""),
                    item.get("description", ""),
                    item.get("order", 0),
                    system_prompt,
                    user_prompt,
                    created_at,
                ),
            )
            def_count += 1
    print(f"    key_info_definitions:  {def_count} rows")

    # --- 2) Determine which attribute columns to keep ---
    kept_attr_cols = report.get("kept_attr_columns", [])

    # Build list of columns for the new projects table
    # Core columns (minus the ones we drop) + kept dynamic attrs + new column
    new_project_cols = [
        c for c in [
            "id", "original_filename", "created_at", "status", "slide_count",
            "title", "subject", "author", "last_modified_by", "revision_number",
            "summary_data", "summary_data_llm",
            "workflow_data", "kept", "key_info_completed",
        ]
    ]
    # Add dynamic attribute columns
    for attr_col in kept_attr_cols:
        if attr_col not in new_project_cols:
            # Need to add the column to the output table
            out_conn.execute(f"ALTER TABLE projects ADD COLUMN [{attr_col}] TEXT")

    # --- 3) Migrate projects + key_info data ---
    src_conn = sqlite3.connect(PROJECTS_DB_PATH)
    src_conn.row_factory = sqlite3.Row
    src_cursor = src_conn.cursor()
    src_cursor.execute("SELECT * FROM projects")
    src_rows = src_cursor.fetchall()

    project_count = 0
    instance_count = 0
    capture_count = 0
    image_ref_count = 0

    for row in src_rows:
        row_dict = dict(row)

        # Compute used_key_info_ids
        used_ids = compute_used_key_info_ids(row_dict.get("key_info_data"))
        used_ids_json = json.dumps(used_ids, ensure_ascii=False) if used_ids else None

        # Build values for core columns
        values = [
            row_dict.get("id"),
            row_dict.get("original_filename"),
            row_dict.get("created_at"),
            row_dict.get("status"),
            row_dict.get("slide_count"),
            row_dict.get("title"),
            row_dict.get("subject"),
            row_dict.get("author"),
            row_dict.get("last_modified_by"),
            row_dict.get("revision_number"),
            row_dict.get("summary_data"),
            row_dict.get("summary_data_llm"),
            row_dict.get("workflow_data"),
            row_dict.get("kept", 0),
            row_dict.get("key_info_completed", 0),
            used_ids_json,
        ]

        col_names = new_project_cols + ["used_key_info_ids"]

        # Add dynamic attribute values
        for attr_col in kept_attr_cols:
            col_names.append(attr_col)
            values.append(row_dict.get(attr_col))

        placeholders = ", ".join(["?"] * len(values))
        col_clause = ", ".join([f"[{c}]" for c in col_names])
        out_conn.execute(
            f"INSERT INTO projects ({col_clause}) VALUES ({placeholders})",
            values,
        )
        project_count += 1

        # --- Parse and insert key_info instances / captures / images ---
        instances, captures, images = parse_key_info_instances(
            row_dict.get("key_info_data")
        )

        for inst in instances:
            out_conn.execute(
                """INSERT INTO key_info_instances
                   (id, project_id, category_id, item_id, text_value,
                    item_order, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    inst["id"],
                    row_dict["id"],
                    inst["category_id"],
                    inst["item_id"],
                    inst["text_value"],
                    inst["item_order"],
                    inst["created_at"],
                    inst["updated_at"],
                ),
            )
            instance_count += 1

        for cap in captures:
            out_conn.execute(
                """INSERT INTO key_info_captures
                   (id, instance_id, slide_index, x, y, width, height, label, caption)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    cap["id"],
                    cap["instance_id"],
                    cap["slide_index"],
                    cap["x"],
                    cap["y"],
                    cap["width"],
                    cap["height"],
                    cap["label"],
                    cap["caption"],
                ),
            )
            capture_count += 1

        for img in images:
            out_conn.execute(
                """INSERT INTO key_info_images
                   (instance_id, image_id, caption)
                   VALUES (?, ?, ?)""",
                (img["instance_id"], img["image_id"], img["caption"]),
            )
            image_ref_count += 1

    src_conn.close()

    print(f"    projects:              {project_count} rows")
    print(f"    key_info_instances:    {instance_count} rows")
    print(f"    key_info_captures:     {capture_count} rows")
    print(f"    key_info_images:       {image_ref_count} rows")

    # --- 4) Copy attachment images ---
    if os.path.exists(ATTACHMENTS_DB_PATH):
        att_conn = sqlite3.connect(ATTACHMENTS_DB_PATH)
        att_cursor = att_conn.cursor()
        att_cursor.execute("SELECT id, project_id, data, created_at FROM images")

        att_count = 0
        while True:
            batch = att_cursor.fetchmany(100)
            if not batch:
                break
            for att_row in batch:
                out_conn.execute(
                    "INSERT INTO images (id, project_id, data, created_at) VALUES (?, ?, ?, ?)",
                    att_row,
                )
                att_count += 1

        att_conn.close()
        print(f"    images:                {att_count} rows")

    out_conn.commit()

    # --- 5) Verification ---
    print("\n  Verification:")
    out_cursor = out_conn.cursor()
    for table in [
        "projects",
        "key_info_definitions",
        "key_info_instances",
        "key_info_captures",
        "key_info_images",
        "images",
    ]:
        out_cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = out_cursor.fetchone()[0]
        print(f"    {table:30s}  {count:>6} rows")

    out_conn.close()

    # Final size
    output_size_mb = os.path.getsize(output_db_path) / (1024 * 1024)
    print(f"\n  Output: {output_db_path}")
    print(f"  Size:   {output_size_mb:.2f} MB")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Consolidate PiPiiTiii data into a single PostgreSQL-ready SQLite DB."
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually create the consolidated DB (default is dry-run).",
    )
    parser.add_argument(
        "--remove-unused-attrs",
        action="store_true",
        help="Remove dynamic attribute columns that have no data.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR}).",
    )
    args = parser.parse_args()

    print()
    print("=" * 60)
    print("  PiPiiTiii Data Consolidation")
    print("=" * 60)

    # Analyze
    report = analyze(args.remove_unused_attrs)

    if report.get("errors"):
        print_report(report)
        sys.exit(1)

    if not args.execute:
        print_report(report)
        return

    # Execute
    print(f"\n  Mode: EXECUTE")
    print(f"  Remove unused attrs: {args.remove_unused_attrs}")
    execute(report, args.output_dir)

    print()
    print("=" * 60)
    print("  Done!")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
