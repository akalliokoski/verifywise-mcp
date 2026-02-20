#!/usr/bin/env bash
# stop-verifywise.sh — Stop the VerifyWise stack gracefully.
# Usage:
#   ./scripts/stop-verifywise.sh              # Stops dev stack, keeps volumes
#   ./scripts/stop-verifywise.sh --test       # Stops test stack, keeps volumes
#   ./scripts/stop-verifywise.sh --volumes    # Also removes volumes (destroys data)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

USE_TEST=false
REMOVE_VOLUMES=false

for arg in "$@"; do
  case "$arg" in
    --test)    USE_TEST=true ;;
    --volumes) REMOVE_VOLUMES=true ;;
  esac
done

if $USE_TEST; then
  COMPOSE_FILE="$REPO_ROOT/docker-compose.test.yml"
  echo "Stopping VerifyWise test stack..."
else
  COMPOSE_FILE="$REPO_ROOT/verifywise/docker-compose.yml"
  echo "Stopping VerifyWise dev stack..."
fi

if $REMOVE_VOLUMES; then
  echo "  (removing volumes)"
  docker compose -f "$COMPOSE_FILE" down -v
else
  docker compose -f "$COMPOSE_FILE" down
fi

echo "VerifyWise stack stopped."
