# ARCHITECTURE.md — VerifyWise MCP Server

> System design, architectural decisions, and integration patterns.

---

## System Overview

```
┌───────────────────────────────────────────────────────────────┐
│                   AI Assistant (Claude)                       │
│                 "List projects in VerifyWise"                 │
└──────────────────────────┬────────────────────────────────────┘
                           │ MCP Protocol (STDIO / HTTP)
┌──────────────────────────▼────────────────────────────────────┐
│              verifywise-mcp (FastMCP Server)                  │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                   FastMCP Core                          │  │
│  │  ┌────────────┐ ┌────────────┐ ┌─────────────────────┐ │  │
│  │  │   Tools    │ │ Resources  │ │      Prompts        │ │  │
│  │  │ (actions)  │ │ (data URIs)│ │  (templates)        │ │  │
│  │  └────────────┘ └────────────┘ └─────────────────────┘ │  │
│  └──────────────────────────┬──────────────────────────────┘  │
│                             │                                 │
│  ┌──────────────────────────▼──────────────────────────────┐  │
│  │              VerifyWise API Client                      │  │
│  │         (async httpx + JWT token management)            │  │
│  └──────────────────────────┬──────────────────────────────┘  │
└─────────────────────────────┼─────────────────────────────────┘
                              │ REST API (HTTP/JSON)
┌─────────────────────────────▼─────────────────────────────────┐
│                    VerifyWise Platform                        │
│                                                               │
│  ┌──────────────┐  ┌────────────────┐  ┌────────────────┐    │
│  │   Frontend   │  │  Node.js API   │  │  Python Eval   │    │
│  │ React + Vite │  │  Express :3000 │  │  Server :8000  │    │
│  │    :8080     │  └───────┬────────┘  └────────────────┘    │
│  └──────────────┘          │                                  │
│                    ┌───────▼──────┐  ┌────────────────┐       │
│                    │  PostgreSQL  │  │     Redis      │       │
│                    │    :5432     │  │     :6379      │       │
│                    └─────────────┘  └────────────────┘       │
└───────────────────────────────────────────────────────────────┘
```

---

## MCP Server Architecture

### Transport Layer

| Mode | Transport | Use Case |
|------|-----------|----------|
| **Local** | STDIO | Claude Desktop, local development, IDE integration |
| **Remote** | Streamable HTTP | Shared team deployment, containerized environments |

**Decision:** Default to STDIO transport for local development. Streamable HTTP can be added later for shared deployment without changing the business logic.

### Server Composition (Modular Design)

The server uses FastMCP's `mount()` pattern to compose specialized sub-servers:

```python
# src/verifywise_mcp/server.py

from fastmcp import FastMCP
from verifywise_mcp.tools.projects import projects_server
from verifywise_mcp.tools.risks import risks_server
from verifywise_mcp.tools.compliance import compliance_server
from verifywise_mcp.tools.vendors import vendors_server
from verifywise_mcp.tools.models import models_server
from verifywise_mcp.resources.frameworks import frameworks_server
from verifywise_mcp.resources.policies import policies_server

mcp = FastMCP(
    name="verifywise-mcp",
    instructions="""
    You are connected to VerifyWise, an AI governance platform.
    Use the available tools to manage AI projects, compliance assessments,
    risks, vendor evaluations, and governance policies.

    Key entities:
    - Projects (also called "Use Cases"): AI applications being governed
    - Risks: Identified threats to responsible AI deployment
    - Controls: Compliance requirements from frameworks (EU AI Act, ISO 42001, etc.)
    - Vendors: Third-party AI service providers
    - Models: AI/ML models in the organization's inventory
    """,
)

# Mount domain-specific sub-servers with namespace prefixes
mcp.mount(projects_server, prefix="projects")   # tools: projects_list, projects_get
mcp.mount(risks_server, prefix="risks")
mcp.mount(compliance_server, prefix="compliance")
mcp.mount(vendors_server, prefix="vendors")
mcp.mount(models_server, prefix="models")
mcp.mount(frameworks_server)   # resources: verifywise://frameworks/{name}/controls
mcp.mount(policies_server)     # resources: verifywise://policies/{id}
```

---

## Module Structure

### `config.py` — Settings

