import urllib.request
import urllib.parse
import json
import os
import mimetypes

API_BASE_URL = "http://localhost:8000/api"
SAMPLE_PPT = r"c:\Users\KimSeongeun\world\PiPiiTiii\samples\sample_presentation.pptx"


def upload_file(file_path):
    url = f"{API_BASE_URL}/upload"
    filename = os.path.basename(file_path)

    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    data = []
    data.append(f"--{boundary}")
    data.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"')
    data.append(
        "Content-Type: application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )
    data.append("")

    with open(file_path, "rb") as f:
        data.append(f.read())

    data.append(f"--{boundary}--")
    data.append("")

    # Join parts. Note: binary file content needs careful handling.
    # It's easier to construct body as bytes.
    body = b""
    for item in data:
        if isinstance(item, str):
            body += item.encode("utf-8") + b"\r\n"
        else:
            body += item + b"\r\n"

    req = urllib.request.Request(url, data=body)
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")

    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"Upload failed: {e.code} {e.reason}")
        print(e.read().decode("utf-8"))
        return None
    except Exception as e:
        print(f"Upload failed: {e}")
        return None


def main():
    if not os.path.exists(SAMPLE_PPT):
        print(f"Sample file not found: {SAMPLE_PPT}")
        return

    print("--- 1st Upload ---")
    res1 = upload_file(SAMPLE_PPT)
    if not res1:
        return
    print(f"Result 1: {res1}")
    id1 = res1.get("id")

    print("\n--- 2nd Upload (Duplicate Check) ---")
    res2 = upload_file(SAMPLE_PPT)
    if not res2:
        return
    print(f"Result 2: {res2}")
    id2 = res2.get("id")

    if id1 == id2:
        print("\n[SUCCESS] IDs match!")
        if res2.get("is_duplicate"):
            print("[SUCCESS] Duplicate flag detected.")
        else:
            print("[WARN] Duplicate flag NOT detected (but IDs match).")
    else:
        print(f"\n[FAIL] IDs do not match: {id1} vs {id2}")


if __name__ == "__main__":
    main()
