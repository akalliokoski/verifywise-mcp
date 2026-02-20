# TASKS.md — VerifyWise MCP Server Implementation Roadmap

> This is the authoritative task list for autonomous implementation.
> Claude Code should work through tasks in order, checking them off as completed.
> Each task references relevant files and includes verification steps.

**Status Legend:**
- `[ ]` — Not started
- `[>]` — In progress (only one at a time)
- `[x]` — Completed
- `[!]` — Blocked (see note)
- `[-]` — Skipped / not applicable

---

## Phase 0: Repository Setup

### 0.1 Project Scaffolding

- [x] Research completed — see RESEARCH.md
- [x] CLAUDE.md created — AI coding guidelines
- [x] SKILLS.md created — Tool usage guide
- [x] ARCHITECTURE.md created — System design
- [x] TASKS.md created — This file

- [x] **Initialize Python project with uv**
  ```bash
  uv init --name verifywise-mcp --python 3.12
  ```
  Verify: `cat pyproject.toml` shows `[project]` section with `name = "verifywise-mcp"`

- [x] **Add runtime dependencies**
  ```bash
  uv add "mcp[cli]" httpx "pydantic>=2.0" "pydantic-settings>=2.0"
  ```
  Verify: `uv run python -c "import mcp; import httpx; import pydantic; print('OK')"` outputs `OK`

- [x] **Add dev dependencies**
  ```bash
  uv add --dev pytest pytest-asyncio pytest-cov ruff pyright respx
  ```
  Verify: `uv run pytest --version` runs without error

- [x] **Configure pyproject.toml**
  Add ruff, pyright, pytest configuration to `pyproject.toml`.
  See ARCHITECTURE.md for configuration blocks.
  Verify: `uvx ruff check .` exits 0 (no errors on empty project)

- [x] **Create directory structure**
  ```bash
  mkdir -p src/verifywise_mcp/{tools,resources}
  mkdir -p tests/{unit/tools,unit/resources,integration,e2e/screenshots}
  mkdir -p demos scripts
  touch src/verifywise_mcp/__init__.py
  touch src/verifywise_mcp/tools/__init__.py
  touch src/verifywise_mcp/resources/__init__.py
  touch tests/__init__.py tests/unit/__init__.py
  touch tests/unit/tools/__init__.py tests/unit/resources/__init__.py
  touch tests/integration/__init__.py
  ```
  Verify: `ls -la src/verifywise_mcp/tools/` shows `__init__.py`

- [x] **Create .env.example**
  ```
  # VerifyWise connection
  VERIFYWISE_BASE_URL=http://localhost:3000
  VERIFYWISE_EMAIL=admin@example.com
  VERIFYWISE_PASSWORD=changeme

  # MCP server settings
  VERIFYWISE_LOG_LEVEL=INFO
  VERIFYWISE_TRANSPORT=stdio
  VERIFYWISE_REQUEST_TIMEOUT=30.0
  VERIFYWISE_MAX_RETRIES=3
  ```
  Verify: File exists and is committed (not in .gitignore)

- [x] **Update .gitignore**
  Add `.env` (not `.env.example`), `screenshots/`, `demos/*.html`
  Verify: `git status` doesn't show `.env` as untracked

---

### 0.2 VerifyWise as Git Submodule

- [ ] **Add VerifyWise as git submodule**
  ```bash
  git submodule add https://github.com/bluewave-labs/verifywise verifywise
  git submodule update --init --recursive
  ```
  Verify: `ls verifywise/` shows `Client/`, `Servers/`, `docker-compose.yml`

- [ ] **Pin to a specific version/tag**
  ```bash
  cd verifywise
  git log --oneline -10  # Review available commits
  # Optionally: git checkout <stable-tag>
  cd ..
  git add verifywise
  git commit -m "chore: pin verifywise submodule to known-good commit"
  ```
  Verify: `git submodule status` shows the pinned commit hash

- [ ] **Explore VerifyWise API routes from submodule**
  ```bash
  ls verifywise/Servers/src/routes/
  cat verifywise/Servers/src/routes/project.route.ts
  cat verifywise/Servers/src/routes/vendor.route.ts
  cat verifywise/Servers/src/routes/risk.route.ts
  ```
  Verify: Routes are visible; note all endpoint paths and HTTP methods in a comment in `src/verifywise_mcp/client.py`

