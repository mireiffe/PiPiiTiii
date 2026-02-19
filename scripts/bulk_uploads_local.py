import argparse
import os
import shutil
import sqlite3
import sys
import time
import uuid

import pythoncom


# Ensure backend modules are importable
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
sys.path.append(BASE_DIR)
sys.path.append(BACKEND_DIR)

from backend import ppt_parser as parsing  # noqa: E402
from backend.attributes.manager import AttributeManager  # noqa: E402
from backend.database import Database  # noqa: E402

DB_PATH = os.path.join(BASE_DIR, "backend", "data", "projects.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
RESULT_DIR = os.path.join(BASE_DIR, "results")
ATTR_DEFINITIONS_DIR = os.path.join(BASE_DIR, "backend", "attributes", "definitions")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)

db = Database(DB_PATH)
attr_manager = AttributeManager(db, ATTR_DEFINITIONS_DIR)


def check_duplicate_by_db(filename: str) -> tuple[bool, str | None]:
    """Check if a project with the same original filename exists in DB."""
    if not os.path.exists(DB_PATH):
        return False, None

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM projects WHERE original_filename = ?",
            (filename,),
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            return True, row[0]
        return False, None
    except Exception as e:
        print(f"DB check error: {e}")
        return False, None


def find_ppt_files_recursive(directory_path):
    """Find all .ppt and .pptx files recursively under the given directory."""
    ppt_files = []
    for root, dirs, files in os.walk(directory_path):
        for f in files:
            if f.lower().endswith((".ppt", ".pptx")):
                full_path = os.path.join(root, f)
                ppt_files.append(full_path)

    ppt_files.sort()
    return ppt_files


def analyze_files(files_to_check, directory_path):
    """Analyze files and check for duplicates in the database."""
    results = []
    total = len(files_to_check)

    for idx, file_path in enumerate(files_to_check, 1):
        rel_path = os.path.relpath(file_path, directory_path)
        print(f"[{idx}/{total}] Analyzing {rel_path}...", flush=True)

        filename = os.path.basename(file_path)
        is_duplicate, project_id = check_duplicate_by_db(filename)

        if is_duplicate:
            status_msg = f"Duplicate (ID: {project_id})"
            is_new = False
        else:
            status_msg = "New"
            is_new = True

        results.append(
            {
                "file_path": file_path,
                "rel_path": rel_path,
                "status": status_msg,
                "is_new": is_new,
            }
        )

    return results


def get_metadata_with_com(file_path):
    """Run metadata extraction with COM initialization."""
    pythoncom.CoInitialize()
    try:
        return parsing.get_presentation_metadata(file_path)
    finally:
        pythoncom.CoUninitialize()


def generate_project_id(filename: str, metadata: dict | None) -> tuple[str, dict]:
    """Generate deterministic project ID using the same strategy as the backend."""
    if metadata is None:
        print(f"[WARN] Could not extract metadata for {filename}. Using random UUID.")
        return str(uuid.uuid4()), {}

    title = metadata.get("title", "")
    slide_count = metadata.get("slide_count", 0)
    subject = metadata.get("subject", "")
    author = metadata.get("author", "")
    last_modified_by = metadata.get("last_modified_by", "")
    revision_number = metadata.get("revision_number", "")

    seed = f"{filename}|{title}|{slide_count}"
    app_namespace = uuid.uuid5(uuid.NAMESPACE_DNS, "pipiitiii.local")
    project_id = str(uuid.uuid5(app_namespace, seed))

    return project_id, {
        "title": title,
        "slide_count": slide_count,
        "subject": subject,
        "author": author,
        "last_modified_by": last_modified_by,
        "revision_number": revision_number,
    }


def register_project(project_id: str, filename: str, metadata: dict):
    """Register the project in the DB and calculate attributes."""
    project_data = {
        "id": project_id,
        "original_filename": filename,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "status": "processing",
        "slide_count": metadata.get("slide_count", 0),
        "title": metadata.get("title", ""),
        "subject": metadata.get("subject", ""),
        "author": metadata.get("author", ""),
        "last_modified_by": metadata.get("last_modified_by", ""),
        "revision_number": metadata.get("revision_number", ""),
    }

    db.add_project(project_data)

    try:
        attributes = attr_manager.calculate_attributes(project_data)
        db.update_project_attributes(project_id, attributes)
    except Exception as e:
        print(f"[ERROR] Failed to calculate attributes for {project_id}: {e}")


