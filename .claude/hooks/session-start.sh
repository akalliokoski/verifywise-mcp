#!/usr/bin/env bash
# .claude/hooks/session-start.sh
# SessionStart hook for Claude Code on the web.
#
# Runs synchronously before the agent session begins. The container state is
# cached after this hook completes, so npm install / uv sync / go install run
# once and subsequent sessions reuse the cached layer.
#
# Phases:
#   1  Check environment (skip if not a web session)
#   2  System services   (PostgreSQL, Redis)
#   3  Python deps       (uv sync)
#   4  Go CLI tools      (showboat, rodney)
#   5  Backend setup     (npm install, build, migrate, seed)
#   6  Start services    (backend + frontend in background)
#   7  Env vars          (write to $CLAUDE_ENV_FILE)
#   8  Health wait       (poll backend until ready)
#
# Env vars set for the session:
#   VERIFYWISE_BASE_URL   http://localhost:3000
#   VERIFYWISE_EMAIL      verifywise@email.com
#   PATH                  extended with $HOME/go/bin
#   VERIFYWISE_PASSWORD   read from secret $VERIFYWISE_PASSWORD (if set)

set -euo pipefail

REPO_ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
SERVERS_DIR="$REPO_ROOT/verifywise/Servers"
CLIENTS_DIR="$REPO_ROOT/verifywise/Clients"
SCRIPTS_DIR="$REPO_ROOT/scripts"

log() { echo "[session-start] $*" >&2; }

# ── Phase 1: Only run in Claude Code web environment ─────────────────────────
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  log "Not a remote session — skipping hook (CLAUDE_CODE_REMOTE != true)"
  exit 0
fi

log "Starting VerifyWise session setup..."

# ── Phase 2: System services ──────────────────────────────────────────────────
log "Phase 2: Starting system services..."
service postgresql start 2>&1 | grep -E "(started|already|done)" >&2 || true
service redis-server start 2>&1 | grep -E "(started|already|done)" >&2 || true

# Wait briefly for PostgreSQL to accept connections
for i in 1 2 3 4 5; do
  pg_isready -q 2>/dev/null && break || sleep 2
done
pg_isready -q || { log "ERROR: PostgreSQL did not start"; exit 1; }
log "  PostgreSQL ready"

redis-cli ping 2>/dev/null | grep -q PONG || { log "ERROR: Redis not responding"; exit 1; }
log "  Redis ready"

# ── Phase 3: Python dependencies ──────────────────────────────────────────────
log "Phase 3: Syncing Python environment (uv sync)..."
cd "$REPO_ROOT"
uv sync --quiet 2>&1 | tail -3 >&2 || true
log "  uv sync done"

# ── Phase 4: Go CLI tools ─────────────────────────────────────────────────────
log "Phase 4: Installing Go CLI tools..."
export PATH="$PATH:$HOME/go/bin"

if ! command -v showboat &>/dev/null; then
  log "  Installing showboat..."
  go install github.com/simonw/showboat@latest 2>&1 >&2 || log "  WARNING: showboat install failed"
else
  log "  showboat already installed"
fi

if ! command -v rodney &>/dev/null; then
  log "  Installing rodney..."
  go install github.com/simonw/rodney@latest 2>&1 >&2 || log "  WARNING: rodney install failed"
else
  log "  rodney already installed"
fi

# ── Phase 5: Database ─────────────────────────────────────────────────────────
log "Phase 5: Database setup..."

# Create database if missing
sudo -u postgres psql -c "CREATE DATABASE verifywise OWNER postgres;" 2>/dev/null || true

# Ensure backend .env exists
if [ ! -f "$SERVERS_DIR/.env" ]; then
  log "  Creating Servers/.env from .env.dev"
  cp "$REPO_ROOT/verifywise/.env.dev" "$SERVERS_DIR/.env"
  sed -i 's/REDIS_HOST=redis/REDIS_HOST=localhost/' "$SERVERS_DIR/.env"
fi
# Always ensure REDIS_HOST points to localhost (not Docker service name)
sed -i 's/^REDIS_HOST=redis$/REDIS_HOST=localhost/' "$SERVERS_DIR/.env"

# ── Phase 6: Backend install, build, migrate ──────────────────────────────────
log "Phase 6: Backend setup (npm install → build → migrate)..."
cd "$SERVERS_DIR"

log "  npm install..."
npm install --prefer-offline --silent 2>&1 | tail -3 >&2 || true

log "  npm run build..."
npm run build --silent 2>&1 | tail -5 >&2

log "  npm run migrate-db..."
npm run migrate-db 2>&1 | tail -5 >&2

log "  Seeding database..."
node "$SCRIPTS_DIR/seed-verifywise.js" 2>&1 >&2

# ── Phase 7: Start backend ────────────────────────────────────────────────────
log "Phase 7: Starting backend server..."
pkill -f "node.*dist/index.js" 2>/dev/null || true
sleep 1
nohup node "$SERVERS_DIR/dist/index.js" > /tmp/verifywise-backend.log 2>&1 &
log "  Backend started (log: /tmp/verifywise-backend.log)"

# ── Phase 8: Frontend install + start ─────────────────────────────────────────
log "Phase 8: Frontend setup..."
cd "$CLIENTS_DIR"

log "  npm install..."
# Use --prefer-offline for speed; delete and reinstall if rollup native module is missing
if ! npm install --prefer-offline --silent 2>&1 | tail -3 >&2; then
  log "  npm install failed; retrying with clean node_modules..."
  rm -rf node_modules package-lock.json
  npm install --silent 2>&1 | tail -3 >&2 || true
fi

log "  Starting Vite dev server..."
pkill -f "vite.*5173" 2>/dev/null || true
sleep 1
nohup npm run dev:vite -- --port 5173 > /tmp/verifywise-frontend.log 2>&1 &
log "  Frontend started (log: /tmp/verifywise-frontend.log)"

# ── Phase 9: Environment variables ────────────────────────────────────────────
log "Phase 9: Writing session environment variables..."
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  cat >> "$CLAUDE_ENV_FILE" << ENV
export PATH="\$PATH:\$HOME/go/bin"
export VERIFYWISE_BASE_URL="http://localhost:3000"
export VERIFYWISE_EMAIL="verifywise@email.com"
ENV
  # Forward the password secret if provided via repository secret
  if [ -n "${VERIFYWISE_PASSWORD:-}" ]; then
    echo "export VERIFYWISE_PASSWORD=\"$VERIFYWISE_PASSWORD\"" >> "$CLAUDE_ENV_FILE"
  fi
  log "  Env vars written to \$CLAUDE_ENV_FILE"
fi

# ── Phase 10: Wait for backend readiness ──────────────────────────────────────
log "Phase 10: Waiting for VerifyWise backend..."
DEADLINE=$(( $(date +%s) + 90 ))
# Use check-user-exists — it returns 400 (no token) but proves the server is up.
# Don't use -f so we accept any HTTP response (including 4xx).
BACKEND_URL="http://localhost:3000/api/users/check-user-exists"

until curl -s --max-time 5 "$BACKEND_URL" | grep -q "message" 2>/dev/null; do
  if (( $(date +%s) >= DEADLINE )); then
    log "ERROR: Backend did not become ready within 90s"
    log "       Check /tmp/verifywise-backend.log"
    exit 1
  fi
  sleep 3
done

log "Backend is ready at http://localhost:3000"
log ""
log "VerifyWise session ready:"
log "  Backend:  http://localhost:3000"
log "  Frontend: http://localhost:5173"
log "  Admin:    verifywise@email.com"
