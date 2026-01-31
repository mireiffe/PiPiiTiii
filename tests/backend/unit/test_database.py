"""
Tests for backend/database.py

Tests Database class methods with in-memory SQLite.
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "backend"))

from database import Database


class TestDatabaseInit:
    """Tests for database initialization."""

    def test_init_creates_projects_table(self, temp_db: Database):
        """Should create projects table on initialization."""
        conn = temp_db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='projects'"
        )
        result = cursor.fetchone()
        conn.close()
        assert result is not None
        assert result[0] == "projects"

    def test_init_creates_all_columns(self, temp_db: Database):
        """Should create all required columns in projects table."""
        conn = temp_db.get_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(projects)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()

        required_columns = {
            "id",
            "original_filename",
            "created_at",
            "status",
            "slide_count",
            "title",
            "subject",
            "author",
            "last_modified_by",
            "revision_number",
            "summary_data",
            "summary_data_llm",
            "summary_prompt_version",
            "workflow_data",
        }
        assert required_columns.issubset(columns)


class TestAddProject:
    """Tests for add_project method."""

    def test_adds_new_project(self, temp_db: Database, sample_project_data):
        """Should add a new project to the database."""
        temp_db.add_project(sample_project_data)

        result = temp_db.get_project(sample_project_data["id"])
        assert result is not None
        assert result["id"] == sample_project_data["id"]
        assert result["original_filename"] == sample_project_data["original_filename"]

    def test_replaces_existing_project(self, temp_db: Database, sample_project_data):
        """Should replace existing project with same ID."""
        temp_db.add_project(sample_project_data)

        # Update and re-add
        sample_project_data["title"] = "Updated Title"
        temp_db.add_project(sample_project_data)

        result = temp_db.get_project(sample_project_data["id"])
        assert result["title"] == "Updated Title"

    def test_handles_optional_fields(self, temp_db: Database):
        """Should handle missing optional fields with defaults."""
        minimal_data = {
            "id": "minimal_project",
            "original_filename": "test.pptx",
            "created_at": datetime.now().isoformat(),
            "status": "processing",
        }
        temp_db.add_project(minimal_data)

        result = temp_db.get_project("minimal_project")
        assert result is not None
        assert result["slide_count"] == 0
        assert result["author"] == "Unknown"


class TestGetProject:
    """Tests for get_project method."""

    def test_returns_project_dict(self, db_with_project: Database, sample_project_data):
        """Should return project as dictionary."""
        result = db_with_project.get_project(sample_project_data["id"])
        assert isinstance(result, dict)
        assert result["id"] == sample_project_data["id"]

    def test_returns_none_for_missing_project(self, temp_db: Database):
        """Should return None when project not found."""
        result = temp_db.get_project("nonexistent_id")
        assert result is None


class TestListProjects:
    """Tests for list_projects method."""

    def test_returns_empty_list_when_no_projects(self, temp_db: Database):
        """Should return empty list when database is empty."""
        result = temp_db.list_projects()
        assert result == []

    def test_returns_all_projects(self, temp_db: Database):
        """Should return all projects."""
        for i in range(3):
            temp_db.add_project({
                "id": f"project_{i}",
                "original_filename": f"file_{i}.pptx",
                "created_at": datetime.now().isoformat(),
                "status": "done",
            })

        result = temp_db.list_projects()
        assert len(result) == 3

    def test_ordered_by_created_at_desc(self, temp_db: Database):
        """Should return projects ordered by created_at descending."""
        temp_db.add_project({
            "id": "old",
            "original_filename": "old.pptx",
            "created_at": "2024-01-01T00:00:00",
            "status": "done",
        })
        temp_db.add_project({
            "id": "new",
            "original_filename": "new.pptx",
            "created_at": "2024-12-31T00:00:00",
            "status": "done",
        })

        result = temp_db.list_projects()
        assert result[0]["id"] == "new"
        assert result[1]["id"] == "old"


class TestUpdateProjectStatus:
    """Tests for update_project_status method."""

    def test_updates_status(self, db_with_project: Database, sample_project_data):
        """Should update project status."""
        db_with_project.update_project_status(sample_project_data["id"], "processing")

        result = db_with_project.get_project(sample_project_data["id"])
        assert result["status"] == "processing"


class TestProjectSummary:
    """Tests for summary-related methods."""

    def test_get_project_summary_empty(self, db_with_project: Database, sample_project_data):
        """Should return empty user and llm dicts for new project."""
        result = db_with_project.get_project_summary(sample_project_data["id"])
        assert result["user"] == {}
        assert result["llm"] == {}

    def test_update_project_summary(self, db_with_project: Database, sample_project_data):
        """Should update user summary data."""
        summary = {"field1": "value1", "field2": "value2"}
        db_with_project.update_project_summary(sample_project_data["id"], summary)

        result = db_with_project.get_project_summary(sample_project_data["id"])
        assert result["user"] == summary

    def test_update_project_summary_llm(self, db_with_project: Database, sample_project_data):
        """Should update LLM summary for specific field."""
        db_with_project.update_project_summary_llm(
            sample_project_data["id"], "analysis", "LLM generated content"
        )

        result = db_with_project.get_project_summary(sample_project_data["id"])
        assert result["llm"]["analysis"] == "LLM generated content"

    def test_update_project_summary_llm_merges(
        self, db_with_project: Database, sample_project_data
    ):
        """Should merge new LLM field with existing data."""
        db_with_project.update_project_summary_llm(
            sample_project_data["id"], "field1", "content1"
        )
        db_with_project.update_project_summary_llm(
            sample_project_data["id"], "field2", "content2"
        )

        result = db_with_project.get_project_summary(sample_project_data["id"])
        assert result["llm"]["field1"] == "content1"
        assert result["llm"]["field2"] == "content2"


class TestProjectWorkflow:
    """Tests for workflow-related methods."""

    def test_get_project_workflow_returns_empty_workflows_dict(
        self, db_with_project: Database, sample_project_data
    ):
        """Should return dict with empty workflows when no workflow_data."""
        result = db_with_project.get_project_workflow(sample_project_data["id"])
        assert result == {"workflows": {}}

    def test_get_project_workflow_specific_id_returns_none(
        self, db_with_project: Database, sample_project_data
    ):
        """Should return None when requesting specific workflow that doesn't exist."""
        result = db_with_project.get_project_workflow(
            sample_project_data["id"], workflow_id="nonexistent"
        )
        assert result is None

    def test_update_and_get_project_workflow_with_id(
        self, db_with_project: Database, sample_project_data, sample_workflow_data
    ):
        """Should update and retrieve specific workflow by ID."""
        db_with_project.update_project_workflow(
            sample_project_data["id"],
            sample_workflow_data,
            workflow_id="workflow_1"
        )

        result = db_with_project.get_project_workflow(
            sample_project_data["id"], workflow_id="workflow_1"
        )
        assert result is not None
        assert "steps" in result

    def test_update_project_workflow_all_workflows(
        self, db_with_project: Database, sample_project_data, sample_workflow_data
    ):
        """Should update all workflows data."""
        all_workflows = {
            "workflows": {
                "workflow_1": sample_workflow_data,
                "workflow_2": {"steps": [], "createdAt": "2024-01-01"},
            }
        }
        db_with_project.update_project_workflow(
            sample_project_data["id"], all_workflows
        )

        result = db_with_project.get_project_workflow(sample_project_data["id"])
        assert result is not None
        assert "workflow_1" in result["workflows"]
        assert "workflow_2" in result["workflows"]

    def test_get_all_workflows(self, temp_db: Database):
        """Should return workflows for all projects."""
        # Add two projects with workflows
        temp_db.add_project({
            "id": "project_1",
            "original_filename": "test1.pptx",
            "created_at": "2024-01-01",
            "status": "done",
        })
        temp_db.add_project({
            "id": "project_2",
            "original_filename": "test2.pptx",
            "created_at": "2024-01-01",
            "status": "done",
        })

        temp_db.update_project_workflow(
            "project_1", {"steps": []}, workflow_id="wf_1"
        )
        temp_db.update_project_workflow(
            "project_2", {"steps": []}, workflow_id="wf_2"
        )

        result = temp_db.get_all_workflows()
        assert len(result) == 2
        assert all("id" in r and "workflows" in r for r in result)


