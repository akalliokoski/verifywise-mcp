# SKILLS.md — VerifyWise MCP Server

> This file documents the skills, tools, and external CLI utilities available for use during autonomous development of this project.
> Claude Code should consult this file when choosing how to accomplish verification, testing, and documentation tasks.

---

## Available CLI Tools

### 1. Showboat — Executable Documentation

**Install:** `go install github.com/simonw/showboat@latest` (Go binary)
**Purpose:** Create executable markdown documents where each code block is run and its real output is embedded. Used as proof-of-work that features actually work.

**When to use:**
- After implementing a new MCP tool — demo its usage
- After getting VerifyWise running — document the working state
- As part of integration testing — create reproducible verification docs
- Before marking a TASKS.md item as complete — create a showboat demo

**Commands:**
```bash
# Start a new demo document
showboat init "Title of Demo"

# Add explanatory text
showboat note "This demonstrates that the list_projects tool works correctly"

# Run a command and embed its actual output
showboat exec "uv run pytest tests/unit/tools/test_projects.py -v"

# Run a command and embed output (with a label)
showboat exec "curl -s http://localhost:3000/api/health | jq ."

# Capture a screenshot and embed it
showboat image screenshots/verifywise-ui.png "VerifyWise UI after login"

# Remove the most recent entry (if it failed or is wrong)
showboat pop

# Re-execute all code blocks to verify outputs still match
showboat verify

# Extract the sequence of commands that built the document
showboat extract
```

**Output format:** Creates a markdown file (e.g., `demo.md`) with each `exec` block showing:
```markdown
## Command
\`\`\`bash
curl -s http://localhost:3000/api/health
\`\`\`
### Output
\`\`\`
{"status": "ok", "version": "1.0.0"}
\`\`\`
```

**Verification workflow:**
```bash
cd demos/
showboat init "MCP Server Integration Test"
showboat note "VerifyWise running via Docker Compose"
showboat exec "docker compose -f ../verifywise/docker-compose.yml ps"
showboat exec "curl -s http://localhost:3000/api/health | jq ."
showboat note "MCP server connects and lists projects"
showboat exec "uv run python scripts/test_tool.py list_projects"
showboat verify  # Re-run everything to confirm
```

**Remote streaming (optional):**
```bash
export SHOWBOAT_REMOTE_URL=http://localhost:9999
showboat exec "..."  # Streams updates to remote viewer in real-time
```

---

### 2. Rodney — Browser Automation for Agents

**Install:** `go install github.com/simonw/rodney@latest` (Go binary, v0.4.0+)
**Purpose:** CLI browser automation using Chrome DevTools Protocol. Designed specifically for AI coding agents — agents read `rodney --help` as their complete instruction set.

**When to use:**
- Verify VerifyWise UI loads correctly at http://localhost:8080
- Capture screenshots as visual evidence in Showboat demos
- Test that MCP tool calls produce visible UI changes
- Validate login flow, navigation, and data display
- E2E testing of the full stack (MCP server → VerifyWise API → UI)

**Commands:**
```bash
# Start Chrome (headless by default)
rodney start

# Navigate to a URL
rodney open http://localhost:8080

# Click on an element (CSS selector)
rodney click "button[type=submit]"
rodney click ".nav-link[href='/projects']"

# Type into an input
rodney type "input[name=email]" "admin@example.com"
rodney type "input[name=password]" "password123"

# Execute JavaScript and capture result
rodney js "document.title"
rodney js "document.querySelector('.project-count').textContent"

# Assert with JavaScript (exits 1 if assertion fails)
rodney js "document.title === 'VerifyWise' || 'FAIL: wrong title'"

# Capture screenshot (for embedding in showboat)
rodney screenshot screenshots/current-state.png

# Stop Chrome
rodney stop
```

