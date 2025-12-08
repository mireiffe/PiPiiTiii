import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import json
import time
import argparse
import uuid

import requests
from requests.exceptions import HTTPError, RequestException

from backend.ppt_parser.slides import get_presentation_metadata
import pythoncom
from cleanup_projects import RESULT_DIR, validate_result_folder

# Configuration
API_BASE_URL = "http://localhost:8000/api"
PROXIES = {
        "http": None,
        "https": None,
    }


def upload_file(file_path):
    """Uploads a single file to the backend and returns the project ID."""
    url = f"{API_BASE_URL}/upload"
    filename    = os.path.basename(file_path)
    parent      = os.path.basename(os.path.dirname(file_path))
    grandparent = os.path.basename(os.path.dirname(os.path.dirname(file_path)))

    # 필요에 맞게 이어 붙이기
    genealogy = os.path.join(grandparent, parent, filename)

    files = {
        "file": (
            filename,
            genealogy,
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
    """Checks the processing status of a project."""
    url = f"{API_BASE_URL}/project/{project_id}/status"
    try:
        response = requests.get(url, timeout=10, proxies=PROXIES)
        response.raise_for_status()
        return response.json()
    except HTTPError as e:
        print(
            f"Error checking status for {project_id}: "
            f"{e.response.status_code} {e.response.reason}"
        )
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


def check_duplicate(project_id: str, use_api: bool = False) -> str:
    """Check if the project already exists via API or filesystem."""

    if use_api:
        check_url = f"{API_BASE_URL}/project/{project_id}"
        try:
            resp = requests.get(check_url, timeout=5, proxies=PROXIES)
            if resp.status_code == 200:
                return f"Duplicate (ID: {project_id})"
            if resp.status_code == 404:
                return "New"
            return f"Error checking ({resp.status_code})"
        except RequestException as e:
            return f"Check failed: {e}"

    folder_path = os.path.join(RESULT_DIR, project_id)
    if not os.path.isdir(folder_path):
        return "New"

    ok, reason = validate_result_folder(project_id, folder_path)
    if ok:
        return f"Duplicate (ID: {project_id})"

    return f"Existing but invalid: {reason}"


def find_ppt_files_recursive(directory_path):
    """
    주어진 디렉토리 하위(서브디렉토리 포함)를 모두 돌면서
    .ppt, .pptx 파일의 전체 경로 리스트를 반환.
    """
    ppt_files = []
    for root, dirs, files in os.walk(directory_path):
        for f in files:
            if f.lower().endswith((".ppt", ".pptx")):
                full_path = os.path.join(root, f)
                ppt_files.append(full_path)

    ppt_files.sort()
    return ppt_files


def process_directory(directory_path, dry_run=True, max_upload=None, use_api_check=False):
    """
    1) 폴더 하위 전체를 돌면서 ppt* 파일을 찾고
    2) (옵션) 업로드할 파일 개수를 max_upload 로 제한해서 업로드.
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
        print(f" - {rel_path}")

    if max_upload is not None:
        if max_upload <= 0:
            print("\n[INFO] --max 값이 0 이하라서 실제 업로드는 수행하지 않습니다.")
            files_to_upload = []
        else:
            files_to_upload = ppt_files[:max_upload]
    else:
        files_to_upload = ppt_files

    print(f"\nTotal PPTs found: {total_found}")
    if max_upload is not None and max_upload < total_found:
        print(f"Will upload at most {max_upload} file(s).")
    else:
        print("Will upload all found PPT files.")

    if dry_run:
        print("\n[DRY RUN] Checking for duplicates...")

        for i, file_path in enumerate(files_to_upload, 1):
            filename = os.path.basename(file_path)
            rel_path = os.path.relpath(file_path, directory_path)

            status_msg = "New"

            if get_presentation_metadata:
                try:
                    pythoncom.CoInitialize()
                    try:
                        # COM requires absolute path
                        abs_path = os.path.abspath(file_path)
                        metadata = get_presentation_metadata(abs_path)
                    finally:
                        pythoncom.CoUninitialize()

                    if metadata:
                        title = metadata.get("title", "")
                        slide_count = metadata.get("slide_count", 0)
                        seed = f"{filename}|{title}|{slide_count}"
                        APP_NAMESPACE = uuid.uuid5(
                            uuid.NAMESPACE_DNS, "pipiitiii.local"
                        )
                        project_id = str(uuid.uuid5(APP_NAMESPACE, seed))

                        status_msg = check_duplicate(project_id, use_api=use_api_check)
                    else:
                        status_msg = "Metadata extraction failed"
                except Exception as e:
                    status_msg = f"Error: {e}"
            else:
                status_msg = "Skipped check (no backend module)"

            print(f" - {rel_path} : {status_msg}")

        print("\n[DRY RUN] No files were uploaded.")
        print("To perform the actual upload, run with the --upload flag:")
        extra = ""
        if max_upload is not None:
            extra = f" --max {max_upload}"
        print(
            f"  python {os.path.basename(sys.argv[0])} {directory_path} --upload{extra}"
        )
        return

    num_to_upload = len(files_to_upload)
    if num_to_upload == 0:
        print("\nNo files selected for upload (maybe --max 0?). Exiting.")
        return

    print(f"\nStarting upload of {num_to_upload} files...")

    for i, file_path in enumerate(files_to_upload, 1):
        filename = os.path.basename(file_path)
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
        "-m",
        "--max",
        type=int,
        default=None,
        help="Maximum number of PPT files to upload (default: all)",
    )
    parser.add_argument(
        "--use-api-duplicate-check",
        action="store_true",
        help="Use API to check duplicates instead of filesystem results",
    )

    args = parser.parse_args()

    process_directory(
        args.directory,
        dry_run=not args.upload,
        max_upload=args.max,
        use_api_check=args.use_api_duplicate_check,
    )
