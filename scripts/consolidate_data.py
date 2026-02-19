#!/usr/bin/env python3
"""
Data consolidation script for PiPiiTiii.

Reads projects.db, attachments.db, settings.json and produces a single
consolidated SQLite database with a normalized, PostgreSQL-ready schema.

Usage:
    python scripts/consolidate_data.py                    # dry-run (default)
    python scripts/consolidate_data.py --execute          # actually create DB
    python scripts/consolidate_data.py --execute --remove-undefined-attrs
    python scripts/consolidate_data.py --execute --output-dir ./export
    python scripts/consolidate_data.py --execute --concat-db ./other1.db ./other2.db
"""

import argparse
import importlib.util
import inspect
import json
import os
import sqlite3
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))

# Source paths
PROJECTS_DB_PATH = os.path.join(BASE_DIR, "backend", "data", "projects.db")
ATTACHMENTS_DB_PATH = os.path.join(BASE_DIR, "backend", "data", "attachments.db")
SETTINGS_FILE_PATH = os.path.join(BASE_DIR, "backend", "data", "settings.json")

# Attribute definitions directory
ATTR_DEFINITIONS_DIR = os.path.join(BASE_DIR, "backend", "attributes", "definitions")

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

-- Settings (full JSON blob, singleton row)
CREATE TABLE IF NOT EXISTS settings (
    id          INTEGER PRIMARY KEY CHECK (id = 1),
    data        TEXT NOT NULL,
    created_at  TEXT NOT NULL
);
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


def load_defined_attr_keys() -> Set[str]:
    """Load attribute keys from backend/attributes/definitions/ Python files.

    Mirrors the logic in AttributeManager.load_attributes(): scans .py files
    in the definitions directory, instantiates BaseAttribute subclasses, and
    collects their ``key`` values.
    """
    from attributes.base import BaseAttribute

    keys: Set[str] = set()

    if not os.path.isdir(ATTR_DEFINITIONS_DIR):
        return keys

    for filename in os.listdir(ATTR_DEFINITIONS_DIR):
        if not filename.endswith(".py") or filename.startswith("_"):
            continue
        filepath = os.path.join(ATTR_DEFINITIONS_DIR, filename)
        try:
            module_name = os.path.splitext(filename)[0]
            spec = importlib.util.spec_from_file_location(module_name, filepath)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                for _name, obj in inspect.getmembers(module):
                    if (
                        inspect.isclass(obj)
                        and issubclass(obj, BaseAttribute)
                        and obj is not BaseAttribute
                    ):
                        instance = obj()
                        keys.add(instance.key)
        except Exception as e:
            print(f"  [WARN] Failed to load attribute from {filepath}: {e}")

    return keys


def detect_undefined_attr_columns(
    dynamic_cols: List[str], defined_keys: Set[str]
) -> List[str]:
    """Return dynamic attribute columns NOT defined in backend/attributes/definitions/."""
    return [c for c in dynamic_cols if c not in defined_keys]


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

    defined_keys = load_defined_attr_keys()
    report["defined_attr_keys"] = sorted(defined_keys)

    undefined_attrs = detect_undefined_attr_columns(attr_cols, defined_keys)
    report["undefined_attr_columns"] = undefined_attrs
    report["remove_undefined_attrs"] = remove_unused_attrs

    if remove_unused_attrs:
        report["kept_attr_columns"] = [c for c in attr_cols if c not in undefined_attrs]
    else:
        report["kept_attr_columns"] = attr_cols

    # --- KeyInfo definitions (from settings) ---
    settings = load_settings()
    ki_settings = settings.get("key_info_settings", {})
    categories = ki_settings.get("categories", [])
    definition_count = sum(len(cat.get("items", [])) for cat in categories)
    report["key_info_categories"] = len(categories)
    report["key_info_definitions"] = definition_count

    # --- Settings top-level keys ---
    report["settings_top_keys"] = sorted(settings.keys()) if settings else []

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
    defined_keys = set(report.get("defined_attr_keys", []))
    undefined = report.get("undefined_attr_columns", [])
    will_remove = report.get("remove_undefined_attrs", False)

    print("\n  Defined Attribute Keys (from backend/attributes/definitions/):")
    if defined_keys:
        for k in sorted(defined_keys):
            print(f"    - {k}")
    else:
        print("    (none)")

    print(f"\n  Dynamic Columns in projects table ({len(report['dynamic_attr_columns'])}):")
    for col in report["dynamic_attr_columns"]:
        is_undefined = col in undefined
        if is_undefined and will_remove:
            marker = " [UNDEFINED — will remove]"
        elif is_undefined:
            marker = " [UNDEFINED]"
        else:
            marker = ""
        print(f"    - {col}{marker}")

    if will_remove and undefined:
        print(f"    → {len(undefined)} undefined column(s) will be removed")

    # KeyInfo
    print(f"\n  KeyInfo Definitions:     {report['key_info_definitions']} items in {report['key_info_categories']} categories")
    print(f"  KeyInfo Instances:       {report['key_info_instances']}")
    print(f"  KeyInfo Captures:        {report['key_info_captures']}")
    print(f"  KeyInfo Image Refs:      {report['key_info_image_refs']}")

    # Attachments
    print(f"\n  Attachment Images:       {report['attachment_count']}  ({report['attachment_blob_mb']:.2f} MB)")

    # Settings
    settings_keys = report.get("settings_top_keys", [])
    print(f"\n  Settings:                {len(settings_keys)} top-level keys")
    if settings_keys:
        for k in settings_keys:
            print(f"    - {k}")

    # Output tables
    print("\n  Output Tables:")
    print("    - projects              (core metadata + active attrs + used_key_info_ids)")
    print("    - key_info_definitions  (category/item definitions from settings)")
    print("    - key_info_instances    (per-project key_info entries)")
    print("    - key_info_captures     (capture regions per instance)")
    print("    - key_info_images       (image refs per instance)")
    print("    - images                (BLOB data from attachments.db)")
    print("    - settings              (full settings.json as single JSON row)")

    # Concat DBs info
    concat_dbs = report.get("concat_dbs")
    if concat_dbs:
        print("\n  Concat DBs:")
        for db_info in concat_dbs:
            path = db_info["path"]
            if db_info["exists"]:
                print(f"    {path:40s}  EXISTS    {db_info['size_mb']:.2f} MB")
            else:
                print(f"    {path:40s}  MISSING")

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

    # --- 1b) settings table ---
    out_conn.execute(
        "INSERT INTO settings (id, data, created_at) VALUES (1, ?, ?)",
        (json.dumps(settings, ensure_ascii=False), datetime.now().isoformat()),
    )
    print("    settings:              1 row")

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
        "settings",
    ]:
        out_cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = out_cursor.fetchone()[0]
        print(f"    {table:30s}  {count:>6} rows")

    out_conn.close()

    # Final size
    output_size_mb = os.path.getsize(output_db_path) / (1024 * 1024)
    print(f"\n  Output: {output_db_path}")
    print(f"  Size:   {output_size_mb:.2f} MB")

    return output_db_path


