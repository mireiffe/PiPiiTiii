import os
import json
import ppt_reconstructor
import pythoncom

# Mocking the environment
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
RESULT_DIR = os.path.join(BASE_DIR, "results")


def debug_reconstruction(project_id):
    project_dir = os.path.join(RESULT_DIR, project_id)
    json_path = os.path.join(project_dir, f"{project_id}.json")

    if not os.path.exists(json_path):
        print(f"Project not found: {json_path}")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    output_filename = f"debug_{data.get('original_filename', 'presentation.pptx')}"
    output_path = os.path.join(project_dir, output_filename)

    print(f"Reconstructing to: {output_path}")

    pythoncom.CoInitialize()
    try:
        success = ppt_reconstructor.reconstruct_presentation(
            data, output_path, image_dir=UPLOAD_DIR
        )
        if success:
            print("Reconstruction SUCCESS")
        else:
            print("Reconstruction FAILED")
    except Exception as e:
        print(f"Reconstruction ERROR: {e}")
    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    # Hardcoded project ID from the previous failure output
    project_id = "33fe3ca9-1062-5c0d-832e-109befb4d826"
    debug_reconstruction(project_id)
