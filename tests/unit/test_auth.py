"""Unit tests for the authentication module.

Tests JWT token expiry detection and token management.
"""

import base64
import json
import time
from unittest.mock import AsyncMock, MagicMock

import pytest


def make_jwt(exp: float | None = None, extra: dict | None = None) -> str:
    """Create a minimal fake JWT token with the given expiry timestamp."""
    header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').decode().rstrip("=")
    payload_data: dict = extra or {}
    if exp is not None:
        payload_data["exp"] = exp
    payload = base64.urlsafe_b64encode(json.dumps(payload_data).encode()).decode().rstrip("=")
    return f"{header}.{payload}.fakesignature"


# --- is_token_expired ---


def test_is_token_expired_with_expired_token():
    """is_token_expired returns True for a token whose exp is in the past."""
    from verifywise_mcp.auth import is_token_expired

    token = make_jwt(exp=time.time() - 100)
    assert is_token_expired(token) is True


def test_is_token_expired_with_valid_token():
    """is_token_expired returns False for a token with future expiry."""
    from verifywise_mcp.auth import is_token_expired

    token = make_jwt(exp=time.time() + 3600)
    assert is_token_expired(token) is False


def test_is_token_expired_with_no_exp_claim():
    """is_token_expired returns False when token has no exp claim."""
    from verifywise_mcp.auth import is_token_expired

    token = make_jwt()  # no exp field
    assert is_token_expired(token) is False


def test_is_token_expired_with_invalid_token():
    """is_token_expired returns True for malformed / non-JWT strings."""
    from verifywise_mcp.auth import is_token_expired

    assert is_token_expired("not.a.valid.jwt.at.all") is True
    assert is_token_expired("invalid") is True
    assert is_token_expired("") is True


def test_is_token_expired_respects_buffer():
    """is_token_expired treats nearly-expired tokens as expired when buffer is set."""
    from verifywise_mcp.auth import is_token_expired

    # Expires in 30 s — within a 60 s buffer, should be considered expired
    near_expiry = make_jwt(exp=time.time() + 30)
    assert is_token_expired(near_expiry, buffer_seconds=60) is True

    # Expires in 120 s — outside the 60 s buffer, should be considered valid
    far_expiry = make_jwt(exp=time.time() + 120)
    assert is_token_expired(far_expiry, buffer_seconds=60) is False


# --- TokenManager ---


async def test_token_manager_login_stores_access_token():
    """TokenManager.login should parse and store the access token."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"token": "access.token.abc"}

    mock_http = AsyncMock()
    mock_http.post.return_value = mock_response

    from verifywise_mcp.auth import TokenManager

    manager = TokenManager(mock_http)
    await manager.login("admin@example.com", "secret", "http://localhost:3000")

    assert manager._access_token == "access.token.abc"
    mock_http.post.assert_called_once_with(
        "http://localhost:3000/api/users/login",
        json={"email": "admin@example.com", "password": "secret"},
    )


async def test_token_manager_login_handles_alternative_field_names():
    """TokenManager.login should handle accessToken as well as token."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"accessToken": "alt.access.token"}

    mock_http = AsyncMock()
    mock_http.post.return_value = mock_response

    from verifywise_mcp.auth import TokenManager

    manager = TokenManager(mock_http)
    await manager.login("admin@example.com", "secret", "http://localhost:3000")

    assert manager._access_token == "alt.access.token"


async def test_token_manager_refresh_updates_token():
    """TokenManager.refresh should update the stored access token."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"token": "refreshed.access.token"}

    mock_http = AsyncMock()
    mock_http.post.return_value = mock_response

    from verifywise_mcp.auth import TokenManager

    manager = TokenManager(mock_http)
    manager._access_token = "old.token"

    await manager.refresh("http://localhost:3000")

    assert manager._access_token == "refreshed.access.token"
    mock_http.post.assert_called_once_with("http://localhost:3000/api/users/refresh-token")


async def test_token_manager_get_valid_token_returns_current_if_not_expired():
    """get_valid_token returns the stored token without refreshing if still valid."""
    valid_token = make_jwt(exp=time.time() + 3600)

    mock_http = AsyncMock()

    from verifywise_mcp.auth import TokenManager

    manager = TokenManager(mock_http)
    manager._access_token = valid_token

    result = await manager.get_valid_token("http://localhost:3000")

    assert result == valid_token
    mock_http.post.assert_not_called()


async def test_token_manager_get_valid_token_refreshes_when_expired():
    """get_valid_token calls refresh when the stored token is expired."""
    expired_token = make_jwt(exp=time.time() - 100)
    new_token = make_jwt(exp=time.time() + 3600)

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"token": new_token}

    mock_http = AsyncMock()
    mock_http.post.return_value = mock_response

    from verifywise_mcp.auth import TokenManager

    manager = TokenManager(mock_http)
    manager._access_token = expired_token

    result = await manager.get_valid_token("http://localhost:3000")

    assert result == new_token
    mock_http.post.assert_called_once()


async def test_token_manager_get_valid_token_refreshes_when_none():
    """get_valid_token calls refresh when no token has been stored yet."""
    new_token = make_jwt(exp=time.time() + 3600)

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"token": new_token}

    mock_http = AsyncMock()
    mock_http.post.return_value = mock_response

    from verifywise_mcp.auth import TokenManager

    manager = TokenManager(mock_http)
    # _access_token starts as None

    result = await manager.get_valid_token("http://localhost:3000")

    assert result == new_token
