import sys
import os

# Add backend to path
sys.path.append(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
)

from database import Database

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "backend",
    "projects.db",
)

print(f"Initializing DB at {DB_PATH}")
db = Database(DB_PATH)
print("DB initialized.")
