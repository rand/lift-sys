#!/bin/bash
#
# Warm-up script for Modal inference endpoint
#
# Purpose: Pre-load the 32B model to avoid 7-minute cold starts during testing/benchmarks
#
# Usage:
#   ./scripts/modal/warmup_modal.sh          # Warm up and wait
#   ./scripts/modal/warmup_modal.sh --async  # Warm up in background
#
# Cold start times:
#   - First time: ~7 minutes (model loading + torch compilation)
#   - With torch cache: ~5 minutes (model loading, cached compilation)
#   - With eager mode (VLLM_EAGER=1): ~5 minutes (model loading, no compilation)
#
# After warm-up, requests complete in 2-10 seconds.

set -e  # Exit on error

# Configuration
WARMUP_URL="${MODAL_WARMUP_URL:-https://rand--warmup.modal.run}"
TIMEOUT=600  # 10 minutes (covers 7min cold start + buffer)
ASYNC_MODE=false

# Parse arguments
if [[ "$1" == "--async" ]]; then
    ASYNC_MODE=true
fi

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🚀 Warming up Modal inference endpoint...${NC}"
echo "   Endpoint: $WARMUP_URL"
echo "   Timeout: ${TIMEOUT}s"
echo ""

if [[ "$ASYNC_MODE" == "true" ]]; then
    echo -e "${YELLOW}⏳ Starting warm-up in background...${NC}"
    echo "   Monitor progress: tail -f /tmp/modal_warmup_\$(date +%Y%m%d).log"

    LOG_FILE="/tmp/modal_warmup_$(date +%Y%m%d_%H%M%S).log"

    # Run in background, log to file
    (
        echo "[$(date)] Starting warm-up request..."
        RESPONSE=$(curl -s -w "\n%{http_code}\n%{time_total}" --max-time "$TIMEOUT" "$WARMUP_URL" 2>&1)
        HTTP_CODE=$(echo "$RESPONSE" | tail -2 | head -1)
        TIME_TOTAL=$(echo "$RESPONSE" | tail -1)
        BODY=$(echo "$RESPONSE" | head -n -2)

        if [[ "$HTTP_CODE" == "200" ]]; then
            echo "[$(date)] ✅ Warm-up successful!"
            echo "   Response: $BODY"
            echo "   Time: ${TIME_TOTAL}s"
        else
            echo "[$(date)] ❌ Warm-up failed!"
            echo "   HTTP code: $HTTP_CODE"
            echo "   Response: $BODY"
            exit 1
        fi
    ) > "$LOG_FILE" 2>&1 &

    echo -e "${GREEN}✓ Warm-up started in background (PID: $!)${NC}"
    echo "   Log file: $LOG_FILE"
    exit 0
fi

# Synchronous warm-up with progress
echo -e "${YELLOW}⏳ Sending warm-up request (this may take 5-7 minutes on cold start)...${NC}"
START_TIME=$(date +%s)

# Show progress dots while waiting
(
    while kill -0 $$ 2>/dev/null; do
        echo -n "."
        sleep 5
    done
) &
PROGRESS_PID=$!

# Make the request
RESPONSE=$(curl -s -w "\n%{http_code}\n%{time_total}" --max-time "$TIMEOUT" "$WARMUP_URL" 2>&1) || {
    kill $PROGRESS_PID 2>/dev/null
    echo ""
    echo -e "${RED}❌ Warm-up request failed (timeout or network error)${NC}"
    exit 1
}

# Stop progress indicator
kill $PROGRESS_PID 2>/dev/null
echo ""

# Parse response
HTTP_CODE=$(echo "$RESPONSE" | tail -2 | head -1)
TIME_TOTAL=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -2)

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

if [[ "$HTTP_CODE" == "200" ]]; then
    echo -e "${GREEN}✅ Modal endpoint is warm and ready!${NC}"
    echo ""
    echo "📊 Warm-up Statistics:"
    echo "   HTTP Status: $HTTP_CODE"
    echo "   Response Time: ${TIME_TOTAL}s"
    echo "   Wall Clock Time: ${DURATION}s"
    echo ""
    echo "📄 Response:"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
    echo ""
    echo -e "${GREEN}✓ Ready for fast inference (2-10s per request)${NC}"
    exit 0
else
    echo -e "${RED}❌ Warm-up failed!${NC}"
    echo "   HTTP Status: $HTTP_CODE"
    echo "   Response: $BODY"
    exit 1
fi
