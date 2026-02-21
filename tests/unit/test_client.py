"""Unit tests for the VerifyWise HTTP client.

Uses respx to mock httpx calls so no real network access is required.
"""

import json
import time
import base64

import httpx
import pytest
import respx
from mcp.server.fastmcp.exceptions import ToolError


def make_jwt(exp: float) -> str:
    """Helper: create a fake but structurally valid JWT."""
    header = base64.urlsafe_b64encode(b'{"alg":"HS256"}').decode().rstrip("=")
    payload = base64.urlsafe_b64encode(json.dumps({"exp": exp}).encode()).decode().rstrip("=")
    return f"{header}.{payload}.sig"


BASE_URL = "http://localhost:3000"
VALID_TOKEN = make_jwt(time.time() + 3600)


@pytest.fixture
def mock_auth_manager():
    """Return a mock TokenManager that always yields a valid token."""
    from unittest.mock import AsyncMock

    from verifywise_mcp.auth import TokenManager

    manager = AsyncMock(spec=TokenManager)
    manager.get_valid_token.return_value = VALID_TOKEN
    return manager


# --- VerifyWiseClient.get ---


@respx.mock
async def test_client_get_success(mock_auth_manager):
    """client.get should return parsed JSON on a 200 response."""
    respx.get(f"{BASE_URL}/api/projects").mock(
        return_value=httpx.Response(200, json=[{"id": "1", "name": "Test Project"}])
    )

    from verifywise_mcp.client import VerifyWiseClient

    http = httpx.AsyncClient()
    client = VerifyWiseClient(
        base_url=BASE_URL,
        email="test@example.com",
        password="pw",
        http_client=http,
        token_manager=mock_auth_manager,
    )

    result = await client.get("/api/projects")
    assert result == [{"id": "1", "name": "Test Project"}]


@respx.mock
async def test_client_get_404_raises_tool_error(mock_auth_manager):
    """client.get should raise ToolError on 404."""
    respx.get(f"{BASE_URL}/api/projects/999").mock(
        return_value=httpx.Response(404, json={"error": "Not found"})
    )

    from verifywise_mcp.client import VerifyWiseClient

    http = httpx.AsyncClient()
    client = VerifyWiseClient(
        base_url=BASE_URL,
        email="test@example.com",
        password="pw",
        http_client=http,
        token_manager=mock_auth_manager,
    )

    with pytest.raises(ToolError, match="not found"):
        await client.get("/api/projects/999")


@respx.mock
async def test_client_get_500_raises_tool_error(mock_auth_manager):
    """client.get should raise ToolError on 5xx server errors."""
    respx.get(f"{BASE_URL}/api/projects").mock(
        return_value=httpx.Response(500, json={"error": "Internal server error"})
    )

    from verifywise_mcp.client import VerifyWiseClient

    http = httpx.AsyncClient()
    client = VerifyWiseClient(
        base_url=BASE_URL,
        email="test@example.com",
        password="pw",
        http_client=http,
        token_manager=mock_auth_manager,
        max_retries=1,
    )

    with pytest.raises(ToolError):
        await client.get("/api/projects")


# --- VerifyWiseClient.post ---


@respx.mock
async def test_client_post_success(mock_auth_manager):
    """client.post should return parsed JSON on a 201 response."""
    respx.post(f"{BASE_URL}/api/projects").mock(
        return_value=httpx.Response(201, json={"id": "2", "name": "New Project"})
    )

    from verifywise_mcp.client import VerifyWiseClient

    http = httpx.AsyncClient()
    client = VerifyWiseClient(
        base_url=BASE_URL,
        email="test@example.com",
        password="pw",
        http_client=http,
        token_manager=mock_auth_manager,
    )

    result = await client.post("/api/projects", json={"name": "New Project"})
    assert result["id"] == "2"


# --- VerifyWiseClient.delete ---


@respx.mock
async def test_client_delete_success(mock_auth_manager):
    """client.delete should return parsed JSON or empty dict on success."""
    respx.delete(f"{BASE_URL}/api/projects/1").mock(
        return_value=httpx.Response(200, json={"deleted": True})
    )

    from verifywise_mcp.client import VerifyWiseClient

    http = httpx.AsyncClient()
    client = VerifyWiseClient(
        base_url=BASE_URL,
        email="test@example.com",
        password="pw",
        http_client=http,
        token_manager=mock_auth_manager,
    )

    result = await client.delete("/api/projects/1")
    assert result == {"deleted": True}


# --- get_client singleton ---


async def test_get_client_returns_same_instance(monkeypatch):
    """get_client() should return the same client instance on repeated calls."""
    monkeypatch.setenv("VERIFYWISE_EMAIL", "test@example.com")
    monkeypatch.setenv("VERIFYWISE_PASSWORD", "testpass")
    monkeypatch.setenv("VERIFYWISE_BASE_URL", BASE_URL)

    from verifywise_mcp import client as client_module

    # Reset singleton so each test is independent
    client_module._client = None

    from verifywise_mcp.client import get_client

    c1 = await get_client()
    c2 = await get_client()

    assert c1 is c2

    # Cleanup
    client_module._client = None
