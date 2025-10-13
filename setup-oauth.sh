#!/bin/bash
# OAuth Setup Helper Script

set -e

echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║                  lift-sys OAuth Configuration                      ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# Check if .env already exists
if [ -f .env ]; then
    echo "⚠️  .env file already exists. Backing up to .env.backup..."
    cp .env .env.backup
fi

# GitHub OAuth
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "GitHub OAuth Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Go to: https://github.com/settings/developers"
echo "2. Click 'New OAuth App'"
echo "3. Use these values:"
echo "   - Application name: lift-sys"
echo "   - Homepage URL: http://localhost:8000"
echo "   - Callback URL: http://localhost:8000/api/auth/callback/github"
echo ""
read -p "Have you created the GitHub OAuth app? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Please create the OAuth app first, then run this script again."
    exit 1
fi
echo ""

read -p "Enter your GitHub Client ID: " GITHUB_CLIENT_ID
read -p "Enter your GitHub Client Secret: " GITHUB_CLIENT_SECRET

# Write to .env
cat > .env <<EOF
# GitHub OAuth Configuration
GITHUB_CLIENT_ID="$GITHUB_CLIENT_ID"
GITHUB_CLIENT_SECRET="$GITHUB_CLIENT_SECRET"

# Backend Configuration
LIFT_SYS_CALLBACK_BASE="http://localhost:8000"
LIFT_SYS_SESSION_SECRET="$(openssl rand -hex 32)"

# Optional: Google OAuth (uncomment and configure if needed)
# GOOGLE_CLIENT_ID="your_google_client_id"
# GOOGLE_CLIENT_SECRET="your_google_client_secret"
EOF

# Frontend configuration
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Frontend Configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
read -p "Disable demo mode in frontend? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cat > frontend/.env.local <<EOF
# Disable demo mode - use real OAuth
VITE_DEMO_MODE=false
EOF
    echo "✅ Demo mode disabled - will use real OAuth"
else
    echo "ℹ️  Demo mode still enabled - OAuth available but demo still works"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║                    ✅ Configuration Complete!                       ║"
echo "╠════════════════════════════════════════════════════════════════════╣"
echo "║                                                                    ║"
echo "║  Next steps:                                                       ║"
echo "║                                                                    ║"
echo "║  1. Restart the servers:                                           ║"
echo "║     ./start.sh                                                     ║"
echo "║                                                                    ║"
echo "║  2. Open http://localhost:5173                                     ║"
echo "║                                                                    ║"
echo "║  3. Click 'Sign in with GitHub' to test OAuth!                     ║"
echo "║                                                                    ║"
echo "║  Your credentials are saved in:                                    ║"
echo "║  - Backend: .env                                                   ║"
echo "║  - Frontend: frontend/.env.local (if you disabled demo mode)      ║"
echo "║                                                                    ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""
