#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# ContractOS — Postman / Newman Integration Test Runner
# ──────────────────────────────────────────────────────────────────────
#
# Usage:
#   ./postman/run_integration_tests.sh              # run all tests
#   ./postman/run_integration_tests.sh --folder "0 — Health & Config"
#   ./postman/run_integration_tests.sh --server     # start server + run tests
#
# Prerequisites:
#   npm install -g newman newman-reporter-htmlextra  (one-time)
#   pip install -e ".[dev]"                          (one-time)
#
# Environment variables:
#   CONTRACTOS_BASE_URL  — override base URL (default: http://127.0.0.1:8742)
#   ANTHROPIC_API_KEY    — required for Q&A tests with real LLM
#   ANTHROPIC_BASE_URL   — optional LiteLLM proxy URL
# ──────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COLLECTION="$SCRIPT_DIR/ContractOS.postman_collection.json"
ENVIRONMENT="$SCRIPT_DIR/ContractOS.postman_environment.json"
RESULTS_DIR="$SCRIPT_DIR/results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       ContractOS — Integration Test Runner              ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# ── Parse arguments ──────────────────────────────────────────────────
START_SERVER=false
FOLDER=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --server)   START_SERVER=true; shift ;;
        --folder)   FOLDER="$2"; shift 2 ;;
        *)          echo "Unknown option: $1"; exit 1 ;;
    esac
done

# ── Check prerequisites ─────────────────────────────────────────────
if ! command -v newman &> /dev/null; then
    echo -e "${RED}Error: newman not found. Install with:${NC}"
    echo "  npm install -g newman newman-reporter-htmlextra"
    exit 1
fi

if [ ! -f "$COLLECTION" ]; then
    echo -e "${RED}Error: Collection not found at $COLLECTION${NC}"
    exit 1
fi

# ── Create results directory ─────────────────────────────────────────
mkdir -p "$RESULTS_DIR"

# ── Optionally start the server ──────────────────────────────────────
SERVER_PID=""
BASE_URL="${CONTRACTOS_BASE_URL:-http://127.0.0.1:8742}"

if [ "$START_SERVER" = true ]; then
    echo -e "${YELLOW}Starting ContractOS server...${NC}"
    cd "$PROJECT_DIR"
    python -m uvicorn contractos.api.app:create_app \
        --host 127.0.0.1 --port 8742 --factory &
    SERVER_PID=$!
    echo "Server PID: $SERVER_PID"

    # Wait for server to be ready
    echo -n "Waiting for server"
    for i in $(seq 1 30); do
        if curl -s "$BASE_URL/health" > /dev/null 2>&1; then
            echo -e " ${GREEN}ready!${NC}"
            break
        fi
        echo -n "."
        sleep 1
    done

    if ! curl -s "$BASE_URL/health" > /dev/null 2>&1; then
        echo -e " ${RED}FAILED — server did not start${NC}"
        kill $SERVER_PID 2>/dev/null || true
        exit 1
    fi
fi

# ── Cleanup function ────────────────────────────────────────────────
cleanup() {
    if [ -n "$SERVER_PID" ]; then
        echo -e "\n${YELLOW}Stopping server (PID: $SERVER_PID)...${NC}"
        kill $SERVER_PID 2>/dev/null || true
    fi
}
trap cleanup EXIT

# ── Build newman command ─────────────────────────────────────────────
NEWMAN_CMD=(
    newman run "$COLLECTION"
    -e "$ENVIRONMENT"
    --env-var "base_url=$BASE_URL"
    --env-var "docx_fixture=$PROJECT_DIR/tests/fixtures/simple_procurement.docx"
    --env-var "pdf_fixture=$PROJECT_DIR/tests/fixtures/simple_nda.pdf"
    --env-var "complex_docx_fixture=$PROJECT_DIR/tests/fixtures/complex_it_outsourcing.docx"
    --env-var "complex_pdf_fixture=$PROJECT_DIR/tests/fixtures/complex_procurement_framework.pdf"
    --env-var "legalbench_nda_fixture=$PROJECT_DIR/tests/fixtures/legalbench_nda.docx"
    --env-var "cuad_license_fixture=$PROJECT_DIR/tests/fixtures/cuad_license_agreement.docx"
    --timeout-request 120000
    --reporters "cli,json"
    --reporter-json-export "$RESULTS_DIR/newman_results_${TIMESTAMP}.json"
)

# Add folder filter if specified
if [ -n "$FOLDER" ]; then
    NEWMAN_CMD+=(--folder "$FOLDER")
fi

# ── Run tests ────────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}Running integration tests...${NC}"
echo "  Collection: $COLLECTION"
echo "  Base URL:   $BASE_URL"
echo "  Results:    $RESULTS_DIR/newman_results_${TIMESTAMP}.json"
echo ""

cd "$PROJECT_DIR"
"${NEWMAN_CMD[@]}" && STATUS=0 || STATUS=$?

# ── Summary ──────────────────────────────────────────────────────────
echo ""
if [ $STATUS -eq 0 ]; then
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ALL INTEGRATION TESTS PASSED                           ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
else
    echo -e "${RED}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  SOME TESTS FAILED — see results above                  ║${NC}"
    echo -e "${RED}╚══════════════════════════════════════════════════════════╝${NC}"
fi

echo ""
echo "Results saved to: $RESULTS_DIR/newman_results_${TIMESTAMP}.json"

exit $STATUS
