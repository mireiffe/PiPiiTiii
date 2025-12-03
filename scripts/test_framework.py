import os
import sys
import json

# Add backend to sys.path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.ppt_parser import parse_presentation, parse_single_slide
from backend.ppt_reconstructor import reconstruct_presentation


def main(ppt_path_raw, slide_index):
    # Resolve absolute path
    # If the path is relative, it's relative to the project root (where the script is run from)
    # or relative to this script location?
    # Let's assume it's relative to the project root if running from root,
    # but to be safe, let's make it relative to this script if it doesn't exist.

    if not os.path.exists(ppt_path_raw):
        # Try relative to script dir
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        candidate = os.path.join(project_root, ppt_path_raw)
        if os.path.exists(candidate):
            ppt_path = candidate
        else:
            # Try absolute path just in case user provided one
            ppt_path = os.path.abspath(ppt_path_raw)
    else:
        ppt_path = os.path.abspath(ppt_path_raw)

    if not os.path.exists(ppt_path):
        print(f"[ERROR] File not found: {ppt_path}")
        return

    base_name = os.path.splitext(os.path.basename(ppt_path))[0]
    # Output directory in the same folder as the PPT or project root?
    # Let's put it in project root for consistency with previous behavior
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(project_root, "debug", f"{base_name}_out")

    if slide_index is not None:
        print(f"Parsing slide {slide_index} of {ppt_path}...")
        result = parse_single_slide(ppt_path, slide_index, out_dir)
        if result:
            # Save the single slide result to JSON
            json_filename = f"{base_name}_slide_{slide_index}.json"
            json_path = os.path.join(out_dir, json_filename)
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2, default=str)
            print(f"[SUCCESS] Slide {slide_index} parsed successfully.")
            print(f"[INFO] JSON saved to: {json_path}")
            print(f"[INFO] Images saved under: {os.path.join(out_dir, 'images')}")

            # Reconstruction Step (Single Slide)
            print("Reconstructing single slide...")
            # Wrap in a structure expected by reconstructor
            # We need slide_width/height if possible, but parse_single_slide doesn't return them currently?
            # parse_single_slide returns slide_info.
            # Let's just pass what we have. reconstructor handles missing width/height gracefully (defaults).
            reconstruct_data = {"slides": [result]}

            reconstruct_path = os.path.join(
                out_dir, f"{base_name}_slide_{slide_index}_reconstructed.pptx"
            )
            if reconstruct_presentation(
                reconstruct_data, reconstruct_path, image_dir=out_dir
            ):
                print(f"[SUCCESS] Reconstruction complete: {reconstruct_path}")
            else:
                print(f"[ERROR] Reconstruction failed.")
        else:
            print(f"[ERROR] Failed to parse slide {slide_index}.")
    else:
        print(f"Parsing entire presentation {ppt_path}...")
        json_path = parse_presentation(ppt_path, out_dir, debug=False)
        if json_path:
            print(f"[SUCCESS] Presentation parsed. JSON saved to {json_path}")

            # Reconstruction Step
            print("Reconstructing presentation...")
            with open(json_path, "r", encoding="utf-8") as f:
                json_data = json.load(f)

            reconstruct_path = os.path.join(out_dir, f"{base_name}_reconstructed.pptx")
            if reconstruct_presentation(json_data, reconstruct_path, image_dir=out_dir):
                print(f"[SUCCESS] Reconstruction complete: {reconstruct_path}")
            else:
                print(f"[ERROR] Reconstruction failed.")
        else:
            print(f"[ERROR] Failed to parse presentation.")


if __name__ == "__main__":
    # ==========================================
    # Configuration
    # ==========================================
    # Change these variables to test different files or slides
    ppt_path_raw = r"samples/sample_presentation.pptx"
    slide_index = None  # Set to None to parse the entire presentation

    main(ppt_path_raw, slide_index)
