#!/bin/bash
# Test script for DoWhy subprocess wrapper
# Tests fit_scm.py with various test cases

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PYTHON_EXEC="$PROJECT_ROOT/.venv-dowhy/bin/python"
FIT_SCRIPT="$SCRIPT_DIR/fit_scm.py"
TEST_FIXTURES="$PROJECT_ROOT/tests/fixtures/dowhy_traces"

echo "========================================"
echo "Testing DoWhy SCM Fitting Subprocess"
echo "========================================"
echo ""

# Check Python 3.11 venv exists
if [ ! -f "$PYTHON_EXEC" ]; then
    echo "ERROR: Python 3.11 venv not found at $PYTHON_EXEC"
    exit 1
fi

echo "Python executable: $PYTHON_EXEC"
echo "Fit script: $FIT_SCRIPT"
echo "Test fixtures: $TEST_FIXTURES"
echo ""

# Function to run test case
run_test() {
    local test_name=$1
    local test_file="$TEST_FIXTURES/${test_name}.json"

    if [ ! -f "$test_file" ]; then
        echo "❌ Test file not found: $test_file"
        return 1
    fi

    echo "Testing: $test_name"
    echo "  Input: $test_file"

    # Run subprocess
    local output=$(cat "$test_file" | "$PYTHON_EXEC" "$FIT_SCRIPT" 2>&1)
    local exit_code=$?

    # Parse status
    local status=$(echo "$output" | grep -o '"status": "[^"]*"' | head -1 | cut -d'"' -f4)

    echo "  Status: $status (exit code: $exit_code)"

    # Check for expected outcomes
    case $test_name in
        "linear_chain"|"multi_parent"|"code_execution"|"perfect_correlation"|"complex_dag")
            if [ "$status" = "success" ]; then
                echo "  ✅ PASS"
            else
                echo "  ❌ FAIL: Expected success, got $status"
                echo "$output" | head -20
                return 1
            fi
            ;;
        "insufficient_data")
            if [ "$status" = "warning" ]; then
                echo "  ✅ PASS"
            else
                echo "  ❌ FAIL: Expected warning, got $status"
                echo "$output" | head -20
                return 1
            fi
            ;;
        "noisy_data")
            if [ "$status" = "validation_failed" ] || [ "$status" = "success" ]; then
                echo "  ✅ PASS"
            else
                echo "  ❌ FAIL: Expected validation_failed or success, got $status"
                echo "$output" | head -20
                return 1
            fi
            ;;
        *)
            echo "  ℹ️  UNCHECKED (status: $status)"
            ;;
    esac

    # Show R² scores if available
    local r2_scores=$(echo "$output" | grep -o '"mean_r2": [0-9.]*' | cut -d' ' -f2)
    if [ -n "$r2_scores" ]; then
        echo "  Mean R²: $r2_scores"
    fi

    echo ""
}

# Run all test cases
echo "Running test cases..."
echo ""

test_cases=(
    "linear_chain"
    "multi_parent"
    "nonlinear"
    "insufficient_data"
    "noisy_data"
    "perfect_correlation"
    "code_execution"
    "validation_function"
    "complex_dag"
)

failed=0
passed=0

for test_case in "${test_cases[@]}"; do
    if run_test "$test_case"; then
        ((passed++))
    else
        ((failed++))
    fi
done

echo "========================================"
echo "Test Summary"
echo "========================================"
echo "Passed: $passed / ${#test_cases[@]}"
echo "Failed: $failed / ${#test_cases[@]}"
echo ""

if [ $failed -eq 0 ]; then
    echo "✅ All tests passed!"
    exit 0
else
    echo "❌ Some tests failed"
    exit 1
fi
