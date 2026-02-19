#!/usr/bin/env python3
"""
Recalculate project attributes for all projects.

Usage:
    python scripts/recalculate_attributes.py              # dry-run (default)
    python scripts/recalculate_attributes.py --execute     # write to DB
"""

import argparse
import os
import sys
from collections import Counter
from typing import Any, Dict, List, Tuple

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from database import Database
from attributes.manager import AttributeManager

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "backend", "data", "projects.db")
ATTR_DIR = os.path.join(BASE_DIR, "backend", "attributes", "definitions")


# ---------------------------------------------------------------------------
# Analysis (dry-run)
# ---------------------------------------------------------------------------

def analyze(
    db: Database, manager: AttributeManager
) -> Dict[str, Any]:
    """Analyze all projects and return a report without writing to DB."""
    projects = db.list_projects()
    active_attrs = manager.get_active_attributes()
    attr_keys = [a["key"] for a in active_attrs]

    # Per-attribute statistics
    stats: Dict[str, Dict[str, Any]] = {}
    for attr in active_attrs:
        key = attr["key"]
        stats[key] = {
            "display_name": attr["display_name"],
            "attr_type": attr["attr_type"],
            "new_values": Counter(),
            "old_values": Counter(),
            "changed_count": 0,
            "unchanged_count": 0,
            "new_only_count": 0,
            "transitions": Counter(),
        }

    results_by_project: List[Tuple[str, Dict[str, Any]]] = []

    for p_data in projects:
        new_attrs = manager.calculate_attributes(p_data)
        results_by_project.append((p_data["id"], new_attrs))

        for key in attr_keys:
            s = stats[key]
            new_val = new_attrs.get(key)
            old_val = p_data.get(key)

            # Count value distributions
            new_label = new_val if new_val is not None and new_val != "" else "(empty)"
            old_label = old_val if old_val is not None and old_val != "" else "(empty)"
            s["new_values"][new_label] += 1
            s["old_values"][old_label] += 1

            # Compare old vs new
            old_is_empty = old_val is None or old_val == ""
            new_is_empty = new_val is None or new_val == ""

            if old_is_empty and not new_is_empty:
                s["new_only_count"] += 1
            elif str(old_val) == str(new_val):
                s["unchanged_count"] += 1
            else:
                s["changed_count"] += 1
                s["transitions"][f"{old_label} -> {new_label}"] += 1

    return {
        "project_count": len(projects),
        "active_attrs": active_attrs,
        "stats": stats,
        "results_by_project": results_by_project,
        "_projects": projects,
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def print_report(report: Dict[str, Any], is_execute: bool = False):
    """Pretty-print the analysis report."""
    print()
    print("=" * 60)
    print("  Attribute Recalculation — Dry Run Report")
    print("=" * 60)

    project_count = report["project_count"]
    active_attrs = report["active_attrs"]
    stats = report["stats"]

    print(f"\n  Projects: {project_count}    Active Attributes: {len(active_attrs)}")

    for attr in active_attrs:
        key = attr["key"]
        s = stats[key]
        display_name = s["display_name"]
        variant = s["attr_type"].get("variant", "")

        print(f"\n  --- {key} ({display_name}) ---")

        # New value distribution
        new_values = s["new_values"]
        if variant == "range":
            # For range-type attributes, show range summary
            numeric_vals = []
            empty_count = 0
            for val, cnt in new_values.items():
                if val == "(empty)":
                    empty_count += cnt
                else:
                    try:
                        numeric_vals.extend([val] * cnt)
                    except (ValueError, TypeError):
                        numeric_vals.extend([val] * cnt)

            if numeric_vals:
                sorted_vals = sorted(set(numeric_vals), key=lambda x: (str(x)))
                distinct = len(set(numeric_vals))
                total = len(numeric_vals)
                print("  New values:")
                print(f"    Range: {sorted_vals[0]} – {sorted_vals[-1]}  ({distinct} distinct, {empty_count} empty)")
            else:
                print("  New values:  (all empty)")
        else:
            # For other types, show value counts
            non_empty_vals = [v for v in new_values.elements() if v != "(empty)"]
            avg_len = sum(len(str(v)) for v in non_empty_vals) / len(non_empty_vals) if non_empty_vals else 0

            if avg_len > 30:
                # Long values — show summary statistics
                total = sum(new_values.values())
                empty_count = new_values.get("(empty)", 0)
                distinct = len([v for v in new_values if v != "(empty)"])
                most_common_val, most_common_cnt = new_values.most_common(1)[0]
                most_common_str = str(most_common_val)
                if len(most_common_str) > 40:
                    most_common_str = most_common_str[:40] + "..."
                least_common_cnt = new_values.most_common()[-1][1]
                least_common_count = sum(1 for _, c in new_values.items() if c == least_common_cnt)
                print("  New values:  (long values — summary)")
                print(f"    Total: {total}    Distinct: {distinct}    Empty: {empty_count}")
                print(f"    Most common (\u00d7{most_common_cnt}):  \"{most_common_str}\"")
                print(f"    Least common (\u00d7{least_common_cnt}):  {least_common_count} values")
            else:
                print("  New values:")
                for val, cnt in new_values.most_common():
                    print(f"    {str(val):20s} {cnt:>5}")

        # Comparison with DB
        print("  Comparison with DB:")
        print(f"    Unchanged:  {s['unchanged_count']:>5}")
        changed = s["changed_count"]
        if changed > 0:
            transition_parts = []
            for t, cnt in s["transitions"].most_common():
                transition_parts.append(f"{t}: {cnt}")
            transitions_str = "  (" + ", ".join(transition_parts) + ")"
            print(f"    Changed:    {changed:>5}{transitions_str}")
        else:
            print(f"    Changed:    {changed:>5}")
        print(f"    New (NULL->val): {s['new_only_count']:>2}")

    print()
    print("=" * 60)
    if not is_execute:
        print("  DRY RUN. Use --execute to write to DB.")
    print("=" * 60)
    print()


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

def execute(
    report: Dict[str, Any],
    db: Database,
    manager: AttributeManager,
    *,
    use_llm: bool = False,
):
    """Write the calculated attributes to the database.

    When use_llm is True, attributes are recalculated with LLM extraction
    instead of using the dry-run results (which never call LLM).
    """
    projects = report.get("_projects")  # original project list, set when use_llm path

    active_attrs = report["active_attrs"]
    llm_keys = {
        a["key"]
        for a in active_attrs
        if manager.attributes.get(a["key"])
        and manager.attributes[a["key"]].llm_extract_config is not None
    }

    if use_llm and projects is not None:
        total = len(projects)
        print(f"\n  Recalculating with LLM for {total} projects...")
        count = 0
        for idx, p_data in enumerate(projects, 1):
            filename = p_data.get("original_filename", p_data["id"])
            print(f"  [{idx}/{total}] {p_data['id']} ({filename})")
            attrs = manager.calculate_attributes(p_data, use_llm=True)
            if attrs:
                for key, val in attrs.items():
                    tag = " (LLM)" if key in llm_keys else ""
                    print(f"         {key}: \"{val}\"{tag}")
                db.update_project_attributes(p_data["id"], attrs)
                count += 1
        print(f"  Done. Updated {count} projects (with LLM).")
    else:
        results = report["results_by_project"]
        total = len(results)
        print(f"\n  Writing attributes for {total} projects...")
        count = 0
        for idx, (project_id, attrs) in enumerate(results, 1):
            if attrs:
                print(f"  [{idx}/{total}] {project_id}")
                db.update_project_attributes(project_id, attrs)
                count += 1
        print(f"  Done. Updated {count} projects.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Recalculate project attributes for all projects."
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually write to DB (default is dry-run).",
    )
    parser.add_argument(
        "--use-llm",
        action="store_true",
        help="Use LLM extraction for attributes that support it (requires --execute).",
    )
    args = parser.parse_args()

    if args.use_llm and not args.execute:
        parser.error("--use-llm requires --execute (LLM calls are not made during dry-run).")

    print()
    print("=" * 60)
    print("  PiPiiTiii Attribute Recalculation")
    print("=" * 60)

    db = Database(DB_PATH)
    manager = AttributeManager(db, ATTR_DIR)

    report = analyze(db, manager)

    if not args.execute:
        print_report(report)
        return

    # Show summary then execute
    print_report(report, is_execute=True)
    execute(report, db, manager, use_llm=args.use_llm)

    print()
    print("=" * 60)
    print("  Done!")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
