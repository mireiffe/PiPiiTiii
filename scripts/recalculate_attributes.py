import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from database import Database
from attributes.manager import AttributeManager

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "backend", "projects.db")
ATTR_DIR = os.path.join(BASE_DIR, "backend", "attributes", "definitions")


def recalculate_all():
    print("Recalculating attributes for all projects...")

    db = Database(DB_PATH)
    manager = AttributeManager(db, ATTR_DIR)

    projects = db.list_projects()
    print(f"Found {len(projects)} projects.")

    count = 0
    for p in projects:
        # Convert Row to dict
        p_data = dict(p)

        # Calculate attributes
        # Note: p_data contains keys like 'original_filename', 'slide_count' which are used by attributes
        attributes = manager.calculate_attributes(p_data)

        if attributes:
            db.update_project_attributes(p_data["id"], attributes)
            count += 1
            print(f"Updated {p_data['id']}: {attributes}")

    print(f"Done. Updated {count} projects.")


if __name__ == "__main__":
    recalculate_all()
