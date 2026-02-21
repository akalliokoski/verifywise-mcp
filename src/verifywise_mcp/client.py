"""Async HTTP client for the VerifyWise REST API.

Provides ``VerifyWiseClient`` for making authenticated requests to VerifyWise,
and a module-level ``get_client()`` helper that returns a lazily-initialised
singleton instance.

VerifyWise API Routes (discovered from verifywise/Servers/routes/ at v2.1):
==========================================================================

Authentication:
  POST   /api/users/login                         - Login, returns access + refresh tokens
  POST   /api/users/refresh-token                 - Get new access token using refresh token
  POST   /api/users/check-user-exists             - Check if any user exists (setup flow)

Projects:
  GET    /api/projects                            - List all projects
  GET    /api/projects/:id                        - Get project by ID
  POST   /api/projects                            - Create project
  PUT    /api/projects/:id                        - Update project
  DELETE /api/projects/:id                        - Delete project
  GET    /api/projects/stats/:id                  - Get project stats
  GET    /api/projects/calculateProjectRisks/:id  - Risk calculations for project
  GET    /api/projects/calculateVendorRisks/:id   - Vendor risk calculations
  GET    /api/projects/compliance/progress/:id    - Compliance progress for project
  GET    /api/projects/assessment/progress/:id    - Assessment progress for project
  GET    /api/projects/all/compliance/progress    - Compliance progress across all projects
  GET    /api/projects/all/assessment/progress    - Assessment progress across all projects

Risks (Project Risks):
  GET    /api/projectRisks                        - List all risks
  GET    /api/projectRisks/by-projid/:id          - Risks by project ID
  GET    /api/projectRisks/by-frameworkid/:id     - Risks by framework ID
  GET    /api/projectRisks/:id                    - Get risk by ID
  POST   /api/projectRisks                        - Create risk
  PUT    /api/projectRisks/:id                    - Update risk
  DELETE /api/projectRisks/:id                    - Delete risk

Vendors:
  GET    /api/vendors                             - List all vendors
  GET    /api/vendors/:id                         - Get vendor by ID
  GET    /api/vendors/project-id/:id              - Vendors by project ID
  POST   /api/vendors                             - Create vendor
  PATCH  /api/vendors/:id                         - Update vendor
  DELETE /api/vendors/:id                         - Delete vendor

Vendor Risks:
  GET    /api/vendorRisks                         - List vendor risks
  GET    /api/vendorRisks/:id                     - Get vendor risk by ID
  POST   /api/vendorRisks                         - Create vendor risk
  PUT    /api/vendorRisks/:id                     - Update vendor risk
  DELETE /api/vendorRisks/:id                     - Delete vendor risk

Compliance:
  GET    /api/compliance/score                    - Compliance score for authenticated org
  GET    /api/compliance/score/:organizationId    - Compliance score for specific org (admin)
  GET    /api/compliance/details/:organizationId  - Detailed compliance breakdown (drill-down)

AI Model Inventory:
  GET    /api/modelInventory                      - List AI models
  GET    /api/modelInventory/:id                  - Get model by ID
  POST   /api/modelInventory                      - Create AI model record
  PUT    /api/modelInventory/:id                  - Update model
  DELETE /api/modelInventory/:id                  - Delete model

Frameworks:
  GET    /api/frameworks                          - List compliance frameworks
  GET    /api/eu-ai-act                           - EU AI Act framework data
  GET    /api/iso-42001                           - ISO 42001 framework data
  GET    /api/iso-27001                           - ISO 27001 framework data

Users:
  GET    /api/users                               - List all users
  GET    /api/users/:id                           - Get user by ID
  GET    /api/users/by-email/:email               - Get user by email
  POST   /api/users                               - Create user
  PUT    /api/users/:id                           - Update user
  DELETE /api/users/:id                           - Delete user

Port mappings:
  Backend API: http://localhost:3000  (env: VERIFYWISE_BASE_URL)
  Frontend:    http://localhost:8080
  EvalServer:  http://localhost:8000  (internal only)
"""

import asyncio
import logging
from typing import Any

import httpx
from mcp.server.fastmcp.exceptions import ToolError

from verifywise_mcp.auth import TokenManager
from verifywise_mcp.config import Settings

logger = logging.getLogger(__name__)


