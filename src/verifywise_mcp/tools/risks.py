"""FastMCP tools for VerifyWise project risk management.

Registers the following tools on a ``FastMCP`` instance via ``register_tools()``:

- ``list_risks`` — list risks, optionally filtered by project
- ``get_risk`` — get a risk by ID
- ``create_risk`` — create a new risk record
- ``update_risk`` — update an existing risk
- ``delete_risk`` — delete a risk record
"""

from __future__ import annotations

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from verifywise_mcp.client import get_client

logger = logging.getLogger(__name__)

# Valid severity values accepted by the VerifyWise API
_VALID_SEVERITIES = {"low", "medium", "high", "critical"}


async def list_risks(project_id: str | None = None) -> list[dict[str, Any]]:
    """List project risks in VerifyWise.

    Args:
        project_id: If provided, return only risks for this project.
            If omitted, returns all risks across all projects.

    Returns:
        List of risk objects.

    Raises:
        ToolError: If the VerifyWise API is unreachable or returns an error.
    """
    client = await get_client()

    if project_id is not None:
        path = f"/api/projectRisks/by-projid/{project_id}"
    else:
        path = "/api/projectRisks"

    risks: list[dict[str, Any]] = await client.get(path)
    return risks


async def get_risk(risk_id: str) -> dict[str, Any]:
    """Get the details of a specific risk by ID.

    Args:
        risk_id: Unique identifier of the risk.

    Returns:
        Risk object with full details.

    Raises:
        ToolError: If the risk is not found or the API returns an error.
    """
    client = await get_client()
    return await client.get(f"/api/projectRisks/{risk_id}")  # type: ignore[return-value]


async def create_risk(
    project_id: str,
    title: str,
    description: str,
    severity: str,
    owner: str | None = None,
    due_date: str | None = None,
) -> dict[str, Any]:
    """Create a new risk record for an AI governance project.

    Args:
        project_id: ID of the project this risk belongs to.
        title: Short title for the risk. Must not be empty.
        description: Detailed description of the risk.
        severity: Risk severity. One of: low, medium, high, critical.
        owner: Optional email of the risk owner.
        due_date: Optional target mitigation date (ISO 8601 format).

    Returns:
        The newly created risk object.

    Raises:
        ToolError: If ``title`` is empty, ``severity`` is invalid, or the
            API returns an error.
    """
    if not title.strip():
        raise ToolError("title must not be empty")

    if severity.lower() not in _VALID_SEVERITIES:
        raise ToolError(
            f"severity must be one of: {', '.join(sorted(_VALID_SEVERITIES))}; got '{severity}'"
        )

    payload: dict[str, Any] = {
        "projectId": project_id,
        "riskName": title,
        "riskDescription": description,
        "severity": severity.lower(),
    }
    if owner is not None:
        payload["owner"] = owner
    if due_date is not None:
        payload["dueDate"] = due_date

    client = await get_client()
    return await client.post("/api/projectRisks", json=payload)  # type: ignore[return-value]


async def update_risk(
    risk_id: str,
    title: str | None = None,
    description: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    owner: str | None = None,
    due_date: str | None = None,
) -> dict[str, Any]:
    """Update an existing risk record.

    Only the fields you pass will be changed.

    Args:
        risk_id: ID of the risk to update.
        title: Updated risk title.
        description: Updated risk description.
        severity: Updated severity (low, medium, high, critical).
        status: Updated status (e.g. open, mitigated, closed).
        owner: Updated owner email.
        due_date: Updated due date (ISO 8601).

    Returns:
        The updated risk object.

    Raises:
        ToolError: If the risk is not found or the API returns an error.
    """
    payload: dict[str, Any] = {}
    if title is not None:
        payload["riskName"] = title
    if description is not None:
        payload["riskDescription"] = description
    if severity is not None:
        payload["severity"] = severity
    if status is not None:
        payload["status"] = status
    if owner is not None:
        payload["owner"] = owner
    if due_date is not None:
        payload["dueDate"] = due_date

    client = await get_client()
    return await client.put(f"/api/projectRisks/{risk_id}", json=payload)  # type: ignore[return-value]


async def delete_risk(risk_id: str) -> dict[str, Any]:
    """Delete a risk record from VerifyWise.

    Args:
        risk_id: ID of the risk to delete.

    Returns:
        Confirmation object (typically ``{"deleted": true}``).

    Raises:
        ToolError: If the risk is not found or the API returns an error.
    """
    client = await get_client()
    return await client.delete(f"/api/projectRisks/{risk_id}")  # type: ignore[return-value]


def register_tools(mcp: FastMCP) -> None:  # type: ignore[type-arg]
    """Register all risk tools on the given FastMCP instance.

    Args:
        mcp: The FastMCP server instance to register tools on.
    """
    mcp.add_tool(
        list_risks,
        name="list_risks",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    mcp.add_tool(
        get_risk,
        name="get_risk",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    mcp.add_tool(create_risk, name="create_risk")
    mcp.add_tool(update_risk, name="update_risk")
    mcp.add_tool(delete_risk, name="delete_risk")
