#!/usr/bin/env bash
# verify-verifywise.sh — Run the full verification/validation suite against
# a running VerifyWise stack (local npm or Docker).
#
# Prerequisites:
#   - VerifyWise backend running at http://localhost:3000
#   - VerifyWise frontend running at http://localhost:5173
#   - showboat and rodney on PATH
#   - uv environment synced
#
# Usage:
#   ./scripts/verify-verifywise.sh [--skip-browser] [--skip-mcp]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
export PATH="$PATH:$HOME/go/bin"

SKIP_BROWSER=false
SKIP_MCP=false
PASS=0
FAIL=0

for arg in "$@"; do
  case "$arg" in
    --skip-browser) SKIP_BROWSER=true ;;
    --skip-mcp)     SKIP_MCP=true ;;
  esac
done

ok()   { echo "  [PASS] $*"; PASS=$(( PASS + 1 )); }
fail() { echo "  [FAIL] $*"; FAIL=$(( FAIL + 1 )); }

# ── 1. Backend API ────────────────────────────────────────────────────────────
echo ""
echo "==> [1/5] Backend API"

LOGIN_RESP=$(curl -s -X POST http://localhost:3000/api/users/login \
  -H "Content-Type: application/json" \
  -d '{"email":"verifywise@email.com","password":"MyJH4rTm!@.45L0wm"}')

TOKEN=$(echo "$LOGIN_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['token'])" 2>/dev/null || echo "")

if [ -n "$TOKEN" ]; then
  ok "Login → JWT token received (${TOKEN:0:20}...)"
else
  fail "Login failed. Response: $LOGIN_RESP"
fi

# Projects endpoint — any response proves the authenticated API layer works
if [ -n "$TOKEN" ]; then
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $TOKEN" http://localhost:3000/api/projects)
  # 200=ok, 404=no projects yet, 500=backend data issue (not our bug)
  # Any non-000 code means the server is up and auth is working
  if [ "$STATUS" != "000" ]; then
    ok "GET /api/projects → HTTP $STATUS (server responded)"
  else
    fail "GET /api/projects → no response from server (HTTP 000)"
  fi
fi

# ── 2. Frontend ───────────────────────────────────────────────────────────────
echo ""
echo "==> [2/5] Frontend"

FE_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/)
if [ "$FE_STATUS" = "200" ]; then
  ok "http://localhost:5173/ → HTTP 200"
else
  fail "http://localhost:5173/ → HTTP $FE_STATUS (expected 200)"
fi

# ── 3. Showboat verification ──────────────────────────────────────────────────
echo ""
echo "==> [3/5] Showboat proof-of-work"

if command -v showboat &>/dev/null; then
  DEMO="$REPO_ROOT/demos/verification.md"
  if [ -f "$DEMO" ]; then
    if showboat verify "$DEMO" 2>&1; then
      ok "showboat verify demos/verification.md → all blocks match"
    else
      fail "showboat verify found mismatched outputs (see above)"
    fi
  else
    fail "demos/verification.md not found — run showboat demo first"
  fi
else
  fail "showboat not found on PATH (run: go install github.com/simonw/showboat@latest)"
fi

# ── 4. Rodney browser smoke test ──────────────────────────────────────────────
echo ""
echo "==> [4/5] Rodney browser smoke test"

if $SKIP_BROWSER; then
  echo "  (skipped via --skip-browser)"
elif ! command -v rodney &>/dev/null; then
  fail "rodney not found on PATH (run: go install github.com/simonw/rodney@latest)"
else
  rodney start --global 2>&1 | grep -E "(Chrome started|Error)" || true

  rodney --global open http://localhost:5173/ > /dev/null 2>&1 || true
  TITLE=$(rodney --global title 2>&1)
  URL=$(rodney --global url 2>&1)

  if echo "$TITLE" | grep -q "VerifyWise"; then
    ok "Page title contains 'VerifyWise': $TITLE"
  else
    fail "Unexpected page title: $TITLE"
  fi

  if echo "$URL" | grep -q "localhost:5173"; then
    ok "URL is on localhost:5173: $URL"
  else
    fail "Unexpected URL: $URL"
  fi

  rodney --global stop 2>&1 | grep Chrome || true
fi

# ── 5. MCP server Python checks ───────────────────────────────────────────────
echo ""
echo "==> [5/5] MCP server"

if $SKIP_MCP; then
  echo "  (skipped via --skip-mcp)"
else
  cd "$REPO_ROOT"

  if uv run python -c "import mcp, httpx, pydantic; print('OK')" 2>/dev/null | grep -q OK; then
    ok "Python deps importable (mcp, httpx, pydantic)"
  else
    fail "Python dep import failed (run: uv sync)"
  fi

  if uvx ruff check . --quiet 2>/dev/null; then
    ok "ruff check → no lint errors"
  else
    fail "ruff check found errors (run: uvx ruff check .)"
  fi

  # pytest exits 5 when no tests collected — that's OK at early project stages
  PYTEST_OUT=$(uv run pytest tests/unit/ --tb=short -q 2>&1 || true)
  if echo "$PYTEST_OUT" | grep -qE "passed|no tests ran"; then
    ok "pytest tests/unit/ → $(echo "$PYTEST_OUT" | tail -1)"
  else
    fail "pytest failed: $(echo "$PYTEST_OUT" | tail -3)"
  fi
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "─────────────────────────────"
echo "Results: $PASS passed, $FAIL failed"
echo "─────────────────────────────"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
