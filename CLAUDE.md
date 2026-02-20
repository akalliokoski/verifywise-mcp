# CLAUDE.md — VerifyWise MCP Server

> This file guides Claude Code when working in this repository.
> Read this file completely before starting any task.

---

## Project Overview

This project implements a **Model Context Protocol (MCP) server** for [VerifyWise](https://github.com/bluewave-labs/verifywise), an open-source AI governance platform. The MCP server enables AI assistants (Claude, etc.) to interact with VerifyWise programmatically — querying compliance status, managing risks, tracking vendors, and generating governance reports.

**Stack:**
- **Language:** Python 3.12+
- **MCP Framework:** FastMCP (via `mcp[cli]` package)
- **Package Manager:** uv (never use pip directly)
- **Linter/Formatter:** ruff
- **Type Checker:** pyright
- **Testing:** pytest + pytest-asyncio
- **Browser Automation:** Rodney (CLI) + Showboat (documentation)
- **VerifyWise:** Runs as Docker Compose via git submodule

---

## Repo Structure

```
verifywise-mcp/
├── src/
│   └── verifywise_mcp/
│       ├── __init__.py
│       ├── server.py           # FastMCP entry point — mounts all sub-servers
│       ├── auth.py             # JWT token management (login, refresh)
│       ├── client.py           # Async HTTP client for VerifyWise REST API
│       ├── config.py           # Pydantic settings (env vars)
│       ├── tools/              # FastMCP tools (LLM-controlled, have side effects)
│       │   ├── projects.py     # Project / use case management
│       │   ├── risks.py        # Risk creation and management
│       │   ├── compliance.py   # Framework compliance controls
│       │   ├── vendors.py      # Vendor risk tracking
│       │   ├── models.py       # AI model inventory
│       │   └── reports.py      # Report generation
│       └── resources/          # FastMCP resources (app-driven, read-only)
│           ├── frameworks.py   # Compliance framework templates
│           └── policies.py     # Internal governance policies
├── tests/
│   ├── unit/                   # Pure unit tests (no network)
│   ├── integration/            # Tests against VerifyWise API (Docker required)
│   └── e2e/                    # Browser-based end-to-end tests (Rodney)
├── demos/                      # Showboat executable markdown demos
├── verifywise/                 # Git submodule: bluewave-labs/verifywise
├── pyproject.toml
├── uv.lock                     # ALWAYS commit this file
├── .env.example                # Template — never commit .env
├── docker-compose.test.yml     # Spins up VerifyWise for integration tests
├── CLAUDE.md                   # This file
├── SKILLS.md                   # Skills and tool usage guide
├── ARCHITECTURE.md             # System design and decisions
├── RESEARCH.md                 # Background research
└── TASKS.md                    # Implementation roadmap (current task list)
```

---

## Development Workflow

### Always Use uv

```bash
# Install dependencies
uv sync

# Add a package
uv add httpx

# Add a dev dependency
uv add --dev pytest-asyncio

# Run the MCP server
uv run src/verifywise_mcp/server.py

# Run tests
uv run pytest

# Lint
uvx ruff check .
uvx ruff format .

# Type check
uv run pyright src/
```

**Never** use `pip install`, `python -m pip`, or `poetry`. Always `uv`.

---

### TDD: Red → Green → Refactor

Follow strict TDD for all new features:

1. **RED:** Write a failing test first
   ```bash
   uv run pytest tests/unit/tools/test_projects.py::test_list_projects -x
   # Confirm it fails (no implementation yet)
   ```

2. **GREEN:** Write the minimal implementation to pass
   ```bash
   uv run pytest tests/unit/tools/test_projects.py::test_list_projects -x
   # Confirm it passes
   ```

3. **REFACTOR:** Clean up while keeping tests green
   ```bash
   uv run pytest tests/ -x
   # Confirm all tests still pass
   ```

4. **Document:** Use Showboat to create a runnable proof of the feature working

---

### Running VerifyWise Locally

VerifyWise runs as a Docker Compose stack from the git submodule:

```bash
# Initialize submodule (first time)
git submodule update --init --recursive

# Start VerifyWise
docker compose -f verifywise/docker-compose.yml up -d

# Wait for health
./scripts/wait-for-verifywise.sh

# Stop when done
docker compose -f verifywise/docker-compose.yml down
```

VerifyWise endpoints once running:
- Frontend: http://localhost:8080
- Backend API: http://localhost:3000
- EvalServer: http://localhost:8000

---

### Environment Configuration

Copy `.env.example` to `.env` and fill in values:

```bash
# VerifyWise connection
VERIFYWISE_BASE_URL=http://localhost:3000
VERIFYWISE_EMAIL=admin@example.com
VERIFYWISE_PASSWORD=your-password

# MCP server settings
MCP_LOG_LEVEL=INFO
MCP_TRANSPORT=stdio
```

**Never commit `.env`** — it's gitignored.

---

## Code Standards

### Python Style

- **Python 3.12+** features: use `str | None` (not `Optional[str]`), `list[str]` (not `List[str]`)
- **Type annotations:** All function signatures must be fully typed
- **Docstrings:** All public functions/classes require docstrings (they become LLM descriptions)
- **Line length:** 100 characters (configured in `pyproject.toml`)
- **Imports:** isort-style (ruff handles this)

### FastMCP Tool Guidelines

```python
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

@mcp.tool(
    annotations={"readOnlyHint": True}  # for read-only tools
)
async def list_projects(
    status: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """List AI governance projects in VerifyWise.

    Args:
        status: Filter by status. One of: active, archived, draft
        limit: Maximum number of results to return (1-100)

    Returns:
        List of project objects with id, name, status, and risk_level

    Raises:
        ToolError: If the VerifyWise API is unreachable or returns an error
    """
    if not 1 <= limit <= 100:
        raise ToolError("limit must be between 1 and 100")
    # ... implementation
```

**Rules:**
- Use `async def` for all tools that make HTTP requests
- Use `ToolError` for expected failures (API down, not found, validation failed)
- Use `raise Exception` only for programming errors (bugs)
- Never use `*args` or `**kwargs` — FastMCP requires complete parameter schemas
- Always document the `Returns:` and `Raises:` sections in docstrings

### Logging

```python
import logging
import sys

# Configure at module level in server.py — always write to stderr
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,  # CRITICAL: never stdout for STDIO MCP servers
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)
```

**Never use `print()`** in the MCP server — it corrupts the STDIO JSON-RPC protocol.

---

## Testing Conventions

### Unit Tests

```python
# tests/unit/tools/test_projects.py
import pytest
from unittest.mock import AsyncMock, patch
from verifywise_mcp.tools.projects import list_projects

@pytest.mark.asyncio
async def test_list_projects_returns_list():
    """list_projects should return a list of project dicts."""
    mock_response = [{"id": "1", "name": "Test Project", "status": "active"}]
    with patch("verifywise_mcp.client.get", return_value=mock_response):
        result = await list_projects()
    assert isinstance(result, list)
    assert result[0]["name"] == "Test Project"

@pytest.mark.asyncio
async def test_list_projects_validates_limit():
    """list_projects should raise ToolError for invalid limit."""
    from fastmcp.exceptions import ToolError
    with pytest.raises(ToolError, match="limit must be between"):
        await list_projects(limit=0)
```

### Integration Tests

Integration tests require VerifyWise to be running:

```python
# tests/integration/test_projects_api.py
import pytest

pytestmark = pytest.mark.integration  # Skip if not in integration mode

@pytest.mark.asyncio
async def test_list_projects_live(verifywise_client):
    """Verify list_projects works against real VerifyWise API."""
    projects = await list_projects()
    assert isinstance(projects, list)
```

Run integration tests:
```bash
uv run pytest tests/integration/ -m integration
```

### E2E Tests with Rodney

```bash
# tests/e2e/test_ui_verification.sh
rodney start
rodney open "http://localhost:8080"
rodney screenshot "tests/e2e/screenshots/homepage.png"
rodney js "document.title"  # Should return VerifyWise page title
rodney stop
```

---

## Verification with Showboat

After implementing a feature, create a Showboat demo:

```bash
cd demos/
showboat init "Feature: List Projects Tool"
showboat note "Starting VerifyWise and testing the list_projects MCP tool"
showboat exec "docker compose -f ../verifywise/docker-compose.yml ps"
showboat exec "echo 'Testing MCP tool...' && uv run python -c 'import asyncio; from verifywise_mcp.tools.projects import list_projects; print(asyncio.run(list_projects()))'"
showboat verify  # Re-run all blocks to confirm outputs match
```

Commit the `.showboat.md` file as proof that the feature works.

---

## Git Workflow

- **Branch:** `claude/research-mcp-server-P33p4` (current)
- **Commit format:** `feat: add list_projects tool with pagination support`
- **Prefix conventions:**
  - `feat:` — new feature
  - `fix:` — bug fix
  - `test:` — adding/updating tests
  - `docs:` — documentation only
  - `refactor:` — code change with no feature/fix
  - `chore:` — tooling, deps, CI

```bash
git add -p                     # Stage interactively (preferred over git add .)
git commit -m "feat: ..."
git push -u origin claude/research-mcp-server-P33p4
```

---

## Autonomy Guidelines

When working autonomously on tasks from TASKS.md:

1. **Read TASKS.md first** — find the next `[ ]` task, understand its scope
2. **Check ARCHITECTURE.md** — understand design decisions before coding
3. **Write the test first** (TDD: RED step)
4. **Implement minimally** (GREEN step)
5. **Refactor** (REFACTOR step)
6. **Run full test suite:** `uv run pytest tests/ -x`
7. **Lint:** `uvx ruff check . && uvx ruff format --check .`
8. **Type check:** `uv run pyright src/`
9. **Create Showboat demo** if it's a user-visible feature
10. **Commit:** descriptive message with feat/fix/test prefix
11. **Update TASKS.md:** check off completed task, add any discovered sub-tasks
12. **Push:** `git push -u origin claude/research-mcp-server-P33p4`

### When to Stop and Ask

- The task requires credentials or secrets not in `.env.example`
- A test is failing after 3 different approaches
- There is ambiguity about which API endpoint to use
- A design decision affects multiple modules

### Key Constraint

This is a **research/planning phase** — no production VerifyWise credentials exist yet. Integration tests should be skipped by default and only run in Docker CI context.

---

## Quick Reference

| Task | Command |
|------|---------|
| Install deps | `uv sync` |
| Add package | `uv add <package>` |
| Run server | `uv run src/verifywise_mcp/server.py` |
| Run all tests | `uv run pytest` |
| Run unit tests only | `uv run pytest tests/unit/` |
| Run integration tests | `uv run pytest tests/integration/ -m integration` |
| Lint | `uvx ruff check .` |
| Format | `uvx ruff format .` |
| Type check | `uv run pyright src/` |
| Start VerifyWise | `docker compose -f verifywise/docker-compose.yml up -d` |
| Stop VerifyWise | `docker compose -f verifywise/docker-compose.yml down` |
| Browser automation | `rodney start && rodney open http://localhost:8080` |
| Create demo | `showboat init "Demo Title"` |
| Verify demo | `showboat verify` |
