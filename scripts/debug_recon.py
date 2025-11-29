import os
import sys
import json

# Add backend to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.ppt_reconstructor import reconstruct_presentation


def main():
    json_path = r"c:\Users\KimSeongeun\world\PiPiiTiii\results\debug\250215_GenerativeModels_out\250215_GenerativeModels_slide_5.json"
    output_ppt = r"c:\Users\KimSeongeun\world\PiPiiTiii\results\debug\250215_GenerativeModels_out\debug_recon_slide_5.pptx"

    if not os.path.exists(json_path):
        print(f"JSON file not found: {json_path}")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Wrap in "slides" list if it's a single slide object
    if "slides" not in data and "shapes" in data:
        presentation_data = {"slides": [data]}
        # Copy slide size if available
        if "slide_width" in data:
            presentation_data["slide_width"] = data["slide_width"]
        if "slide_height" in data:
            presentation_data["slide_height"] = data["slide_height"]
    else:
        presentation_data = data

    success = reconstruct_presentation(presentation_data, output_ppt)
    if success:
        print(f"Reconstruction successful: {output_ppt}")
    else:
        print("Reconstruction failed.")


if __name__ == "__main__":
    main()
