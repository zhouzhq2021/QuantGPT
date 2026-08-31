#!/usr/bin/env bash
set -u

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

UNIVERSE="${1:-hs300}"
FUNDAMENTAL_VARS="${PREWARM_FUNDAMENTAL_VARS:-core}"
LOG_FILE="$PROJECT_DIR/logs/scheduled_prewarm_${UNIVERSE}.log"
mkdir -p "$PROJECT_DIR/logs"
exec >>"$LOG_FILE" 2>&1

echo "[$(date '+%F %T %Z')] scheduled prewarm started: ${UNIVERSE}"

# One login + one quarter query is the only probe. Any non-zero result stops
# the run so an active BaoStock cooldown is not extended by repeated retries.
if ! "$PROJECT_DIR/.venv/bin/python" "$PROJECT_DIR/scripts/check_baostock.py"; then
    echo "[$(date '+%F %T %Z')] BaoStock probe failed; remote prewarm skipped"
    exit 42
fi

"$PROJECT_DIR/.venv/bin/python" "$PROJECT_DIR/scripts/prewarm.py" \
    --universe "$UNIVERSE" \
    --start 2018-01-01 \
    --end 2025-12-31 \
    --skip-market \
    --skip-dividends \
    --skip-factors \
    --fundamental-vars "$FUNDAMENTAL_VARS" \
    --batch-size 10 \
    --pause 2

echo "[$(date '+%F %T %Z')] scheduled prewarm completed: ${UNIVERSE}"
