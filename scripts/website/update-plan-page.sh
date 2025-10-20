#!/bin/bash
# Update the plan progress page on the lift-sys website
# Run this script after updating planning documents or beads

WEBSITE_DIR="/Users/rand/src/site-lift-sys"

echo "🔄 Updating plan progress page..."

# Check if website directory exists
if [ ! -d "$WEBSITE_DIR" ]; then
    echo "❌ Error: Website directory not found at $WEBSITE_DIR"
    exit 1
fi

# Change to website directory
cd "$WEBSITE_DIR" || exit 1

# Run the update command
npm run update:plan

if [ $? -eq 0 ]; then
    echo "✅ Plan progress page updated successfully!"
    echo ""
    echo "📄 Generated files:"
    echo "   - plan-data.js (data)"
    echo "   - plan_progress.html (page)"
    echo ""
    echo "🌐 View at: file://${WEBSITE_DIR}/plan_progress.html"
    echo ""
    echo "To deploy, copy to website and access at: /plan_progress.html"
else
    echo "❌ Error updating plan progress page"
    exit 1
fi
