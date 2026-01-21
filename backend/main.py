import os
import uvicorn
import sys
import shutil

import json
import hashlib
from datetime import datetime
from typing import List, Dict, Any
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pythoncom

import uuid
import ppt_parser as parsing
from database import Database
from attachments_db import AttachmentsDatabase
import asyncio
from attributes.manager import AttributeManager
from llm_service import LLMService
from typing import Optional

# Import utility modules
from utils import (
    create_file_resolver,
    extract_preserved_descriptions,
    update_shape_property,
)


def calculate_prompt_version(settings: dict) -> str:
    """Calculate a hash of all prompt configurations for version tracking."""
    summary_fields = settings.get("summary_fields", [])
    # Create a deterministic string from prompts
    prompt_data = []
    for field in sorted(summary_fields, key=lambda x: x.get("id", "")):
        prompt_data.append(
            {
                "id": field.get("id", ""),
                "system_prompt": field.get("system_prompt", ""),
                "user_prompt": field.get("user_prompt", ""),
            }
        )
    prompt_str = json.dumps(prompt_data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(prompt_str.encode()).hexdigest()[:12]


app = FastAPI()

# Database setup
DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "backend",
    "data",
    "projects.db",
)
db = Database(DB_PATH)

# Attachments database (separate DB for BLOB storage)
ATTACHMENTS_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "backend",
    "data",
    "attachments.db",
)
attachments_db = AttachmentsDatabase(ATTACHMENTS_DB_PATH)


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
SETTINGS_FILE = os.path.join(BASE_DIR, "backend", "data", "settings.json")

attr_manager = AttributeManager(
    db, os.path.join(BASE_DIR, "backend", "attributes", "definitions")
)

# Initialize file resolver
file_resolver = create_file_resolver(BASE_DIR, UPLOAD_DIR, db)

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)

# Mount static files for images - serve from project-specific directories
app.mount("/api/results", StaticFiles(directory=RESULT_DIR), name="results")

# Global progress store: { project_id: { "percent": int, "message": str, "status": "processing"|"done"|"error" } }
progress_store: Dict[str, Dict[str, Any]] = {}


def sync_legacy_projects():
    """Import existing projects from disk to DB if not present."""
    if not os.path.exists(RESULT_DIR):
        return

    existing_ids = {p["id"] for p in db.list_projects()}

    for folder_name in os.listdir(RESULT_DIR):
        if folder_name in existing_ids:
            continue

        folder_path = os.path.join(RESULT_DIR, folder_name)
        if not os.path.isdir(folder_path):
            continue

        json_path = os.path.join(folder_path, f"{folder_name}.json")
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                stats = os.stat(json_path)
                created_at = datetime.fromtimestamp(stats.st_ctime).isoformat()
                metadata = data.get("metadata", {})
                builtin = metadata.get("builtin_properties", {})

                db.add_project(
                    {
                        "id": folder_name,
                        "original_filename": f"{folder_name}.pptx",  # Best guess for legacy
                        "created_at": created_at,
                        "status": "done",
                        "slide_count": data.get("slides_count", 0),
                        "title": builtin.get("Title") or "",
                        "subject": builtin.get("Subject") or "",
                        "last_modified_by": builtin.get("Last Author") or "",
                        "revision_number": str(builtin.get("Revision Number") or ""),
                    }
                )
                print(f"Imported legacy project: {folder_name}")
            except Exception as e:
                print(f"Error importing {folder_name}: {e}")


# Sync on startup
sync_legacy_projects()


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


# extract_preserved_descriptions is now imported from utils.shape_utils


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
            db.update_project_status(project_id, "error")
            return

        # JSON 읽어서 메타데이터 추출 (필요하다면)
        # with open(json_path, "r", encoding="utf-8") as f:
        #     data = json.load(f)

        db.update_project_status(project_id, "done")

        update_progress(project_id, 100, "Done")

    except Exception as e:
        print(f"Background task error: {e}")
        update_progress(project_id, -1, str(e))
        db.update_project_status(project_id, "error")
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

    class Config:
        extra = "allow"


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