class TestAttributes:
    """Tests for attribute-related methods."""

    def test_sync_active_attributes_inserts_new(self, temp_db: Database):
        """Should insert new attributes."""
        attrs = [
            {"key": "attr1", "display_name": "Attribute 1", "attr_type": {"type": "text"}},
            {"key": "attr2", "display_name": "Attribute 2", "attr_type": {"type": "number"}},
        ]
        temp_db.sync_active_attributes(attrs)

        result = temp_db.get_active_attributes()
        assert "attr1" in result
        assert "attr2" in result

    def test_sync_active_attributes_removes_old(self, temp_db: Database):
        """Should remove attributes not in new list."""
        temp_db.sync_active_attributes([
            {"key": "old_attr", "display_name": "Old", "attr_type": {}},
        ])
        temp_db.sync_active_attributes([
            {"key": "new_attr", "display_name": "New", "attr_type": {}},
        ])

        result = temp_db.get_active_attributes()
        assert "new_attr" in result
        assert "old_attr" not in result

    def test_get_distinct_values(self, temp_db: Database):
        """Should return distinct values for column."""
        # Add projects with different statuses
        for i, status in enumerate(["done", "processing", "done", "error"]):
            temp_db.add_project({
                "id": f"project_{i}",
                "original_filename": "test.pptx",
                "created_at": datetime.now().isoformat(),
                "status": status,
            })

        result = temp_db.get_distinct_values("status")
        assert set(result) == {"done", "processing", "error"}

    def test_get_numeric_range(self, temp_db: Database):
        """Should return min/max for numeric column."""
        for i, count in enumerate([5, 10, 15, 20]):
            temp_db.add_project({
                "id": f"project_{i}",
                "original_filename": "test.pptx",
                "created_at": datetime.now().isoformat(),
                "status": "done",
                "slide_count": count,
            })

        result = temp_db.get_numeric_range("slide_count")
        assert result is not None
        assert result["min"] == 5.0
        assert result["max"] == 20.0


