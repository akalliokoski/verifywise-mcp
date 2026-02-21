#!/usr/bin/env bash
# start-verifywise-local.sh — Start the VerifyWise stack using npm (no Docker).
#
# Starts:
#   - PostgreSQL and Redis (system services)
#   - Backend Node.js server  (http://localhost:3000)
#   - Frontend Vite dev server (http://localhost:5173)
#
# Usage:
#   ./scripts/start-verifywise-local.sh          # normal start
#   ./scripts/start-verifywise-local.sh --skip-install   # skip npm install steps
#   ./scripts/start-verifywise-local.sh --skip-build     # skip TypeScript build

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVERS_DIR="$REPO_ROOT/verifywise/Servers"
CLIENTS_DIR="$REPO_ROOT/verifywise/Clients"

SKIP_INSTALL=false
SKIP_BUILD=false
for arg in "$@"; do
  case "$arg" in
    --skip-install) SKIP_INSTALL=true ;;
    --skip-build)   SKIP_BUILD=true ;;
  esac
done

echo "==> VerifyWise local startup"
echo "    Repo:     $REPO_ROOT"
echo "    Backend:  $SERVERS_DIR"
echo "    Frontend: $CLIENTS_DIR"
echo ""

# ── 1. System services ────────────────────────────────────────────────────────
echo "[1/8] Starting system services..."
service postgresql start 2>&1 | grep -E "(started|already|done)" || true
service redis-server start 2>&1 | grep -E "(started|already|done)" || true

pg_isready -q || { echo "ERROR: PostgreSQL not ready"; exit 1; }
redis-cli ping -q | grep -q PONG || { echo "ERROR: Redis not responding"; exit 1; }
echo "      PostgreSQL and Redis OK"

# ── 2. Database ───────────────────────────────────────────────────────────────
echo "[2/8] Ensuring database exists..."
sudo -u postgres psql -c "CREATE DATABASE verifywise OWNER postgres;" 2>/dev/null || true

# ── 3. Backend .env ───────────────────────────────────────────────────────────
echo "[3/8] Checking backend .env..."
if [ ! -f "$SERVERS_DIR/.env" ]; then
  echo "      Creating $SERVERS_DIR/.env from verifywise/.env.dev"
  cp "$REPO_ROOT/verifywise/.env.dev" "$SERVERS_DIR/.env"
  sed -i 's/REDIS_HOST=redis/REDIS_HOST=localhost/' "$SERVERS_DIR/.env"
fi
# Ensure REDIS_HOST is localhost (not the Docker hostname)
sed -i 's/^REDIS_HOST=redis$/REDIS_HOST=localhost/' "$SERVERS_DIR/.env"

# ── 4. Backend install + build ────────────────────────────────────────────────
cd "$SERVERS_DIR"

if ! $SKIP_INSTALL; then
  echo "[4/8] Installing backend npm dependencies..."
  npm install --prefer-offline 2>&1 | tail -3
else
  echo "[4/8] Skipping npm install (--skip-install)"
fi

if ! $SKIP_BUILD; then
  echo "[5/8] Building backend TypeScript..."
  npm run build 2>&1 | tail -5
else
  echo "[5/8] Skipping build (--skip-build)"
fi

# ── 5. Migrate + seed ─────────────────────────────────────────────────────────
echo "[6/8] Running database migrations..."
npm run migrate-db 2>&1 | tail -3

echo "      Seeding default org and admin user..."
node "$SCRIPT_DIR/seed-verifywise.js" 2>&1

# ── 6. Start backend ──────────────────────────────────────────────────────────
echo "[7/8] Starting backend server (port 3000)..."
# Kill any existing backend
pkill -f "node.*dist/index.js" 2>/dev/null || true
sleep 1
node "$SERVERS_DIR/dist/index.js" > /tmp/verifywise-backend.log 2>&1 &
BACKEND_PID=$!
echo "      Backend PID: $BACKEND_PID (log: /tmp/verifywise-backend.log)"

# ── 7. Frontend ───────────────────────────────────────────────────────────────
cd "$CLIENTS_DIR"

if ! $SKIP_INSTALL; then
  echo "      Installing frontend npm dependencies..."
  npm install --prefer-offline 2>&1 | tail -3
fi

echo "[8/8] Starting frontend Vite server (port 5173)..."
pkill -f "vite.*5173" 2>/dev/null || true
sleep 1
npm run dev:vite -- --port 5173 > /tmp/verifywise-frontend.log 2>&1 &
FRONTEND_PID=$!
echo "      Frontend PID: $FRONTEND_PID (log: /tmp/verifywise-frontend.log)"

# ── 8. Health check ───────────────────────────────────────────────────────────
echo ""
echo "Waiting for VerifyWise to become ready..."
"$SCRIPT_DIR/wait-for-verifywise.sh" --timeout 60 --url http://localhost:3000

# Quick frontend check
for i in 1 2 3 4 5 6 7 8 9 10; do
  if curl -sf http://localhost:5173/ > /dev/null 2>&1; then break; fi
  sleep 2
done
curl -sf http://localhost:5173/ > /dev/null && echo "Frontend OK at http://localhost:5173" \
  || echo "WARNING: Frontend may still be starting — check /tmp/verifywise-frontend.log"

echo ""
echo "VerifyWise is ready:"
echo "  Backend:   http://localhost:3000"
echo "  Frontend:  http://localhost:5173"
echo "  Admin:     verifywise@email.com / MyJH4rTm!@.45L0wm"
echo ""
echo "Stop with: ./scripts/stop-verifywise-local.sh"