class LLMConfig(BaseModel):
    api_type: str = "openai"  # "openai" | "gemini" | "openai_compatible"
    api_endpoint: str = "https://api.openai.com/v1"
    model_name: str = "gpt-4o"


class SummaryField(BaseModel):
    id: str
    name: str
    order: int
    system_prompt: str = ""
    user_prompt: str = ""


class WorkflowStepColumn(BaseModel):
    id: str
    name: str
    isDefault: bool = False  # Default columns cannot be deleted, only renamed


class WorkflowStepRow(BaseModel):
    id: str
    values: Dict[str, str] = {}  # column_id -> value


class WorkflowSteps(BaseModel):
    columns: List[WorkflowStepColumn] = []
    rows: List[WorkflowStepRow] = []


class StepContainer(BaseModel):
    id: str
    name: str
    order: int


class PhaseType(BaseModel):
    id: str
    name: str
    color: str
    order: int


class WorkflowDefinition(BaseModel):
    id: str
    name: str
    order: int
    useGlobalSteps: bool = True
    steps: Optional[WorkflowSteps] = None
    createdAt: str = ""
    # Legacy fields (for backwards compatibility)
    includeGlobalSteps: Optional[bool] = None
    additionalSteps: Optional[WorkflowSteps] = None


class WorkflowSettingsModel(BaseModel):
    workflows: List[WorkflowDefinition] = []
    phaseTypes: List[PhaseType] = []
    globalStepsLabel: str = "발생현상"


# Core Step Models
class CoreStepPreset(BaseModel):
    id: str
    name: str
    allowedTypes: List[str] = []  # 'capture', 'text', 'image_clipboard'
    order: int


class CoreStepDefinition(BaseModel):
    id: str
    name: str
    presets: List[CoreStepPreset] = []
    createdAt: str = ""


class CoreStepsSettings(BaseModel):
    definitions: List[CoreStepDefinition] = []


class Settings(BaseModel):
    llm: LLMConfig
    summary_fields: List[SummaryField]
    use_thumbnails: bool = False
    phenomenon_attributes: Optional[List[str]] = None
    workflow_steps: Optional[WorkflowSteps] = None
    step_containers: Optional[List[StepContainer]] = None
    phase_types: Optional[List[PhaseType]] = None
    workflow_settings: Optional[WorkflowSettingsModel] = None
    core_steps: Optional[CoreStepsSettings] = None


class WorkflowData(BaseModel):
    rootId: str
    nodes: Dict[str, Any]
    meta: Dict[str, Any] = {}


class WorkflowUpdateRequest(BaseModel):
    workflow: Optional[Dict[str, Any]] = None
    workflow_id: Optional[str] = None  # If provided, updates specific workflow


class SummaryData(BaseModel):
    data: Dict[str, str]


class GenerateSummaryRequest(BaseModel):
    slide_indices: List[int]


@app.middleware("http")
async def log_requests(request, call_next):
    print(f"Request: {request.method} {request.url.path}")
    response = await call_next(request)
    return response


@app.get("/api/projects", response_model=List[ProjectSummary])
def list_projects():
    projects = db.list_projects()
    # Convert DB rows to ProjectSummary objects
    summary_list = []
    for p in projects:
        p_dict = dict(p)
        p_dict["name"] = p_dict.get("original_filename", "Unknown")
        summary_list.append(ProjectSummary(**p_dict))
    return summary_list


@app.get("/api/filters")
def get_filters():
    """Get available filters and their options."""
    active_attrs = attr_manager.get_active_attributes()
    filters = []
    for attr in active_attrs:
        key = attr["key"]
        attr_type = attr.get("attr_type", {})
        variant = attr_type.get("variant")
        filter_entry = {
            "key": key,
            "display_name": attr["display_name"],
            "attr_type": attr_type,
        }

        if attr_type.get("category") == "filtering" and variant == "multi_select":
            filter_entry["options"] = db.get_distinct_values(key)
        elif attr_type.get("category") == "filtering" and variant == "range":
            bounds = db.get_numeric_range(key)
            if bounds:
                filter_entry["range"] = bounds
        elif attr_type.get("category") == "filtering" and variant == "toggle":
            filter_entry["options"] = [True, False]

        filters.append(filter_entry)
    return filters


