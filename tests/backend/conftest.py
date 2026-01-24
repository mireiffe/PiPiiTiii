"""
Pytest fixtures for backend tests.
"""

import os
import sys
import tempfile
from datetime import datetime
from typing import Generator, Dict, Any

import pytest

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from database import Database


@pytest.fixture
def temp_db() -> Generator[Database, None, None]:
    """Create a temporary in-memory database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    db = Database(db_path)
    yield db

    # Cleanup
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture
def sample_project_data() -> Dict[str, Any]:
    """Sample project data for testing."""
    return {
        "id": "test_project_001",
        "original_filename": "test_presentation.pptx",
        "created_at": datetime.now().isoformat(),
        "status": "done",
        "slide_count": 10,
        "title": "Test Presentation",
        "subject": "Testing",
        "author": "Test Author",
        "last_modified_by": "Test User",
        "revision_number": "1",
    }


@pytest.fixture
def sample_workflow_data() -> Dict[str, Any]:
    """Sample workflow data for testing."""
    return {
        "steps": [
            {
                "id": "step_001",
                "stepId": "workflow_step_001",
                "captures": [],
                "attachments": [],
                "order": 0,
                "createdAt": datetime.now().isoformat(),
            }
        ],
        "coreStepInstances": [],
        "unifiedSteps": [],
        "phaseTypes": [],
        "supportRelations": [],
        "createdAt": datetime.now().isoformat(),
    }


@pytest.fixture
def sample_shapes() -> list:
    """Sample shape data for testing shape utilities."""
    return [
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
            "name": "Content",
            "type": "TextBox",
            "left": 100,
            "top": 150,
            "width": 400,
            "height": 200,
            "description": "Main content",
            "children": [
                {
                    "shape_index": 3,
                    "name": "Nested Shape",
                    "type": "Rectangle",
                    "left": 10,
                    "top": 10,
                    "width": 50,
                    "height": 50,
                    "description": "Nested element",
                }
            ],
        },
        {
            "shape_index": "4",  # String ID for testing
            "name": "Image",
            "type": "Picture",
            "left": 500,
            "top": 100,
            "width": 200,
            "height": 150,
        },
    ]


@pytest.fixture
def db_with_project(temp_db: Database, sample_project_data: Dict[str, Any]) -> Database:
    """Database with a sample project already added."""
    temp_db.add_project(sample_project_data)
    return temp_db
