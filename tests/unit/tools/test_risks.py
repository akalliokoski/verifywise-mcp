"""Unit tests for the risks tools.

All VerifyWise API calls are mocked; no network access required.
"""

from unittest.mock import AsyncMock, patch

import pytest
from mcp.server.fastmcp.exceptions import ToolError


@pytest.fixture
def mock_client():
    """Return a mock VerifyWiseClient."""
    client = AsyncMock()
    client.get.return_value = []
    client.post.return_value = {"id": "r1", "title": "Test Risk"}
    client.put.return_value = {"id": "r1", "status": "mitigated"}
    client.delete.return_value = {"deleted": True}
    return client


# --- list_risks ---


async def test_list_risks_returns_list(mock_client):
    """list_risks should return a list of risk dicts."""
    mock_client.get.return_value = [
        {"id": "r1", "title": "Bias Risk"},
        {"id": "r2", "title": "Data Leakage"},
    ]

    with patch("verifywise_mcp.tools.risks.get_client", return_value=mock_client):
        from verifywise_mcp.tools.risks import list_risks

        result = await list_risks()

    assert isinstance(result, list)
    assert len(result) == 2


async def test_list_risks_by_project_id(mock_client):
    """list_risks with project_id should call the by-project endpoint."""
    mock_client.get.return_value = [{"id": "r1", "project_id": "p1"}]

    with patch("verifywise_mcp.tools.risks.get_client", return_value=mock_client):
        from verifywise_mcp.tools.risks import list_risks

        result = await list_risks(project_id="p1")

    mock_client.get.assert_called_once_with("/api/projectRisks/by-projid/p1")
    assert len(result) == 1


async def test_list_risks_without_project_id(mock_client):
    """list_risks without project_id should call the base risks endpoint."""
    with patch("verifywise_mcp.tools.risks.get_client", return_value=mock_client):
        from verifywise_mcp.tools.risks import list_risks

        await list_risks()

    mock_client.get.assert_called_once_with("/api/projectRisks")


# --- get_risk ---


async def test_get_risk_returns_risk(mock_client):
    """get_risk should return the risk dict for a valid ID."""
    mock_client.get.return_value = {"id": "r42", "title": "Model Bias"}

    with patch("verifywise_mcp.tools.risks.get_client", return_value=mock_client):
        from verifywise_mcp.tools.risks import get_risk

        result = await get_risk(risk_id="r42")

    assert result["id"] == "r42"
    mock_client.get.assert_called_once_with("/api/projectRisks/r42")


async def test_get_risk_raises_on_not_found(mock_client):
    """get_risk should propagate ToolError from the client (e.g. 404)."""
    mock_client.get.side_effect = ToolError("Resource not found")

    with patch("verifywise_mcp.tools.risks.get_client", return_value=mock_client):
        from verifywise_mcp.tools.risks import get_risk

        with pytest.raises(ToolError):
            await get_risk(risk_id="nonexistent")


# --- create_risk ---


async def test_create_risk_returns_new_risk(mock_client):
    """create_risk should POST to /api/projectRisks and return the created risk."""
    mock_client.post.return_value = {
        "id": "r-new",
        "title": "Model bias in loan approval",
        "severity": "high",
    }

    with patch("verifywise_mcp.tools.risks.get_client", return_value=mock_client):
        from verifywise_mcp.tools.risks import create_risk

        result = await create_risk(
            project_id="p1",
            title="Model bias in loan approval",
            description="Demographic bias may affect approval rates",
            severity="high",
        )

    assert result["id"] == "r-new"
    mock_client.post.assert_called_once()


async def test_create_risk_validates_empty_title(mock_client):
    """create_risk should raise ToolError when title is empty."""
    with patch("verifywise_mcp.tools.risks.get_client", return_value=mock_client):
        from verifywise_mcp.tools.risks import create_risk

        with pytest.raises(ToolError, match="title"):
            await create_risk(
                project_id="p1",
                title="",
                description="desc",
                severity="high",
            )


async def test_create_risk_validates_severity(mock_client):
    """create_risk should raise ToolError for an unknown severity value."""
    with patch("verifywise_mcp.tools.risks.get_client", return_value=mock_client):
        from verifywise_mcp.tools.risks import create_risk

        with pytest.raises(ToolError, match="severity"):
            await create_risk(
                project_id="p1",
                title="Some risk",
                description="desc",
                severity="unknown",
            )


# --- update_risk ---


async def test_update_risk_calls_put(mock_client):
    """update_risk should call PUT /api/projectRisks/{id}."""
    mock_client.put.return_value = {"id": "r1", "status": "mitigated"}

    with patch("verifywise_mcp.tools.risks.get_client", return_value=mock_client):
        from verifywise_mcp.tools.risks import update_risk

        result = await update_risk(risk_id="r1", status="mitigated")

    assert result["status"] == "mitigated"
    mock_client.put.assert_called_once()


# --- delete_risk ---


async def test_delete_risk_calls_delete(mock_client):
    """delete_risk should call DELETE /api/projectRisks/{id}."""
    mock_client.delete.return_value = {"deleted": True}

    with patch("verifywise_mcp.tools.risks.get_client", return_value=mock_client):
        from verifywise_mcp.tools.risks import delete_risk

        result = await delete_risk(risk_id="r1")

    assert result["deleted"] is True
    mock_client.delete.assert_called_once_with("/api/projectRisks/r1")
