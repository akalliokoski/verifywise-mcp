#!/usr/bin/env bash
# stop-verifywise-local.sh — Stop the locally-running VerifyWise stack (npm mode).
# Usage:
#   ./scripts/stop-verifywise-local.sh              # stop Node processes only
#   ./scripts/stop-verifywise-local.sh --services   # also stop postgres and redis

set -euo pipefail

STOP_SERVICES=false
for arg in "$@"; do
  case "$arg" in
    --services) STOP_SERVICES=true ;;
  esac
done

echo "Stopping VerifyWise local stack..."

pkill -f "node.*dist/index.js" 2>/dev/null && echo "  Backend stopped" || echo "  Backend was not running"
pkill -f "vite.*5173"           2>/dev/null && echo "  Frontend stopped" || echo "  Frontend was not running"

if $STOP_SERVICES; then
  service postgresql stop 2>&1 | grep -E "(stopped|done)" || true
  service redis-server stop 2>&1 | grep -E "(stopped|done)" || true
  echo "  PostgreSQL and Redis stopped"
fi

echo "Done."