```python
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    base_url: str = Field("http://localhost:3000", description="VerifyWise API base URL")
    email: str = Field(..., description="VerifyWise admin email")
    password: str = Field(..., description="VerifyWise admin password")
    log_level: str = Field("INFO", description="Log level: DEBUG, INFO, WARNING, ERROR")
    transport: str = Field("stdio", description="MCP transport: stdio or http")
    http_port: int = Field(8080, description="HTTP transport port (if transport=http)")
    request_timeout: float = Field(30.0, description="HTTP request timeout in seconds")
    max_retries: int = Field(3, description="Max retries for failed API requests")

    class Config:
        env_prefix = "VERIFYWISE_"
        env_file = ".env"
        env_file_encoding = "utf-8"
```

Environment variables:
```
VERIFYWISE_BASE_URL=http://localhost:3000
VERIFYWISE_EMAIL=admin@example.com
VERIFYWISE_PASSWORD=changeme
VERIFYWISE_LOG_LEVEL=INFO
VERIFYWISE_TRANSPORT=stdio
```

---

### `auth.py` — JWT Token Management

VerifyWise uses short-lived access tokens (15 min) + HTTP-only refresh token cookies.

```
Flow:
1. POST /api/users/login  → access_token (15 min) + Set-Cookie: refreshToken
2. Use access_token in Authorization: Bearer header
3. On 401 → POST /api/users/refresh-token (with cookie) → new access_token
4. MCP server transparently handles refresh in the client layer
```

The `auth.py` module manages:
- Login and token storage (in memory, not on disk)
- Proactive token refresh (before expiry, not after 401)
- Thread-safe token access (asyncio.Lock)

---

### `client.py` — HTTP Client

Single `VerifyWiseClient` instance shared across all tools via FastMCP dependency injection:

```python
from fastmcp import Context
from fastmcp.dependencies import Depends

async def get_client(ctx: Context) -> VerifyWiseClient:
    """Dependency: returns the authenticated VerifyWise HTTP client."""
    client = await VerifyWiseClient.get_instance()
    await client.ensure_authenticated()
    return client

# Used in tools:
@mcp.tool
async def list_projects(client: VerifyWiseClient = Depends(get_client)) -> list[Project]:
    return await client.get("/api/projects")
```

Key design choices:
- **Singleton pattern** — one client instance, token shared across all tool calls
- **Proactive refresh** — refresh tokens before they expire (every ~13 minutes)
- **Retry with backoff** — automatic retry on 5xx errors and network failures
- **Timeout on all requests** — configurable `request_timeout` setting

---

### `tools/` — FastMCP Tool Modules

Each module defines a `FastMCP` sub-server with domain-specific tools:

```python
# tools/projects.py
from fastmcp import FastMCP
from verifywise_mcp.models import Project, ProjectCreate, ProjectList

projects_server = FastMCP(name="projects")

@projects_server.tool(annotations={"readOnlyHint": True})
async def list(
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> ProjectList:
    """List AI governance projects (Use Cases) in VerifyWise."""
    ...

@projects_server.tool(annotations={"readOnlyHint": True})
async def get(project_id: str) -> Project:
    """Get details of a specific project by ID."""
    ...

@projects_server.tool
async def create(name: str, description: str, framework: str) -> Project:
    """Create a new AI governance project/use case."""
    ...
```

---

### `resources/` — FastMCP Resource Modules

Resources provide read-only data via URI-based access:

```python
# resources/frameworks.py
from fastmcp import FastMCP
import json

frameworks_server = FastMCP(name="frameworks")

@frameworks_server.resource("verifywise://frameworks")
async def list_frameworks() -> str:
    """List all available compliance frameworks."""
    frameworks = ["eu-ai-act", "iso-42001", "iso-27001", "nist-ai-rmf"]
    return json.dumps({"frameworks": frameworks})

@frameworks_server.resource("verifywise://frameworks/{framework_id}/controls")
async def get_framework_controls(framework_id: str) -> str:
    """Get all compliance controls for a specific framework."""
    controls = await client.get(f"/api/{framework_id}/controls")
    return json.dumps(controls)

@frameworks_server.resource("verifywise://projects/{project_id}/assessment")
async def get_project_assessment(project_id: str) -> str:
    """Get the compliance assessment status for a project."""
    assessment = await client.get(f"/api/projects/{project_id}/assessment")
    return json.dumps(assessment)
```

---

## Data Models

Define Pydantic models for all VerifyWise entities:

