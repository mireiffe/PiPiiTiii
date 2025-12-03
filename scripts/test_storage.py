import urllib.request
import urllib.parse
import json
import os
import sqlite3
import time
import mimetypes

BASE_URL = "http://localhost:8000"
DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "backend",
    "projects.db",
)


def upload_file(url, file_path):
    # Simple multipart/form-data upload using urllib
    boundary = "----WebKitFormBoundary" + hex(int(time.time() * 1000))[2:]
    data = []

    with open(file_path, "rb") as f:
        file_content = f.read()

    filename = os.path.basename(file_path)
    mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

    data.append(f"--{boundary}".encode())
    data.append(
        f'Content-Disposition: form-data; name="file"; filename="{filename}"'.encode()
    )
    data.append(f"Content-Type: {mime_type}".encode())
    data.append(b"")
    data.append(file_content)
    data.append(f"--{boundary}--".encode())
    data.append(b"")

    body = b"\r\n".join(data)
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}

    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())


def get_json(url):
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read().decode())


def test_upload_and_storage():
    # Create a dummy PPT file
    dummy_ppt = "test_storage.pptx"
    with open(dummy_ppt, "wb") as f:
        f.write(b"dummy content")

    try:
        # Upload
        print("Uploading file...")
        try:
            data = upload_file(f"{BASE_URL}/api/upload", dummy_ppt)
        except Exception as e:
            print(f"Upload failed: {e}")
            return

        project_id = data["id"]
        print(f"Project ID: {project_id}")

        # Verify UUID format (simple check)
        if len(project_id) != 36:
            print("Warning: Project ID does not look like a UUID")

        # Check DB
        print("Checking database...")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            print("Project found in DB!")
            # row[1] is original_filename
            if row[1] == dummy_ppt:
                print("Original filename matches.")
            else:
                print(f"Mismatch: {row[1]} != {dummy_ppt}")
        else:
            print("Project NOT found in DB!")

        # Check List Projects API
        print("Checking list projects API...")
        projects = get_json(f"{BASE_URL}/api/projects")
        found = False
        for p in projects:
            if p["id"] == project_id:
                found = True
                print(f"Project found in list: {p['name']} (ID: {p['id']})")
                break

        if not found:
            print("Project NOT found in list API!")

    finally:
        if os.path.exists(dummy_ppt):
            os.remove(dummy_ppt)


if __name__ == "__main__":
    test_upload_and_storage()
