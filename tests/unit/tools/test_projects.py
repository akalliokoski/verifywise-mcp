"""Unit tests for the projects tools.

All VerifyWise API calls are mocked via patch; no network access required.
"""

from unittest.mock import AsyncMock, patch

import pytest
from mcp.server.fastmcp.exceptions import ToolError


@pytest.fixture
def mock_client():
    """Return a mock VerifyWiseClient."""
    client = AsyncMock()
    client.get.return_value = []
    client.post.return_value = {"id": "1", "name": "Test Project"}
    client.put.return_value = {"id": "1", "name": "Updated Project"}
    client.delete.return_value = {"deleted": True}
    return client


# --- list_projects ---


async def test_list_projects_returns_list(mock_client):
    """list_projects should return a list of project dicts."""
    mock_client.get.return_value = [
        {"id": "1", "name": "AI Loan System", "status": "active"},
        {"id": "2", "name": "CV Model", "status": "draft"},
    ]

    with patch("verifywise_mcp.tools.projects.get_client", return_value=mock_client):
        from verifywise_mcp.tools.projects import list_projects

        result = await list_projects()

    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["name"] == "AI Loan System"


async def test_list_projects_calls_correct_endpoint(mock_client):
    """list_projects should call /api/projects."""
    with patch("verifywise_mcp.tools.projects.get_client", return_value=mock_client):
        from verifywise_mcp.tools.projects import list_projects

        await list_projects()

    mock_client.get.assert_called_once_with("/api/projects")


async def test_list_projects_validates_limit_min(mock_client):
    """list_projects should raise ToolError when limit < 1."""
    with patch("verifywise_mcp.tools.projects.get_client", return_value=mock_client):
        from verifywise_mcp.tools.projects import list_projects

        with pytest.raises(ToolError, match="limit"):
            await list_projects(limit=0)


async def test_list_projects_validates_limit_max(mock_client):
    """list_projects should raise ToolError when limit > 100."""
    with patch("verifywise_mcp.tools.projects.get_client", return_value=mock_client):
        from verifywise_mcp.tools.projects import list_projects

        with pytest.raises(ToolError, match="limit"):
            await list_projects(limit=101)


async def test_list_projects_applies_limit(mock_client):
    """list_projects should return at most `limit` items."""
    mock_client.get.return_value = [{"id": str(i)} for i in range(10)]

    with patch("verifywise_mcp.tools.projects.get_client", return_value=mock_client):
        from verifywise_mcp.tools.projects import list_projects

        result = await list_projects(limit=3)

    assert len(result) == 3


# --- get_project ---


async def test_get_project_returns_project(mock_client):
    """get_project should return the project dict for a valid ID."""
    mock_client.get.return_value = {"id": "42", "name": "Chatbot Risk"}

    with patch("verifywise_mcp.tools.projects.get_client", return_value=mock_client):
        from verifywise_mcp.tools.projects import get_project

        result = await get_project(project_id="42")

    assert result["id"] == "42"
    mock_client.get.assert_called_once_with("/api/projects/42")


async def test_get_project_raises_tool_error_on_not_found(mock_client):
    """get_project should propagate ToolError from the client (e.g. 404)."""
    mock_client.get.side_effect = ToolError("Resource not found")

    with patch("verifywise_mcp.tools.projects.get_client", return_value=mock_client):
        from verifywise_mcp.tools.projects import get_project

        with pytest.raises(ToolError):
            await get_project(project_id="999")


# --- create_project ---


async def test_create_project_returns_new_project(mock_client):
    """create_project should post to /api/projects and return the new project."""
    mock_client.post.return_value = {
        "id": "new-1",
        "name": "New AI System",
        "status": "draft",
    }

    with patch("verifywise_mcp.tools.projects.get_client", return_value=mock_client):
        from verifywise_mcp.tools.projects import create_project

        result = await create_project(name="New AI System", ai_risk_classification="high")

    assert result["id"] == "new-1"
    mock_client.post.assert_called_once()


async def test_create_project_validates_empty_name(mock_client):
    """create_project should raise ToolError when name is empty."""
    with patch("verifywise_mcp.tools.projects.get_client", return_value=mock_client):
        from verifywise_mcp.tools.projects import create_project

        with pytest.raises(ToolError, match="name"):
            await create_project(name="", ai_risk_classification="high")


# --- update_project ---


async def test_update_project_calls_put(mock_client):
    """update_project should call PUT /api/projects/{id}."""
    mock_client.put.return_value = {"id": "1", "name": "Renamed"}

    with patch("verifywise_mcp.tools.projects.get_client", return_value=mock_client):
        from verifywise_mcp.tools.projects import update_project

        result = await update_project(project_id="1", name="Renamed")

    assert result["name"] == "Renamed"
    mock_client.put.assert_called_once()


# --- delete_project ---


async def test_delete_project_calls_delete(mock_client):
    """delete_project should call DELETE /api/projects/{id}."""
    mock_client.delete.return_value = {"deleted": True}

    with patch("verifywise_mcp.tools.projects.get_client", return_value=mock_client):
        from verifywise_mcp.tools.projects import delete_project

        result = await delete_project(project_id="1")

    assert result["deleted"] is True
    mock_client.delete.assert_called_once_with("/api/projects/1")
