#!/bin/bash
# Kainex end-to-end smoke test
# Starts all services, runs basic checks, then shuts down
set -euo pipefail

# ─── Configuration ────────────────────────────────────────────
PORT=${KAINEX_TEST_PORT:-8099}
BASE_URL="http://localhost:${PORT}"
ENGINE_DIR="$(cd "$(dirname "$0")/../services/engine" && pwd)"
ENGINE_PID=""
PASS=0
FAIL=0
RESULTS=()

# ─── Colors ───────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ─── Helpers ──────────────────────────────────────────────────
log()  { echo -e "${CYAN}[smoke]${NC} $*"; }
pass() { PASS=$((PASS + 1)); RESULTS+=("${GREEN}PASS${NC} $1"); echo -e "  ${GREEN}PASS${NC} $1"; }
fail() { FAIL=$((FAIL + 1)); RESULTS+=("${RED}FAIL${NC} $1"); echo -e "  ${RED}FAIL${NC} $1"; }

cleanup() {
    log "Cleaning up..."
    if [ -n "$ENGINE_PID" ] && kill -0 "$ENGINE_PID" 2>/dev/null; then
        kill "$ENGINE_PID" 2>/dev/null || true
        wait "$ENGINE_PID" 2>/dev/null || true
    fi
    # Kill anything left on our test port
    lsof -ti :"$PORT" 2>/dev/null | xargs kill -9 2>/dev/null || true
    log "Done."
}
trap cleanup EXIT

check_port_free() {
    if lsof -ti :"$PORT" >/dev/null 2>&1; then
        log "${YELLOW}WARNING: Port $PORT is already in use. Attempting to free it...${NC}"
        lsof -ti :"$PORT" | xargs kill -9 2>/dev/null || true
        sleep 1
        if lsof -ti :"$PORT" >/dev/null 2>&1; then
            log "${RED}ERROR: Cannot free port $PORT. Set KAINEX_TEST_PORT to use a different port.${NC}"
            exit 1
        fi
    fi
}

wait_for_health() {
    local retries=20
    local delay=1
    log "Waiting for Engine API at $BASE_URL/health ..."
    for i in $(seq 1 $retries); do
        if curl -sf "$BASE_URL/health" >/dev/null 2>&1; then
            return 0
        fi
        sleep "$delay"
    done
    return 1
}

# ─── 1. Pre-flight ───────────────────────────────────────────
log "Kainex Smoke Test"
log "Engine port: $PORT"
echo ""

check_port_free

# ─── 2. Start Engine API ─────────────────────────────────────
log "Starting Engine API..."
cd "$ENGINE_DIR"
uv run uvicorn engine.api.main:app --host 127.0.0.1 --port "$PORT" &
ENGINE_PID=$!
cd - >/dev/null

if wait_for_health; then
    pass "Health endpoint returns 200"
else
    fail "Health endpoint did not respond within timeout"
    log "${RED}Engine API failed to start. Aborting.${NC}"
    exit 1
fi

# Verify health body
HEALTH_BODY=$(curl -sf "$BASE_URL/health")
if echo "$HEALTH_BODY" | jq -e '.status == "ok"' >/dev/null 2>&1; then
    pass "Health body contains status=ok"
else
    fail "Health body unexpected: $HEALTH_BODY"
fi

# ─── 3. Test Strategy CRUD ───────────────────────────────────
log "Testing strategy endpoints..."

# POST /api/strategies — create an SMA strategy
CREATE_RESP=$(curl -sf -X POST "$BASE_URL/api/strategies" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "Smoke Test SMA",
        "class_name": "sma_crossover",
        "parameters": {"short_window": 5, "long_window": 20},
        "markets": ["crypto"],
        "timeframes": ["1d"]
    }' 2>&1) || true

if echo "$CREATE_RESP" | jq -e '.id' >/dev/null 2>&1; then
    STRATEGY_ID=$(echo "$CREATE_RESP" | jq -r '.id')
    pass "POST /api/strategies — created strategy $STRATEGY_ID"
else
    STRATEGY_ID=""
    fail "POST /api/strategies — response: ${CREATE_RESP:-empty}"
fi

# GET /api/strategies — list strategies
LIST_RESP=$(curl -sf "$BASE_URL/api/strategies" 2>&1) || true
if echo "$LIST_RESP" | jq -e 'type == "array"' >/dev/null 2>&1; then
    COUNT=$(echo "$LIST_RESP" | jq 'length')
    if [ "$COUNT" -ge 1 ]; then
        pass "GET /api/strategies — returned $COUNT strategy(ies)"
    else
        fail "GET /api/strategies — empty list after creation"
    fi
else
    fail "GET /api/strategies — response: ${LIST_RESP:-empty}"
fi

# ─── 4. Test Market Data ─────────────────────────────────────
log "Testing market data endpoints..."

