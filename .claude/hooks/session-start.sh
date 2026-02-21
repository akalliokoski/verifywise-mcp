#!/usr/bin/env bash
# .claude/hooks/session-start.sh
# SessionStart hook for Claude Code on the web.
#
# The container filesystem IS cached between sessions — node_modules, .venv,
# go binaries, and built dist/ all survive across resume/restart. This hook
# therefore checks whether each step is already done before repeating it.
# On a warm (cached) container most phases are skipped in <5s total.
#
# What IS cached across sessions (survives in container filesystem):
#   - verifywise/Servers/node_modules   → skip npm install if present
#   - verifywise/Clients/node_modules   → skip npm install if present
#   - verifywise/Servers/dist/          → skip tsc build if newer than sources
#   - .venv/                            → uv sync is fast (no-op) when current
#   - ~/go/bin/showboat, ~/go/bin/rodney→ skip go install if binary exists
#   - PostgreSQL data dir               → DB + migrations survive
#
# What is NOT cached (must redo every session):
#   - Running processes (backend, frontend servers must be restarted)
#   - /tmp files
#   - PostgreSQL and Redis service state (must start services)
#
# Phases:
#   1  Guard        (skip if not a web session)
#   2  Services     (start postgres + redis — always needed)
#   3  Python deps  (uv sync — fast no-op when .venv is current)
#   4  Go tools     (skip if binaries already on PATH)
#   5  DB setup     (create DB if missing; ensure .env)
#   6  Backend deps (skip npm install if node_modules exists)
#   7  Backend build(skip tsc if dist/ is newer than source)
#   8  DB migrate   (sequelize migrate — instant when up-to-date)
#   9  DB seed      (idempotent — instant when user exists)
#  10  Start backend(always restart — process state not cached)
#  11  Frontend deps(skip npm install if node_modules exists)
#  12  Start frontend(always restart — process state not cached)
#  13  Env vars     (write to $CLAUDE_ENV_FILE)
#  14  Health wait  (poll until backend responds)

set -euo pipefail

REPO_ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
SERVERS_DIR="$REPO_ROOT/verifywise/Servers"
CLIENTS_DIR="$REPO_ROOT/verifywise/Clients"
SCRIPTS_DIR="$REPO_ROOT/scripts"

log()  { echo "[session-start] $*" >&2; }
skip() { echo "[session-start]   SKIP: $*" >&2; }

# ── Phase 1: Only run in Claude Code web environment ─────────────────────────
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  log "Not a remote session — skipping (CLAUDE_CODE_REMOTE != true)"
  exit 0
fi

log "Starting VerifyWise session setup (cached where possible)..."

# ── Phase 2: System services (always needed — process state not cached) ───────
log "Phase 2: System services..."
service postgresql start 2>&1 | grep -E "(started|already|done)" >&2 || true
service redis-server start 2>&1 | grep -E "(started|already|done)" >&2 || true

for i in 1 2 3 4 5; do pg_isready -q 2>/dev/null && break || sleep 2; done
pg_isready -q || { log "ERROR: PostgreSQL did not start"; exit 1; }
log "  PostgreSQL OK"

redis-cli ping 2>/dev/null | grep -q PONG || { log "ERROR: Redis not responding"; exit 1; }
log "  Redis OK"

# ── Phase 3: Python deps (uv sync is a fast no-op when .venv is current) ─────
log "Phase 3: Python deps (uv sync)..."
cd "$REPO_ROOT"
uv sync --quiet 2>&1 | tail -2 >&2 || true
log "  uv sync done"

# ── Phase 4: Go CLI tools (skip if binaries already exist) ───────────────────
export PATH="$PATH:$HOME/go/bin"

if ! command -v showboat &>/dev/null; then
  log "Phase 4: Installing showboat..."
  go install github.com/simonw/showboat@latest 2>&1 >&2 || log "  WARNING: showboat install failed"
else
  skip "Phase 4: showboat already at $(command -v showboat)"
fi

if ! command -v rodney &>/dev/null; then
  log "Phase 4: Installing rodney..."
  go install github.com/simonw/rodney@latest 2>&1 >&2 || log "  WARNING: rodney install failed"
else
  skip "Phase 4: rodney already at $(command -v rodney)"
fi

# ── Phase 5: Database setup ───────────────────────────────────────────────────
log "Phase 5: Database setup..."
sudo -u postgres psql -c "CREATE DATABASE verifywise OWNER postgres;" 2>/dev/null || true

if [ ! -f "$SERVERS_DIR/.env" ]; then
  log "  Creating Servers/.env from .env.dev"
  cp "$REPO_ROOT/verifywise/.env.dev" "$SERVERS_DIR/.env"
  sed -i 's/REDIS_HOST=redis/REDIS_HOST=localhost/' "$SERVERS_DIR/.env"
