import os
import sys
import argparse

# Add backend to path to import Database
sys.path.append(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
)

from database import Database

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULT_DIR = os.path.join(BASE_DIR, "results")
DB_PATH = os.path.join(BASE_DIR, "backend", "data", "projects.db")


def cleanup_db(delete=False):
    if not os.path.exists(RESULT_DIR):
        print(f"Result directory not found: {RESULT_DIR}")
        return

    if not os.path.exists(DB_PATH):
        print(f"Database not found: {DB_PATH}")
        return

    print(f"Checking {DB_PATH} against {RESULT_DIR}...")

    db = Database(DB_PATH)
    projects = db.list_projects()

    # 실제 파일 시스템에 존재하는 폴더 목록
    existing_folders = {
        name
        for name in os.listdir(RESULT_DIR)
        if os.path.isdir(os.path.join(RESULT_DIR, name))
    }

    # DB에는 있는데, 파일 시스템에는 없는 uid들
    orphans_in_db = [p for p in projects if str(p["id"]) not in existing_folders]

    if not orphans_in_db:
        print("No orphaned DB entries found. All clean!")
        return

    print(f"Found {len(orphans_in_db)} orphaned DB entries (no matching folder):")
    for p in orphans_in_db:
        # list_projects 가 id 외에 다른 필드도 줄 수 있으면 여기서 추가로 출력해도 됨
        print(f" - id={p['id']}")

    if delete:
        print("\nDeleting orphaned entries from database...")
        for p in orphans_in_db:
            project_id = p["id"]
            try:
                # ⚠️ Database 클래스에 맞게 메서드 이름을 수정해서 사용하세요.
                # 예: delete_project, remove_project, delete, 등
                db.delete_project(project_id)
                print(f"Deleted from DB: {project_id}")
            except Exception as e:
                print(f"Failed to delete {project_id} from DB: {e}")
        print("DB cleanup complete.")
    else:
        print("\nRun with --delete to remove these DB entries.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Cleanup orphaned DB entries that have no result folder."
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete orphaned DB entries instead of just listing them.",
    )
    args = parser.parse_args()

    cleanup_db(delete=args.delete)