class TestProjectsSummaryStatus:
    """Tests for get_projects_summary_status method."""

    def test_returns_status_for_all_projects(self, temp_db: Database):
        """Should return summary status for all projects."""
        # Add project without summary
        temp_db.add_project({
            "id": "no_summary",
            "original_filename": "test.pptx",
            "created_at": datetime.now().isoformat(),
            "status": "done",
        })

        # Add project with summary
        temp_db.add_project({
            "id": "with_summary",
            "original_filename": "test.pptx",
            "created_at": datetime.now().isoformat(),
            "status": "done",
        })
        temp_db.update_project_summary_llm("with_summary", "field1", "content")

        result = temp_db.get_projects_summary_status()
        assert len(result) == 2

        no_summary = next(r for r in result if r["id"] == "no_summary")
        with_summary = next(r for r in result if r["id"] == "with_summary")

        assert no_summary["has_summary"] is False
        assert with_summary["has_summary"] is True


class TestProjectKeyInfo:
    """Tests for key info (핵심정보) related methods."""

    def test_get_project_key_info_returns_empty_instances(
        self, db_with_project: Database, sample_project_data
    ):
        """Should return dict with empty instances array when no key_info_data."""
        result = db_with_project.get_project_key_info(sample_project_data["id"])
        assert result == {"instances": []}

    def test_update_and_get_project_key_info(
        self, db_with_project: Database, sample_project_data, sample_key_info_data
    ):
        """Should save and retrieve key info data correctly."""
        db_with_project.update_project_key_info(
            sample_project_data["id"], sample_key_info_data
        )

        result = db_with_project.get_project_key_info(sample_project_data["id"])
        assert result is not None
        assert "instances" in result
        assert len(result["instances"]) == 2

    def test_key_info_instance_fields_preserved(
        self, db_with_project: Database, sample_project_data, sample_key_info_data
    ):
        """Should preserve all instance fields after save/load."""
        db_with_project.update_project_key_info(
            sample_project_data["id"], sample_key_info_data
        )

        result = db_with_project.get_project_key_info(sample_project_data["id"])
        instance = result["instances"][0]

        assert instance["id"] == "kiin_001"
        assert instance["categoryId"] == "kic_001"
        assert instance["itemId"] == "kii_001"
        assert instance["textValue"] == "Test text value"
        assert instance["order"] == 0

    def test_key_info_capture_value_preserved(
        self, db_with_project: Database, sample_project_data, sample_key_info_data
    ):
        """Should preserve captureValue with all its fields."""
        db_with_project.update_project_key_info(
            sample_project_data["id"], sample_key_info_data
        )

        result = db_with_project.get_project_key_info(sample_project_data["id"])
        instance_with_capture = result["instances"][1]
        capture = instance_with_capture["captureValue"]

        assert capture is not None
        assert capture["id"] == "kicap_001"
        assert capture["slideIndex"] == 0
        assert capture["x"] == 100
        assert capture["y"] == 50
        assert capture["width"] == 200
        assert capture["height"] == 100

    def test_key_info_add_instance_updates_correctly(
        self, db_with_project: Database, sample_project_data, sample_key_info_data
    ):
        """Should correctly update when adding new instances."""
        # Save initial data
        db_with_project.update_project_key_info(
            sample_project_data["id"], sample_key_info_data
        )

        # Add new instance
        updated_data = sample_key_info_data.copy()
        updated_data["instances"] = sample_key_info_data["instances"] + [
            {
                "id": "kiin_003",
                "categoryId": "kic_002",
                "itemId": "kii_003",
                "textValue": "New instance",
                "captureValue": None,
                "imageId": None,
                "imageCaption": None,
                "order": 2,
                "createdAt": "2024-01-01T00:00:00",
                "updatedAt": None,
            }
        ]
        db_with_project.update_project_key_info(
            sample_project_data["id"], updated_data
        )

        result = db_with_project.get_project_key_info(sample_project_data["id"])
        assert len(result["instances"]) == 3
        assert result["instances"][2]["id"] == "kiin_003"
        assert result["instances"][2]["textValue"] == "New instance"

    def test_key_info_remove_instance_updates_correctly(
        self, db_with_project: Database, sample_project_data, sample_key_info_data
    ):
        """Should correctly update when removing instances."""
        # Save initial data with 2 instances
        db_with_project.update_project_key_info(
            sample_project_data["id"], sample_key_info_data
        )

        # Remove one instance
        updated_data = sample_key_info_data.copy()
        updated_data["instances"] = [sample_key_info_data["instances"][0]]
        db_with_project.update_project_key_info(
            sample_project_data["id"], updated_data
        )

        result = db_with_project.get_project_key_info(sample_project_data["id"])
        assert len(result["instances"]) == 1
        assert result["instances"][0]["id"] == "kiin_001"

    def test_get_project_key_info_nonexistent_project(self, temp_db: Database):
        """Should return empty instances for nonexistent project."""
        result = temp_db.get_project_key_info("nonexistent_id")
        assert result == {"instances": []}

    def test_key_info_handles_invalid_json(
        self, db_with_project: Database, sample_project_data
    ):
        """Should return empty instances when key_info_data is invalid JSON."""
        # Manually insert invalid JSON
        conn = db_with_project.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE projects SET key_info_data = ? WHERE id = ?",
            ("invalid json {{{", sample_project_data["id"]),
        )
        conn.commit()
        conn.close()

        result = db_with_project.get_project_key_info(sample_project_data["id"])
        assert result == {"instances": []}
