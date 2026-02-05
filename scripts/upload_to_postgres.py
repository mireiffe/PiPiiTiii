#!/usr/bin/env python3
"""
Upload consolidated SQLite DB to PostgreSQL.

Reads the consolidated .db file produced by consolidate_data.py,
creates tables in PostgreSQL, and inserts all data.

Usage:
    python scripts/upload_to_postgres.py consolidated.db --pg-dsn "host=localhost dbname=pipitiii user=postgres password=pass"
    python scripts/upload_to_postgres.py consolidated.db --pg-dsn "host=localhost dbname=pipitiii user=postgres" --drop-existing
"""

import argparse
import sqlite3
import sys

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("psycopg2 is required. Install it with:")
    print("  pip install psycopg2-binary")
    sys.exit(1)


# Columns in the projects table that should be stored as JSONB in PostgreSQL
JSONB_COLUMNS = {"summary_data", "summary_data_llm", "workflow_data", "used_key_info_ids"}

# Fixed core columns for the projects table (order matters)
CORE_PROJECT_COLUMNS = [
    "id", "original_filename", "created_at", "status", "slide_count",
    "title", "subject", "author", "last_modified_by", "revision_number",
    "summary_data", "summary_data_llm", "workflow_data",
    "kept", "key_info_completed", "used_key_info_ids",
]


def get_sqlite_columns(src, table: str) -> list[str]:
    """Get column names from a SQLite table."""
    cur = src.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cur.fetchall()]


def detect_dynamic_columns(src) -> list[str]:
    """Detect dynamic attribute columns added to the projects table."""
    all_cols = get_sqlite_columns(src, "projects")
    core_set = set(CORE_PROJECT_COLUMNS)
    return [c for c in all_cols if c not in core_set]


def build_projects_ddl(dynamic_cols: list[str]) -> str:
    """Build CREATE TABLE DDL for projects, including dynamic attribute columns."""
    col_defs = [
        "id                  TEXT PRIMARY KEY",
        "original_filename   TEXT",
        "created_at          TEXT",
        "status              TEXT",
        "slide_count         INTEGER",
        "title               TEXT",
        "subject             TEXT",
        "author              TEXT",
        "last_modified_by    TEXT",
        "revision_number     TEXT",
        "summary_data        JSONB",
        "summary_data_llm    JSONB",
        "workflow_data       JSONB",
        "kept                INTEGER DEFAULT 0",
        "key_info_completed  INTEGER DEFAULT 0",
        "used_key_info_ids   JSONB",
    ]
    for col in dynamic_cols:
        col_defs.append(f"{col}    TEXT")

    inner = ",\n    ".join(col_defs)
    return f"CREATE TABLE projects (\n    {inner}\n);"


FIXED_TABLES_DDL = """
CREATE TABLE key_info_definitions (
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

CREATE TABLE key_info_instances (
    id                  TEXT PRIMARY KEY,
    project_id          TEXT NOT NULL REFERENCES projects(id),
    category_id         TEXT NOT NULL,
    item_id             TEXT NOT NULL,
    text_value          TEXT,
    item_order          INTEGER,
    created_at          TEXT,
    updated_at          TEXT
);
CREATE INDEX idx_kii_project ON key_info_instances(project_id);
CREATE INDEX idx_kii_category ON key_info_instances(category_id);
CREATE INDEX idx_kii_item ON key_info_instances(item_id);

CREATE TABLE key_info_captures (
    id                  TEXT PRIMARY KEY,
    instance_id         TEXT NOT NULL REFERENCES key_info_instances(id),
    slide_index         INTEGER,
    x                   DOUBLE PRECISION,
    y                   DOUBLE PRECISION,
    width               DOUBLE PRECISION,
    height              DOUBLE PRECISION,
    label               TEXT,
    caption             TEXT
);
CREATE INDEX idx_kic_instance ON key_info_captures(instance_id);

CREATE TABLE key_info_images (
    instance_id         TEXT NOT NULL REFERENCES key_info_instances(id),
    image_id            TEXT NOT NULL,
    caption             TEXT,
    PRIMARY KEY (instance_id, image_id)
);
CREATE INDEX idx_kim_instance ON key_info_images(instance_id);

CREATE TABLE images (
    id                  TEXT PRIMARY KEY,
    project_id          TEXT NOT NULL REFERENCES projects(id),
    data                BYTEA NOT NULL,
    created_at          TEXT NOT NULL
);
CREATE INDEX idx_images_project ON images(project_id);
"""

ALL_TABLES = [
    "images",
    "key_info_images",
    "key_info_captures",
    "key_info_instances",
    "key_info_definitions",
    "projects",
]


def create_tables(pg, dynamic_cols: list[str], drop_existing: bool):
    """Create all tables in PostgreSQL."""
    cur = pg.cursor()

    if drop_existing:
        for table in ALL_TABLES:
            cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
        print("  Dropped existing tables")

    cur.execute(build_projects_ddl(dynamic_cols))
    cur.execute(FIXED_TABLES_DDL)
    pg.commit()
    print("  Created tables")