def get_metadata_with_com(file_path):
    """Wrapper to run metadata extraction in a separate thread with COM init."""
    pythoncom.CoInitialize()
    try:
        return parsing.get_presentation_metadata(file_path)
    finally:
        pythoncom.CoUninitialize()


@app.post("/api/upload")
async def upload_ppt(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    filename = file.filename

    # Save to uploads with ORIGINAL filename
    # WARNING: This overwrites existing files with the same name!
    upload_filename = filename
    file_path = os.path.join(UPLOAD_DIR, upload_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Extract metadata for deterministic UID
    # Run in thread pool to avoid blocking event loop
    loop = asyncio.get_event_loop()
    metadata = await loop.run_in_executor(None, get_metadata_with_com, file_path)

    if metadata is None:
        print(f"[WARN] Could not extract metadata for {filename}. Using random UUID.")
        project_id = str(uuid.uuid4())
        # Default values
        slide_count = 0
        title = ""
        subject = ""
        author = ""
        last_modified_by = ""
        revision_number = ""
    else:
        title = metadata.get("title", "")
        slide_count = metadata.get("slide_count", 0)
        subject = metadata.get("subject", "")
        author = metadata.get("author", "")
        last_modified_by = metadata.get("last_modified_by", "")
        revision_number = metadata.get("revision_number", "")

        # Generate deterministic UID
        # Seed: filename|title|slide_count
        seed = f"{filename}|{title}|{slide_count}"

        APP_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "pipiitiii.local")
        project_id = str(uuid.uuid5(APP_NAMESPACE, seed))

        print(f"[INFO] Generated UID {project_id} for {filename}")

    # Check if project already exists
    existing_project = db.get_project(project_id)
    if existing_project:
        print(f"[INFO] Project {project_id} already exists. Returning existing status.")
        status = existing_project.get("status", "unknown")
        return {
            "id": project_id,
            "message": "Project already exists (duplicate detected)",
            "status": status,
            "is_duplicate": True,
        }

    # Create result directory
    project_dir = os.path.join(RESULT_DIR, project_id)
    os.makedirs(project_dir, exist_ok=True)

    # Initialize progress
    progress_store[project_id] = {
        "percent": 0,
        "message": "Uploaded",
        "status": "processing",
    }

    # Add to DB with FULL metadata
    db.add_project(
        {
            "id": project_id,
            "original_filename": filename,
            "created_at": datetime.now().isoformat(),
            "status": "processing",
            "slide_count": slide_count,
            "title": title,
            "subject": subject,
            "author": author,
            "last_modified_by": last_modified_by,
            "revision_number": revision_number,
        }
    )

    # Calculate and save dynamic attributes
    try:
        project_data = {
            "original_filename": filename,
            "title": title,
            "slide_count": slide_count,
            "subject": subject,
            "author": author,
            "last_modified_by": last_modified_by,
            "revision_number": revision_number,
        }
        attributes = attr_manager.calculate_attributes(project_data)
        db.update_project_attributes(project_id, attributes)
    except Exception as e:
        print(f"[ERROR] Failed to calculate attributes for {project_id}: {e}")

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

    # Use shape_utils to update shape description
    found = update_shape_property(
        target_slide.get("shapes", []),
        str(update.shape_index),
        {"description": update.description},
    )

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
    # Use file resolver to find PPT file
    ppt_path = file_resolver.resolve_ppt_path(ppt_path, project_id)

    try:
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
    # Use file resolver to find PPT file
    ppt_path = file_resolver.resolve_ppt_path(ppt_path, project_id)

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


def get_default_workflow_steps() -> dict:
    """Return default workflow steps structure."""
    return {
        "columns": [
            {"id": "step_category", "name": "스텝 구분", "isDefault": True},
            {"id": "system", "name": "System", "isDefault": True},
            {"id": "access_target", "name": "접근 Target", "isDefault": True},
            {"id": "purpose", "name": "목적", "isDefault": True},
            {"id": "related_db_table", "name": "연관 DB Table", "isDefault": True},
        ],
        "rows": [],
    }


def load_settings() -> dict:
    """Load settings from file or return defaults."""
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            settings = json.load(f)
            # Ensure workflow_steps exists (migration for existing settings)
            if "workflow_steps" not in settings:
                settings["workflow_steps"] = get_default_workflow_steps()
            # Ensure step_containers exists (migration for existing settings)
            if "step_containers" not in settings:
                settings["step_containers"] = []
            # Ensure phase_types exists (migration for existing settings)
            if "phase_types" not in settings:
                settings["phase_types"] = []
            # Ensure core_steps exists (migration for existing settings)
            if "core_steps" not in settings:
                settings["core_steps"] = {"definitions": []}
            # Ensure phenomenon_attributes exists (migration for existing settings)
            if "phenomenon_attributes" not in settings:
                settings["phenomenon_attributes"] = []
            return settings
    else:
        return {
            "llm": {
                "api_type": "openai",
                "api_endpoint": "https://api.openai.com/v1",
                "model_name": "gpt-4o",
            },
            "summary_fields": [],
            "use_thumbnails": True,
            "phenomenon_attributes": [],
            "workflow_steps": get_default_workflow_steps(),
            "step_containers": [],
            "phase_types": [],
            "core_steps": {"definitions": []},
        }


@app.get("/api/settings")
def get_settings():
    """Get application settings."""
    try:
        return load_settings()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to load settings: {str(e)}"
        )