class VerifyWiseClient:
    """Authenticated async HTTP client for the VerifyWise REST API.

    Wraps ``httpx.AsyncClient`` with:

    - Automatic Bearer token injection on every request
    - Transparent token refresh when the stored token expires
    - Conversion of 404 responses to ``ToolError`` (expected "not found" case)
    - Conversion of other HTTP errors to ``ToolError``

    Attributes:
        base_url: VerifyWise API base URL.
    """

    def __init__(
        self,
        base_url: str,
        email: str,
        password: str,
        *,
        timeout: float = 30.0,
        max_retries: int = 3,
        http_client: httpx.AsyncClient | None = None,
        token_manager: TokenManager | None = None,
    ) -> None:
        """Create a new client.

        Args:
            base_url: VerifyWise API base URL (e.g. ``http://localhost:3000``).
            email: Admin email for initial login.
            password: Admin password for initial login.
            timeout: HTTP request timeout in seconds.
            max_retries: Max number of retry attempts on transient errors.
            http_client: Optional pre-built httpx client (used in tests).
            token_manager: Optional pre-built TokenManager (used in tests).
        """
        self.base_url = base_url
        self._email = email
        self._password = password
        self._max_retries = max_retries
        self._http = http_client or httpx.AsyncClient(timeout=timeout)
        self._token_manager = token_manager or TokenManager(self._http)
        self._authenticated = False
        self._auth_lock = asyncio.Lock()

    async def _ensure_authenticated(self) -> None:
        """Perform initial login if not yet authenticated."""
        if self._authenticated:
            return
        async with self._auth_lock:
            if not self._authenticated:
                await self._token_manager.login(self._email, self._password, self.base_url)
                self._authenticated = True

    async def _auth_headers(self) -> dict[str, str]:
        """Return Authorization headers with a valid Bearer token."""
        await self._ensure_authenticated()
        token = await self._token_manager.get_valid_token(self.base_url)
        return {"Authorization": f"Bearer {token}"}

    def _handle_response(self, response: httpx.Response) -> Any:
        """Raise ``ToolError`` for error responses; otherwise return parsed JSON.

        Args:
            response: The httpx response to inspect.

        Returns:
            Parsed JSON body as a Python object.

        Raises:
            ToolError: For 404 (not found) or other HTTP error status codes.
        """
        if response.status_code == 404:
            raise ToolError(f"Resource not found: {response.url}")
        if response.is_error:
            raise ToolError(f"VerifyWise API error {response.status_code}: {response.text[:200]}")
        try:
            return response.json()
        except Exception:
            return response.text

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Make an authenticated GET request.

        Args:
            path: API path (e.g. ``/api/projects``).
            params: Optional query parameters.

        Returns:
            Parsed JSON response body.

        Raises:
            ToolError: On HTTP error or network failure.
        """
        headers = await self._auth_headers()
        for attempt in range(max(1, self._max_retries)):
            try:
                response = await self._http.get(
                    f"{self.base_url}{path}",
                    headers=headers,
                    params=params,
                )
                return self._handle_response(response)
            except ToolError:
                raise
            except httpx.HTTPError as exc:
                if attempt == self._max_retries - 1:
                    raise ToolError(f"Network error calling {path}: {exc}") from exc
                await asyncio.sleep(2**attempt)
        raise ToolError(
            f"Failed to GET {path} after {self._max_retries} attempts"
        )  # pragma: no cover

    async def post(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> Any:
        """Make an authenticated POST request.

        Args:
            path: API path.
            json: Optional JSON body.
            data: Optional form data body.

        Returns:
            Parsed JSON response body.

        Raises:
            ToolError: On HTTP error or network failure.
        """
        headers = await self._auth_headers()
        try:
            response = await self._http.post(
                f"{self.base_url}{path}",
                headers=headers,
                json=json,
                data=data,
            )
            return self._handle_response(response)
        except ToolError:
            raise
        except httpx.HTTPError as exc:
            raise ToolError(f"Network error calling {path}: {exc}") from exc

    async def put(self, path: str, json: dict[str, Any] | None = None) -> Any:
        """Make an authenticated PUT request.

        Args:
            path: API path.
            json: Optional JSON body.

        Returns:
            Parsed JSON response body.

        Raises:
            ToolError: On HTTP error or network failure.
        """
        headers = await self._auth_headers()
        try:
            response = await self._http.put(
                f"{self.base_url}{path}",
                headers=headers,
                json=json,
            )
            return self._handle_response(response)
        except ToolError:
            raise
        except httpx.HTTPError as exc:
            raise ToolError(f"Network error calling {path}: {exc}") from exc

    async def patch(self, path: str, json: dict[str, Any] | None = None) -> Any:
        """Make an authenticated PATCH request.

        Args:
            path: API path.
            json: Optional JSON body.

        Returns:
            Parsed JSON response body.

        Raises:
            ToolError: On HTTP error or network failure.
        """
        headers = await self._auth_headers()
        try:
            response = await self._http.patch(
                f"{self.base_url}{path}",
                headers=headers,
                json=json,
            )
            return self._handle_response(response)
        except ToolError:
            raise
        except httpx.HTTPError as exc:
            raise ToolError(f"Network error calling {path}: {exc}") from exc

    async def delete(self, path: str) -> Any:
        """Make an authenticated DELETE request.

        Args:
            path: API path.

        Returns:
            Parsed JSON response body.

        Raises:
            ToolError: On HTTP error or network failure.
        """
        headers = await self._auth_headers()
        try:
            response = await self._http.delete(
                f"{self.base_url}{path}",
                headers=headers,
            )
            return self._handle_response(response)
        except ToolError:
            raise
        except httpx.HTTPError as exc:
            raise ToolError(f"Network error calling {path}: {exc}") from exc

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._http.aclose()


# Module-level singleton — lazily initialised on first call to get_client()
_client: VerifyWiseClient | None = None
_client_lock = asyncio.Lock()


async def get_client() -> VerifyWiseClient:
    """Return the shared ``VerifyWiseClient`` instance.

    Initialises the client from environment variables (``VERIFYWISE_*``) on
    the first call. Subsequent calls return the same cached instance.

    Returns:
        An authenticated ``VerifyWiseClient`` ready for API calls.
    """
    global _client
    if _client is None:
        async with _client_lock:
            if _client is None:
                settings = Settings()  # type: ignore[call-arg]
                _client = VerifyWiseClient(
                    base_url=settings.base_url,
                    email=settings.email,
                    password=settings.password,
                    timeout=settings.request_timeout,
                    max_retries=settings.max_retries,
                )
    return _client