def parse_presentation(project_id: str, upload_path: str, project_dir: str):
    """Parse the uploaded presentation using backend parser directly."""
    pythoncom.CoInitialize()
    try:
        def callback(percent, message):
            print(f"\r    Progress: {percent}% - {message}", end="", flush=True)

        json_path = parsing.parse_presentation(
            upload_path, project_dir, debug=False, progress_callback=callback
        )

        if not json_path:
            db.update_project_status(project_id, "error")
            print("\n    Parsing failed: No JSON produced.")
            return False

        db.update_project_status(project_id, "done")
        print("\n    Parsing completed.")
        return True
    except Exception as e:
        db.update_project_status(project_id, "error")
        print(f"\n    Parsing error for {project_id}: {e}")
        return False
    finally:
        pythoncom.CoUninitialize()


def process_file(file_path: str, directory_path: str):
    filename = os.path.basename(file_path)
    print(f"\nUploading '{os.path.relpath(file_path, directory_path)}'")

    upload_path = os.path.join(UPLOAD_DIR, filename)
    shutil.copyfile(file_path, upload_path)

    metadata_raw = get_metadata_with_com(upload_path)
    project_id, metadata = generate_project_id(filename, metadata_raw)

    existing = db.get_project(project_id)
    if existing:
        print(f"  -> Skipped duplicate. Project ID: {project_id}")
        return

    project_dir = os.path.join(RESULT_DIR, project_id)
    os.makedirs(project_dir, exist_ok=True)

    register_project(project_id, filename, metadata)
    print(f"  -> Registered project ID: {project_id}")

    success = parse_presentation(project_id, upload_path, project_dir)
    if not success:
        print("  -> Processing failed.")


def process_directory(directory_path, dry_run=True, max_upload=None):
    """
    Process a directory:
    1. Find all PPT files recursively
    2. Check for duplicates in DB
    3. Upload and process new files directly via backend methods
    """
    if not os.path.isdir(directory_path):
        print(f"Error: Directory '{directory_path}' not found.")
        return

    ppt_files = find_ppt_files_recursive(directory_path)

    if not ppt_files:
        print(f"No PPT files found under '{directory_path}'.")
        return

    total_found = len(ppt_files)
    print(f"Found {total_found} PPT files under '{directory_path}':")

    for f in ppt_files:
        rel_path = os.path.relpath(f, directory_path)
        print(f"  - {rel_path}")

    # Apply max_upload limit
    if max_upload is not None and max_upload > 0:
        files_to_check = ppt_files[:max_upload]
    elif max_upload is not None and max_upload <= 0:
        print("\n[INFO] --max is 0 or less, no upload will be performed.")
        return
    else:
        files_to_check = ppt_files

    print(f"\nTotal PPTs found: {total_found}")
    if max_upload is not None and max_upload < total_found:
        print(f"Will check at most {max_upload} file(s).")

    # Check for duplicates
    print("\n[INFO] Checking for duplicates in database...")
    analysis_results = analyze_files(files_to_check, directory_path)

    print("\nAnalysis results:")
    for result in analysis_results:
        print(f"  - {result['rel_path']} : {result['status']}")

    new_files = [res for res in analysis_results if res["is_new"]]

    if dry_run:
        print(f"\n[DRY RUN] Eligible new files: {len(new_files)}")
        print("[DRY RUN] No files were uploaded.")
        print("To perform the actual upload, run with the --upload flag:")
        extra = f" --max {max_upload}" if max_upload is not None else ""
        print(f"  python {os.path.basename(sys.argv[0])} {directory_path} --upload{extra}")
        return

    files_to_upload = [res["file_path"] for res in new_files]
    num_to_upload = len(files_to_upload)

    if num_to_upload == 0:
        print("\nNo new files to upload after duplicate check. Exiting.")
        return

    print(f"\nStarting direct upload of {num_to_upload} files...")

    for i, file_path in enumerate(files_to_upload, 1):
        print(f"[{i}/{num_to_upload}] Processing...")
        process_file(file_path, directory_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Bulk upload PPT files directly using backend methods."
    )
    parser.add_argument("directory", help="Root directory containing PPT files")
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Perform actual upload (default is dry-run)",
    )
    parser.add_argument(
        "-m",
        "--max",
        type=int,
        default=None,
        help="Maximum number of PPT files to upload (default: all)",
    )

    args = parser.parse_args()

    process_directory(
        args.directory,
        dry_run=not args.upload,
        max_upload=args.max,
    )