else
  # Ensure REDIS_HOST is localhost even if .env was recreated from .env.dev
  sed -i 's/^REDIS_HOST=redis$/REDIS_HOST=localhost/' "$SERVERS_DIR/.env"
  skip "Phase 5: Servers/.env already exists"
fi

# ── Phase 6: Backend npm install (skip if node_modules present) ───────────────
cd "$SERVERS_DIR"

if [ ! -d node_modules ]; then
  log "Phase 6: Backend npm install (node_modules missing)..."
  npm install --prefer-offline --silent 2>&1 | tail -3 >&2 || true
else
  skip "Phase 6: Backend node_modules already installed"
fi

# ── Phase 7: Backend TypeScript build (skip if dist/ is newer than sources) ───
# Compare newest .ts source file against dist/index.js as the build sentinel
NEWEST_SRC=$(find "$SERVERS_DIR" -name "*.ts" -not -path "*/node_modules/*" \
  -printf "%T@\n" 2>/dev/null | sort -rn | head -1 || echo "0")
DIST_MTIME=$(stat -c "%Y" "$SERVERS_DIR/dist/index.js" 2>/dev/null || echo "0")

if [ ! -d "$SERVERS_DIR/dist" ] || \
   [ "$(echo "$NEWEST_SRC > $DIST_MTIME" | awk '{print ($1 > $3)}')" = "1" ]; then
  log "Phase 7: Building backend TypeScript (dist/ stale or missing)..."
  npm run build --silent 2>&1 | tail -5 >&2
else
  skip "Phase 7: dist/ is up-to-date (build skipped)"
fi

# ── Phase 8: DB migrations (sequelize is instant when already up-to-date) ────
log "Phase 8: DB migrations..."
npm run migrate-db 2>&1 | grep -E "(migrated|up to date|Loaded)" >&2 || true
log "  Migrations done"

# ── Phase 9: Seed (idempotent — instant when user already exists) ─────────────
log "Phase 9: Seeding database..."
node "$SCRIPTS_DIR/seed-verifywise.js" 2>&1 >&2

# ── Phase 10: Start backend (always restart — process state not cached) ───────
log "Phase 10: Starting backend server..."
pkill -f "node.*dist/index.js" 2>/dev/null || true
sleep 1
nohup node "$SERVERS_DIR/dist/index.js" > /tmp/verifywise-backend.log 2>&1 &
log "  Backend started (log: /tmp/verifywise-backend.log)"

# ── Phase 11: Frontend npm install (skip if node_modules present) ─────────────
cd "$CLIENTS_DIR"

if [ ! -d node_modules ]; then
  log "Phase 11: Frontend npm install (node_modules missing)..."
  npm install --prefer-offline --silent 2>&1 | tail -3 >&2 || true
else
  # Validate rollup native module is present (common failure point)
  if ! node -e "require('./node_modules/rollup/dist/native.js')" 2>/dev/null; then
    log "Phase 11: Rollup native module broken — clean reinstall..."
    rm -rf node_modules package-lock.json
    npm install --silent 2>&1 | tail -3 >&2 || true
  else
    skip "Phase 11: Frontend node_modules OK"
  fi
fi

# ── Phase 12: Start frontend (always restart — process state not cached) ──────
log "Phase 12: Starting frontend Vite server..."
pkill -f "vite.*5173" 2>/dev/null || true
sleep 1
nohup npm run dev:vite -- --port 5173 > /tmp/verifywise-frontend.log 2>&1 &
log "  Frontend started (log: /tmp/verifywise-frontend.log)"

# ── Phase 13: Environment variables ───────────────────────────────────────────
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  cat >> "$CLAUDE_ENV_FILE" << ENV
export PATH="\$PATH:\$HOME/go/bin"
export VERIFYWISE_BASE_URL="http://localhost:3000"
export VERIFYWISE_EMAIL="verifywise@email.com"
ENV
  if [ -n "${VERIFYWISE_PASSWORD:-}" ]; then
    echo "export VERIFYWISE_PASSWORD=\"$VERIFYWISE_PASSWORD\"" >> "$CLAUDE_ENV_FILE"
  fi
  log "Phase 13: Env vars written to \$CLAUDE_ENV_FILE"
fi

# ── Phase 14: Wait for backend readiness ──────────────────────────────────────
log "Phase 14: Waiting for backend..."
DEADLINE=$(( $(date +%s) + 90 ))
BACKEND_URL="http://localhost:3000/api/users/check-user-exists"

until curl -s --max-time 5 "$BACKEND_URL" 2>/dev/null | grep -q "message"; do
  if (( $(date +%s) >= DEADLINE )); then
    log "ERROR: Backend not ready within 90s — check /tmp/verifywise-backend.log"
    exit 1
  fi
  sleep 3
done

log "VerifyWise session ready:"
log "  Backend:  http://localhost:3000"
log "  Frontend: http://localhost:5173"
log "  Admin:    verifywise@email.com"
