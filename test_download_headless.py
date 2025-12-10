import urllib.request
import urllib.error
import json
import os

BASE_URL = "http://localhost:8000"


def test_download():
    print("Fetching projects...")
    try:
        with urllib.request.urlopen(f"{BASE_URL}/api/projects") as response:
            data = response.read()
            projects = json.loads(data)
    except Exception as e:
        print(f"Failed to fetch projects: {e}")
        return

    if not projects:
        print("No projects found to test download.")
        return

    project_id = projects[0]["id"]
    print(f"Testing download for project ID: {project_id}")

    print("Requesting download...")
    try:
        download_url = f"{BASE_URL}/api/project/{project_id}/download"
        with urllib.request.urlopen(download_url) as response:
            content_disposition = response.headers.get("Content-Disposition")
            print(f"Content-Disposition: {content_disposition}")

            if content_disposition and "reconstructed_" in content_disposition:
                print("SUCCESS: Filename contains 'reconstructed_' prefix.")
            else:
                print("FAILURE: Filename does NOT contain 'reconstructed_' prefix.")

            # Save file
            filename = "test_downloaded.pptx"
            if content_disposition:
                if 'filename="' in content_disposition:
                    filename = content_disposition.split('filename="')[1].split('"')[0]
                elif "filename=" in content_disposition:
                    filename = content_disposition.split("filename=")[1]

            with open(filename, "wb") as f:
                f.write(response.read())

            print(f"File downloaded to: {filename}")
            print(f"File size: {os.path.getsize(filename)} bytes")

    except Exception as e:
        print(f"Download failed: {e}")


if __name__ == "__main__":
    test_download()
