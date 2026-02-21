"""FastMCP tools for VerifyWise project (Use Case) management.

Registers the following tools on a ``FastMCP`` instance via ``register_tools()``:

- ``list_projects`` — list all AI governance projects
- ``get_project`` — get a project by ID
- ``create_project`` — create a new project
- ``update_project`` — update an existing project
- ``delete_project`` — delete a project
"""

from __future__ import annotations

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from verifywise_mcp.client import get_client

logger = logging.getLogger(__name__)


# --- Tool functions (plain async functions, registered by register_tools) ---


async def list_projects(
    limit: int = 20,
) -> list[dict[str, Any]]:
    """List AI governance projects (Use Cases) in VerifyWise.

    Args:
        limit: Maximum number of projects to return (1–100). Defaults to 20.

    Returns:
        List of project objects, each with id, name, and status fields.

    Raises:
        ToolError: If the VerifyWise API is unreachable or returns an error,
            or if ``limit`` is out of range.
    """
    if not 1 <= limit <= 100:
        raise ToolError("limit must be between 1 and 100")

    client = await get_client()
    projects: list[dict[str, Any]] = await client.get("/api/projects")
    return projects[:limit]


async def get_project(project_id: str) -> dict[str, Any]:
    """Get the details of a specific AI governance project.

    Args:
        project_id: The unique identifier of the project.

    Returns:
        Project object with full details.

    Raises:
        ToolError: If the project is not found or the API returns an error.
    """
    client = await get_client()
    return await client.get(f"/api/projects/{project_id}")  # type: ignore[return-value]


async def create_project(
    name: str,
    ai_risk_classification: str,
    type_of_high_risk_role: str | None = None,
    goal: str | None = None,
    last_updated_by: str | None = None,
) -> dict[str, Any]:
    """Create a new AI governance project (Use Case) in VerifyWise.

    Args:
        name: Project name. Must not be empty.
        ai_risk_classification: Risk classification (e.g. high, limited, minimal).
        type_of_high_risk_role: Optional role descriptor for high-risk AI systems.
        goal: Optional description of the project's governance goal.
        last_updated_by: Optional email/ID of the user making this change.

    Returns:
        The newly created project object.

    Raises:
        ToolError: If ``name`` is empty or the API returns an error.
    """
    if not name.strip():
        raise ToolError("name must not be empty")

    payload: dict[str, Any] = {
        "projectName": name,
        "aiRiskClassification": ai_risk_classification,
    }
    if type_of_high_risk_role is not None:
        payload["typeOfHighRiskRole"] = type_of_high_risk_role
    if goal is not None:
        payload["goal"] = goal
    if last_updated_by is not None:
        payload["lastUpdatedBy"] = last_updated_by

    client = await get_client()
    return await client.post("/api/projects", json=payload)  # type: ignore[return-value]


async def update_project(
    project_id: str,
    name: str | None = None,
    ai_risk_classification: str | None = None,
    type_of_high_risk_role: str | None = None,
    goal: str | None = None,
    last_updated_by: str | None = None,
) -> dict[str, Any]:
    """Update an existing AI governance project.

    Only the fields you pass will be changed; omitted fields are left as-is.

    Args:
        project_id: ID of the project to update.
        name: New project name.
        ai_risk_classification: Updated risk classification.
        type_of_high_risk_role: Updated role descriptor.
        goal: Updated governance goal description.
        last_updated_by: Email/ID of the user making this change.

    Returns:
        The updated project object.

    Raises:
        ToolError: If the project is not found or the API returns an error.
    """
    payload: dict[str, Any] = {}
    if name is not None:
        payload["projectName"] = name
    if ai_risk_classification is not None:
        payload["aiRiskClassification"] = ai_risk_classification
    if type_of_high_risk_role is not None:
        payload["typeOfHighRiskRole"] = type_of_high_risk_role
    if goal is not None:
        payload["goal"] = goal
    if last_updated_by is not None:
        payload["lastUpdatedBy"] = last_updated_by

    client = await get_client()
    return await client.put(f"/api/projects/{project_id}", json=payload)  # type: ignore[return-value]


async def delete_project(project_id: str) -> dict[str, Any]:
    """Delete an AI governance project from VerifyWise.

    Args:
        project_id: ID of the project to delete.

    Returns:
        Confirmation object (typically ``{"deleted": true}``).

    Raises:
        ToolError: If the project is not found or the API returns an error.
    """
    client = await get_client()
    return await client.delete(f"/api/projects/{project_id}")  # type: ignore[return-value]


def register_tools(mcp: FastMCP) -> None:  # type: ignore[type-arg]
    """Register all project tools on the given FastMCP instance.

    Call this from ``server.py`` during startup:

    .. code-block:: python

        from verifywise_mcp.tools.projects import register_tools
        register_tools(mcp)

    Args:
        mcp: The FastMCP server instance to register tools on.
    """
    mcp.add_tool(
        list_projects,
        name="list_projects",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    mcp.add_tool(
        get_project,
        name="get_project",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    mcp.add_tool(create_project, name="create_project")
    mcp.add_tool(update_project, name="update_project")
    mcp.add_tool(delete_project, name="delete_project")
