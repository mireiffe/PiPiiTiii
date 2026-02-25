#!/usr/bin/env python3
"""
Show statistics for project attributes stored in the database.

Usage:
    python scripts/attr_stats.py              # all attributes
    python scripts/attr_stats.py -a db_no     # specific attribute only
"""

import argparse
import json
import os
import sys
from collections import Counter
from typing import Any, Dict, List

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from database import Database
from attributes.manager import AttributeManager

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "backend", "data", "projects.db")
ATTR_DIR = os.path.join(BASE_DIR, "backend", "attributes", "definitions")


# ---------------------------------------------------------------------------
# Data collection
# ---------------------------------------------------------------------------

def collect_stats(
    db: Database, manager: AttributeManager, *, filter_attr: str | None = None
) -> Dict[str, Any]:
    """Collect value-distribution statistics from the DB (read-only)."""
    projects = db.list_projects()
    active_attrs = manager.get_active_attributes()

    if filter_attr:
        active_attrs = [a for a in active_attrs if a["key"] == filter_attr]
        if not active_attrs:
            valid = [a["key"] for a in manager.get_active_attributes()]
            print(f"  ERROR: attribute '{filter_attr}' not found.")
            print(f"  Available: {', '.join(valid)}")
            sys.exit(1)

    stats: Dict[str, Dict[str, Any]] = {}
    for attr in active_attrs:
        key = attr["key"]
        stats[key] = {
            "display_name": attr["display_name"],
            "attr_type": attr["attr_type"],
            "total": 0,
            "empty": 0,
            "non_empty": 0,
            "values": Counter(),
            "total_len": 0,  # sum of str lengths for non-empty values
        }

    for p_data in projects:
        for attr in active_attrs:
            key = attr["key"]
            s = stats[key]
            val = p_data.get(key)
            s["total"] += 1

            is_empty = val is None or val == ""
            if is_empty:
                s["empty"] += 1
                s["values"]["(empty)"] += 1
            else:
                s["non_empty"] += 1
                s["values"][val] += 1
                s["total_len"] += len(str(val))

    # Compute avg_len for each attribute
    for key, s in stats.items():
        s["avg_len"] = s["total_len"] / s["non_empty"] if s["non_empty"] else 0

    return {
        "project_count": len(projects),
        "active_attrs": active_attrs,
        "stats": stats,
    }


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def print_stats(report: Dict[str, Any]):
    """Pretty-print attribute statistics."""
    print()
    print("=" * 60)
    print("  Attribute Statistics")
    print("=" * 60)

    project_count = report["project_count"]
    active_attrs = report["active_attrs"]
    stats = report["stats"]

    print(f"\n  Projects: {project_count}")

    for attr in active_attrs:
        key = attr["key"]
        s = stats[key]
        display_name = s["display_name"]
        variant = s["attr_type"].get("variant", "")

        print(f"\n  --- {key} ({display_name}) [{variant}] ---")
        print(f"  Total: {s['total']}    Non-empty: {s['non_empty']}    Empty: {s['empty']}")

        values: Counter = s["values"]

        if variant == "range":
            # Range-type: show min/max/distinct
            numeric_vals = [v for v in values if v != "(empty)"]
            if numeric_vals:
                sorted_vals = sorted(numeric_vals, key=lambda x: str(x))
                distinct = len(numeric_vals)
                print(f"  Min: {sorted_vals[0]}    Max: {sorted_vals[-1]}    Distinct: {distinct}")
            else:
                print("  (all empty)")
        elif s["avg_len"] > 30:
            # Long values: summary only
            distinct = len([v for v in values if v != "(empty)"])
            if distinct > 0:
                most_common_val, most_common_cnt = values.most_common(1)[0]
                least_common_cnt = values.most_common()[-1][1]
                most_str = str(most_common_val)
                if len(most_str) > 50:
                    most_str = most_str[:50] + "..."
                print(f"  Distinct: {distinct}")
                print(f"  Most common  (\u00d7{most_common_cnt}):  \"{most_str}\"")
                print(f"  Least common (\u00d7{least_common_cnt})")
        else:
            # Short values: full table
            if not values:
                print("  (no data)")
                continue
            max_val_len = max(len(str(v)) for v in values)
            col_width = max(max_val_len, 5)
            print()
            print(f"  {'Value':<{col_width}}   Count")
            print(f"  {'─' * col_width}───{'─' * 5}")
            for val, cnt in values.most_common():
                print(f"  {str(val):<{col_width}}   {cnt:>5}")

    print()
    print("=" * 60)
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Show statistics for project attributes stored in the DB."
    )
    parser.add_argument(
        "--attribute", "-a",
        type=str,
        default=None,
        help="Show stats for a specific attribute only.",
    )
    args = parser.parse_args()

    db = Database(DB_PATH)
    manager = AttributeManager(db, ATTR_DIR)

    report = collect_stats(db, manager, filter_attr=args.attribute)
    print_stats(report)


if __name__ == "__main__":
    main()
