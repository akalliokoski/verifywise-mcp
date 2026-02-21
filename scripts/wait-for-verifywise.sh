#!/usr/bin/env bash
# wait-for-verifywise.sh — Poll the VerifyWise backend until it accepts requests.
# Exits 0 when ready, exits 1 on timeout.
# Usage: ./scripts/wait-for-verifywise.sh [--timeout 120] [--url http://localhost:3000]
set -euo pipefail

TIMEOUT=120
BACKEND_URL="http://localhost:3000"
POLL_INTERVAL=5

while [[ $# -gt 0 ]]; do
  case "$1" in
    --timeout) TIMEOUT="$2"; shift 2 ;;
    --url)     BACKEND_URL="$2"; shift 2 ;;
    *) shift ;;
  esac
done

HEALTH_URL="$BACKEND_URL/api/users/check-user-exists"
DEADLINE=$(( $(date +%s) + TIMEOUT ))

echo "Polling $HEALTH_URL (timeout: ${TIMEOUT}s)..."

while true; do
  # The endpoint returns 400 (no token) but proves the server is up.
  # Don't use -f so we accept any HTTP response including 4xx.
  if curl -s --max-time 5 "$HEALTH_URL" 2>/dev/null | grep -q "message"; then
    echo "VerifyWise backend is up at $BACKEND_URL"
    exit 0
  fi

  NOW=$(date +%s)
  if (( NOW >= DEADLINE )); then
    echo "ERROR: Timed out after ${TIMEOUT}s waiting for VerifyWise at $BACKEND_URL"
    exit 1
  fi

  REMAINING=$(( DEADLINE - NOW ))
  echo "  Not ready yet. Retrying in ${POLL_INTERVAL}s (${REMAINING}s remaining)..."
  sleep "$POLL_INTERVAL"
done