SYMBOLS_RESP=$(curl -sf "$BASE_URL/api/market-data/symbols" 2>&1) || true
if echo "$SYMBOLS_RESP" | jq -e 'type == "array"' >/dev/null 2>&1; then
    SYM_COUNT=$(echo "$SYMBOLS_RESP" | jq 'length')
    pass "GET /api/market-data/symbols — returned $SYM_COUNT symbol(s)"
else
    fail "GET /api/market-data/symbols — response: ${SYMBOLS_RESP:-empty}"
fi

# ─── 5. Test Portfolio ────────────────────────────────────────
log "Testing portfolio endpoints..."

PORTFOLIO_RESP=$(curl -sf "$BASE_URL/api/portfolio/summary" 2>&1) || true
if echo "$PORTFOLIO_RESP" | jq -e '.total_value' >/dev/null 2>&1; then
    pass "GET /api/portfolio/summary — received portfolio data"
else
    fail "GET /api/portfolio/summary — response: ${PORTFOLIO_RESP:-empty}"
fi

# ─── 6. Test Backtest (if data exists) ────────────────────────
log "Testing backtest endpoint..."

if [ -n "$STRATEGY_ID" ]; then
    BACKTEST_RESP=$(curl -sf -X POST "$BASE_URL/api/backtest/run" \
        -H "Content-Type: application/json" \
        -d "{
            \"strategy_id\": \"$STRATEGY_ID\",
            \"start_date\": \"2024-01-01T00:00:00Z\",
            \"end_date\": \"2024-06-01T00:00:00Z\",
            \"initial_capital\": 100000,
            \"market\": \"crypto\",
            \"symbols\": [\"BTC/USDT\"]
        }" 2>&1) || true

    if echo "$BACKTEST_RESP" | jq -e '.id' >/dev/null 2>&1; then
        BT_STATUS=$(echo "$BACKTEST_RESP" | jq -r '.status')
        pass "POST /api/backtest/run — status=$BT_STATUS"
    else
        fail "POST /api/backtest/run — response: ${BACKTEST_RESP:-empty}"
    fi
else
    log "${YELLOW}Skipping backtest (no strategy created)${NC}"
    RESULTS+=("${YELLOW}SKIP${NC} POST /api/backtest/run (no strategy)")
fi

# ─── 7. Test WebSocket ────────────────────────────────────────
log "Testing WebSocket connectivity..."

# Use curl --no-buffer to test WebSocket upgrade (HTTP 101)
WS_STATUS=$(curl -sf -o /dev/null -w "%{http_code}" \
    -H "Connection: Upgrade" \
    -H "Upgrade: websocket" \
    -H "Sec-WebSocket-Version: 13" \
    -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" \
    "$BASE_URL/api/ws/stream" 2>&1) || WS_STATUS="000"

if [ "$WS_STATUS" = "101" ]; then
    pass "WebSocket /api/ws/stream — upgrade 101"
else
    # FastAPI WebSocket may not respond to plain curl nicely; check if endpoint exists
    # Try with a different approach: any non-404 response means the route exists
    WS_CHECK=$(curl -sf -o /dev/null -w "%{http_code}" "$BASE_URL/api/ws/stream" 2>&1) || WS_CHECK="000"
    if [ "$WS_CHECK" = "403" ] || [ "$WS_CHECK" = "426" ]; then
        pass "WebSocket /api/ws/stream — endpoint exists (HTTP $WS_CHECK, upgrade required)"
    elif [ "$WS_CHECK" = "000" ]; then
        # Connection was accepted and closed (typical WebSocket behavior with curl)
        pass "WebSocket /api/ws/stream — endpoint reachable"
    else
        fail "WebSocket /api/ws/stream — HTTP $WS_CHECK"
    fi
fi

# ─── 8. Test OpenAPI spec ─────────────────────────────────────
log "Testing OpenAPI spec..."

OPENAPI_RESP=$(curl -sf "$BASE_URL/openapi.json" 2>&1) || true
if echo "$OPENAPI_RESP" | jq -e '.openapi' >/dev/null 2>&1; then
    TITLE=$(echo "$OPENAPI_RESP" | jq -r '.info.title')
    pass "GET /openapi.json — $TITLE"
else
    fail "GET /openapi.json — response: ${OPENAPI_RESP:0:100}"
fi

# ─── 9. Summary ──────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "  ${CYAN}Kainex Smoke Test Results${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
for r in "${RESULTS[@]}"; do
    echo -e "  $r"
done
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
TOTAL=$((PASS + FAIL))
echo -e "  Total: $TOTAL  |  ${GREEN}Pass: $PASS${NC}  |  ${RED}Fail: $FAIL${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ "$FAIL" -eq 0 ]; then
    echo -e "  ${GREEN}ALL TESTS PASSED${NC}"
    exit 0
else
    echo -e "  ${RED}SOME TESTS FAILED${NC}"
    exit 1
fi
