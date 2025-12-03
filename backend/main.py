import os
import uvicorn
import sys
import shutil

import json
from datetime import datetime
from typing import List, Dict, Any
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pythoncom

import ppt_parser as parsing

app = FastAPI()

# CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
RESULT_DIR = os.path.join(BASE_DIR, "results")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)

# Mount static files for images - serve from project-specific directories
app.mount("/results", StaticFiles(directory=RESULT_DIR), name="results")

# Global progress store: { project_id: { "percent": int, "message": str, "status": "processing"|"done"|"error" } }
progress_store: Dict[str, Dict[str, Any]] = {}


def update_progress(project_id: str, percent: int, message: str):
    if project_id not in progress_store:
        progress_store[project_id] = {
            "percent": 0,
            "message": "",
            "status": "processing",
        }

    progress_store[project_id]["percent"] = percent
    progress_store[project_id]["message"] = message

    if percent >= 100:
        progress_store[project_id]["status"] = "done"
    elif percent < 0:
        progress_store[project_id]["status"] = "error"


def extract_preserved_descriptions(
    shapes: List[Dict[str, Any]], slide_index: int, preserved_data: Dict[tuple, str]
):
    """Recursively extract descriptions from shapes to preserve them during reparse."""
    for shape in shapes:
        name = shape.get("name")
        desc = shape.get("description")
        if name and desc:
            preserved_data[(slide_index, name)] = desc
        if "children" in shape:
            extract_preserved_descriptions(
                shape["children"], slide_index, preserved_data
            )


def run_parsing_task(file_path: str, project_dir: str, project_id: str):
    # Initialize COM for this thread
    pythoncom.CoInitialize()
    try:

        def callback(p, m):
            update_progress(project_id, p, m)

        update_progress(project_id, 0, "Starting...")
        json_path = parsing.parse_presentation(
            file_path, project_dir, debug=False, progress_callback=callback
        )

        if not json_path:
            update_progress(project_id, -1, "Parsing failed to produce JSON")
    except Exception as e:
        print(f"Background task error: {e}")
        update_progress(project_id, -1, str(e))
    finally:
        # Uninitialize COM when done
        pythoncom.CoUninitialize()


class ProjectSummary(BaseModel):
    id: str
    name: str
    created_at: str
    author: str = "Unknown"
    slide_count: int
    title: str = ""
    subject: str = ""
    last_modified_by: str = ""
    revision_number: str = ""


class PositionUpdate(BaseModel):
    slide_index: int
    shape_index: str | int
    left: float
    top: float


class BulkPositionUpdate(BaseModel):
    updates: List[PositionUpdate]


class DescriptionUpdate(BaseModel):
    slide_index: int
    shape_index: str | int
    description: str


@app.middleware("http")
async def log_requests(request, call_next):
    print(f"Request: {request.method} {request.url.path}")
    response = await call_next(request)
    return response


@app.get("/api/projects", response_model=List[ProjectSummary])
def list_projects():
    projects = []
    if not os.path.exists(RESULT_DIR):
        return []

    for folder_name in os.listdir(RESULT_DIR):
        folder_path = os.path.join(RESULT_DIR, folder_name)
        if not os.path.isdir(folder_path):
            continue

        json_path = os.path.join(folder_path, f"{folder_name}.json")
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Extract metadata
                stats = os.stat(json_path)
                created_at = datetime.fromtimestamp(stats.st_ctime).isoformat()

                metadata = data.get("metadata", {})
                builtin = metadata.get("builtin_properties", {})

                projects.append(
                    ProjectSummary(
                        id=folder_name,
                        name=folder_name,
                        created_at=created_at,
                        author=builtin.get("Author") or "Unknown",
                        slide_count=data.get("slides_count", 0),
                        title=builtin.get("Title") or "",
                        subject=builtin.get("Subject") or "",
                        last_modified_by=builtin.get("Last Author") or "",
                        revision_number=str(builtin.get("Revision Number") or ""),
                    )
                )
            except Exception as e:
                print(f"Error reading {json_path}: {e}")

    # Sort by creation time desc
    projects.sort(key=lambda x: x.created_at, reverse=True)
    return projects


