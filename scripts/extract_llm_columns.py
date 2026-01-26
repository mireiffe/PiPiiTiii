"""
Extract specific fields from summary_data_llm JSON column
and add them as separate columns in the projects table.

Supports two extraction modes:
  - "direct": Store the value as-is in a column named after the key.
  - "markdown_table": Parse a markdown table into a dict, then create
    one column per dict key named {field_key}_{subdict_key}.

Usage:
  python scripts/extract_llm_columns.py                 # dry run (default)
  python scripts/extract_llm_columns.py --apply         # actually apply changes
  python scripts/extract_llm_columns.py --dry-run       # explicit dry run
"""

import argparse
import json
import os
import re
import sqlite3
import sys
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
# Each entry maps a field_id (key in summary_data_llm JSON) to an extraction mode.
#
#   "direct"         -> value stored as-is; column name = field_id
#   "markdown_table" -> value is a horizontal markdown table:
#                         | key1 | key2 | ... |
#                         |------|------|-----|
#                         | val1 | val2 | ... |
#                       Headers become dict keys, first data row becomes values.
#                       Each entry becomes a column named {field_id}_{header}.
#
# Example:
#   EXTRACTION_CONFIG = [
#       {"key": "executive_summary", "mode": "direct"},
#       {"key": "key_metrics",      "mode": "markdown_table"},
#   ]
# ---------------------------------------------------------------------------
EXTRACTION_CONFIG: List[Dict[str, str]] = [
    # ---- add your entries here ----
    # {"key": "executive_summary", "mode": "direct"},
    # {"key": "key_metrics",      "mode": "markdown_table"},
]

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "backend", "data", "projects.db")


# ---------------------------------------------------------------------------
# Markdown table parser
# ---------------------------------------------------------------------------
def parse_markdown_table(md_text: str) -> Dict[str, str]:
    """Parse a horizontal markdown table into a {header: value} dict.

    Accepts tables like:
        | key1 | key2 | key3 |
        |------|------|------|
        | val1 | val2 | val3 |

    The header row provides dict keys, the first data row provides values.
    Handles tables with or without leading/trailing pipes.
    If multiple data rows exist, only the first is used.
    """
    lines = md_text.strip().splitlines()
    result: Dict[str, str] = {}

    table_lines: List[str] = []
    for line in lines:
        stripped = line.strip()
        if "|" in stripped:
            table_lines.append(stripped)

    if len(table_lines) < 3:
        # Need at least: header + separator + 1 data row
        return result

    def is_separator(line: str) -> bool:
        return bool(re.match(r"^[\s|:\-]+$", line))

    def split_cells(line: str) -> List[str]:
        line = line.strip()
        if line.startswith("|"):
            line = line[1:]
        if line.endswith("|"):
            line = line[:-1]
        return [c.strip() for c in line.split("|")]

    # Find header: the line right before the first separator
    header_idx = None
    sep_idx = None
    for i, tl in enumerate(table_lines):
        if is_separator(tl):
            sep_idx = i
            header_idx = i - 1 if i > 0 else None
            break

    if header_idx is None or sep_idx is None:
        return result

    headers = split_cells(table_lines[header_idx])

    # First data row = line right after the separator
    data_lines = [
        tl for tl in table_lines[sep_idx + 1:] if not is_separator(tl)
    ]
    if not data_lines:
        return result

    values = split_cells(data_lines[0])

    for key, val in zip(headers, values):
        key = key.strip()
        if key:
            result[key] = val.strip()

    return result


# ---------------------------------------------------------------------------
# Column name helpers
# ---------------------------------------------------------------------------
def sanitize_column_name(name: str) -> str:
    """Sanitize a string into a valid SQLite column name."""
    # Replace non-alphanumeric characters (except underscore) with underscore
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    # Collapse consecutive underscores
    sanitized = re.sub(r"_+", "_", sanitized)
    # Strip leading/trailing underscores
    sanitized = sanitized.strip("_")
    # Ensure it doesn't start with a digit
    if sanitized and sanitized[0].isdigit():
        sanitized = "_" + sanitized
    return sanitized.lower()


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------
def get_existing_columns(conn: sqlite3.Connection) -> set:
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(projects)")
    return {row[1] for row in cursor.fetchall()}


