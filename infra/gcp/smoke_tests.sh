#!/bin/bash
# =============================================================================
# HVAC-ADS-2026: Smoke Tests (run ON the VM)
# =============================================================================
# This script runs basic smoke tests to verify the deployment is working.
# Run this script on the VM after bootstrap is complete.
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0

echo -e "${GREEN}=============================================================================${NC}"
echo -e "${GREEN}HVAC-ADS-2026: Smoke Tests${NC}"
echo -e "${GREEN}=============================================================================${NC}"
echo ""

# Helper function to run tests
run_test() {
    local test_name="$1"
    local test_command="$2"
    local expected_pattern="$3"

    echo -e "${YELLOW}TEST: ${test_name}${NC}"

    if output=$(eval "$test_command" 2>&1); then
        if echo "$output" | grep -q "$expected_pattern"; then
            echo -e "${GREEN}✓ PASS${NC}"
            echo ""
            ((PASSED++))
            return 0
        else
            echo -e "${RED}✗ FAIL - Output doesn't match expected pattern${NC}"
            echo "Expected pattern: $expected_pattern"
            echo "Actual output:"
            echo "$output"
            echo ""
            ((FAILED++))
            return 1
        fi
    else
        echo -e "${RED}✗ FAIL - Command failed${NC}"
        echo "$output"
        echo ""
        ((FAILED++))
        return 1
    fi
}

# -----------------------------------------------------------------------------
# Container Status Tests
# -----------------------------------------------------------------------------
echo -e "${YELLOW}=== Container Status ===${NC}"
echo ""

run_test "MCP container running" \
    "docker compose ps mcp | grep -i up" \
    "Up"

run_test "Baseline container running" \
    "docker compose ps baseline | grep -i up" \
    "Up"

# -----------------------------------------------------------------------------
# MCP Server Tests
# -----------------------------------------------------------------------------
echo -e "${YELLOW}=== MCP Server ===${NC}"
echo ""

run_test "MCP health endpoint" \
    "curl -sf http://localhost:8080/health" \
    "healthy"

run_test "MCP tools endpoint" \
    "curl -sf http://localhost:8080/tools" \
    "gsc_query"

run_test "MCP gsc_query stub" \
    "curl -sf -X POST http://localhost:8080/invoke/gsc_query -H 'Content-Type: application/json' -d '{\"site_url\":\"https://buycomfortdirect.com\"}'" \
    "NOT_IMPLEMENTED"

run_test "MCP indexing_publish stub" \
    "curl -sf -X POST http://localhost:8080/invoke/indexing_publish -H 'Content-Type: application/json' -d '{\"urls\":[\"https://buycomfortdirect.com/test\"]}'" \
    "NOT_IMPLEMENTED"

run_test "MCP twilio_events stub" \
    "curl -sf -X POST http://localhost:8080/invoke/twilio_events -H 'Content-Type: application/json' -d '{\"event_type\":\"calls\"}'" \
    "NOT_IMPLEMENTED"

# -----------------------------------------------------------------------------
# Baseline CLI Tests (READ-ONLY)
# -----------------------------------------------------------------------------
echo -e "${YELLOW}=== Baseline CLI ===${NC}"
echo ""

# Check if dump can be invoked (don't actually run it to avoid API calls)
run_test "Baseline container exec access" \
    "docker compose exec -T baseline ls -la /app/bin/dump" \
    "bin/dump"

run_test "Baseline Python environment" \
    "docker compose exec -T baseline python --version" \
    "Python 3"

run_test "Baseline snapshots directory" \
    "docker compose exec -T baseline ls -la /app/snapshots" \
    "snapshots"

run_test "Baseline reports directory" \
    "docker compose exec -T baseline ls -la /app/reports" \
    "reports"

run_test "Baseline plans directory" \
    "docker compose exec -T baseline ls -la /app/plans" \
    "plans"

# -----------------------------------------------------------------------------
# File System Tests
# -----------------------------------------------------------------------------
echo -e "${YELLOW}=== File System ===${NC}"
echo ""

run_test ".env file exists and secured" \
    "ls -la /opt/hvac-ads-2026/.env | grep -E '^-rw-------'" \
    "rw-------"

run_test "Core modules present" \
    "ls -la /opt/hvac-ads-2026/core/" \
    "dump"

run_test "Docker compose file present" \
    "ls -la /opt/hvac-ads-2026/docker-compose.yml" \
    "docker-compose.yml"

# -----------------------------------------------------------------------------
# Network Tests
# -----------------------------------------------------------------------------
echo -e "${YELLOW}=== Network ===${NC}"
echo ""

run_test "MCP port 8080 listening" \
    "ss -tlnp | grep :8080" \
    "8080"

run_test "DNS resolution" \
    "dig +short buycomfortdirect.com" \
    "[0-9]"

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
echo ""
echo -e "${GREEN}=============================================================================${NC}"
echo -e "${GREEN}SMOKE TEST RESULTS${NC}"
echo -e "${GREEN}=============================================================================${NC}"
echo ""
echo "Tests Passed: ${PASSED}"
echo "Tests Failed: ${FAILED}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ ALL TESTS PASSED${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Test MCP from your local machine:"
    echo "   curl http://\$(hostname -I | awk '{print \$1}'):8080/health"
    echo ""
    echo "2. Run a baseline dump (LIVE API call):"
    echo "   docker compose exec baseline bin/dump"
    echo ""
    echo "3. Generate a report:"
    echo "   docker compose exec baseline bin/report --latest"
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "1. Check container logs:"
    echo "   docker compose logs mcp"
    echo "   docker compose logs baseline"
    echo ""
    echo "2. Verify .env file has correct credentials:"
    echo "   sudo nano /opt/hvac-ads-2026/.env"
    echo ""
    echo "3. Restart containers:"
    echo "   docker compose restart"
    exit 1
fi