# ---------------------------------------------------------------------------
# Concat
# ---------------------------------------------------------------------------

def concat_databases(output_db_path: str, concat_paths: List[str]):
    """Copy tables from additional DB files into the output DB.

    For each concat DB, copies all tables into the output DB.
    Raises an error if any table name conflicts with existing tables.
    """
    out_conn = sqlite3.connect(output_db_path)
    out_cursor = out_conn.cursor()

    # Get existing tables in output DB
    out_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = {row[0] for row in out_cursor.fetchall()}

    for concat_path in concat_paths:
        if not os.path.exists(concat_path):
            print(f"\n  [WARN] Concat DB not found, skipping: {concat_path}")
            continue

        print(f"\n  Concatenating: {concat_path}")

        # ATTACH the concat DB
        out_conn.execute("ATTACH DATABASE ? AS concat_src", (concat_path,))
        out_cursor.execute("SELECT name FROM concat_src.sqlite_master WHERE type='table'")
        src_tables = [row[0] for row in out_cursor.fetchall()]

        # Check for conflicts
        conflicts = [t for t in src_tables if t in existing_tables]
        if conflicts:
            out_conn.execute("DETACH DATABASE concat_src")
            out_conn.close()
            raise SystemExit(
                f"  [ERROR] Table name conflict in {concat_path}: {conflicts}\n"
                f"  Output DB already has these tables. Aborting."
            )

        # Copy each table
        for table in src_tables:
            out_conn.execute(
                f"CREATE TABLE [{table}] AS SELECT * FROM concat_src.[{table}]"
            )
            out_cursor.execute(f"SELECT COUNT(*) FROM [{table}]")
            count = out_cursor.fetchone()[0]
            print(f"    {table:30s}  {count:>6} rows")
            existing_tables.add(table)

        out_conn.execute("DETACH DATABASE concat_src")

    out_conn.commit()
    out_conn.close()


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
        "--remove-undefined-attrs",
        action="store_true",
        help="Remove attribute columns not defined in backend/attributes/definitions/.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR}).",
    )
    parser.add_argument(
        "--concat-db",
        nargs="+",
        metavar="DB_PATH",
        help="Additional DB files whose tables will be copied into the output.",
    )
    args = parser.parse_args()

    print()
    print("=" * 60)
    print("  PiPiiTiii Data Consolidation")
    print("=" * 60)

    # Analyze
    report = analyze(args.remove_undefined_attrs)

    # Add concat DB info to report
    if args.concat_db:
        concat_dbs_info = []
        for db_path in args.concat_db:
            exists = os.path.exists(db_path)
            size_mb = os.path.getsize(db_path) / (1024 * 1024) if exists else 0
            concat_dbs_info.append({
                "path": db_path,
                "exists": exists,
                "size_mb": round(size_mb, 2),
            })
        report["concat_dbs"] = concat_dbs_info

    if report.get("errors"):
        print_report(report)
        sys.exit(1)

    if not args.execute:
        if args.concat_db:
            print("\n  Note: --concat-db requires --execute to take effect.")
        print_report(report)
        return

    # Execute
    print("\n  Mode: EXECUTE")
    print(f"  Remove undefined attrs: {args.remove_undefined_attrs}")
    output_db_path = execute(report, args.output_dir)

    # Concat
    if args.concat_db:
        concat_databases(output_db_path, args.concat_db)

    print()
    print("=" * 60)
    print("  Done!")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
