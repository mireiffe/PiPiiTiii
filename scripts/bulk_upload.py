import os
import sys
import json
import time
import argparse

import requests


# Configuration
API_BASE_URL = "http://localhost:8000/api"


def upload_file(file_path):
    """Uploads a single file to the backend and returns the project ID."""
    url = f"{API_BASE_URL}/upload"
    filename = os.path.basename(file_path)

    # requests가 multipart/form-data를 알아서 만들어주므로 직접 boundary 만들 필요 없음
    files = {
        "file": (
            filename,
            open(file_path, "rb"),
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        )
    }

    proxies = {
        "http": None,
        "https": None,
    }

    try:
        # 필요하면 timeout 값 조정 가능
        resp = requests.post(url, files=files, timeout=10, proxies=proxies)
        resp.raise_for_status()
        result = resp.json()
        return result.get("id")
    except requests.exceptions.HTTPError as e:
        print(f"Error uploading {filename}: {resp.status_code} {resp.reason}")
        try:
            print(resp.text)
        except Exception:
            pass
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error uploading {filename}: {str(e)}")
        return None
    finally:
        # 파일 핸들 닫기
        try:
            files["file"][1].close()
        except Exception:
            pass


def check_status(project_id):
    """Checks the processing status of a project."""
    url = f"{API_BASE_URL}/project/{project_id}/status"
    proxies = {
        "http": None,
        "https": None,
    }
    try:
        resp = requests.get(url, timeout=10, proxies=proxies)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        print(f"Error checking status for {project_id}: {str(e)}")
        return None


def process_directory(directory_path, dry_run=True):
    """Finds and uploads all PPT files in the directory."""
    if not os.path.isdir(directory_path):
        print(f"Error: Directory '{directory_path}' not found.")
        return

    ppt_files = [
        f for f in os.listdir(directory_path) if f.lower().endswith((".pptx", ".ppt"))
    ]

    if not ppt_files:
        print(f"No PPT files found in '{directory_path}'.")
        return

    print(f"Found {len(ppt_files)} PPT files in '{directory_path}':")
    for f in ppt_files:
        print(f" - {f}")

    if dry_run:
        print("\n[DRY RUN] No files were uploaded.")
        print("To perform the actual upload, run with the --upload flag:")
        print(f"  python {os.path.basename(sys.argv[0])} {directory_path} --upload")
        return

    print(f"\nStarting upload of {len(ppt_files)} files...")

    for i, filename in enumerate(ppt_files, 1):
        file_path = os.path.join(directory_path, filename)
        print(f"\n[{i}/{len(ppt_files)}] Uploading '{filename}'...")

        project_id = upload_file(file_path)

        if not project_id:
            print("  -> Upload failed. Skipping.")
            continue

        print(f"  -> Uploaded. Project ID: {project_id}")
        print("  -> Waiting for processing...", end="", flush=True)

        # Poll for completion
        while True:
            status = check_status(project_id)
            if not status:
                print("\n  -> Status check failed.")
                break

            if status["status"] == "done":
                print(" Done!")
                break
            elif status["status"] == "error":
                print(f"\n  -> Processing failed: {status.get('message')}")
                break

            print(".", end="", flush=True)
            time.sleep(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Bulk upload PPT files to PiPiiTiii backend."
    )
    parser.add_argument("directory", help="Directory containing PPT files")
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Perform actual upload (default is dry-run)",
    )

    args = parser.parse_args()

    process_directory(args.directory, dry_run=not args.upload)
