import argparse
import os
import sys
import json
import pythoncom
import win32com.client as win32

# Ensure backend modules are importable
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
sys.path.append(BASE_DIR)
sys.path.append(BACKEND_DIR)

from backend.database import Database

DB_PATH = os.path.join(BASE_DIR, "backend", "data", "projects.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
RESULT_DIR = os.path.join(BASE_DIR, "results")

db = Database(DB_PATH)


def generate_slide_thumbnail(slide, slide_index, thumbnail_dir, max_dimension=1920):
    """
    Generate a thumbnail image for a single slide.
    The thumbnail maintains the slide's aspect ratio with the longest side set to max_dimension.
    Returns the relative path to the thumbnail file, or None if failed.
    """
    try:
        os.makedirs(thumbnail_dir, exist_ok=True)
        thumbnail_filename = f"slide_{slide_index:03d}_thumb.png"
        thumbnail_path = os.path.join(thumbnail_dir, thumbnail_filename)

        # Get slide dimensions from presentation
        presentation = slide.Parent
        slide_width = float(presentation.PageSetup.SlideWidth)
        slide_height = float(presentation.PageSetup.SlideHeight)

        # Calculate thumbnail dimensions maintaining aspect ratio
        # Set the longer side to max_dimension
        if slide_width >= slide_height:
            # Landscape or square
            thumb_width = max_dimension
            thumb_height = int(max_dimension * slide_height / slide_width)
        else:
            # Portrait
            thumb_height = max_dimension
            thumb_width = int(max_dimension * slide_width / slide_height)

        # Export slide as image
        slide.Export(thumbnail_path, "PNG", ScaleWidth=thumb_width, ScaleHeight=thumb_height)

        print(f"    Generated thumbnail: {thumbnail_filename} ({thumb_width}x{thumb_height})")
        return thumbnail_filename
    except Exception as e:
        print(f"    [WARN] Failed to generate thumbnail for slide {slide_index}: {e}")
        return None


def regenerate_thumbnails_for_project(project_id, ppt_path, project_dir):
    """
    Regenerate thumbnails for a single project.
    Reads the existing JSON, opens the PPT, generates thumbnails, and updates the JSON.
    """
    print(f"\nProcessing project: {project_id}")

    if not os.path.exists(ppt_path):
        print(f"  [ERROR] PPT file not found: {ppt_path}")
        return False

    # Check if JSON exists
    json_path = os.path.join(project_dir, f"{project_id}.json")
    if not os.path.exists(json_path):
        print(f"  [ERROR] JSON file not found: {json_path}")
        return False

    # Load existing JSON
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    thumbnail_dir = os.path.join(project_dir, "thumbnails")
    os.makedirs(thumbnail_dir, exist_ok=True)

    pythoncom.CoInitialize()
    try:
        powerpoint = win32.gencache.EnsureDispatch("PowerPoint.Application")
        presentation = None

        try:
            # Open presentation read-only
            presentation = powerpoint.Presentations.Open(
                ppt_path, ReadOnly=True, Untitled=False, WithWindow=False
            )

            slides_count = presentation.Slides.Count
            print(f"  Slides count: {slides_count}")

            # Generate thumbnails and update slide info
            updated = False
            for i, slide_data in enumerate(data.get("slides", [])):
                slide_index = slide_data.get("slide_index", i + 1)

                try:
                    slide = presentation.Slides(slide_index)
                    thumbnail_filename = generate_slide_thumbnail(
                        slide, slide_index, thumbnail_dir
                    )

                    if thumbnail_filename:
                        slide_data["thumbnail"] = thumbnail_filename
                        updated = True
                except Exception as e:
                    print(f"    [ERROR] Failed to process slide {slide_index}: {e}")

            if updated:
                # Save updated JSON
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2, default=str)
                print("  [INFO] Updated JSON with thumbnail information")
                return True
            else:
                print("  [WARN] No thumbnails were generated")
                return False

        except Exception as e:
            print(f"  [ERROR] Failed to open presentation: {e}")
            return False
        finally:
            if presentation:
                try:
                    presentation.Close()
                except Exception:
                    pass
            try:
                powerpoint.Quit()
            except Exception:
                pass

    finally:
        pythoncom.CoUninitialize()


def regenerate_all_thumbnails(dry_run=True, max_process=None):
    """
    Regenerate thumbnails for all projects in the database.
    """
    projects = db.list_projects()

    if not projects:
        print("No projects found in database.")
        return

    print(f"Found {len(projects)} project(s) in database.")

    # Filter projects with status 'done'
    done_projects = [p for p in projects if p.get("status") == "done"]
    print(f"{len(done_projects)} project(s) with status 'done'.")

    if not done_projects:
        print("No projects to process.")
        return

    # Apply max_process limit
    if max_process is not None and max_process > 0:
        projects_to_process = done_projects[:max_process]
    else:
        projects_to_process = done_projects

    print(f"\nWill process {len(projects_to_process)} project(s).")

    if dry_run:
        print("\n[DRY RUN] Projects that would be processed:")
        for p in projects_to_process:
            project_id = p["id"]
            filename = p.get("original_filename", "Unknown")
            print(f"  - {project_id}: {filename}")

        print("\nTo perform actual thumbnail regeneration, run with --execute flag:")
        extra = f" --max {max_process}" if max_process is not None else ""
        print(f"  python {os.path.basename(sys.argv[0])} --execute{extra}")
        return

    # Process each project
    success_count = 0
    fail_count = 0

    for idx, project in enumerate(projects_to_process, 1):
        project_id = project["id"]
        filename = project.get("original_filename", "Unknown")

        print(f"\n[{idx}/{len(projects_to_process)}] Processing {filename}")

        # Find PPT file
        ppt_path = os.path.join(UPLOAD_DIR, filename)
        project_dir = os.path.join(RESULT_DIR, project_id)

        if not os.path.exists(project_dir):
            print(f"  [ERROR] Project directory not found: {project_dir}")
            fail_count += 1
            continue

        success = regenerate_thumbnails_for_project(project_id, ppt_path, project_dir)

        if success:
            success_count += 1
        else:
            fail_count += 1

    print("\n=== Summary ===")
    print(f"Total processed: {len(projects_to_process)}")
    print(f"Success: {success_count}")
    print(f"Failed: {fail_count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Regenerate thumbnails for existing projects."
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute thumbnail regeneration (default is dry-run)",
    )
    parser.add_argument(
        "-m",
        "--max",
        type=int,
        default=None,
        help="Maximum number of projects to process (default: all)",
    )

    args = parser.parse_args()

    regenerate_all_thumbnails(dry_run=not args.execute, max_process=args.max)