```python
# src/verifywise_mcp/models.py
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ProjectStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    UNDER_REVIEW = "under_review"
    ARCHIVED = "archived"

class Project(BaseModel):
    id: str
    name: str
    description: str | None = None
    status: ProjectStatus
    risk_level: RiskLevel | None = None
    framework: str | None = None
    created_at: datetime
    updated_at: datetime

class Risk(BaseModel):
    id: str
    project_id: str
    title: str
    description: str
    severity: RiskLevel
    status: str
    owner: str | None = None
    due_date: datetime | None = None
    created_at: datetime

class ComplianceControl(BaseModel):
    id: str
    framework: str
    subclause: str
    title: str
    description: str
    status: str  # not_started, in_progress, complete, not_applicable
    evidence_count: int = 0
    last_reviewed: datetime | None = None
```

---

## Testing Architecture

### Test Pyramid

```
           ┌─────────────┐
           │    E2E      │  Few tests, slow, Rodney + Showboat
           │  (browser)  │  Tests: full stack integration
           └──────┬──────┘
         ┌────────▼────────┐
         │  Integration    │  Some tests, medium speed
         │  (Docker + API) │  Tests: real VerifyWise API calls
         └────────┬────────┘
        ┌─────────▼──────────┐
        │     Unit Tests     │  Many tests, fast, no network
        │  (mocked clients)  │  Tests: tool logic and validation
        └────────────────────┘
```

### Test Configuration

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
markers = [
    "integration: requires running VerifyWise Docker stack",
    "e2e: requires running VerifyWise + browser automation",
    "slow: marks tests as slow (deselect with '-m not slow')",
]
testpaths = ["tests"]
filterwarnings = ["error"]

[tool.coverage.run]
source = ["src/verifywise_mcp"]
omit = ["tests/*", "*/migrations/*"]

[tool.coverage.report]
fail_under = 80
show_missing = true
```

### Fixtures

```python
# tests/conftest.py
import pytest
from unittest.mock import AsyncMock
from verifywise_mcp.client import VerifyWiseClient

@pytest.fixture
def mock_client():
    """Mock VerifyWise API client for unit tests."""
    client = AsyncMock(spec=VerifyWiseClient)
    client.get.return_value = []
    client.post.return_value = {"id": "test-id"}
    return client

@pytest.fixture(scope="session")
async def live_client():
    """Real VerifyWise client for integration tests (requires Docker)."""
    client = await VerifyWiseClient.create(
        base_url="http://localhost:3000",
        email="admin@example.com",
        password="changeme",
    )
    yield client
    await client.close()
```

---

## Dependency Graph

```
server.py
├── config.py (pydantic-settings)
├── auth.py (httpx)
├── client.py (httpx, auth.py, config.py)
├── tools/
│   ├── projects.py (fastmcp, client.py, models.py)
│   ├── risks.py    (fastmcp, client.py, models.py)
│   ├── compliance.py (fastmcp, client.py, models.py)
│   ├── vendors.py  (fastmcp, client.py, models.py)
│   ├── models.py   (fastmcp, client.py, models.py)  [AI model inventory]
│   └── reports.py  (fastmcp, client.py)
└── resources/
    ├── frameworks.py (fastmcp, client.py)
    └── policies.py   (fastmcp, client.py)
```

**External dependencies:**
- `mcp[cli]` — MCP protocol + FastMCP framework
- `httpx` — Async HTTP client
- `pydantic` — Data validation and serialization
- `pydantic-settings` — Environment-based configuration

**Dev dependencies:**
- `pytest` + `pytest-asyncio` — Test runner
- `pytest-cov` — Coverage reporting
- `ruff` — Linting + formatting
- `pyright` — Type checking
- `respx` — HTTP mocking for unit tests (httpx-compatible)

---

## Security Considerations

### Credentials

- VerifyWise credentials stored in `.env` (never committed)
- JWT access tokens held in memory only (never written to disk)
- Refresh token sent as HTTP-only cookie automatically by httpx
- No credentials logged at any log level

### Input Validation

```python
from pydantic import Field, field_validator

@mcp.tool
async def get_project(
    project_id: str = Field(..., pattern=r"^[a-zA-Z0-9_-]{1,64}$")
) -> Project:
    """Get a project by ID. Validates ID format to prevent injection."""
    ...