- [ ] **Explore VerifyWise Docker Compose configuration**
  ```bash
  cat verifywise/docker-compose.yml
  # Note: required environment variables, port mappings, service names
  ```
  Verify: Understand how to start the full stack

---

### 0.3 VerifyWise Docker Setup and Verification

- [ ] **Create docker-compose.test.yml**
  Create a test-specific Docker Compose file that:
  - Mounts VerifyWise services
  - Uses fixed test credentials
  - Includes health checks
  See ARCHITECTURE.md "Docker Compose (Integration Testing)" section.
  Verify: File is syntactically valid (`docker compose -f docker-compose.test.yml config` exits 0)

- [ ] **Create scripts/start-verifywise.sh**
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  echo "Starting VerifyWise stack..."
  docker compose -f verifywise/docker-compose.yml up -d
  echo "Waiting for VerifyWise to be healthy..."
  ./scripts/wait-for-verifywise.sh
  echo "VerifyWise is ready at http://localhost:8080"
  ```
  Verify: Script is executable (`chmod +x scripts/start-verifywise.sh`)

- [ ] **Create scripts/wait-for-verifywise.sh**
  A script that polls `http://localhost:3000/api/health` until it returns 200
  or times out after 120 seconds.
  Verify: Script correctly detects when VerifyWise is ready

- [ ] **Create scripts/stop-verifywise.sh**
  Gracefully stops and optionally removes volumes.
  Verify: `docker compose ps` shows no running containers after script

- [ ] **Verify VerifyWise starts correctly**
  ```bash
  ./scripts/start-verifywise.sh
  ```
  Expected: All services healthy, accessible at http://localhost:8080
  Verify with Showboat:
  ```bash
  cd demos/
  showboat init "VerifyWise Startup Verification"
  showboat exec "docker compose -f ../verifywise/docker-compose.yml ps"
  showboat exec "curl -s http://localhost:3000/api/health | jq ."
  showboat verify
  ```
  Commit: `demos/verifywise-startup.md`

- [ ] **Verify VerifyWise UI with Rodney**
  ```bash
  rodney start
  rodney open http://localhost:8080
  rodney screenshot tests/e2e/screenshots/verifywise-homepage.png
  rodney js "document.title"
  rodney stop
  ```
  Verify: Screenshot shows VerifyWise login page; document title is correct.
  Commit: screenshot as part of the repo (in `tests/e2e/screenshots/`)

---

## Phase 1: Core MCP Server Infrastructure

### 1.1 Configuration Module

- [ ] **Write failing test for Settings** (TDD: RED)
  ```bash
  # tests/unit/test_config.py
  uv run pytest tests/unit/test_config.py -x
  # Confirm: ImportError (module doesn't exist yet)
  ```

- [ ] **Implement `src/verifywise_mcp/config.py`** (TDD: GREEN)
  Pydantic Settings with all env vars from .env.example.
  See ARCHITECTURE.md "config.py — Settings" section.
  ```bash
  uv run pytest tests/unit/test_config.py -x
  # Confirm: PASSED
  ```

- [ ] **Quality checks**
  ```bash
  uvx ruff check src/verifywise_mcp/config.py --fix
  uv run pyright src/verifywise_mcp/config.py
  ```

---

### 1.2 Authentication Module

- [ ] **Write failing tests for auth** (TDD: RED)
  Test: login flow, token refresh, token expiry detection
  ```bash
  uv run pytest tests/unit/test_auth.py -x
  ```

- [ ] **Implement `src/verifywise_mcp/auth.py`** (TDD: GREEN)
  - `login(email, password) -> TokenPair`
  - `refresh_token(cookie) -> str`
  - `is_token_expired(token) -> bool`
  - `TokenManager` class with asyncio.Lock for thread safety

- [ ] **Quality checks** (ruff + pyright)

---

### 1.3 HTTP Client Module

- [ ] **Write failing tests for client** (TDD: RED)
  Use `respx` to mock httpx calls.
  Test: GET, POST, error handling (401→refresh→retry, 404→ToolError, network error)

