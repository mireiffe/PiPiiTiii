import os
import sys
import sqlite3
import time
import argparse

import requests
from requests.exceptions import HTTPError, RequestException

# Configuration
API_BASE_URL = "http://localhost:8000/api"
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "backend", "data", "projects.db")
PROXIES = {
    "http": None,
    "https": None,
}


def upload_file(file_path):
    """Upload a single file to the backend and return the project ID."""
    url = f"{API_BASE_URL}/upload"
    filename = os.path.basename(file_path)

    files = {
        "file": (
            filename,
            open(file_path, "rb"),
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        )
    }

    try:
        with requests.post(url, files=files, timeout=60, proxies=PROXIES) as response:
            response.raise_for_status()
            result = response.json()
            return result.get("id")

    except HTTPError as e:
        print(f"Error uploading {filename}: {e.response.status_code} {e.response.reason}")
        try:
            print(e.response.text)
        except Exception:
            pass
        return None
    except RequestException as e:
        print(f"Error uploading {filename}: {str(e)}")
        return None
    except Exception as e:
        print(f"Unexpected error uploading {filename}: {str(e)}")
        return None


def check_status(project_id):
    """Check the processing status of a project."""
    url = f"{API_BASE_URL}/project/{project_id}/status"
    try:
        response = requests.get(url, timeout=10, proxies=PROXIES)
        response.raise_for_status()
        return response.json()
    except HTTPError as e:
        print(f"Error checking status for {project_id}: {e.response.status_code} {e.response.reason}")
        try:
            print(e.response.text)
        except Exception:
            pass
        return None
    except RequestException as e:
        print(f"Error checking status for {project_id}: {str(e)}")
        return None
    except Exception as e:
        print(f"Unexpected error checking status for {project_id}: {str(e)}")
        return None


def check_duplicate_by_db(filename: str) -> tuple[bool, str | None]:
    """Check if a project with the same original_filename exists in DB."""
    if not os.path.exists(DB_PATH):
        return False, None

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM projects WHERE original_filename = ?",
            (filename,)
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

        results.append({
            "file_path": file_path,
            "rel_path": rel_path,
            "status": status_msg,
            "is_new": is_new,
        })

    return results


def process_directory(directory_path, dry_run=True, max_upload=None):
    """
    Process a directory:
    1. Find all PPT files recursively
    2. Check for duplicates in DB
    3. Upload new files (respecting max_upload limit)
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

    # Upload new files
    files_to_upload = [res["file_path"] for res in new_files]
    num_to_upload = len(files_to_upload)

    if num_to_upload == 0:
        print("\nNo new files to upload after duplicate check. Exiting.")
        return

    print(f"\nStarting upload of {num_to_upload} files...")

    for i, file_path in enumerate(files_to_upload, 1):
        rel_path = os.path.relpath(file_path, directory_path)
        print(f"\n[{i}/{num_to_upload}] Uploading '{rel_path}'...")

        project_id = upload_file(file_path)

        if not project_id:
            print("  -> Upload failed. Skipping.")
            continue

        print(f"  -> Uploaded. Project ID: {project_id}")
        print("  -> Waiting for processing...", end="", flush=True)

        while True:
            status = check_status(project_id)
            if not status:
                print("\n  -> Status check failed.")
                break

            if status.get("status") == "done":
                print(" Done!")
                break
            elif status.get("status") == "error":
                print(f"\n  -> Processing failed: {status.get('message')}")
                break

            print(".", end="", flush=True)
            time.sleep(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Bulk upload PPT files (recursively) to PiPiiTiii backend."
    )
    parser.add_argument("directory", help="Root directory containing PPT files")
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Perform actual upload (default is dry-run)",
    )
    parser.add_argument(
        "-m", "--max",
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
