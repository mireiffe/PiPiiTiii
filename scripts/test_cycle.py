"""
PPT Parsing & Reconstruction Cycle Test

Tests the complete cycle:
1. Parse original PPT -> Reconstruct to AB folder
2. Parse reconstructed PPT -> Reconstruct to BA folder

This validates that parsing + reconstruction maintains data integrity.
"""

import sys
import os
import json
from pathlib import Path
import shutil

# Add backend to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.ppt_parser.slides import parse_presentation, parse_single_slide
from backend.ppt_reconstructor import reconstruct_presentation


def ensure_clean_directory(directory: Path):
    """Remove and recreate a directory to ensure clean state."""
    if directory.exists():
        shutil.rmtree(directory)
    directory.mkdir(parents=True, exist_ok=True)


def cycle_test(
    ppt_path_raw: str, slide_index: int = None, output_base: str = "debug_cycle"
):
    """
    Run complete parsing & reconstruction cycle test.

    Args:
        ppt_path_raw: Path to original PowerPoint file
        slide_index: Index of the slide to test (1-based). If None, tests entire PPT.
        output_base: Base directory for cycle outputs (default: debug_cycle)
    """
    ppt_path = Path(ppt_path_raw).resolve()
    if not ppt_path.exists():
        raise FileNotFoundError(f"PPT file not found: {ppt_path}")

    print(f"\n{'=' * 60}")
    print(f"PPT CYCLE TEST: {ppt_path.name}")
    print(f"{'=' * 60}\n")

    # Setup output directories
    base_dir = Path(output_base).resolve()
    ab_dir = base_dir / "AB"
    ba_dir = base_dir / "BA"

    ensure_clean_directory(ab_dir)
    ensure_clean_directory(ba_dir)

    # =========================================================================
    # CYCLE A->B: Parse original PPT, reconstruct to AB folder
    # =========================================================================
    print("\n[CYCLE A->B] Step 1: Parsing original PPT...")
    ab_json_path = ab_dir / f"{ppt_path.stem}.json"
    ab_images_dir = ab_dir / "images"
    # ab_images_dir.mkdir(exist_ok=True) # parse_presentation creates this

    try:
        if slide_index is not None:
            print(f"Parsing single slide {slide_index}...")
            slide_data = parse_single_slide(str(ppt_path), slide_index, str(ab_dir))
            if not slide_data:
                raise Exception(f"Failed to parse slide {slide_index}")

            # Wrap in full structure for reconstruction
            ab_data = {
                "ppt_path": str(ppt_path),
                "slides_count": 1,
                "slides": [slide_data],
            }

            with open(ab_json_path, "w", encoding="utf-8") as f:
                json.dump(ab_data, f, ensure_ascii=False, indent=2, default=str)
        else:
            parse_presentation(str(ppt_path), str(ab_dir), debug=False)

        print(f"[OK] Parsing complete: {ab_json_path}")
    except Exception as e:
        print(f"[FAIL] Parsing failed: {e}")
        raise

    print("\n[CYCLE A->B] Step 2: Reconstructing from parsed JSON...")
    ab_recon_path = ab_dir / f"{ppt_path.stem}_reconstructed.pptx"
    ab_recon_images_dir = ab_dir / "recon"
    # ab_recon_images_dir.mkdir(exist_ok=True) # reconstruct_presentation creates this

    try:
        if slide_index is None:
            with open(ab_json_path, "r", encoding="utf-8") as f:
                ab_data = json.load(f)
        # If slide_index is not None, ab_data is already in memory from previous step

        reconstruct_presentation(ab_data, str(ab_recon_path), image_dir=str(ab_dir))
        print(f"[OK] Reconstruction complete: {ab_recon_path}")
    except Exception as e:
        print(f"[FAIL] Reconstruction failed: {e}")
        raise

    # =========================================================================
    # CYCLE B->A: Parse reconstructed PPT, reconstruct to BA folder
    # =========================================================================
    print("\n[CYCLE B->A] Step 3: Parsing reconstructed PPT...")
    ba_json_path = ba_dir / f"{ppt_path.stem}_reconstructed.json"
    ba_images_dir = ba_dir / "images"
    # ba_images_dir.mkdir(exist_ok=True)

    try:
        if not ab_recon_path.exists():
            raise FileNotFoundError(f"Reconstructed file not found: {ab_recon_path}")

        if slide_index is not None:
            # The reconstructed PPT has only 1 slide (which is the one we extracted)
            # So we parse slide 1 from the new PPT
            print(f"Parsing single slide 1 from reconstructed PPT: {ab_recon_path}")
            slide_data_ba = parse_single_slide(str(ab_recon_path), 1, str(ba_dir))
            if not slide_data_ba:
                raise Exception("Failed to parse slide 1 from reconstructed PPT")

            ba_data = {
                "ppt_path": str(ab_recon_path),
                "slides_count": 1,
                "slides": [slide_data_ba],
            }

            with open(ba_json_path, "w", encoding="utf-8") as f:
                json.dump(ba_data, f, ensure_ascii=False, indent=2, default=str)
        else:
            parse_presentation(str(ab_recon_path), str(ba_dir), debug=False)

        print(f"[OK] Parsing complete: {ba_json_path}")
    except Exception as e:
        print(f"[FAIL] Parsing failed: {e}")
        raise

    print("\n[CYCLE B->A] Step 4: Reconstructing from re-parsed JSON...")
    ba_recon_path = ba_dir / f"{ppt_path.stem}_reconstructed_v2.pptx"
    ba_recon_images_dir = ba_dir / "recon"
    # ba_recon_images_dir.mkdir(exist_ok=True)

    try:
        if slide_index is None:
            with open(ba_json_path, "r", encoding="utf-8") as f:
                ba_data = json.load(f)
        # If slide_index is not None, ba_data is already in memory or we should load it?
        # Actually we constructed ba_data in the previous block if slide_index is not None.
        # But to be safe and consistent (and if we want to ensure we use what's on disk), let's reload it or just use it.
        # The original code loaded it. Let's just ensure ba_data is available.
        if "ba_data" not in locals():
            with open(ba_json_path, "r", encoding="utf-8") as f:
                ba_data = json.load(f)

        reconstruct_presentation(ba_data, str(ba_recon_path), image_dir=str(ba_dir))
        print(f"[OK] Reconstruction complete: {ba_recon_path}")
    except Exception as e:
        print(f"[FAIL] Reconstruction failed: {e}")
        raise

    # =========================================================================
    # Summary
    # =========================================================================
    print(f"\n{'=' * 60}")
    print("CYCLE TEST COMPLETE")
    print(f"{'=' * 60}")
    print(f"\nCycle A->B outputs:")
    print(f"  JSON:   {ab_json_path}")
    print(f"  Images: {ab_images_dir}")
    print(f"  Recon:  {ab_recon_path}")
    print(f"  Slides: {ab_recon_images_dir}")

    print(f"\nCycle B->A outputs:")
    print(f"  JSON:   {ba_json_path}")
    print(f"  Images: {ba_images_dir}")
    print(f"  Recon:  {ba_recon_path}")
    print(f"  Slides: {ba_recon_images_dir}")

    print(f"\n[OK] All cycles completed successfully!")
    print(f"Compare AB vs BA outputs to verify data integrity.\n")


if __name__ == "__main__":
    # =========================================================================
    # CONFIGURATION
    # =========================================================================
    # Edit these variables before running:

    ppt_path_raw = r"samples/sample_presentation.pptx"
    slide_index = None  # Set to None to test entire PPT, or integer (e.g. 1) to test specific slide
    output_base = "debug_cycle"

    # =========================================================================
    # RUN CYCLE TEST
    # =========================================================================
    try:
        cycle_test(ppt_path_raw, slide_index, output_base)
    except Exception as e:
        print(f"\n[FAIL] Cycle test failed with error:\n{e}")
        sys.exit(1)