- [ ] **Implement `src/verifywise_mcp/client.py`** (TDD: GREEN)
  - `VerifyWiseClient` with singleton pattern
  - Auto-refresh tokens on 401
  - Retry with backoff on 5xx and network errors
  - All methods: `get()`, `post()`, `put()`, `patch()`, `delete()`

- [ ] **Quality checks** (ruff + pyright)

---

### 1.4 Data Models

- [ ] **Explore VerifyWise TypeScript types for data shapes**
  ```bash
  cat verifywise/Servers/src/models/project.model.ts
  cat verifywise/Servers/src/models/vendor.model.ts
  cat verifywise/Servers/src/models/risk.model.ts
  ```

- [ ] **Write failing tests for models** (TDD: RED)

- [ ] **Implement `src/verifywise_mcp/models.py`** (TDD: GREEN)
  Pydantic models for: Project, Risk, Vendor, ComplianceControl, AIModel, Policy, Incident
  See ARCHITECTURE.md "Data Models" section.

- [ ] **Quality checks** (ruff + pyright)

---

### 1.5 Minimal Server Entry Point

- [ ] **Write failing test: server instantiates** (TDD: RED)
  ```python
  from verifywise_mcp.server import mcp
  assert mcp.name == "verifywise-mcp"
  ```

- [ ] **Implement `src/verifywise_mcp/server.py`** (TDD: GREEN)
  - Create `FastMCP` instance with name and instructions
  - Configure logging to stderr
  - `main()` function calling `mcp.run(transport="stdio")`
  - `if __name__ == "__main__": main()`

- [ ] **Verify server starts without error**
  ```bash
  timeout 3 uv run src/verifywise_mcp/server.py || echo "Server started (timeout expected)"
  ```
  Verify: No Python import errors or crashes

---

## Phase 2: Projects & Risks Tools

### 2.1 Projects Tools

- [ ] **Read VerifyWise projects API** from submodule
  ```bash
  cat verifywise/Servers/src/routes/project.route.ts
  cat verifywise/Servers/src/controllers/project.controller.ts
  ```

- [ ] **Write failing tests for projects tools** (TDD: RED)
  Tests in `tests/unit/tools/test_projects.py`:
  - `test_list_projects_returns_list`
  - `test_list_projects_filters_by_status`
  - `test_list_projects_validates_limit_range`
  - `test_get_project_returns_project`
  - `test_get_project_raises_on_not_found`
  - `test_create_project_returns_new_project`
  - `test_create_project_validates_required_fields`

- [ ] **Implement `src/verifywise_mcp/tools/projects.py`** (TDD: GREEN)
  Tools: `list`, `get`, `create`, `update`, `archive`
  Mount on `projects_server = FastMCP(name="projects")`

- [ ] **Mount projects sub-server in `server.py`**
  ```python
  from verifywise_mcp.tools.projects import projects_server
  mcp.mount(projects_server, prefix="projects")
  ```

- [ ] **Quality checks** (ruff + pyright + full test suite)

- [ ] **Integration test: list projects against live VerifyWise**
  Requires Docker stack running.
  ```bash
  uv run pytest tests/integration/test_projects.py -m integration -v
  ```

- [ ] **Showboat demo for projects tools**
  ```bash
  showboat init "Projects Tools Demo"
  showboat exec "uv run pytest tests/unit/tools/test_projects.py -v"
  showboat verify
  ```

---

### 2.2 Risks Tools

- [ ] **Read VerifyWise risks API** from submodule
  ```bash
  cat verifywise/Servers/src/routes/risk.route.ts
  ```

- [ ] **Write failing tests for risks tools** (TDD: RED)
  Tests: list_risks, get_risk, create_risk, update_risk_status, delete_risk

- [ ] **Implement `src/verifywise_mcp/tools/risks.py`** (TDD: GREEN)

- [ ] **Mount + quality checks + integration test + showboat demo**

---

## Phase 3: Compliance & Vendor Tools

### 3.1 Compliance Tools

