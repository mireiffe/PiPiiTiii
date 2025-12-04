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

    # 정렬해두면 재현성 있음 (원하면 제거 가능)
    ppt_files.sort()
    return ppt_files


def process_directory(directory_path, dry_run=True, max_upload=None):
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
        # 루트 기준 상대경로로 보여주면 보기 편함
        rel_path = os.path.relpath(f, directory_path)
        print(f" - {rel_path}")

    # 업로드 개수 제한 처리
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
        print("\n[DRY RUN] No files were uploaded.")
        print("To perform the actual upload, run with the --upload flag:")
        extra = ""
        if max_upload is not None:
            extra = f" --max {max_upload}"
        print(f"  python {os.path.basename(sys.argv[0])} {directory_path} --upload{extra}")
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

    args = parser.parse_args()

    process_directory(
        args.directory,
        dry_run=not args.upload,
        max_upload=args.max,
    )