**Typical verification workflow:**
```bash
rodney start
rodney open http://localhost:8080
rodney screenshot screenshots/01-homepage.png
# Check if login form is present
rodney js "!!document.querySelector('form[action*=login]') || 'no login form found'"
rodney click "input[name=email]"
rodney type "input[name=email]" "admin@example.com"
rodney type "input[name=password]" "changeme"
rodney click "button[type=submit]"
rodney screenshot screenshots/02-after-login.png
rodney js "window.location.pathname"  # Should be /dashboard
rodney stop
```

**Directory-scoped sessions (v0.4.0+):**
```bash
# Sessions are scoped to current directory by default
cd demos/
rodney start   # Creates session in demos/.rodney/
rodney stop
```

---

### 3. uv — Python Package Manager

**Purpose:** All Python dependency management. Never use pip directly.

**When to use:** Any time you need to install packages, run Python scripts, or manage the virtual environment.

```bash
# Sync environment to lockfile
uv sync

# Add a runtime dependency
uv add httpx pydantic "mcp[cli]"

# Add a dev dependency
uv add --dev pytest pytest-asyncio ruff pyright

# Run a Python script in the project's environment
uv run src/verifywise_mcp/server.py

# Run tests
uv run pytest
uv run pytest tests/unit/ -v
uv run pytest tests/integration/ -m integration -v
uv run pytest -x --tb=short  # Stop at first failure, short tracebacks

# Run tools without installing globally (ephemeral)
uvx ruff check .
uvx ruff format .
uvx pyright src/
```

---

### 4. ruff — Linting and Formatting

**Purpose:** Linting (replaces flake8, pylint) and formatting (replaces black, isort). Always run before committing.

```bash
# Check for lint issues
uvx ruff check .

# Auto-fix lint issues where possible
uvx ruff check . --fix

# Format code
uvx ruff format .

# Check formatting without making changes (CI mode)
uvx ruff format --check .

# Check a specific file
uvx ruff check src/verifywise_mcp/tools/projects.py
```

**All code must pass `ruff check` with zero errors before committing.**

---

### 5. pyright — Type Checking

**Purpose:** Static type checking for Python. Configured in `pyproject.toml`.

```bash
# Type-check the source directory
uv run pyright src/

# Type-check a specific file
uv run pyright src/verifywise_mcp/tools/projects.py
```

**All code must pass pyright with no errors before committing.**

---

### 6. pytest — Testing Framework

**Purpose:** Running all tests (unit, integration, e2e).

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Stop at first failure
uv run pytest -x

# Run specific test file
uv run pytest tests/unit/tools/test_projects.py

# Run specific test
uv run pytest tests/unit/tools/test_projects.py::test_list_projects

# Run by marker
uv run pytest -m "not integration"   # Skip integration tests
uv run pytest -m integration          # Only integration tests

# Show coverage
uv run pytest --cov=verifywise_mcp --cov-report=term-missing

# Run and capture output
uv run pytest -s
```

---

### 7. Local npm Stack — VerifyWise Without Docker

**Purpose:** Run the full VerifyWise stack using npm and system services (no Docker required).
This is the preferred mode for Claude Code web sessions and resource-constrained environments.

**Full docs:** See `RUNNING.md` for step-by-step instructions and troubleshooting.

```bash
# One-command startup (handles everything)
./scripts/start-verifywise-local.sh

# Skip reinstalling node_modules (faster if already installed)
./scripts/start-verifywise-local.sh --skip-install

# Stop backend and frontend processes
./scripts/stop-verifywise-local.sh

# Stop processes AND system services (postgres/redis)
./scripts/stop-verifywise-local.sh --services
```

**Default credentials once running:**
```
Backend:   http://localhost:3000
Frontend:  http://localhost:5173
Email:     verifywise@email.com
Password:  MyJH4rTm!@.45L0wm
```

**Seed database (idempotent — safe to re-run):**
```bash
node scripts/seed-verifywise.js
```

**Run full verification suite against live stack:**
```bash
# All checks: API, frontend, showboat, rodney browser, MCP deps
./scripts/verify-verifywise.sh

