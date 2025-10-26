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

# Get all deployed/active app IDs
DEPLOYED_APPS=$(modal app list --json 2>/dev/null | jq -r '.[] | select(.state == "deployed") | .app_id' 2>/dev/null || echo "")

STOPPED=0
if [ -z "$DEPLOYED_APPS" ]; then
    echo "No deployed apps found"
else
    for app_id in $DEPLOYED_APPS; do
        echo "Stopping $app_id..."
        modal app stop "$app_id" 2>/dev/null && STOPPED=$((STOPPED + 1)) || echo "  (Failed to stop)"
    done
fi

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