@app.post("/api/upload")
async def upload_ppt(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    # Generate a unique ID or use filename
    filename = file.filename
    base_name = os.path.splitext(filename)[0]
    base_name = parsing.make_safe_filename(base_name)

    project_id = base_name
    project_dir = os.path.join(RESULT_DIR, project_id)
    os.makedirs(project_dir, exist_ok=True)

    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Initialize progress
    progress_store[project_id] = {
        "percent": 0,
        "message": "Uploaded",
        "status": "processing",
    }

    # Run parsing in background
    background_tasks.add_task(run_parsing_task, file_path, project_dir, project_id)

    return {"id": project_id, "message": "Upload successful, processing started"}


@app.get("/api/project/{project_id}/status")
def get_project_status(project_id: str):
    if project_id in progress_store:
        return progress_store[project_id]

    # If not in memory, check if it exists on disk (maybe restarted server?)
    project_dir = os.path.join(RESULT_DIR, project_id)
    json_path = os.path.join(project_dir, f"{project_id}.json")
    if os.path.exists(json_path):
        return {"percent": 100, "message": "Done", "status": "done"}

    return {"percent": 0, "message": "Unknown project", "status": "error"}


@app.get("/api/project/{project_id}")
def get_project(project_id: str):
    project_dir = os.path.join(RESULT_DIR, project_id)
    json_path = os.path.join(project_dir, f"{project_id}.json")

    if not os.path.exists(json_path):
        raise HTTPException(status_code=404, detail="Project not found")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data


@app.post("/api/project/{project_id}/update")
def update_project_shape(project_id: str, update: PositionUpdate):
    project_dir = os.path.join(RESULT_DIR, project_id)
    json_path = os.path.join(project_dir, f"{project_id}.json")

    if not os.path.exists(json_path):
        raise HTTPException(status_code=404, detail="Project not found")

    # Read-Modify-Write
    # This is not efficient for high concurrency but fine for this prototype
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Find the slide and shape
    # Shape index in JSON is unique per slide?
    # parsing.py: shape_index=shape_index (1-based integer)
    # But for groups it's "1_1".

    target_slide = None
    for slide in data.get("slides", []):
        if slide.get("slide_index") == update.slide_index:
            target_slide = slide
            break

    if not target_slide:
        raise HTTPException(status_code=404, detail="Slide not found")

    # Helper to find shape recursively
    def find_and_update_shape(shapes, target_id):
        for shape in shapes:
            # shape_index in parsing.py is integer or string.
            # Let's convert to string for comparison
            if str(shape.get("shape_index")) == str(target_id):
                shape["left"] = update.left
                shape["top"] = update.top
                return True

            if "children" in shape:
                if find_and_update_shape(shape["children"], target_id):
                    return True
        return False

    found = find_and_update_shape(target_slide.get("shapes", []), update.shape_index)

    if not found:
        raise HTTPException(status_code=404, detail="Shape not found")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    return {"status": "success"}


@app.post("/api/project/{project_id}/update_positions")
def update_project_positions(project_id: str, bulk_update: BulkPositionUpdate):
    project_dir = os.path.join(RESULT_DIR, project_id)
    json_path = os.path.join(project_dir, f"{project_id}.json")

    if not os.path.exists(json_path):
        raise HTTPException(status_code=404, detail="Project not found")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Create a map for faster lookup: slide_index -> {shape_index -> shape_obj}
    slide_map = {}
    for slide in data.get("slides", []):
        s_idx = slide.get("slide_index")
        shape_map = {}

        def map_shapes(shapes):
            for shape in shapes:
                shape_map[str(shape.get("shape_index"))] = shape
                if "children" in shape:
                    map_shapes(shape["children"])

        map_shapes(slide.get("shapes", []))
        slide_map[s_idx] = shape_map

    # Apply updates
    updated_count = 0
    for update in bulk_update.updates:
        if update.slide_index in slide_map:
            shape_map = slide_map[update.slide_index]
            if str(update.shape_index) in shape_map:
                shape = shape_map[str(update.shape_index)]
                shape["left"] = update.left
                shape["top"] = update.top
                updated_count += 1

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    return {"status": "success", "updated": updated_count}


@app.post("/api/project/{project_id}/update_description")
def update_project_description(project_id: str, update: DescriptionUpdate):
    project_dir = os.path.join(RESULT_DIR, project_id)
    json_path = os.path.join(project_dir, f"{project_id}.json")

    if not os.path.exists(json_path):
        raise HTTPException(status_code=404, detail="Project not found")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    target_slide = None
    for slide in data.get("slides", []):
        if slide.get("slide_index") == update.slide_index:
            target_slide = slide
            break

    if not target_slide:
        raise HTTPException(status_code=404, detail="Slide not found")

    def find_and_update_desc(shapes, target_id):
        for shape in shapes:
            if str(shape.get("shape_index")) == str(target_id):
                shape["description"] = update.description
                return True
            if "children" in shape:
                if find_and_update_desc(shape["children"], target_id):
                    return True
        return False

    found = find_and_update_desc(target_slide.get("shapes", []), update.shape_index)

    if not found:
        raise HTTPException(status_code=404, detail="Shape not found")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    return {"status": "success"}


@app.post("/api/project/{project_id}/reparse_all")
def reparse_all_project(project_id: str):
    project_dir = os.path.join(RESULT_DIR, project_id)
    json_path = os.path.join(project_dir, f"{project_id}.json")

    if not os.path.exists(json_path):
        raise HTTPException(status_code=404, detail="Project not found")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    ppt_path = data.get("ppt_path")
    # Convert relative path to absolute path if needed
    if ppt_path and not os.path.isabs(ppt_path):
        ppt_path = os.path.join(BASE_DIR, ppt_path)

    if not ppt_path or not os.path.exists(ppt_path):
        # Try to find it in uploads if absolute path is missing or wrong
        ppt_path = os.path.join(UPLOAD_DIR, f"{project_id}.pptx")
        if not os.path.exists(ppt_path):
            raise HTTPException(status_code=404, detail="Original PPT file not found")

    try:
        # Extract existing descriptions to preserve them
        # Extract existing descriptions to preserve them
        preserved_data = {}
        for slide in data.get("slides", []):
            extract_preserved_descriptions(
                slide.get("shapes", []), slide.get("slide_index"), preserved_data
            )

        # Initialize COM for this thread
        pythoncom.CoInitialize()

        # Re-run parsing with preserved data
        new_json_path = parsing.parse_presentation(
            ppt_path, project_dir, debug=False, preserved_data=preserved_data
        )

        if not new_json_path:
            raise HTTPException(status_code=500, detail="Reparsing failed")

        return {"status": "success", "message": "Project reparsed successfully"}

    except Exception as e:
        print(f"Reparse error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Uninitialize COM when done
        pythoncom.CoUninitialize()


@app.post("/api/project/{project_id}/slides/{slide_index}/reparse")
def reparse_slide_endpoint(project_id: str, slide_index: int):
    project_dir = os.path.join(RESULT_DIR, project_id)
    json_path = os.path.join(project_dir, f"{project_id}.json")

    if not os.path.exists(json_path):
        raise HTTPException(status_code=404, detail="Project not found")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    ppt_path = data.get("ppt_path")
    # Convert relative path to absolute path if needed
    if ppt_path and not os.path.isabs(ppt_path):
        ppt_path = os.path.join(BASE_DIR, ppt_path)

    if not ppt_path or not os.path.exists(ppt_path):
        ppt_path = os.path.join(UPLOAD_DIR, f"{project_id}.pptx")
        if not os.path.exists(ppt_path):
            raise HTTPException(status_code=404, detail="Original PPT file not found")

    try:
        # Extract existing descriptions to preserve them
        preserved_data = {}
        target_slide = next(
            (s for s in data.get("slides", []) if s.get("slide_index") == slide_index),
            None,
        )
        if target_slide:
            extract_preserved_descriptions(
                target_slide.get("shapes", []), slide_index, preserved_data
            )

        # Initialize COM for this thread
        pythoncom.CoInitialize()

        # Parse single slide
        new_slide_info = parsing.parse_single_slide(
            ppt_path, slide_index, project_dir, preserved_data=preserved_data
        )

        if not new_slide_info:
            raise HTTPException(status_code=500, detail="Slide parsing failed")

        # Update slide in data
        slides = data.get("slides", [])
        found = False
        for i, slide in enumerate(slides):
            if slide.get("slide_index") == slide_index:
                slides[i] = new_slide_info
                found = True
                break

        if not found:
            # If for some reason it wasn't there, append it (though index order might be off)
            slides.append(new_slide_info)
            # Sort by slide_index just in case
            slides.sort(key=lambda x: x.get("slide_index", 0))

        data["slides"] = slides

        # Save updated JSON
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

        return {
            "status": "success",
            "message": f"Slide {slide_index} reparsed successfully",
            "slide": new_slide_info,
        }

    except Exception as e:
        print(f"Slide reparse error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Uninitialize COM when done
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    port = 8000
    if os.environ.get("BACKEND_PORT"):
        port = int(os.environ.get("BACKEND_PORT"))
    elif len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass

    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