- [ ] **Read VerifyWise compliance APIs** from submodule
  ```bash
  ls verifywise/Servers/src/routes/ | grep -E "eu|iso|nist"
  cat verifywise/Servers/src/routes/euAiAct.route.ts
  ```

- [ ] **Write failing tests** (TDD: RED)
  Tests: get_framework_status, list_controls, update_control_status, get_assessment_summary

- [ ] **Implement `src/verifywise_mcp/tools/compliance.py`** (TDD: GREEN)
  Supports all four frameworks: EU AI Act, ISO 42001, ISO 27001, NIST AI RMF

- [ ] **Mount + quality checks + integration test + showboat demo**

---

### 3.2 Vendor Tools

- [ ] **Read VerifyWise vendors API** from submodule

- [ ] **Write failing tests** (TDD: RED)

- [ ] **Implement `src/verifywise_mcp/tools/vendors.py`** (TDD: GREEN)
  Tools: list_vendors, get_vendor, create_vendor, update_vendor_risk_score

- [ ] **Mount + quality checks + integration test + showboat demo**

---

### 3.3 AI Model Inventory Tools

- [ ] **Read VerifyWise model inventory API** from submodule
  ```bash
  cat verifywise/Servers/src/routes/modelInventory.route.ts
  ```

- [ ] **Write failing tests** (TDD: RED)

- [ ] **Implement `src/verifywise_mcp/tools/models.py`** (TDD: GREEN)
  Tools: list_models, get_model, add_model, update_model, list_evaluations

- [ ] **Mount + quality checks + integration test + showboat demo**

---

## Phase 4: Resources (Read-Only Data)

### 4.1 Compliance Framework Resources

- [ ] **Write failing tests for framework resources** (TDD: RED)
  Tests: resource URI resolution, correct data shape, framework listing

- [ ] **Implement `src/verifywise_mcp/resources/frameworks.py`** (TDD: GREEN)
  Resources:
  - `verifywise://frameworks` — list available frameworks
  - `verifywise://frameworks/{framework_id}/controls` — all controls
  - `verifywise://projects/{project_id}/assessment` — per-project assessment

- [ ] **Mount + quality checks + integration test**

---

### 4.2 Policy Resources

- [ ] **Write failing tests for policy resources** (TDD: RED)

- [ ] **Implement `src/verifywise_mcp/resources/policies.py`** (TDD: GREEN)
  Resources:
  - `verifywise://policies` — list all policies
  - `verifywise://policies/{policy_id}` — get specific policy

- [ ] **Mount + quality checks + integration test**

---

## Phase 5: Reports & Prompts

### 5.1 Report Generation Tool

- [ ] **Read VerifyWise report generation API** from submodule

- [ ] **Write failing tests** (TDD: RED)

- [ ] **Implement `src/verifywise_mcp/tools/reports.py`** (TDD: GREEN)
  Tools: generate_compliance_report (returns download URL or base64 PDF)

- [ ] **Mount + quality checks + integration test**

---

### 5.2 MCP Prompts

- [ ] **Implement prompts for common governance workflows**
  In `server.py` or `src/verifywise_mcp/prompts.py`:
  - `risk_assessment_prompt(project_name, framework)` — structured risk review
  - `compliance_gap_analysis_prompt(project_id, target_framework)` — gap analysis template
  - `vendor_due_diligence_prompt(vendor_name, vendor_type)` — vendor evaluation guide

---

## Phase 6: Full Integration & E2E Verification

### 6.1 Complete Integration Test Suite

- [ ] **Run full integration test suite against live Docker stack**
  ```bash
  ./scripts/start-verifywise.sh
  uv run pytest tests/integration/ -m integration -v
  ```
  Verify: All integration tests pass

---

### 6.2 E2E Browser Verification with Rodney + Showboat

