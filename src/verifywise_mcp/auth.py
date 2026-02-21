"""JWT token management for VerifyWise authentication.

VerifyWise uses short-lived JWT access tokens (15 min) combined with an
HTTP-only refresh token cookie. This module handles:

- Checking whether a token is expired or nearly expired
- Logging in to get an initial access token
- Refreshing the token when it expires
- Thread-safe token access via ``asyncio.Lock``
"""

import asyncio
import base64
import json
import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)


def is_token_expired(token: str, buffer_seconds: int = 60) -> bool:
    """Check whether a JWT access token is expired (or about to expire).

    Args:
        token: A JWT string in ``header.payload.signature`` format.
        buffer_seconds: Treat the token as expired if it expires within
            this many seconds. Defaults to 60.

    Returns:
        ``True`` if the token is expired or will expire within
        ``buffer_seconds``, or if it cannot be parsed. ``False`` otherwise.
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return True

        # JWT payload is base64url-encoded; add padding if needed
        payload_b64 = parts[1]
        remainder = len(payload_b64) % 4
        if remainder:
            payload_b64 += "=" * (4 - remainder)

        payload: dict[str, Any] = json.loads(base64.urlsafe_b64decode(payload_b64))
        exp = payload.get("exp")

        if exp is None:
            # No expiry claim — treat as non-expiring
            return False

        return time.time() >= float(exp) - buffer_seconds

    except Exception:
        # Malformed token — treat as expired to force re-authentication
        return True


class TokenManager:
    """Thread-safe manager for VerifyWise JWT access tokens.

    Holds the current access token in memory and provides methods to
    authenticate (login) and refresh when the token is near expiry.

    The underlying ``httpx.AsyncClient`` is expected to store the
    HTTP-only refresh token cookie automatically.
    """

    def __init__(self, http_client: httpx.AsyncClient) -> None:
        """Initialise the manager with a shared httpx client.

        Args:
            http_client: The async HTTP client to use for auth requests.
                The client's cookie jar will hold the refresh token.
        """
        self._http_client = http_client
        self._access_token: str | None = None
        self._lock = asyncio.Lock()

    def _parse_token(self, data: dict[str, Any]) -> str:
        """Extract the access token from a login / refresh response body.

        VerifyWise may use different field names across versions.

        Args:
            data: Parsed JSON response body.

        Returns:
            The access token string.

        Raises:
            ValueError: If no recognised token field is present.
        """
        for field in ("token", "accessToken", "access_token"):
            value = data.get(field)
            if value:
                return str(value)
        raise ValueError(f"No token field found in response: {list(data.keys())}")

    async def login(self, email: str, password: str, base_url: str) -> None:
        """Authenticate with VerifyWise and store the access token.

        Args:
            email: Admin email address.
            password: Admin password.
            base_url: VerifyWise API base URL (e.g. ``http://localhost:3000``).
        """
        logger.debug("Logging in to VerifyWise as %s", email)
        response = await self._http_client.post(
            f"{base_url}/api/users/login",
            json={"email": email, "password": password},
        )
        response.raise_for_status()
        self._access_token = self._parse_token(response.json())
        logger.debug("Login successful; access token stored")

    async def refresh(self, base_url: str) -> None:
        """Refresh the access token using the stored refresh token cookie.

        Args:
            base_url: VerifyWise API base URL.
        """
        logger.debug("Refreshing access token")
        response = await self._http_client.post(f"{base_url}/api/users/refresh-token")
        response.raise_for_status()
        self._access_token = self._parse_token(response.json())
        logger.debug("Token refreshed successfully")

    async def get_valid_token(self, base_url: str) -> str:
        """Return a valid access token, refreshing if expired or absent.

        Uses an asyncio lock to prevent concurrent refresh calls.

        Args:
            base_url: VerifyWise API base URL.

        Returns:
            A non-expired JWT access token string.
        """
        async with self._lock:
            if self._access_token is None or is_token_expired(self._access_token):
                await self.refresh(base_url)
            # After refresh, _access_token must be set
            assert self._access_token is not None
            return self._access_token