def collect_extractions(
    conn: sqlite3.Connection,
    config: List[Dict[str, str]],
) -> Tuple[Dict[str, Dict[str, Optional[str]]], List[str]]:
    """Scan all projects and collect the column values to write.

    Returns:
        columns_data: {project_id: {column_name: value, ...}, ...}
        all_columns:  sorted list of all new column names that will be created
    """
    cursor = conn.cursor()
    cursor.execute("SELECT id, summary_data_llm FROM projects")
    rows = cursor.fetchall()

    all_columns_set: set = set()
    # project_id -> {col_name: value}
    columns_data: Dict[str, Dict[str, Optional[str]]] = {}

    for project_id, raw_llm in rows:
        if not raw_llm:
            continue
        try:
            llm_data: Dict[str, Any] = json.loads(raw_llm)
        except json.JSONDecodeError:
            print(f"  [WARN] Project {project_id}: invalid JSON in summary_data_llm, skipping")
            continue

        project_cols: Dict[str, Optional[str]] = {}

        for entry in config:
            field_key = entry["key"]
            mode = entry["mode"]

            value = llm_data.get(field_key)
            if value is None:
                continue

            if mode == "direct":
                col_name = sanitize_column_name(field_key)
                project_cols[col_name] = str(value)
                all_columns_set.add(col_name)

            elif mode == "markdown_table":
                parsed = parse_markdown_table(str(value))
                if not parsed:
                    print(
                        f"  [WARN] Project {project_id}: "
                        f"could not parse markdown table for key '{field_key}'"
                    )
                    continue
                prefix = sanitize_column_name(field_key)
                for sub_key, sub_val in parsed.items():
                    col_name = f"{prefix}_{sanitize_column_name(sub_key)}"
                    project_cols[col_name] = sub_val
                    all_columns_set.add(col_name)
            else:
                print(f"  [WARN] Unknown mode '{mode}' for key '{field_key}', skipping")

        if project_cols:
            columns_data[project_id] = project_cols

    return columns_data, sorted(all_columns_set)


def apply_changes(
    conn: sqlite3.Connection,
    columns_data: Dict[str, Dict[str, Optional[str]]],
    all_columns: List[str],
    existing_columns: set,
):
    """Add columns and update rows."""
    cursor = conn.cursor()

    # 1. Add missing columns
    for col in all_columns:
        if col not in existing_columns:
            cursor.execute(f"ALTER TABLE projects ADD COLUMN [{col}] TEXT")
            print(f"  [ADD COLUMN] {col}")

    # 2. Update rows
    for project_id, cols in columns_data.items():
        set_parts = []
        values = []
        for col_name, col_value in cols.items():
            set_parts.append(f"[{col_name}] = ?")
            values.append(col_value)
        values.append(project_id)
        sql = f"UPDATE projects SET {', '.join(set_parts)} WHERE id = ?"
        cursor.execute(sql, values)

    conn.commit()


def print_dry_run_report(
    columns_data: Dict[str, Dict[str, Optional[str]]],
    all_columns: List[str],
    existing_columns: set,
):
    new_cols = [c for c in all_columns if c not in existing_columns]
    existing_cols = [c for c in all_columns if c in existing_columns]

    print("\n===== DRY RUN REPORT =====\n")

    print(f"Columns to ADD ({len(new_cols)}):")
    for c in new_cols:
        print(f"  + {c}")
    if not new_cols:
        print("  (none)")

    if existing_cols:
        print(f"\nColumns that ALREADY EXIST ({len(existing_cols)}):")
        for c in existing_cols:
            print(f"  = {c}")

    print(f"\nProjects to UPDATE ({len(columns_data)}):")
    for pid, cols in columns_data.items():
        print(f"\n  Project: {pid}")
        for col_name, col_value in cols.items():
            preview = col_value[:80] + "..." if col_value and len(col_value) > 80 else col_value
            print(f"    {col_name} = {preview}")

    if not columns_data:
        print("  (no projects matched)")

    print("\n===========================")
    print("Run with --apply to execute these changes.\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Extract fields from summary_data_llm JSON into separate DB columns."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Preview changes without modifying the database (default)",
    )
    group.add_argument(
        "--apply",
        action="store_true",
        help="Actually apply changes to the database",
    )
    parser.add_argument(
        "--db",
        default=DB_PATH,
        help=f"Path to projects.db (default: {DB_PATH})",
    )
    args = parser.parse_args()

    dry_run = not args.apply

    if not EXTRACTION_CONFIG:
        print("ERROR: EXTRACTION_CONFIG is empty. Add entries before running.")
        print("Edit the EXTRACTION_CONFIG list at the top of this script.")
        sys.exit(1)

    if not os.path.exists(args.db):
        print(f"ERROR: Database not found: {args.db}")
        sys.exit(1)

    print(f"Database: {args.db}")
    print(f"Mode: {'DRY RUN' if dry_run else 'APPLY'}")
    print(f"Extraction config ({len(EXTRACTION_CONFIG)} entries):")
    for entry in EXTRACTION_CONFIG:
        print(f"  - key='{entry['key']}' mode='{entry['mode']}'")

    conn = sqlite3.connect(args.db)
    try:
        existing_columns = get_existing_columns(conn)
        columns_data, all_columns = collect_extractions(conn, EXTRACTION_CONFIG)

        if dry_run:
            print_dry_run_report(columns_data, all_columns, existing_columns)
        else:
            print("\nApplying changes...")
            apply_changes(conn, columns_data, all_columns, existing_columns)
            print(f"\nDone. Added {len([c for c in all_columns if c not in existing_columns])} column(s), "
                  f"updated {len(columns_data)} project(s).")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
