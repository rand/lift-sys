#!/usr/bin/env bash
#
# Start Modal inference in DEV mode (cost-optimized)
#
# Features:
# - 120s scaledown window (aggressive cost savings)
# - Cold starts acceptable (3-7 minutes)
# - Automatically stops after 2 minutes of inactivity
#
# Usage:
#   ./scripts/modal/start_dev.sh

set -euo pipefail

echo "🚀 Starting Modal inference in DEV mode..."
echo ""
echo "Configuration:"
echo "  Mode: DEV (cost-optimized)"
echo "  Scaledown: 120 seconds"
echo "  GPU: A100-80GB (~\$4/hr when active)"
echo "  Cost: ~\$0.13 per active request + 2min buffer"
echo ""
echo "💡 Cold starts expected (3-7 min first request)"
echo "💡 Remember to stop when done: ./scripts/modal/stop_session.sh"
echo ""

# Set DEV mode
export MODAL_MODE=dev

# Deploy the app
echo "Deploying lift-sys-inference..."
modal deploy lift_sys/inference/modal_app.py

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Health check:"
curl -s https://rand--health.modal.run | jq '.'

echo ""
echo "🎯 Ready for development!"
echo ""
echo "Test with:"
echo "  curl https://rand--warmup.modal.run"
echo ""
echo "Stop when done:"
echo "  ./scripts/modal/stop_session.sh"