- [ ] **Create comprehensive E2E verification document**
  ```bash
  cd demos/
  showboat init "VerifyWise MCP Server — End-to-End Verification"

  showboat note "Step 1: VerifyWise stack is running"
  showboat exec "docker compose -f ../verifywise/docker-compose.yml ps"
  showboat exec "curl -s http://localhost:3000/api/health | jq ."

  showboat note "Step 2: MCP server tools respond correctly"
  showboat exec "uv run python scripts/call_tool.py projects_list"
  showboat exec "uv run python scripts/call_tool.py compliance_get_framework_status --framework eu-ai-act"

  showboat note "Step 3: UI reflects data created via MCP tools"
  rodney start
  rodney open http://localhost:8080
  rodney screenshot screenshots/e2e-homepage.png
  showboat image screenshots/e2e-homepage.png "VerifyWise UI loaded"
  rodney stop

  showboat verify  # Re-run all blocks to confirm
  ```
  Commit: `demos/e2e-verification.md`

---

### 6.3 Claude Desktop Integration Test

- [ ] **Document Claude Desktop configuration** in README.md
- [ ] **Test manually in Claude Desktop** (if available):
  - Ask Claude: "List my AI governance projects in VerifyWise"
  - Ask Claude: "What is the EU AI Act compliance status for project X?"
  - Ask Claude: "Create a new risk: 'Model bias in loan approval system' with high severity"
- [ ] **Document the session** using Showboat if possible

---

## Phase 7: Polish and CI/CD

### 7.1 Documentation

- [ ] **Create README.md** with:
  - What it is and why it's useful
  - Prerequisites (Docker, uv, rodney, showboat)
  - Quick start instructions
  - All available tools (auto-generated from FastMCP if possible)
  - Claude Desktop configuration
  - Development workflow
  - Contributing guide

- [ ] **Create CHANGELOG.md** with version history

---

### 7.2 CI/CD Pipeline

- [ ] **Create `.github/workflows/test.yml`**
  - Trigger: push to `claude/*` branches, pull requests
  - Jobs:
    1. `lint`: `uvx ruff check . && uvx ruff format --check .`
    2. `type-check`: `uv run pyright src/`
    3. `unit-tests`: `uv run pytest tests/unit/ -v`
    4. `integration-tests`: Start Docker stack, run `pytest tests/integration/ -m integration`

---

### 7.3 Final Quality Gate

- [ ] **All unit tests pass:** `uv run pytest tests/unit/ -v`
- [ ] **All integration tests pass:** `uv run pytest tests/integration/ -m integration -v`
- [ ] **Zero lint errors:** `uvx ruff check .`
- [ ] **Zero format issues:** `uvx ruff format --check .`
- [ ] **Zero type errors:** `uv run pyright src/`
- [ ] **Coverage ≥ 80%:** `uv run pytest --cov=verifywise_mcp --cov-report=term-missing`
- [ ] **Showboat verification passes:** `showboat verify` in `demos/` directory
- [ ] **All TASKS.md items checked off** (except explicitly skipped ones)

---

## Backlog (Future Phases)

These are out of scope for the initial implementation but should be tracked:

- [ ] HTTP transport mode for shared/team deployment
- [ ] OAuth 2.1 for MCP-level authentication (required for HTTP transport per MCP spec)
- [ ] LLM Arena evaluation tools (via Python EvalServer at port 8000)
- [ ] Shadow AI detection tool (POST /api/automations/shadow-ai-scan)
- [ ] Training records management tools
- [ ] Approval workflow tools
- [ ] Incident management tools
- [ ] Streaming support for report generation (long-running operations)
- [ ] MCP sampling for AI-generated compliance recommendations
- [ ] VerifyWise webhook → MCP notification bridge
- [ ] Multi-tenant support (configure tenantId per request)

---

## Notes for Claude Code

When working through this task list autonomously:

1. **One task at a time** — mark `[>]` while working, `[x]` when done
2. **TDD is mandatory** — always write the test first (RED), then implement (GREEN), then clean up (REFACTOR)
3. **Never skip quality checks** — ruff + pyright must pass before committing
4. **Showboat for user-visible features** — create demos for every tool the user will actually invoke
5. **Read before implementing** — always read the VerifyWise route files from the submodule before building a tool for that domain
6. **Atomic commits** — one logical change per commit, descriptive message
7. **Push after each phase** — don't accumulate too many uncommitted changes

If you get stuck on a task:
- Try a different approach (max 3 attempts)
- Leave a `[!] BLOCKED:` note explaining the issue
- Move to the next task and come back
- Document the blocker in a GitHub issue if it's significant