# Skip browser (for headless/CI environments)
./scripts/verify-verifywise.sh --skip-browser

# Skip MCP checks (only verify VerifyWise itself)
./scripts/verify-verifywise.sh --skip-mcp
```

**Individual checks:**
```bash
# 1. API login
TOKEN=$(curl -s -X POST http://localhost:3000/api/users/login \
  -H "Content-Type: application/json" \
  -d '{"email":"verifywise@email.com","password":"MyJH4rTm!@.45L0wm"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['token'])")
echo "Token: ${TOKEN:0:30}..."

# 2. Frontend reachable
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:5173/

# 3. Showboat proof-of-work
showboat verify demos/verification.md

# 4. Rodney browser smoke test
export PATH=$PATH:~/go/bin
rodney start --global
rodney --global open http://localhost:5173/
rodney --global title    # → VerifyWise - Open Source AI Governance Platform
rodney --global url      # → http://localhost:5173/login
rodney --global stop
```

**Known issues:**
- `resetDatabase.js` fails with FK error: use `node scripts/seed-verifywise.js` instead
- `@rollup/rollup-linux-x64-gnu` not found: `rm -rf verifywise/Clients/node_modules && npm install`
- `REDIS_HOST=redis` in .env: run `sed -i 's/REDIS_HOST=redis/REDIS_HOST=localhost/' verifywise/Servers/.env`

---

### 8. Docker Compose — VerifyWise Infrastructure

**Purpose:** Running the full VerifyWise stack for integration and E2E testing.

```bash
# Start VerifyWise (from repo root)
docker compose -f verifywise/docker-compose.yml up -d

# Check status
docker compose -f verifywise/docker-compose.yml ps

# View logs
docker compose -f verifywise/docker-compose.yml logs -f server
docker compose -f verifywise/docker-compose.yml logs -f frontend

# Wait until healthy (use scripts/wait-for-verifywise.sh)
./scripts/wait-for-verifywise.sh

# Stop and clean up
docker compose -f verifywise/docker-compose.yml down
docker compose -f verifywise/docker-compose.yml down -v  # Also remove volumes (fresh start)
```

**Health check endpoints:**
```bash
curl http://localhost:3000/api/health    # Backend API
curl http://localhost:8080              # Frontend
curl http://localhost:8000/health       # Python EvalServer
```

---

### 8. Git Submodule — VerifyWise Codebase

**Purpose:** The VerifyWise source code is a git submodule at `verifywise/`. This provides access to the actual codebase for understanding the API.

```bash
# Initialize submodule (first time after clone)
git submodule update --init --recursive

# Update to latest VerifyWise version
git submodule update --remote verifywise

# Check submodule status
git submodule status

# Read VerifyWise API routes
ls verifywise/Servers/src/routes/
cat verifywise/Servers/src/routes/project.route.ts

# Read VerifyWise models/schemas
ls verifywise/Servers/src/models/
```

---

## Development Patterns

### Pattern 1: Test-Driven Feature Development

```bash
# 1. RED — Write failing test
cat > tests/unit/tools/test_new_tool.py << 'EOF'
import pytest
from verifywise_mcp.tools.new_tool import new_tool

@pytest.mark.asyncio
async def test_new_tool_basic():
    result = await new_tool(param="value")
    assert result is not None
EOF

uv run pytest tests/unit/tools/test_new_tool.py -x
# Confirm: FAILED (ImportError or similar)

# 2. GREEN — Implement minimally
# ... write implementation ...
uv run pytest tests/unit/tools/test_new_tool.py -x
# Confirm: PASSED

# 3. REFACTOR — Clean up
# ... improve implementation ...
uv run pytest tests/ -x
# Confirm: all tests still pass

# 4. QUALITY CHECKS
uvx ruff check . --fix
uvx ruff format .
uv run pyright src/

# 5. DOCUMENT
cd demos/
showboat init "New Tool: new_tool"
showboat exec "uv run pytest tests/unit/tools/test_new_tool.py -v"
showboat verify

# 6. COMMIT
git add tests/unit/tools/test_new_tool.py src/verifywise_mcp/tools/new_tool.py
git commit -m "feat: add new_tool with basic param support"
```

---

### Pattern 2: VerifyWise API Exploration

Before implementing a tool, explore the VerifyWise API to understand the endpoints:

```bash
# Explore the route files in the submodule
ls verifywise/Servers/src/routes/

# Read a specific route to understand its endpoints
cat verifywise/Servers/src/routes/project.route.ts

# Read the controller to understand request/response shapes
cat verifywise/Servers/src/controllers/project.controller.ts

# Test with curl once VerifyWise is running
# 1. Get auth token
TOKEN=$(curl -s -X POST http://localhost:3000/api/users/login \
  -H "Content-Type: application/json" \
  -d '{"email":"verifywise@email.com","password":"MyJH4rTm!@.45L0wm"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['token'])")

# 2. Call an endpoint
curl -s http://localhost:3000/api/projects \
  -H "Authorization: Bearer $TOKEN" | jq .
```

---

### Pattern 3: UI Verification After MCP Tool Call

```bash
# Start browser
export PATH=$PATH:~/go/bin
rodney start --global

# Login to VerifyWise (local npm: port 5173 / Docker: port 8080)
rodney --global open http://localhost:5173/
rodney --global wait "input[type=email]"
rodney --global input "input[type=email]" "verifywise@email.com"
rodney --global input "input[type=password]" 'MyJH4rTm!@.45L0wm'
rodney --global click "button[type=submit]"
rodney --global sleep 2

# Before tool call — capture state
rodney --global screenshot /tmp/before-create-risk.png
rodney --global js "document.querySelectorAll('.risk-item').length"  # Count risks

# Run MCP tool (create a risk via the server)
uv run python scripts/call_tool.py create_risk --project-id "proj-123" --title "Test Risk"

# After tool call — verify UI updated
rodney --global open http://localhost:5173/projects/proj-123/risks
rodney --global screenshot /tmp/after-create-risk.png
rodney --global js "document.querySelectorAll('.risk-item').length"  # Should be +1

# Stop browser
rodney --global stop
```

---

## MCP Tool Annotations Reference

Use these annotations on tools to help LLMs understand behavior:

| Annotation | Type | Meaning |
|-----------|------|---------|
| `readOnlyHint` | bool | Tool does not modify state |
| `destructiveHint` | bool | Tool may delete/overwrite data |
| `idempotentHint` | bool | Multiple identical calls have same effect as one |
| `openWorldHint` | bool | Tool interacts with external systems beyond VerifyWise |

```python
# Read-only tool
@mcp.tool(annotations={"readOnlyHint": True, "idempotentHint": True})
async def list_projects(...): ...

# Destructive tool (needs confirmation)
@mcp.tool(annotations={"destructiveHint": True})
async def delete_project(project_id: str): ...

# External integration tool
@mcp.tool(annotations={"openWorldHint": True})
async def send_compliance_report_email(...): ...
```

---

## Error Handling Reference

```python
from fastmcp.exceptions import ToolError

# Use ToolError for all user-facing errors
async def my_tool(param: str) -> dict:
    if not param:
        raise ToolError("param is required and cannot be empty")

    try:
        result = await verifywise_client.get(f"/api/resource/{param}")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise ToolError(f"Resource '{param}' not found in VerifyWise")
        if e.response.status_code == 403:
            raise ToolError("Access denied. Check your VerifyWise credentials.")
        raise ToolError(f"VerifyWise API error: {e.response.status_code}")
    except httpx.ConnectError:
        raise ToolError(
            f"Cannot connect to VerifyWise at {settings.base_url}. "
            "Is the server running? Try: docker compose -f verifywise/docker-compose.yml up -d"
        )

    return result
```
