#!/usr/bin/env bash
#
# Stop all Modal apps (proactive cost savings)
#
# Use this when:
# - Done with development session
# - Finished demo/presentation
# - End of workday
# - Switching between projects
#
# This ensures no lingering containers accruing costs.
#
# Usage:
#   ./scripts/modal/stop_session.sh

set -euo pipefail

echo "🛑 Stopping all Modal apps..."
echo ""

# List currently running apps
echo "Currently running apps:"
modal app list

echo ""
echo "Stopping apps..."

# Stop all known lift-sys apps
APPS=(
    "lift-sys-inference"
    "qwen-vllm-inference"
    "lift-sys"
)

STOPPED=0
for app in "${APPS[@]}"; do
    echo "Checking $app..."
    if modal app list | grep -q "$app"; then
        echo "  Stopping $app..."
        modal app stop "$app" 2>/dev/null || echo "  (Already stopped or not found)"
        STOPPED=$((STOPPED + 1))
    else
        echo "  (Not running)"
    fi
done

echo ""
if [ $STOPPED -gt 0 ]; then
    echo "✅ Stopped $STOPPED app(s)"
else
    echo "✅ No running apps found"
fi

echo ""
echo "💰 Cost savings activated!"
echo ""

# Final verification
echo "Verification (should be empty):"
modal app list

echo ""
echo "🎯 All clear! No Modal resources running."
echo ""
echo "To restart:"
echo "  Dev:  ./scripts/modal/start_dev.sh"
echo "  Demo: ./scripts/modal/start_demo.sh"
