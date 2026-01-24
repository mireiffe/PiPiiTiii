"""
Shared test fixtures and mock data for backend tests.
"""

from datetime import datetime
from typing import Dict, Any, List


def create_sample_project(
    project_id: str = "test_project_001",
    status: str = "done",
    slide_count: int = 10,
    **kwargs
) -> Dict[str, Any]:
    """Create a sample project data dict."""
    return {
        "id": project_id,
        "original_filename": kwargs.get("filename", "test_presentation.pptx"),
        "created_at": kwargs.get("created_at", datetime.now().isoformat()),
        "status": status,
        "slide_count": slide_count,
        "title": kwargs.get("title", "Test Presentation"),
        "subject": kwargs.get("subject", "Testing"),
        "author": kwargs.get("author", "Test Author"),
        "last_modified_by": kwargs.get("last_modified_by", "Test User"),
        "revision_number": kwargs.get("revision_number", "1"),
    }


def create_sample_slide(
    slide_index: int = 0,
    shape_count: int = 3,
    **kwargs
) -> Dict[str, Any]:
    """Create a sample slide data dict."""
    return {
        "index": slide_index,
        "shapes": [create_sample_shape(i) for i in range(shape_count)],
        "thumbnail": f"images/slide_{slide_index}_thumbnail.png",
        "width": kwargs.get("width", 960),
        "height": kwargs.get("height", 540),
    }


def create_sample_shape(
    shape_index: int = 1,
    shape_type: str = "TextBox",
    **kwargs
) -> Dict[str, Any]:
    """Create a sample shape data dict."""
    return {
        "shape_index": shape_index,
        "name": kwargs.get("name", f"Shape_{shape_index}"),
        "type": shape_type,
        "left": kwargs.get("left", 100 + shape_index * 50),
        "top": kwargs.get("top", 100 + shape_index * 30),
        "width": kwargs.get("width", 200),
        "height": kwargs.get("height", 100),
        "text": kwargs.get("text", f"Text content {shape_index}"),
        "description": kwargs.get("description", ""),
    }


def create_sample_workflow_data(**kwargs) -> Dict[str, Any]:
    """Create a sample workflow data dict."""
    return {
        "steps": kwargs.get("steps", []),
        "coreStepInstances": kwargs.get("coreStepInstances", []),
        "unifiedSteps": kwargs.get("unifiedSteps", []),
        "phaseTypes": kwargs.get("phaseTypes", []),
        "supportRelations": kwargs.get("supportRelations", []),
        "keyStepLinks": kwargs.get("keyStepLinks", []),
        "isConfirmed": kwargs.get("isConfirmed", False),
        "createdAt": kwargs.get("createdAt", datetime.now().isoformat()),
        "updatedAt": kwargs.get("updatedAt", datetime.now().isoformat()),
    }


def create_sample_step_instance(
    step_id: str = "step_001",
    order: int = 0,
    **kwargs
) -> Dict[str, Any]:
    """Create a sample workflow step instance."""
    return {
        "id": f"inst_{step_id}",
        "stepId": step_id,
        "captures": kwargs.get("captures", []),
        "attachments": kwargs.get("attachments", []),
        "order": order,
        "createdAt": kwargs.get("createdAt", datetime.now().isoformat()),
    }


def create_sample_core_step_instance(
    core_step_id: str = "cs_001",
    order: int = 0,
    **kwargs
) -> Dict[str, Any]:
    """Create a sample core step instance."""
    return {
        "id": f"csi_{core_step_id}_{order}",
        "coreStepId": core_step_id,
        "presetValues": kwargs.get("presetValues", []),
        "order": order,
        "createdAt": kwargs.get("createdAt", datetime.now().isoformat()),
    }


def create_sample_unified_step(
    step_type: str = "regular",
    order: int = 0,
    **kwargs
) -> Dict[str, Any]:
    """Create a sample unified step item."""
    base = {
        "id": f"us_{step_type}_{order}",
        "type": step_type,
        "order": order,
        "createdAt": kwargs.get("createdAt", datetime.now().isoformat()),
    }

    if step_type == "core":
        base["coreStepId"] = kwargs.get("coreStepId", f"cs_{order}")
        base["presetValues"] = kwargs.get("presetValues", [])
    else:
        base["stepId"] = kwargs.get("stepId", f"step_{order}")
        base["captures"] = kwargs.get("captures", [])
        base["attachments"] = kwargs.get("attachments", [])

    return base


def create_sample_settings(**kwargs) -> Dict[str, Any]:
    """Create sample application settings."""
    return {
        "llm": {
            "enabled": kwargs.get("llm_enabled", True),
            "provider": kwargs.get("llm_provider", "openai"),
            "model": kwargs.get("llm_model", "gpt-4"),
            "system_prompt": kwargs.get("system_prompt", "You are a helpful assistant."),
        },
        "summary_fields": kwargs.get("summary_fields", [
            {"id": "analysis", "name": "Analysis", "prompt": "Analyze this..."},
            {"id": "summary", "name": "Summary", "prompt": "Summarize this..."},
        ]),
        "workflow": {
            "workflows": kwargs.get("workflows", []),
            "phaseTypes": kwargs.get("phaseTypes", []),
        },
        "core_steps": {
            "definitions": kwargs.get("core_step_definitions", []),
        },
    }


# Sample shapes for testing shape utilities
SAMPLE_NESTED_SHAPES: List[Dict[str, Any]] = [
    {
        "shape_index": 1,
        "name": "Title",
        "type": "TextBox",
        "left": 100,
        "top": 50,
        "width": 400,
        "height": 60,
        "description": "Main title",
    },
    {
        "shape_index": 2,
        "name": "Group",
        "type": "Group",
        "left": 100,
        "top": 150,
        "width": 400,
        "height": 200,
        "children": [
            {
                "shape_index": 3,
                "name": "Nested Rectangle",
                "type": "Rectangle",
                "left": 10,
                "top": 10,
                "width": 50,
                "height": 50,
                "description": "Nested shape",
            },
            {
                "shape_index": 4,
                "name": "Nested Text",
                "type": "TextBox",
                "left": 70,
                "top": 10,
                "width": 100,
                "height": 30,
            },
        ],
    },
]


# Sample BGR color values for testing RGB conversion
SAMPLE_BGR_COLORS = {
    "white": (0xFFFFFF, [255, 255, 255]),
    "black": (0x000000, [0, 0, 0]),
    "pure_red": (0x0000FF, [255, 0, 0]),
    "pure_green": (0x00FF00, [0, 255, 0]),
    "pure_blue": (0xFF0000, [0, 0, 255]),
    "gray": (0x808080, [128, 128, 128]),
}
