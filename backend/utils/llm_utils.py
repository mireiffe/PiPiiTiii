"""
LLM Response Processing Utilities

This module provides utilities for extracting and validating JSON from LLM responses,
particularly for workflow generation.
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple


def extract_json_from_response(text: str) -> Optional[str]:
    """
    Extract JSON from LLM response text using multiple strategies.

    Strategy 1: Look for JSON inside markdown code blocks (```json or ```)
    Strategy 2: Extract JSON by brace counting from first '{' to matching '}'

    Args:
        text: Raw LLM response text

    Returns:
        JSON string if found, None otherwise
    """
    try:
        # Strategy 1: Try markdown code blocks
        code_blocks = re.findall(r"```(?:json)?(.*?)```", text, re.DOTALL)
        for block in code_blocks:
            block = block.strip()
            start = block.find("{")

            if start != -1:
                # Try brace counting within the block
                json_str = _extract_json_by_brace_counting(block, start)
                if json_str and _is_valid_json(json_str):
                    return json_str

        # Strategy 2: Global brace counting if no valid JSON in code blocks
        start_index = text.find("{")
        if start_index == -1:
            return None

        return _extract_json_by_brace_counting(text, start_index)

    except Exception as e:
        print(f"JSON Extraction Error: {e}")
        return None


def _extract_json_by_brace_counting(text: str, start_index: int) -> Optional[str]:
    """
    Extract JSON string by counting opening/closing braces.

    Args:
        text: Text containing JSON
        start_index: Index of first '{'

    Returns:
        JSON string if valid structure found, None otherwise
    """
    count = 0
    for i in range(start_index, len(text)):
        if text[i] == "{":
            count += 1
        elif text[i] == "}":
            count -= 1
            if count == 0:
                return text[start_index : i + 1]

    return None


def _is_valid_json(json_str: str) -> bool:
    """
    Check if a string is valid JSON.

    Args:
        json_str: String to validate

    Returns:
        True if valid JSON, False otherwise
    """
    try:
        json.loads(json_str)
        return True
    except:
        return False


def validate_workflow_schema(workflow: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate basic workflow schema structure.

    Args:
        workflow: Workflow data dictionary

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    errors = []

    # Check required top-level fields
    if "rootId" not in workflow:
        errors.append("Missing required field: 'rootId'")

    if "nodes" not in workflow:
        errors.append("Missing required field: 'nodes'")

    # Basic structure validation
    if "nodes" in workflow and not isinstance(workflow["nodes"], dict):
        errors.append("Field 'nodes' must be a dictionary")

    return (len(errors) == 0, errors)


def validate_workflow_actions(
    workflow: Dict[str, Any], available_actions: List[Dict[str, Any]]
) -> List[str]:
    """
    Validate workflow actions and parameters against available action definitions.

    Checks:
    - Action IDs are defined
    - Parameters are defined for the action
    - Required parameters are present

    Args:
        workflow: Workflow data dictionary
        available_actions: List of available action definitions

    Returns:
        List of validation issue messages (empty if valid)
    """
    validation_issues = []
    defined_actions = {a["id"]: a for a in available_actions}

    nodes = workflow.get("nodes", {})

    for node_id, node in nodes.items():
        if node.get("type") != "Action":
            continue

        action_id = node.get("actionId")
        if not action_id:
            continue

        node_name = node.get("name", node_id)

        # Check if action is defined
        if action_id not in defined_actions:
            validation_issues.append(
                f"Node '{node_name}' uses undefined action '{action_id}'"
            )
            continue

        # Validate parameters
        action_def = defined_actions[action_id]
        defined_params = {p["id"]: p for p in action_def.get("params", [])}
        node_params = node.get("params", {}) or {}

        # Check for undefined params
        for param_key in node_params.keys():
            if param_key not in defined_params:
                validation_issues.append(
                    f"Node '{node_name}' (Action: {action_id}) "
                    f"uses undefined param '{param_key}'"
                )

        # Check for missing required params
        for param_id, param_def in defined_params.items():
            if param_def.get("required", False) and param_id not in node_params:
                validation_issues.append(
                    f"Node '{node_name}' (Action: {action_id}) "
                    f"missing required param '{param_id}'"
                )

    return validation_issues


def parse_workflow_from_llm_response(
    response: str, available_actions: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Parse and validate workflow from LLM response.

    Returns a result dictionary with status and relevant data:
    - status: "success" | "confirmation_required" | "error"
    - workflow: Parsed workflow data (if successful)
    - validation_issues: List of validation problems (if any)
    - message: Error or warning message
    - llm_response: Original LLM response

    Args:
        response: Raw LLM response text
        available_actions: List of available action definitions

    Returns:
        Result dictionary with status and workflow data
    """
    # Extract JSON from response
    json_str = extract_json_from_response(response)

    if not json_str:
        return {
            "status": "error",
            "message": "No JSON found in LLM response",
            "llm_response": response,
        }

    # Parse JSON
    try:
        workflow_data = json.loads(json_str)
    except json.JSONDecodeError as e:
        return {
            "status": "error",
            "message": f"Failed to parse LLM response as JSON: {str(e)}",
            "llm_response": response,
            "extracted_json": json_str,
        }

    # Validate schema
    schema_valid, schema_errors = validate_workflow_schema(workflow_data)
    if not schema_valid:
        return {
            "status": "error",
            "message": "Invalid workflow structure: " + "; ".join(schema_errors),
            "llm_response": response,
        }

    # Validate actions and parameters
    validation_issues = validate_workflow_actions(workflow_data, available_actions)

    if validation_issues:
        return {
            "status": "confirmation_required",
            "workflow": workflow_data,
            "undefined_actions": validation_issues,  # Keep for frontend compatibility
            "message": "워크플로우 검증 문제 발생",
            "llm_response": response,
        }

    return {
        "status": "success",
        "workflow": workflow_data,
        "llm_response": response,
    }