@app.post("/api/settings")
def update_settings(settings: Settings):
    """Update application settings."""
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings.dict(), f, ensure_ascii=False, indent=2)
        return {"status": "success", "message": "Settings updated successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to save settings: {str(e)}"
        )


@app.get("/api/attributes")
def get_all_attributes():
    """Get all available attribute definitions."""
    return attr_manager.get_active_attributes()


# ========== Workflow API ==========


@app.get("/api/project/{project_id}/workflow")
def get_project_workflow(project_id: str, workflow_id: str = None):
    """Get workflow data for a project.

    Args:
        project_id: The project ID
        workflow_id: Optional query param. If provided, returns only that workflow's data.
                    If not provided, returns all workflows data.
    """
    try:
        data = db.get_project_workflow(project_id, workflow_id)
        if workflow_id is not None:
            # Return specific workflow data
            return {"workflow": data}
        else:
            # Return all workflows data
            return data
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to load workflow: {str(e)}"
        )


@app.post("/api/project/{project_id}/workflow")
def update_project_workflow(project_id: str, request: WorkflowUpdateRequest):
    """Update workflow data for a project.

    If workflow_id is provided in the request, updates only that workflow.
    Otherwise, replaces all workflow data.
    """
    try:
        db.update_project_workflow(project_id, request.workflow, request.workflow_id)
        return {"status": "success", "message": "Workflow updated successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to save workflow: {str(e)}"
        )


