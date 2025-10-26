#!/usr/bin/env bash
#
# Start Modal inference in DEMO mode (presentation-optimized)
#
# Features:
# - 600s (10 min) scaledown window
# - Minimizes cold starts during demos
# - Good for presentations, user testing, live demos
#
# Usage:
#   ./scripts/modal/start_demo.sh
#
# Important: Remember to stop after demo!
#   ./scripts/modal/stop_session.sh

set -euo pipefail

echo "🎬 Starting Modal inference in DEMO mode..."
echo ""
echo "Configuration:"
echo "  Mode: DEMO (presentation-optimized)"
echo "  Scaledown: 600 seconds (10 minutes)"
echo "  GPU: A100-80GB (~\$4/hr when active)"
echo "  Cost: ~\$0.67 per request + 10min buffer"
echo ""
echo "⚡ Stays warm for 10 minutes between requests"
echo "🎯 Ideal for demos, presentations, user testing"
echo ""
echo "⚠️  IMPORTANT: Stop after demo to avoid costs!"
echo "    ./scripts/modal/stop_session.sh"
echo ""

# Set DEMO mode
export MODAL_MODE=demo

# Deploy the app
echo "Deploying lift-sys-inference..."
modal deploy lift_sys/inference/modal_app.py

echo ""
echo "✅ Deployment complete!"
echo ""

# Health check
echo "Health check:"
curl -s https://rand--health.modal.run | jq '.'

echo ""
echo "🔥 Warming up model (this takes 3-7 minutes)..."
echo "   Please wait for model to load..."
curl -s https://rand--warmup.modal.run | jq '.'

echo ""
echo "✅ Model warmed up and ready!"
echo ""
echo "🎬 Ready for demo! Container stays warm for 10 minutes."
echo ""
echo "When demo is complete, STOP THE APP:"
echo "  ./scripts/modal/stop_session.sh"
