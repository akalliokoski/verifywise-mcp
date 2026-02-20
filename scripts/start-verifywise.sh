#!/usr/bin/env bash
# start-verifywise.sh — Start VerifyWise stack for local development or testing.
# Usage:
#   ./scripts/start-verifywise.sh           # Uses verifywise/docker-compose.yml (requires .env)
#   ./scripts/start-verifywise.sh --test    # Uses docker-compose.test.yml (test credentials)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

USE_TEST=false
for arg in "$@"; do
  case "$arg" in
    --test) USE_TEST=true ;;
  esac
done

if $USE_TEST; then
  COMPOSE_FILE="$REPO_ROOT/docker-compose.test.yml"
  echo "Starting VerifyWise (test mode) from $COMPOSE_FILE ..."
else
  COMPOSE_FILE="$REPO_ROOT/verifywise/docker-compose.yml"
  echo "Starting VerifyWise (dev mode) from $COMPOSE_FILE ..."
  if [ ! -f "$REPO_ROOT/verifywise/.env.dev" ]; then
    echo "ERROR: $REPO_ROOT/verifywise/.env.dev not found."
    echo "       Copy verifywise/.env.dev.example and fill in values."
    exit 1
  fi
fi

docker compose -f "$COMPOSE_FILE" up -d

echo "Waiting for VerifyWise to become healthy..."
"$SCRIPT_DIR/wait-for-verifywise.sh"

echo ""
echo "VerifyWise is ready:"
echo "  Frontend: http://localhost:8080"
echo "  Backend:  http://localhost:3000"