@app.get("/api/workflow/validate")
def validate_all_workflows():
    """
    Validate all project workflows against current settings.
    Returns list of projects with invalid workflow steps.
    Supports multi-workflow format: each workflow can use global or its own step definitions.
    """
    try:
        settings = load_settings()
        global_steps = settings.get("workflow_steps", {})
        global_step_ids = {row["id"] for row in global_steps.get("rows", [])}

        # Get workflow definitions to check which steps each workflow uses
        workflow_settings = settings.get("workflow_settings", {})
        workflow_defs = {wf["id"]: wf for wf in workflow_settings.get("workflows", [])}

        # Check all workflows
        all_projects = db.get_all_workflows()
        invalid_projects = []

        for project in all_projects:
            project_workflows = project.get("workflows", {})
            if not project_workflows:
                continue

            project_issues = []

            for workflow_id, workflow_data in project_workflows.items():
                if not workflow_data:
                    continue

                # Determine valid step IDs for this workflow
                workflow_def = workflow_defs.get(workflow_id)
                if workflow_def and not workflow_def.get("useGlobalSteps", True):
                    # Use workflow's own steps
                    wf_steps = workflow_def.get("steps", {})
                    valid_step_ids = {row["id"] for row in wf_steps.get("rows", [])}
                else:
                    # Use global steps
                    valid_step_ids = global_step_ids

                # Validate workflow steps
                steps = workflow_data.get("steps", [])
                for step in steps:
                    step_id = step.get("stepId")
                    if step_id and step_id not in valid_step_ids:
                        project_issues.append({
                            "type": "invalid_step",
                            "workflow_id": workflow_id,
                            "step_id": step_id,
                        })

            if project_issues:
                invalid_projects.append({
                    "project_id": project["id"],
                    "issues": project_issues
                })

        return {"invalid_projects": invalid_projects}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to validate workflows: {str(e)}"
        )


@app.get("/api/project/{project_id}/summary")
def get_project_summary(project_id: str):
    """Get summary data for a project."""
    try:
        summary = db.get_project_summary(project_id)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load summary: {str(e)}")


@app.post("/api/project/{project_id}/summary")
def update_project_summary_endpoint(project_id: str, summary: SummaryData):
    """Update user summary data for a project."""
    try:
        db.update_project_summary(project_id, summary.data)
        return {"status": "success", "message": "Summary updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save summary: {str(e)}")


class LLMSummaryUpdate(BaseModel):
    field_id: str
    content: str


@app.post("/api/project/{project_id}/summary_llm")
def update_project_summary_llm_endpoint(project_id: str, update: LLMSummaryUpdate):
    """Update LLM-generated summary for a specific field."""
    try:
        db.update_project_summary_llm(project_id, update.field_id, update.content)
        return {"status": "success", "message": "LLM summary updated successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to save LLM summary: {str(e)}"
        )


