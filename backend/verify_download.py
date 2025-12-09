import urllib.request
import urllib.error
import json
import os
import zipfile

# Assuming the server is running on localhost:8000
BASE_URL = "http://localhost:8000"


def test_download(project_id):
    url = f"{BASE_URL}/api/project/{project_id}/download"
    print(f"Testing download for project: {project_id}")

    try:
        with urllib.request.urlopen(url) as response:
            if response.status == 200:
                filename = "downloaded_test.pptx"
                content_disposition = response.headers.get("Content-Disposition")
                if content_disposition:
                    print(f"Content-Disposition: {content_disposition}")

                with open(filename, "wb") as f:
                    f.write(response.read())

                print(f"SUCCESS: File downloaded to {filename}")
                print(f"File size: {os.path.getsize(filename)} bytes")

                if zipfile.is_zipfile(filename):
                    print("SUCCESS: File is a valid ZIP/PPTX archive")
                else:
                    print("ERROR: File is NOT a valid ZIP/PPTX archive")

            else:
                print(f"FAILED: Status code {response.status}")

    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} {e.reason}")
        print(e.read().decode())
    except Exception as e:
        print(f"ERROR: {e}")


if __name__ == "__main__":
    try:
        with urllib.request.urlopen(f"{BASE_URL}/api/projects") as response:
            projects = json.loads(response.read().decode())
            if projects:
                print(f"Found {len(projects)} projects. Testing with the first one.")
                test_download(projects[0]["id"])
            else:
                print("No projects found to test.")
    except Exception as e:
        print(f"Failed to fetch projects: {e}")
