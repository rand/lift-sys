# Authentication Setup

lift-sys supports OAuth authentication with GitHub and Google. For local development, a **demo mode** is available that bypasses OAuth.

## Demo Mode (Local Development)

Demo mode is **automatically enabled** in development (`npm run dev`). No configuration required!

### How it works:
1. Click "Sign in with GitHub" or "Sign in with Google"
2. Instead of redirecting to OAuth, you'll be logged in immediately with a mock user
3. The session persists across page refreshes
4. Backend API calls work without authentication errors

### Demo User Details:
- **ID**: `demo:github-user` or `demo:google-user`
- **Email**: `demo@github.com` or `demo@google.com`
- **Name**: "Demo GitHub User" or "Demo Google User"

## Production OAuth Setup

For production deployment, you need to configure OAuth providers:

### GitHub OAuth

1. **Create a GitHub OAuth App**:
   - Go to https://github.com/settings/developers
   - Click "New OAuth App"
   - Set **Application name**: "lift-sys"
   - Set **Homepage URL**: `http://localhost:8000` (or your domain)
   - Set **Authorization callback URL**: `http://localhost:8000/api/auth/callback/github`
   - Click "Register application"

2. **Configure Environment Variables**:
   ```bash
   export GITHUB_CLIENT_ID="your_github_client_id"
   export GITHUB_CLIENT_SECRET="your_github_client_secret"
   export LIFT_SYS_CALLBACK_BASE="http://localhost:8000"
   ```

3. **Restart the Backend**:
   ```bash
   ./start.sh
   ```

### Google OAuth

1. **Create Google OAuth Credentials**:
   - Go to https://console.cloud.google.com/apis/credentials
   - Create a new project (if needed)
   - Click "Create Credentials" > "OAuth client ID"
   - Set **Application type**: "Web application"
   - Add **Authorized redirect URIs**: `http://localhost:8000/api/auth/callback/google`
   - Click "Create"

2. **Configure Environment Variables**:
   ```bash
   export GOOGLE_CLIENT_ID="your_google_client_id"
   export GOOGLE_CLIENT_SECRET="your_google_client_secret"
   export LIFT_SYS_CALLBACK_BASE="http://localhost:8000"
   ```

3. **Restart the Backend**:
   ```bash
   ./start.sh
   ```

## Disabling Demo Mode

To test production OAuth locally:

1. **Create frontend `.env.local`**:
   ```bash
   VITE_DEMO_MODE=false
   ```

2. **Configure OAuth credentials** (see above)

3. **Restart both servers**:
   ```bash
   ./start.sh
   ```

## Environment Variables Reference

### Backend
- `GITHUB_CLIENT_ID` - GitHub OAuth client ID
- `GITHUB_CLIENT_SECRET` - GitHub OAuth client secret
- `GOOGLE_CLIENT_ID` - Google OAuth client ID
- `GOOGLE_CLIENT_SECRET` - Google OAuth client secret
- `LIFT_SYS_CALLBACK_BASE` - Base URL for OAuth callbacks (default: `http://localhost:8000`)
- `LIFT_SYS_SESSION_SECRET` - Session encryption secret (auto-generated if not set)
- `LIFT_SYS_ENABLE_DEMO_USER_HEADER` - Enable `x-demo-user` header for testing (default: `0`)

### Frontend
- `VITE_DEMO_MODE` - Override demo mode (default: auto-enabled in dev, disabled in prod)

## Troubleshooting

### "404 Not Found" on GitHub Login

**Cause**: GitHub OAuth credentials not configured.

**Solutions**:
1. **Use demo mode** (default in dev): Just click sign in - no OAuth needed!
2. **Configure OAuth**: Follow "GitHub OAuth" setup above

### Session Not Persisting

**In demo mode**: Sessions persist in `localStorage`. Clear browser storage to reset.

**In production**: Check that `LIFT_SYS_SESSION_SECRET` is set and backend is running.

### Frontend Still Redirecting to OAuth in Dev

**Cause**: `VITE_DEMO_MODE=false` might be set.

**Solution**: Remove `.env.local` or set `VITE_DEMO_MODE=true`