@app.post("/api/project/{project_id}/generate_summary/{field_id}")
async def generate_summary(
    project_id: str, field_id: str, request: GenerateSummaryRequest
):
    """
    Generate summary using LLM with slide thumbnails.
    Returns streaming response.
    """
    # Load settings
    settings = load_settings()

    # Find the field by ID
    field = None
    for f in settings.get("summary_fields", []):
        if f.get("id") == field_id:
            field = f
            break

    if not field:
        raise HTTPException(
            status_code=404, detail=f"Summary field '{field_id}' not found"
        )

    # Verify project exists
    project_dir = os.path.join(RESULT_DIR, project_id)
    if not os.path.exists(project_dir):
        raise HTTPException(status_code=404, detail="Project not found")

    # Build thumbnail paths (max 3)
    slide_indices = request.slide_indices[:3]
    thumbnail_paths = []
    for idx in slide_indices:
        thumb_path = os.path.join(
            project_dir, "thumbnails", f"slide_{idx:03d}_thumb.png"
        )
        if os.path.exists(thumb_path):
            thumbnail_paths.append(thumb_path)

    if not thumbnail_paths:
        raise HTTPException(
            status_code=404, detail="No thumbnails found for specified slides"
        )

    # Get prompts with defaults
    system_prompt = field.get("system_prompt", "")
    user_prompt = field.get("user_prompt", "")

    if not system_prompt:
        system_prompt = "당신은 PPT 프레젠테이션을 분석하는 전문가입니다."
    if not user_prompt:
        user_prompt = "이 슬라이드들의 내용을 요약해주세요."

    # Create LLM service
    llm_config = settings.get("llm", {})
    llm_service = LLMService(llm_config)

    # Return streaming response
    async def stream_generator():
        async for chunk in llm_service.generate_stream(
            system_prompt, user_prompt, thumbnail_paths
        ):
            yield chunk

    return StreamingResponse(
        stream_generator(),
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/project/{project_id}/download")
def download_project(project_id: str):
    project_dir = os.path.join(RESULT_DIR, project_id)
    json_path = os.path.join(project_dir, f"{project_id}.json")

    if not os.path.exists(json_path):
        raise HTTPException(status_code=404, detail="Project not found")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Reconstruct PPT
    # We'll save it to a temporary file or directly to the result dir with a specific name
    output_filename = (
        f"reconstructed_{data.get('original_filename', 'presentation.pptx')}"
    )
    output_path = os.path.join(project_dir, output_filename)

    # Ensure we have the image directory if needed (usually uploads or recon)
    # The reconstructor might need absolute paths for images.
    # If images are local, we might need to handle that.
    # For now, let's assume images are accessible via absolute paths in JSON or relative to project root?
    # In ppt_reconstructor.py, it takes image_dir.
    # Let's pass UPLOAD_DIR as image_dir fallback?

    # Run reconstruction in a separate thread because it uses COM
    # We need a wrapper for COM initialization
    def reconstruct_task():
        pythoncom.CoInitialize()
        try:
            import ppt_reconstructor

            return ppt_reconstructor.reconstruct_presentation(
                data, output_path, image_dir=UPLOAD_DIR
            )
        finally:
            pythoncom.CoUninitialize()

    success = reconstruct_task()

    if not success:
        raise HTTPException(
            status_code=500, detail="Failed to reconstruct presentation"
        )

    return FileResponse(
        output_path,
        filename=output_filename,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )


@app.get("/api/settings/prompt_version")
def get_prompt_version():
    """Get the current prompt version hash."""
    settings = load_settings()
    version = calculate_prompt_version(settings)
    return {"version": version}


@app.post("/api/project/{project_id}/update_prompt_version")
def update_project_prompt_version_endpoint(project_id: str):
    """Update the prompt version for a project to the current version."""
    settings = load_settings()
    current_version = calculate_prompt_version(settings)
    db.update_project_summary_prompt_version(project_id, current_version)
    return {"status": "success", "version": current_version}


@app.get("/api/projects/summary_status")
def get_projects_summary_status():
    """Get summary status for all projects including version info."""
    settings = load_settings()
    current_version = calculate_prompt_version(settings)
    statuses = db.get_projects_summary_status()

    # Add outdated flag based on version comparison
    for status in statuses:
        if status["has_summary"] and status["prompt_version"]:
            status["is_outdated"] = status["prompt_version"] != current_version
        else:
            status["is_outdated"] = False

    return {"current_version": current_version, "projects": statuses}


class BatchGenerateSummaryRequest(BaseModel):
    project_ids: List[str]
    slide_indices: Optional[List[int]] = None  # If None, use first 3 slides


@app.post("/api/projects/batch_generate_summary")
async def batch_generate_summary(request: BatchGenerateSummaryRequest):
    """
    Generate summaries for multiple projects.
    Returns streaming response with progress updates.
    Processes projects sequentially, but summary fields in parallel for each project.
    """
    settings = load_settings()
    current_version = calculate_prompt_version(settings)

    async def stream_generator():
        total = len(request.project_ids)
        for idx, project_id in enumerate(request.project_ids):
            try:
                # Send progress update
                yield f"data: {json.dumps({'type': 'progress', 'project_id': project_id, 'current': idx + 1, 'total': total, 'status': 'generating'})}\n\n"

                project_dir = os.path.join(RESULT_DIR, project_id)
                if not os.path.exists(project_dir):
                    yield f"data: {json.dumps({'type': 'error', 'project_id': project_id, 'message': 'Project not found'})}\n\n"
                    continue

                # Get project data to determine slide indices
                json_path = os.path.join(project_dir, f"{project_id}.json")
                if not os.path.exists(json_path):
                    yield f"data: {json.dumps({'type': 'error', 'project_id': project_id, 'message': 'Project data not found'})}\n\n"
                    continue

                with open(json_path, "r", encoding="utf-8") as f:
                    project_data = json.load(f)

                # Use provided slide indices or first 3 slides
                if request.slide_indices:
                    slide_indices = request.slide_indices[:3]
                else:
                    slides = project_data.get("slides", [])
                    slide_indices = [s.get("slide_index") for s in slides[:3]]

                # Build thumbnail paths
                thumbnail_paths = []
                for si in slide_indices:
                    thumb_path = os.path.join(
                        project_dir, "thumbnails", f"slide_{si:03d}_thumb.png"
                    )
                    if os.path.exists(thumb_path):
                        thumbnail_paths.append(thumb_path)

                if not thumbnail_paths:
                    yield f"data: {json.dumps({'type': 'error', 'project_id': project_id, 'message': 'No thumbnails found'})}\n\n"
                    continue

                # Generate summary for each field IN PARALLEL
                llm_config = settings.get("llm", {})
                llm_service = LLMService(llm_config)

                async def generate_field_summary(field):
                    """Generate summary for a single field"""
                    field_id = field.get("id")
                    system_prompt = field.get(
                        "system_prompt",
                        "당신은 PPT 프레젠테이션을 분석하는 전문가입니다.",
                    )
                    user_prompt = field.get(
                        "user_prompt", "이 슬라이드들의 내용을 요약해주세요."
                    )

                    content = ""
                    async for chunk in llm_service.generate_stream(
                        system_prompt, user_prompt, thumbnail_paths
                    ):
                        content += chunk

                    return (field_id, content)

                # Run all field generations in parallel
                summary_fields = settings.get("summary_fields", [])
                tasks = [generate_field_summary(field) for field in summary_fields]
                results = await asyncio.gather(*tasks)

                # Save results to database
                summary_data = {}
                for field_id, content in results:
                    summary_data[field_id] = content
                    db.update_project_summary_llm(project_id, field_id, content)

                # Save user version same as LLM version
                db.update_project_summary(project_id, summary_data)
                # Update prompt version
                db.update_project_summary_prompt_version(project_id, current_version)

                yield f"data: {json.dumps({'type': 'complete', 'project_id': project_id})}\n\n"

            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'project_id': project_id, 'message': str(e)})}\n\n"

        yield f"data: {json.dumps({'type': 'done', 'total': total})}\n\n"

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ========== Attachments API ==========


