#!/usr/bin/env bash
set -u

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

UNIVERSE="${1:-hs300}"
FUNDAMENTAL_VARS="${PREWARM_FUNDAMENTAL_VARS:-core}"
SKIP_FUNDAMENTALS="${PREWARM_SKIP_FUNDAMENTALS:-0}"
INCLUDE_DIVIDENDS="${PREWARM_INCLUDE_DIVIDENDS:-0}"
SKIP_MARKET="${PREWARM_SKIP_MARKET:-1}"
REFRESH_FUNDAMENTALS="${PREWARM_REFRESH_FUNDAMENTALS:-0}"
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

ARGS=(
    --universe "$UNIVERSE"
    --start 2018-01-01
    --end 2025-12-31
    --skip-factors
    --batch-size 10
    --pause 2
)
if [ "$SKIP_MARKET" = "1" ]; then
    ARGS+=(--skip-market)
fi
if [ "$SKIP_FUNDAMENTALS" = "1" ]; then
    ARGS+=(--skip-fundamentals)
else
    ARGS+=(--fundamental-vars "$FUNDAMENTAL_VARS")
    if [ "$REFRESH_FUNDAMENTALS" = "1" ]; then
        ARGS+=(--refresh-fundamentals)
    fi
fi
if [ "$INCLUDE_DIVIDENDS" != "1" ]; then
    ARGS+=(--skip-dividends)
fi

"$PROJECT_DIR/.venv/bin/python" "$PROJECT_DIR/scripts/prewarm.py" "${ARGS[@]}"

echo "[$(date '+%F %T %Z')] scheduled prewarm completed: ${UNIVERSE}"
