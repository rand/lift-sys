# Claude Development Guidelines

## 1. Agentic Work
**Default:** Beads framework (https://github.com/steveyegge/beads)

Use for all agentic work and sub-agents. Break tasks into discrete beads with clear I/O. Chain beads for workflows, maintain state between beads.

**Session Start:** Update beads CLI at the start of each session:
```bash
go install github.com/steveyegge/beads/cmd/bd@latest
```

**No incomplete work:** Never leave `TODO`, mocks, or stubbed implementations. Either fully implement NOW or create explicit Beads plan to revisit when unblocked.

## 2. Critical Thinking
Don't default to "you're absolutely right" - challenge assumptions and decisions.

**Push back on:**
- Vague requirements that cause rework
- Tech choices that don't fit constraints
- Architectural decisions with hidden costs
- Missing error handling or edge cases
- Overly complex solutions

**Be constructive:** Offer alternatives with reasoning ("Consider X because Y"), flag potential issues, explain tradeoffs.

## 3. Language Stack

**Python** → `uv` (not pip/poetry)
```bash
uv init project && cd project && uv add package-name && uv run script.py
```

**Zig** → Latest stable, explicit allocators, comptime, `defer` cleanup

**Rust** → `cargo`, ownership/borrowing, `Result`/`Option`, iterators over loops, `anyhow` (apps), `thiserror` (libs), `tokio` (async)

**Go** → Standard toolchain, small interfaces, explicit errors, table-driven tests

**C/C++** → CMake 3.20+, C11/C17 or C++17/20, RAII, smart pointers, STL algorithms

**TypeScript** → Strict mode, ESM, `async/await`, Vitest/Jest
```json
{"compilerOptions": {"strict": true, "target": "ES2022", "module": "ESNext"}}
```

**Lean** → Lean 4, mathlib4, readable tactics, `snake_case`

## 4. Cloud Platforms

**AWS** → Lambda layers, S3 presigned URLs, DynamoDB single-table, IAM least privilege, Secrets Manager

**Cloudflare** → Workers (TypeScript), KV/R2/D1 bindings, `wrangler dev`

**Modal** → `@app.function(gpu="L40S")`, volumes for persistence, Modal secrets, `uv_pip_install()` for packages
  - **See**: `docs/MODAL_REFERENCE.md` for comprehensive guide
  - **Examples**: https://github.com/modal-labs/modal-examples (check 01-14 learning tracks)
  - **Recommended GPU**: L40S for best cost/performance
  - **Image building**: Use `uv_pip_install()`, pin versions, optimize caching

**Cloud Run** → Listen on PORT, multi-stage Dockerfile, Secret Manager, set concurrency

**WorkOS** → SSO (SAML/OAuth), Directory Sync, server-side API keys only

**Resend** → React Email templates, domain verification, batch sending

### Cost Management & Resource Cleanup

**Always spin down resources when not in use**, especially for development and testing:

**Modal**
- Use `modal app stop` to stop running apps
- Delete unused volumes: `modal volume list` → `modal volume delete [name]`
- Check running apps: `modal app list`
- Use `--timeout` parameter for auto-shutdown on functions

**AWS**
- Stop EC2 instances when not needed (not terminate, just stop)
- Delete unused EBS volumes and snapshots
- Use Lambda for dev/test (pay per invocation, no idle costs)
- Set CloudWatch alarms for unexpected usage

**Cloud Run**
- Scales to zero automatically (no manual cleanup needed)
- Set `max-instances` to prevent runaway costs: `gcloud run services update SERVICE --max-instances=10`
- Review Cloud Run logs for unexpected invocations

**Cloudflare Workers**
- Free tier scales to zero automatically
- Paid plans: review analytics for unexpected traffic

**General practices:**
- Tag resources with `environment: dev/test/prod` for easy identification
- Use infrastructure-as-code (Terraform, Pulumi) to tear down entire stacks: `terraform destroy`
- Set budget alerts in cloud provider consoles
- Schedule automatic shutdown for dev/test: cron jobs, AWS Instance Scheduler, Cloud Run jobs
- Delete after testing: databases, caches, load balancers (high idle costs)

**Development workflow:**
```bash
# Start work
modal app deploy                    # or equivalent

# End work session
modal app stop [app-name]          # Stop Modal apps
terraform destroy -target=module.dev  # or tear down dev environment
```

**Anti-pattern:** Leaving GPU instances, databases, or load balancers running overnight/weekends in dev/test environments.

## 5. Design Aesthetics

Inspired by: v0.dev (minimal, purposeful contrast), Firebase (high-density dashboards), Hex (scannable complexity), Principle (data-rich but breathable)

## 6. Project Initiation

**Gather requirements first - ASK, don't assume:**
- Functional: Problem, users, features, workflows, edge cases
- Technical: Language, framework, database, auth, integrations, performance
- Deploy: Platform, domain, environments, CI/CD
- Constraints: Budget, timeline, compliance, browser support
- Success: Metrics, KPIs, definition of done

**Confirm before coding:**
```
Building [PROJECT]:
- Tech: [stack]
- Deploy: [platform] at [domain]
- Timeline: [dates]
- Success: [criteria]
Confirmed?
```

## 7. Version Control & Git Workflow

**Keep GitHub synchronized:** Push changes regularly to keep remote up to date

### Branch Strategy

**Use branches for all work:**
- `main` - Production-ready code only
- `feature/*` - New features (e.g., `feature/modal-inference`, `feature/ir-versioning`)
- `fix/*` - Bug fixes (e.g., `fix/session-validation`)
- `refactor/*` - Code improvements (e.g., `refactor/provider-interface`)
- `docs/*` - Documentation updates (e.g., `docs/modal-guide`)

**Branch workflow:**
```bash
# Start new feature
git checkout -b feature/my-feature

# Work and commit frequently
git add . && git commit -m "Clear, descriptive message"

# Push branch to remote
git push -u origin feature/my-feature

# Create PR when ready
gh pr create --title "Add my feature" --body "Description..."

# After PR approved and merged
git checkout main && git pull
git branch -d feature/my-feature
```

### Commit Hygiene

**Good commits:**
- Atomic: One logical change per commit
- Descriptive: Clear what and why (not just what)
- Tested: Code works before committing
- Formatted: Pass pre-commit hooks (or use `--no-verify` with justification)

**Commit message format:**
```
Brief summary (50 chars or less)

Optional detailed explanation of what changed and why.
Include motivation, implementation notes, and impact.

- Bullet points for multiple changes
- Reference issues/beads: Fixes lift-sys-42
```

### Pull Request Process

**Before creating PR:**
1. Ensure branch is up to date: `git pull origin main` (or rebase)
2. All tests passing
3. Documentation updated
4. Beads updated with status
5. Self-review the diff

**PR Description:**
```markdown
## Summary
Brief overview of changes

## Changes
- List of specific changes
- Organized by category if needed

## Testing
- How changes were tested
- Test results

## Related
- Beads: lift-sys-XX
- Docs: Link to relevant documentation
```

**Reviewing PRs:**
- Read entire diff carefully
- Check for logic errors, edge cases, security issues
- Verify tests cover new functionality
- Ensure documentation is updated
- Test locally if substantial changes
- Ask questions if anything unclear
- Approve only when confident

**Merging PRs:**
- Squash small PRs (< 5 commits of iteration)
- Merge commit for feature branches (preserves history)
- Never force-push to `main`
- Delete branch after merge

### Daily Workflow

**Start of day:**
```bash
go install github.com/steveyegge/beads/cmd/bd@latest  # Update beads
git checkout main && git pull origin main              # Sync with remote
```

**End of session:**
```bash
git status                                             # Check for uncommitted work
git add -A && git commit -m "WIP: Description"        # Save progress if needed
git push origin <branch-name>                          # Push to remote
```

**Keep main updated:**
- Push to `main` directly only for: documentation fixes, minor typos, config updates
- Use branches + PRs for: features, refactors, bug fixes, breaking changes
- When in doubt, use a branch

### Anti-Patterns

❌ Force push to `main`
❌ Commit directly to `main` for features
❌ Large commits mixing multiple concerns
❌ Vague commit messages ("fix stuff", "updates")
❌ Merging PRs without review/testing
❌ Leaving branches un-pushed (risk of data loss)
❌ Forgetting to sync before starting work
❌ Not deleting merged branches

## 8. UI Development

**Always follow this sequence:**

1. Map states with Graphviz - all user states, transitions, edge cases, minimize dead ends

2. Browse shadcn blocks (https://ui.shadcn.com/blocks) FIRST for complete solutions

3. Use shadcn components (https://ui.shadcn.com/) SECOND for granular needs

4. Custom components ONLY with explicit permission - STOP and ASK if shadcn doesn't cover it

**Implementation steps:**
```
STEP 1: Browse https://ui.shadcn.com/blocks
STEP 2: Copy complete block unchanged
STEP 3: npx shadcn@latest add [components]
STEP 4: Customize colors/text/spacing ONLY
STEP 5: Add business logic
```

Plan loading states (skeleton) and error states (alerts) from the start.

**DO:** Change colors, text, spacing
**DON'T:** Restructure, change composition, rewrite

## 9. Anti-Patterns
❌ Assume tech stack
❌ Skip shadcn blocks exploration
❌ Restructure shadcn components
❌ Use pip/poetry instead of uv
❌ Skip loading/error states
❌ Deploy without environment config
❌ Leave TODOs, mocks, or stubs
❌ Accept vague requirements without pushback
❌ Agree reflexively without critical analysis
❌ Leave cloud resources running when not in use (dev/test)
❌ Commit directly to `main` for features (use branches)
❌ Force push to `main` or shared branches
❌ Merge PRs without careful review

## 10. Quick Reference

**Languages:** Python (uv), Zig, Rust (cargo), Go, C/C++ (CMake), TS (strict), Lean 4

**Cloud:** Workers/Modal (serverless), Cloud Run (containers), WorkOS (auth), Resend (email)
  - Modal details: `docs/MODAL_REFERENCE.md`

**UI:** shadcn blocks → shadcn components → custom (permission only), theme colors from https://ui.shadcn.com/themes

**Git:** Branches for features, PRs for review, keep `main` clean, sync daily

**Workflow:** Requirements → Confirm → Map flows → shadcn blocks → Implement

**When in doubt:** Ask questions, check shadcn blocks, test edge cases
