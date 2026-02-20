# Research Report: VerifyWise MCP Server

> Generated: 2026-02-20
> Branch: `claude/research-mcp-server-P33p4`

---

## 1. VerifyWise AI Governance Platform

### Overview

**Repository:** [github.com/bluewave-labs/verifywise](https://github.com/bluewave-labs/verifywise)

VerifyWise is a source-available AI governance and LLM evaluation platform designed to help organizations manage AI responsibly. It supports compliance with:
- EU AI Act
- ISO 42001 (AI Management Systems)
- ISO 27001 (Information Security)
- NIST AI Risk Management Framework (RMF)

**License:** BSL 1.1 (Business Source License) — self-hostable, enterprise licensing available.

---

### Architecture (Three-Tier)

```
┌─────────────────────────────────────────────────────────┐
│                   Browser / Client                      │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│         Frontend: React.js + Vite                       │
│         Dev: port 5173 | Prod: port 8080                │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│         Backend: Node.js Express API                    │
│         Port: 3000                                      │
│         Pattern: Controller → Utils → Model             │
└──────────┬───────────────────────────┬──────────────────┘
           │                           │
┌──────────▼──────────┐   ┌────────────▼────────────────┐
│  PostgreSQL (5432)  │   │  Python EvalServer (8000)   │
│  Redis cache (6379) │   │  LLM evaluation & Arena     │
└─────────────────────┘   └─────────────────────────────┘
```

**Multi-tenancy:** Schema-based — each organization gets its own PostgreSQL schema. The `authenticateJWT` middleware extracts `tenantId` from JWT, and all queries are scoped per tenant.

---

### Authentication

- JWT access tokens (15-minute expiry) + refresh tokens (HTTP-only cookies)
- Auto-refresh via Axios interceptors
- Key endpoints:
  - `POST /api/users/login` — get initial token pair
  - `POST /api/users/refresh-token` — refresh expired access token
- Roles: Admin, Reviewer, Editor, Auditor

---

### Main API Routes

| Route Prefix           | Domain                              |
|------------------------|-------------------------------------|
| `/api/users`           | Authentication, profile management  |
| `/api/projects`        | Use case / project management       |
| `/api/vendors`         | Vendor risk tracking                |
| `/api/projectRisks`    | Risk management                     |
| `/api/file-manager`    | Evidence and document storage       |
| `/api/eu-ai-act`       | EU AI Act compliance framework      |
| `/api/iso-42001`       | ISO 42001 framework                 |
| `/api/iso-27001`       | ISO 27001 framework                 |
| `/api/nist-ai-rmf`     | NIST AI RMF framework               |
| `/api/policies`        | Internal AI governance policies     |
| `/api/training`        | Training records                    |
| `/api/modelInventory`  | AI model inventory tracking         |
| `/api/tasks`           | Global workflow task management     |
| `/api/automations`     | Automation workflows                |
| `/api/approval-workflows` | Approval pipeline               |

---

### Core Data Entities

| Entity | Description |
|--------|-------------|
| **Projects/Use Cases** | AI applications requiring governance assessment (central entity) |
| **Vendors** | Third-party AI providers with risk scores |
| **Risks** | Cross-linked to projects, vendors, models; framework-mapped |
| **Controls/Assessments** | Compliance evaluations against regulatory standards |
| **Models** | AI/LLM inventory: deployed and external systems |
| **Evidence/Files** | Supporting documentation |
| **Policies** | Internal AI governance policies with templates |
| **Incidents** | AI-related incident logging and management |
| **Tasks** | Global workflow management |

---

### Key Features

- Executive and operating dashboards
- Vendor and AI model inventory management
- Use case risk assessment and tracking
- Complete LLM evaluation suite with Arena functionality
- AI incident management
- Evidence management with folder organization
- Policy creation tools
- Shadow AI detection
- 15+ integrated plugins with automation support
- PDF/DOCX report generation
- AI-generated answers for compliance and assessment questions
- 24+ AI and data governance framework templates

---

### Docker Deployment

VerifyWise ships with Docker Compose configuration. Key containers:
- `frontend` — React/Vite app
- `server` — Node.js Express backend
- `db` — PostgreSQL 15
- `redis` — Redis 7
- `evalserver` — Python 3.12 evaluation service

Quick start:
```bash
git clone https://github.com/bluewave-labs/verifywise
cd verifywise
docker compose up -d
# Access at http://localhost:8080
```

---

## 2. FastMCP Python Library

### Overview

**Website:** [gofastmcp.com](https://gofastmcp.com)
**GitHub:** Incorporated into the official MCP Python SDK
**Status:** Powers ~70% of all MCP servers across all languages

FastMCP is the standard Python framework for building MCP (Model Context Protocol) servers. It handles schema generation, validation, and protocol lifecycle — letting developers focus on business logic.

---

### The Three Primitives

| Primitive | Controlled By | Has Side Effects? | Purpose |
|-----------|--------------|-------------------|---------|
| **Tools** | Model (LLM) | Yes | Execute actions, call APIs, mutate state |
| **Resources** | Application | No | Read-only data access (files, DB, config) |
| **Prompts** | User | No | Reusable message templates |

---

### Tools — Model-Controlled Actions

```python
from fastmcp import FastMCP

mcp = FastMCP(name="verifywise-mcp")

@mcp.tool
async def list_projects(
    status: str | None = None,
    limit: int = 20
) -> list[dict]:
    """List AI governance projects/use cases in VerifyWise.

    Args:
        status: Filter by status (active, archived, draft)
        limit: Maximum number of results (1-100)

    Returns:
        List of project objects with id, name, status, risk_level
    """
    # implementation
    ...
```

**Key tool design rules:**
1. Explicit type annotations — drives schema generation
2. Clear docstrings — becomes the LLM's tool description
3. Mark read-only ops: `@mcp.tool(annotations={"readOnlyHint": True})`
4. Use `ToolError` for user-visible failures (not exceptions)
5. Set `timeout` for all I/O operations
6. Return `Pydantic` models or `dataclasses` for structured output
7. Never use `*args` or `**kwargs` — FastMCP needs complete schemas
8. `async def` for network I/O, `def` for CPU-bound work

---

### Resources — Application-Driven Data

```python
@mcp.resource("verifywise://projects/{project_id}/compliance-status")
async def get_compliance_status(project_id: str) -> str:
    """Read-only compliance status for a project."""
    data = await fetch_compliance(project_id)
    return json.dumps(data)  # Always serialize complex types

@mcp.resource("verifywise://frameworks/eu-ai-act/template")
async def eu_ai_act_template() -> str:
    """EU AI Act compliance framework template."""
    return load_template("eu-ai-act")
```

---

### Prompts — Reusable Templates

```python
@mcp.prompt
def risk_assessment_prompt(project_name: str, framework: str) -> str:
    """Generate a risk assessment prompt for a given project and framework."""
    return f"""
    You are an AI governance expert conducting a risk assessment.
    Project: {project_name}
    Compliance Framework: {framework}

    Please assess the following risk categories...
    """
```

---

### Project Structure (Recommended)

```
verifywise-mcp/
├── src/
│   └── verifywise_mcp/
│       ├── __init__.py
│       ├── server.py           # FastMCP server entry point
│       ├── auth.py             # JWT auth and token management
│       ├── client.py           # HTTP client for VerifyWise API
│       ├── config.py           # Pydantic settings
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── projects.py     # Project/use case tools
│       │   ├── risks.py        # Risk management tools
│       │   ├── compliance.py   # Framework compliance tools
│       │   ├── vendors.py      # Vendor management tools
│       │   ├── models.py       # AI model inventory tools
│       │   └── reports.py      # Report generation tools
│       └── resources/
│           ├── __init__.py
│           ├── frameworks.py   # Compliance framework templates
│           └── policies.py     # Policy document resources
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── verifywise/                 # Git submodule
├── pyproject.toml
├── uv.lock
├── .env.example
├── CLAUDE.md
├── SKILLS.md
├── ARCHITECTURE.md
├── TASKS.md
└── docker-compose.test.yml
```

---

### Composition Pattern (Modular Architecture)

```python
# server.py — main entry point
from fastmcp import FastMCP
from verifywise_mcp.tools.projects import projects_mcp
from verifywise_mcp.tools.risks import risks_mcp
from verifywise_mcp.tools.compliance import compliance_mcp

mcp = FastMCP(name="verifywise-mcp")
mcp.mount(projects_mcp, prefix="projects")
mcp.mount(risks_mcp, prefix="risks")
mcp.mount(compliance_mcp, prefix="compliance")

def main():
    mcp.run(transport="stdio")
```

---

## 3. Simon Willison's Tools: Showboat & Rodney

### Showboat

**GitHub:** [github.com/simonw/showboat](https://github.com/simonw/showboat)
**Purpose:** CLI tool for AI coding agents to create **executable markdown documents** — readable documentation that also serves as verifiable proof of work.

**Key insight:** Each code execution is documented alongside its actual output, creating reproducible documentation. The `verify` command re-runs all code blocks to confirm outputs still match, preventing agents from falsifying results.

**Commands:**
| Command | Description |
|---------|-------------|
| `showboat init <title>` | Create a new demo document |
| `showboat note <text>` | Add explanatory commentary |
| `showboat exec <command>` | Run command, embed actual output |
| `showboat image <file> <alt>` | Capture/embed image files |
| `showboat pop` | Remove most recent entry |
| `showboat verify` | Re-execute all code blocks, confirm outputs match |
| `showboat extract` | Output the sequence of commands that built the document |

**Environment variable:**
```bash
export SHOWBOAT_REMOTE_URL=http://...  # Enable real-time streaming to remote viewers
```

**Use in this project:** Use Showboat to document that VerifyWise starts correctly, that the MCP server connects, and that tools produce correct outputs. Committed `.showboat.md` files serve as living documentation.

---

### Rodney

**GitHub:** [github.com/simonw/rodney](https://github.com/simonw/rodney)
**Purpose:** CLI browser automation tool built specifically for AI coding agents. Wraps the **Rod Go library** (Chrome DevTools Protocol) into a CLI that agents can use by reading `rodney --help`.

**Commands:**
| Command | Description |
|---------|-------------|
| `rodney start` | Start Chrome browser instance |
| `rodney stop` | Stop Chrome instance |
| `rodney open <url>` | Navigate to URL |
| `rodney click <selector>` | Click page element |
| `rodney js <script>` | Execute JavaScript, capture result |
| `rodney screenshot <file>` | Capture visual evidence |

**Version:** v0.4.0 (Feb 2026) adds: Windows support, JavaScript assertion engine, directory-scoped sessions.

**Use in this project:** Use Rodney to:
1. Navigate to VerifyWise UI (`http://localhost:8080`)
2. Verify the app loads correctly
3. Capture screenshots as evidence
4. Test UI flows after MCP operations
5. Validate that MCP tool calls produce visible UI changes

---

### shot-scraper

**GitHub:** [github.com/simonw/shot-scraper](https://github.com/simonw/shot-scraper)
**Purpose:** CLI tool built on Playwright for automated screenshot capture.

**Use in this project:** Simpler screenshot-only tasks; use as fallback if Rodney is not available.

---

## 4. Python Tooling: uv + ruff

### uv Package Manager

**Docs:** [docs.astral.sh/uv](https://docs.astral.sh/uv)

uv is a Rust-based Python package manager that is **10-100x faster** than pip. It consolidates: pip, pip-tools, pipx, poetry, pyenv, twine, virtualenv.

**Key commands:**
```bash
# Project setup
uv init verifywise-mcp
uv add "mcp[cli]" httpx pydantic pydantic-settings
uv add --dev pytest pytest-asyncio ruff pyright

# Running
uv run src/verifywise_mcp/server.py
uv run pytest

# Tools
uvx ruff check .
uvx ruff format .
```

**Lockfile:** Always commit `uv.lock` — cross-platform reproducible builds.

**MCP server Claude Desktop config:**
```json
{
  "mcpServers": {
    "verifywise": {
      "command": "uv",
      "args": ["--directory", "/path/to/verifywise-mcp", "run", "src/verifywise_mcp/server.py"]
    }
  }
}
```

---

### ruff

**Docs:** [docs.astral.sh/ruff](https://docs.astral.sh/ruff)

Rust-based Python linter and formatter — replaces flake8, isort, black. Configured in `pyproject.toml`:

```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "B",    # flake8-bugbear
    "UP",   # pyupgrade
    "ANN",  # flake8-annotations
    "ASYNC", # flake8-async
]
ignore = ["ANN101", "ANN102"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

---

## 5. MCP Best Practices

### Transport Selection

| Transport | Use Case |
|-----------|----------|
| **STDIO** | Local tools, IDE extensions, CLI assistants — fast, secure, no network |
| **Streamable HTTP** | Networked, horizontally scalable, incremental results |
| SSE | **Deprecated** as of June 2025 spec |

### Critical Rules

1. **Never write to stdout** in STDIO servers — corrupts JSON-RPC protocol
   ```python
   # BAD — breaks the server
   print("Processing...")

   # GOOD
   import sys, logging
   logging.basicConfig(stream=sys.stderr)
   logger = logging.getLogger(__name__)
   logger.info("Processing...")
   ```

2. **Validate all inputs** — treat LLM-provided data as untrusted
3. **Idempotent tools** — safe for agent retries
4. **Rate limiting** — implement for all external API calls
5. **Cursor-based pagination** — for list operations
6. **ToolError for business failures**, exceptions only for programming errors

---

## 6. Key Integration Points for VerifyWise MCP Server

Based on the research, the highest-value MCP tools to implement (in priority order):

### Phase 1: Core Read Operations (Tools with `readOnlyHint`)
1. `list_projects` — List all AI governance projects/use cases
2. `get_project` — Get detailed project info including risk level
3. `get_compliance_status` — Get framework compliance status for a project
4. `list_risks` — List risks for a project with severity/status
5. `list_vendors` — List vendors with risk scores

### Phase 2: Compliance Framework Resources
6. Resource: `verifywise://frameworks/{framework}/controls` — All controls for a framework
7. Resource: `verifywise://projects/{id}/assessment` — Assessment status per control
8. Tool: `update_control_status` — Mark a compliance control as complete/in-progress

### Phase 3: Active Governance Actions
9. `create_risk` — Log a new risk finding
10. `create_incident` — Log an AI governance incident
11. `generate_report` — Generate PDF/DOCX compliance report
12. `search_policies` — Search internal governance policies
13. `add_evidence` — Upload supporting documentation

### Phase 4: LLM Evaluation (Python EvalServer)
14. `run_evaluation` — Submit LLM for evaluation via EvalServer
15. `get_evaluation_results` — Fetch evaluation results/scores
16. `list_model_inventory` — List all tracked AI models

---

## 7. Project Verification Strategy

Using Showboat + Rodney for automated verification:

```bash
# Verify VerifyWise is running
showboat init "VerifyWise MCP Server Integration Demo"
showboat exec "docker compose ps"
showboat exec "curl -s http://localhost:3000/api/health | jq ."
rodney start
rodney open "http://localhost:8080"
rodney screenshot "verifywise-login.png"
showboat image "verifywise-login.png" "VerifyWise login page loaded"

# Verify MCP server tools work
showboat exec "echo '{\"tool\": \"list_projects\"}' | uv run src/verifywise_mcp/server.py"
showboat verify
```

---

## Sources

- [bluewave-labs/verifywise on GitHub](https://github.com/bluewave-labs/verifywise)
- [DeepWiki: bluewave-labs/verifywise](https://deepwiki.com/bluewave-labs/verifywise)
- [FastMCP Documentation](https://gofastmcp.com/)
- [FastMCP Tools](https://gofastmcp.com/servers/tools)
- [FastMCP Resources](https://gofastmcp.com/servers/resources)
- [FastMCP Composition Patterns](https://gofastmcp.com/patterns/composition)
- [Simon Willison — Introducing Showboat and Rodney](https://simonwillison.net/2026/Feb/10/showboat-and-rodney/)
- [github.com/simonw/showboat](https://github.com/simonw/showboat)
- [github.com/simonw/rodney](https://github.com/simonw/rodney)
- [uv Documentation](https://docs.astral.sh/uv/)
- [ruff Documentation](https://docs.astral.sh/ruff/)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/docs)
- [MCP Best Practices](https://modelcontextprotocol.info/docs/best-practices/)
- [15 Best Practices for Building MCP Servers — The New Stack](https://thenewstack.io/15-best-practices-for-building-mcp-servers-in-production/)