class AttachmentImageUpload(BaseModel):
    image_id: str
    project_id: str
    data: str  # Base64 encoded image data


@app.post("/api/attachments/image")
def upload_attachment_image(request: AttachmentImageUpload):
    """Upload an attachment image to the separate BLOB database."""
    try:
        success = attachments_db.save_image(
            request.image_id,
            request.project_id,
            request.data
        )
        if success:
            return {"status": "success", "image_id": request.image_id}
        else:
            raise HTTPException(status_code=500, detail="Failed to save image")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")


@app.get("/api/attachments/image/{image_id}")
def get_attachment_image(image_id: str):
    """Retrieve an attachment image from the BLOB database."""
    try:
        image_data = attachments_db.get_image(image_id)
        if image_data is None:
            raise HTTPException(status_code=404, detail="Image not found")

        # Detect image type from magic bytes
        content_type = "image/png"  # Default
        if image_data[:3] == b'\xff\xd8\xff':
            content_type = "image/jpeg"
        elif image_data[:4] == b'\x89PNG':
            content_type = "image/png"
        elif image_data[:6] in (b'GIF87a', b'GIF89a'):
            content_type = "image/gif"
        elif image_data[:4] == b'RIFF' and image_data[8:12] == b'WEBP':
            content_type = "image/webp"

        from fastapi.responses import Response
        return Response(content=image_data, media_type=content_type)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve image: {str(e)}")


@app.delete("/api/attachments/image/{image_id}")
def delete_attachment_image(image_id: str):
    """Delete an attachment image from the BLOB database."""
    try:
        deleted = attachments_db.delete_image(image_id)
        if deleted:
            return {"status": "success", "message": "Image deleted"}
        else:
            raise HTTPException(status_code=404, detail="Image not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete image: {str(e)}")


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
