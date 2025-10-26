# Security Policy

## Reporting Security Issues

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to: [rand.arete@gmail.com](mailto:rand.arete@gmail.com)

Include as much information as possible:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

You should receive a response within 48 hours. If the issue is confirmed, we will release a patch as soon as possible.

---

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.3.x   | :white_check_mark: |
| 0.2.x   | :white_check_mark: |
| < 0.2   | :x:                |

---

## Secret Management Best Practices

### ✅ DO

**Use environment variables for credentials:**
```bash
# .env.local (gitignored)
SUPABASE_URL=https://yourproject.supabase.co
SUPABASE_ANON_KEY=your_actual_anon_key
SUPABASE_SERVICE_KEY=your_actual_service_key
DATABASE_URL=postgresql://postgres.yourproject:password@...
```

**Use template placeholders in documentation:**
```bash
# Good - clearly a template
DATABASE_URL=postgresql://postgres.<YOUR_PROJECT_REF>:<YOUR_PASSWORD>@...

# Also good - obvious placeholder
SUPABASE_ANON_KEY=<YOUR_ANON_KEY_HERE>
```

**Verify .gitignore before committing:**
```bash
# Check what will be committed
git status

# Verify .env files are ignored
git check-ignore .env.local  # Should output: .env.local
```

### ❌ DON'T

**Never commit actual credentials:**
```bash
# Bad - actual credentials
DATABASE_URL=postgresql://postgres.abc123:mysecretpassword@...
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.actual_jwt_token_here...
```

**Never use ambiguous placeholders that look like real secrets:**
```bash
# Bad - looks like it could be real
DATABASE_URL=postgresql://postgres.project:password@aws-1-us-east-1...

# Good - clearly fake
DATABASE_URL=postgresql://postgres.<YOUR_PROJECT>:<YOUR_PASSWORD>@aws-1-us-east-1...
```

**Never disable pre-commit hooks to bypass secret detection:**
```bash
# Bad - bypasses security checks
git commit --no-verify

# Good - fix the issue or update baseline if false positive
detect-secrets scan --baseline .secrets.baseline
```

---

## Secret Detection Tools

### Pre-Commit Hook (detect-secrets)

Automatically scans for secrets on every commit:

```bash
# Test manually
uv run detect-secrets scan

# Update baseline for new false positives
uv run detect-secrets scan --baseline .secrets.baseline

# Audit current baseline
uv run detect-secrets audit .secrets.baseline
```

### Local Scanning (gitleaks)

Optional local scanning tool:

```bash
# Install gitleaks
brew install gitleaks  # macOS
# or download from: https://github.com/gitleaks/gitleaks/releases

# Scan repository
gitleaks detect --config .gitleaks.toml

# Scan specific files
gitleaks detect --config .gitleaks.toml --source .

# Scan git history
gitleaks protect --config .gitleaks.toml
```

### GitHub Secret Scanning

Automatically enabled for this repository. False positives are excluded via `.github/secret_scanning.yml`.

If you receive an alert:
1. Verify if it's a real secret or template
2. If real: **IMMEDIATELY** rotate the credential and remove from git history
3. If template: Update to use `<YOUR_*>` placeholder format

---

## What to Do If You Accidentally Commit a Secret

### CRITICAL: Act Immediately

1. **Rotate the compromised credential** (first priority!)
   - Supabase: Dashboard → Settings → API → Reset keys
   - Modal: Dashboard → Secrets → Regenerate
   - Database: Change password via Supabase dashboard

2. **Remove from git history:**
   ```bash
   # Install git-filter-repo
   brew install git-filter-repo  # macOS

   # Create file with secret to remove
   echo "your-secret-value" > /tmp/secret.txt

   # Remove from history (DESTRUCTIVE - rewrites history)
   git filter-repo --replace-text /tmp/secret.txt --force

   # Re-add remote
   git remote add origin git@github.com:rand/lift-sys.git

   # Force push (coordinate with team first!)
   git push --force origin main
   ```

3. **Update .env.local** with new credentials

4. **Document the incident** (internal notes, not in public repo)

---

## Credential Types and Storage

### Environment Variables (.env.local - gitignored)

**Supabase:**
- `SUPABASE_URL` - Public project URL (OK to commit in docs as template)
- `SUPABASE_ANON_KEY` - Public anon key (OK in frontend, low privilege)
- `SUPABASE_SERVICE_KEY` - ⚠️ **NEVER COMMIT** (bypasses RLS, full access)
- `DATABASE_URL` - ⚠️ **NEVER COMMIT** (contains password)

**Modal:**
- Stored via Modal dashboard → Secrets
- Accessed via `modal.Secret.from_name()`
- Never hardcoded in code

**GitHub:**
- Stored via repository Settings → Secrets
- Used in GitHub Actions workflows
- Never logged or exposed

### Secret Precedence

```python
# 1. Environment variable (highest priority)
url = os.getenv("SUPABASE_URL")

# 2. Modal secret (for serverless functions)
@app.function(secrets=[modal.Secret.from_name("supabase")])
def my_function():
    url = os.getenv("SUPABASE_URL")  # Set by Modal from secret

# 3. Error if not set (no hardcoded defaults!)
if not url:
    raise ValueError("SUPABASE_URL not set")
```

---

## False Positive Handling

Template strings in documentation may trigger secret scanners. This is expected.

**Allowed patterns:**
- `<YOUR_PROJECT_REF>`, `<YOUR_PASSWORD>`, etc.
- `PROJECT_REF`, `PASSWORD@aws` in template context
- Truncated JWTs with `...`: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`

**Excluded paths:**
- `docs/**/*.md` - Documentation
- `tests/fixtures/**` - Test data
- `*_test.py`, `test_*.py` - Test files

**If you get a false positive:**
1. Verify it's actually a template (not a real secret)
2. Update template to use `<YOUR_*>` format
3. Run `detect-secrets scan` to update baseline
4. Commit updated `.secrets.baseline`

---

## Security Checklist for Contributors

Before committing:
- [ ] No actual credentials in code
- [ ] `.env.local` exists and is gitignored
- [ ] Templates use `<YOUR_*>` placeholder format
- [ ] Pre-commit hooks passed (`detect-secrets`)
- [ ] No secrets in commit message or diff

Before pushing:
- [ ] Double-check `git diff` for secrets
- [ ] Verify GitHub secret scanning won't trigger
- [ ] Modal/Supabase secrets are environment-based

Before deploying:
- [ ] Environment variables set in deployment platform
- [ ] Secrets rotated if exposed during development
- [ ] RLS policies enabled on database tables

---

## Additional Resources

- [GitHub Secret Scanning Docs](https://docs.github.com/en/code-security/secret-scanning)
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [Supabase Security Best Practices](https://supabase.com/docs/guides/platform/security)
- [Modal Secrets Documentation](https://modal.com/docs/guide/secrets)

---

## Incident Response

If a security incident occurs:
1. **Contain**: Rotate affected credentials immediately
2. **Investigate**: Determine scope of exposure
3. **Remediate**: Remove from git history if committed
4. **Document**: Record incident details (internal only)
5. **Notify**: Email security contact if user data affected
6. **Improve**: Update security practices to prevent recurrence

**Last Updated**: 2025-10-26