def upload_projects(src, pg, dynamic_cols: list[str]) -> int:
    """Upload projects table with JSONB casting."""
    all_cols = CORE_PROJECT_COLUMNS + dynamic_cols
    cur_src = src.cursor()
    cur_src.execute(f"SELECT {', '.join(all_cols)} FROM projects")

    cur_pg = pg.cursor()
    count = 0
    for row in cur_src.fetchall():
        values = []
        placeholders = []
        for i, col in enumerate(all_cols):
            val = row[i]
            if col in JSONB_COLUMNS:
                placeholders.append("%s::jsonb")
            else:
                placeholders.append("%s")
            values.append(val)

        sql = (
            f"INSERT INTO projects ({', '.join(all_cols)}) "
            f"VALUES ({', '.join(placeholders)})"
        )
        cur_pg.execute(sql, values)
        count += 1

    pg.commit()
    return count


def upload_simple_table(src, pg, table: str, columns: list[str], bytea_cols: set[str] | None = None) -> int:
    """Upload a table with optional BLOB → BYTEA handling."""
    bytea_cols = bytea_cols or set()
    cur_src = src.cursor()
    cur_src.execute(f"SELECT {', '.join(columns)} FROM {table}")

    cur_pg = pg.cursor()
    placeholders = ["%s" for _ in columns]
    sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"

    count = 0
    while True:
        batch = cur_src.fetchmany(500)
        if not batch:
            break
        for row in batch:
            values = []
            for i, col in enumerate(columns):
                if col in bytea_cols and row[i] is not None:
                    values.append(psycopg2.Binary(row[i]))
                else:
                    values.append(row[i])
            cur_pg.execute(sql, values)
            count += 1

    pg.commit()
    return count


def main():
    parser = argparse.ArgumentParser(
        description="Upload consolidated SQLite DB to PostgreSQL."
    )
    parser.add_argument(
        "sqlite_path",
        help="Path to the consolidated .db file from consolidate_data.py",
    )
    parser.add_argument(
        "--pg-dsn",
        required=True,
        help='PostgreSQL connection string, e.g. "host=localhost dbname=pipitiii user=postgres password=pass"',
    )
    parser.add_argument(
        "--drop-existing",
        action="store_true",
        help="DROP existing tables before creating (WARNING: destroys data).",
    )
    args = parser.parse_args()

    print()
    print("=" * 60)
    print("  Upload to PostgreSQL")
    print("=" * 60)

    # Open connections
    src = sqlite3.connect(args.sqlite_path)
    src.row_factory = None  # use tuple rows
    print(f"\n  SQLite: {args.sqlite_path}")

    pg = psycopg2.connect(args.pg_dsn)
    print(f"  PostgreSQL: connected")

    # Detect dynamic columns
    dynamic_cols = detect_dynamic_columns(src)
    if dynamic_cols:
        print(f"  Dynamic attr columns: {dynamic_cols}")

    # Create tables
    print()
    create_tables(pg, dynamic_cols, args.drop_existing)

    # Upload data
    print("\n  Uploading data:")

    count = upload_projects(src, pg, dynamic_cols)
    print(f"    projects:              {count}")

    count = upload_simple_table(src, pg, "key_info_definitions", [
        "item_id", "category_id", "category_name", "category_order",
        "item_title", "item_description", "item_order",
        "system_prompt", "user_prompt", "created_at",
    ])
    print(f"    key_info_definitions:  {count}")

    count = upload_simple_table(src, pg, "key_info_instances", [
        "id", "project_id", "category_id", "item_id",
        "text_value", "item_order", "created_at", "updated_at",
    ])
    print(f"    key_info_instances:    {count}")

    count = upload_simple_table(src, pg, "key_info_captures", [
        "id", "instance_id", "slide_index",
        "x", "y", "width", "height", "label", "caption",
    ])
    print(f"    key_info_captures:     {count}")

    count = upload_simple_table(src, pg, "key_info_images", [
        "instance_id", "image_id", "caption",
    ])
    print(f"    key_info_images:       {count}")

    count = upload_simple_table(
        src, pg, "images",
        ["id", "project_id", "data", "created_at"],
        bytea_cols={"data"},
    )
    print(f"    images:                {count}")

    # Verify
    print("\n  Verification:")
    cur_pg = pg.cursor()
    for table in ["projects", "key_info_definitions", "key_info_instances",
                   "key_info_captures", "key_info_images", "images"]:
        cur_pg.execute(f"SELECT COUNT(*) FROM {table}")
        cnt = cur_pg.fetchone()[0]
        print(f"    {table:30s}  {cnt:>6} rows")

    pg.close()
    src.close()

    print()
    print("=" * 60)
    print("  Done!")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