```

- All tool inputs validated via Pydantic type annotations
- Project/resource IDs validated against expected patterns
- No SQL injection risk (uses VerifyWise REST API, not direct DB)
- API calls use parameterized URL construction (not string concatenation)

### Rate Limiting

The client implements exponential backoff retry for 429 responses:
```
Attempt 1: immediate
Attempt 2: wait 1s
Attempt 3: wait 2s
Max retries: 3 (configurable via VERIFYWISE_MAX_RETRIES)
```

---

## Deployment

### Local Development (Claude Desktop)

```json
// ~/Library/Application Support/Claude/claude_desktop_config.json
{
  "mcpServers": {
    "verifywise": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/verifywise-mcp",
        "run",
        "src/verifywise_mcp/server.py"
      ],
      "env": {
        "VERIFYWISE_BASE_URL": "http://localhost:3000",
        "VERIFYWISE_EMAIL": "admin@example.com",
        "VERIFYWISE_PASSWORD": "changeme"
      }
    }
  }
}
```

### Docker Compose (Integration Testing)

```yaml
# docker-compose.test.yml
services:
  # VerifyWise stack (from submodule)
  verifywise-db:
    image: postgres:15
    environment:
      POSTGRES_DB: verifywise
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres

  verifywise-server:
    build: verifywise/Servers
    environment:
      DATABASE_URL: postgresql://postgres:postgres@verifywise-db:5432/verifywise
    depends_on:
      verifywise-db:
        condition: service_healthy
    ports:
      - "3000:3000"

  verifywise-frontend:
    build: verifywise/Client
    ports:
      - "8080:8080"

  # MCP server for testing
  mcp-server:
    build: .
    environment:
      VERIFYWISE_BASE_URL: http://verifywise-server:3000
      VERIFYWISE_EMAIL: ${VERIFYWISE_EMAIL}
      VERIFYWISE_PASSWORD: ${VERIFYWISE_PASSWORD}
    depends_on:
      - verifywise-server
```

---

## ADR: Key Architectural Decisions

### ADR-001: FastMCP over raw MCP SDK

**Decision:** Use FastMCP (`mcp[cli]`) rather than the low-level MCP Python SDK.

**Rationale:**
- FastMCP provides decorator-based API (`@mcp.tool`, `@mcp.resource`) that auto-generates JSON schemas
- Handles all protocol lifecycle (initialization, capability negotiation, tool listing)
- Powers ~70% of all MCP servers — well-tested and widely used
- Supports modular composition via `mount()` — essential for our domain-driven design

---

### ADR-002: STDIO as Default Transport

**Decision:** Default to STDIO transport; add HTTP transport as an option later.

**Rationale:**
- STDIO is the standard for local MCP tools and Claude Desktop integration
- No network port management required for development
- Simpler security model (no authentication of the MCP connection itself)
- Can add `mcp.run(transport="streamable-http")` later without changing business logic

---

### ADR-003: Modular Sub-Server Composition

**Decision:** One sub-server per domain (projects, risks, compliance, vendors, models).

**Rationale:**
- Each module is independently testable
- Tool names get namespace prefixes (e.g., `projects_list`, `risks_create`) — prevents conflicts
- Sub-servers can be conditionally mounted based on VerifyWise capabilities
- Follows Single Responsibility Principle

---

### ADR-004: VerifyWise as Git Submodule

**Decision:** Include VerifyWise as a git submodule at `verifywise/`.

**Rationale:**
- Gives direct access to VerifyWise TypeScript source for API exploration
- Can run Docker Compose from the submodule for integration testing
- Pinned to a specific version — prevents surprise breakage from upstream changes
- Developers don't need to separately clone VerifyWise

---

### ADR-005: Docker Compose for Integration Testing

**Decision:** Use Docker Compose (from submodule) to spin up VerifyWise for integration and E2E tests.

**Rationale:**
- Fully isolated test environment
- Reproducible across CI/CD and developer machines
- No need for a shared test instance
- Headless Chrome (via Rodney) can connect to the containerized frontend

---

### ADR-006: Showboat + Rodney for Automated Verification

**Decision:** Use Simon Willison's Showboat and Rodney tools for agent-driven verification.

**Rationale:**
- Showboat creates executable markdown that proves features work
- Rodney enables browser automation without manual testing
- Both tools are designed for AI agent use — read `--help` as instruction set
- Verification documents are committed as living proof of correctness
- Prevents the common AI agent failure mode of "documenting what should happen" vs. "what does happen"

---

### ADR-007: Pydantic Models for All Data Shapes

**Decision:** Define Pydantic models for all VerifyWise API response types.

**Rationale:**
- FastMCP uses these for JSON schema generation (LLMs see typed tool outputs)
- Runtime validation catches VerifyWise API changes early
- Type checker (pyright) validates usage throughout the codebase
- Models serve as documentation of the VerifyWise data model
