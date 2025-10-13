# OAuth Quick Start Guide

## 🚀 Quick Setup (5 minutes)

### Option 1: Interactive Setup (Recommended)

Run the setup script and follow the prompts:

```bash
./setup-oauth.sh
```

### Option 2: Manual Setup

1. **Create GitHub OAuth App**
   - Go to: https://github.com/settings/developers
   - Click "New OAuth App"
   - Fill in:
     - Name: `lift-sys`
     - Homepage: `http://localhost:8000`
     - Callback: `http://localhost:8000/api/auth/callback/github`
   - Copy your Client ID and Secret

2. **Create `.env` file**:
   ```bash
   cat > .env <<'ENVFILE'
   GITHUB_CLIENT_ID="your_client_id_here"
   GITHUB_CLIENT_SECRET="your_secret_here"
   LIFT_SYS_CALLBACK_BASE="http://localhost:8000"
   LIFT_SYS_SESSION_SECRET="$(openssl rand -hex 32)"
   ENVFILE
   ```

3. **Disable demo mode** (optional):
   ```bash
   echo 'VITE_DEMO_MODE=false' > frontend/.env.local
   ```

4. **Restart servers**:
   ```bash
   ./start.sh
   ```

## ✅ Testing OAuth

1. Open http://localhost:5173
2. Click "Sign in with GitHub"
3. Authorize the app on GitHub
4. You'll be redirected back and logged in!

## 🔧 Troubleshooting

### "404 Not Found" when clicking Sign In

**Cause**: `.env` file not loaded or OAuth not configured

**Fix**:
```bash
# Check if .env exists
ls -la .env

# Check if environment variables are set
./start.sh
# Look for: "GitHub OAuth client not configured" in logs
```

### Still using demo mode

**Cause**: `VITE_DEMO_MODE` not disabled in frontend

**Fix**:
```bash
echo 'VITE_DEMO_MODE=false' > frontend/.env.local
cd frontend && npm run dev
```

### OAuth callback fails

**Cause**: Callback URL mismatch

**Fix**: Verify in GitHub OAuth app settings:
- Callback URL: `http://localhost:8000/api/auth/callback/github`
- Not: `http://localhost:5173/...`

## 📚 More Information

See `AUTHENTICATION.md` for full documentation including:
- Google OAuth setup
- Production deployment
- Environment variables reference
