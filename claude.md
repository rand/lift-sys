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
  - **Comprehensive skill**: Use `/zig-dev` for Zig projects, build.zig, testing, package management
  - See: Section 11 (Skills Reference) for detailed capabilities

**Rust** → `cargo`, ownership/borrowing, `Result`/`Option`, iterators over loops, `anyhow` (apps), `thiserror` (libs), `tokio` (async)

**Go** → Standard toolchain, small interfaces, explicit errors, table-driven tests
  - **TUI Development**: Use `/tui-development` for terminal UIs with Charm.sh (Bubble Tea, Lip Gloss, Bubbles)
  - See: Section 11 (Skills Reference) for TUI patterns

**C/C++** → CMake 3.20+, C11/C17 or C++17/20, RAII, smart pointers, STL algorithms

**TypeScript** → Strict mode, ESM, `async/await`, Vitest/Jest
```json
{"compilerOptions": {"strict": true, "target": "ES2022", "module": "ESNext"}}
```

**Swift** → iOS/macOS native development with SwiftUI, Swift 6 concurrency, async/await
  - **Comprehensive skill**: Use `/ios-native-dev` for iOS apps with SwiftUI, UIKit, SwiftData
  - See: Section 11 (Skills Reference) for iOS architecture patterns

**Lean** → Lean 4, mathlib4, readable tactics, `snake_case`

## 4. Cloud Platforms

**AWS** → Lambda layers, S3 presigned URLs, DynamoDB single-table, IAM least privilege, Secrets Manager

**Cloudflare** → Workers (TypeScript), KV/R2/D1 bindings, `wrangler dev`

**Modal** → `@app.function(gpu="L40S")`, volumes for persistence, Modal secrets, `uv_pip_install()` for packages
  - **Comprehensive skill**: Use `/modal-dev` for Modal app development, GPU workloads, web endpoints
  - **See**: `docs/MODAL_REFERENCE.md` for project-specific implementation details
  - **Examples**: https://github.com/modal-labs/modal-examples (check 01-14 learning tracks)
  - **Recommended GPU**: L40S for best cost/performance
  - **Image building**: Use `uv_pip_install()`, pin versions, optimize caching
  - See: Section 11 (Skills Reference) for Modal patterns and best practices

**Cloud Run** → Listen on PORT, multi-stage Dockerfile, Secret Manager, set concurrency

**WorkOS** → SSO (SAML/OAuth), Directory Sync, server-side API keys only

**Resend** → React Email templates, domain verification, batch sending

### Secure Networking & Infrastructure

**VPN & Secure Access** → Tailscale (WireGuard-based mesh), WireGuard for custom implementations
**Resilient Connectivity** → mosh (Mobile Shell) for unstable networks, SSH alternatives
**Service Security** → mTLS for service-to-service auth, certificate management
**NAT Traversal** → STUN/TURN, hole punching, peer-to-peer connectivity

- **Comprehensive skill**: Use `/secure-networking` for secure networking implementation
- Covers: Tailscale, mosh, mTLS, WireGuard, NAT traversal, zero-trust architectures
- See: Section 11 (Skills Reference) for networking security patterns

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

## 7. Testing Protocol

**MANDATORY: Read `.claude/testing-protocol.md` before running ANY validation tests**

This protocol prevents wasting time by running tests with stale code. Key rules:

1. **NEVER** run tests in background while making changes
2. **ALWAYS** kill background tests before making code changes
3. **ALWAYS** commit changes BEFORE starting validation tests
4. **ALWAYS** verify commit applied: `git log -1 --oneline`
5. **ALWAYS** use timestamped log files: `/tmp/test_$(date +%Y%m%d_%H%M%S).log`
6. **ALWAYS** check test timestamp vs commit timestamp before reporting results

**Correct sequence:**
```
CHANGE → COMMIT → VERIFY COMMITTED → KILL OLD TESTS → START NEW TEST
```

See `.claude/testing-protocol.md` for complete protocol and violation consequences.

## 8. Version Control & Git Workflow

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

**IMPORTANT - No Co-Author Attribution:**
- ❌ **NEVER** add "Co-Authored-By: Claude" or similar attribution to commits
- ❌ **NEVER** add "Generated with Claude Code" footers to commits
- ✅ Commits should appear as regular commits by the developer
- ✅ Keep commit messages professional and focused on the change

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

## 10. Anti-Patterns
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
❌ Start specialized work without activating relevant skill (e.g., Zig project without `/zig-dev`)
❌ **Run tests before committing code changes** (CRITICAL - see Testing Protocol)
❌ **Run tests in background while making changes** (CRITICAL - see Testing Protocol)
❌ **Report test results without verifying test used current code** (CRITICAL - see Testing Protocol)

## 11. Quick Reference

**Languages:** Python (uv), Zig (/zig-dev), Rust (cargo), Go (/tui-development), Swift (/ios-native-dev), C/C++ (CMake), TS (strict), Lean 4

**Cloud:** Modal (/modal-dev), Workers/Cloudflare, Cloud Run (containers), WorkOS (auth), Resend (email)
  - Modal details: `docs/MODAL_REFERENCE.md`

**Networking:** Tailscale, mosh, mTLS, WireGuard (/secure-networking for comprehensive guide)

**UI:** shadcn blocks → shadcn components → custom (permission only), theme colors from https://ui.shadcn.com/themes

**Git:** Branches for features, PRs for review, keep `main` clean, sync daily

**Workflow:** Requirements → Confirm → Map flows → shadcn blocks → Implement

**Skills:** Use slash commands (e.g., `/modal-dev`) to activate specialized knowledge - see Section 12

**When in doubt:** Ask questions, check shadcn blocks, test edge cases, activate relevant skill

## 12. Skills Reference

**Specialized knowledge domains available via slash commands** - These skills provide comprehensive, expert-level guidance for specific technologies and workflows. Activate them when working in their respective domains.

### `/zig-dev` - Zig Development Expert

**When to use:** Zig projects, build.zig, testing, package management, comptime, ZLS

**Capabilities:**
- Project setup and build configuration (build.zig, build.zig.zon)
- Testing patterns and test organization
- Package management and dependency handling
- Cross-compilation for multiple targets
- Memory management patterns (allocators, defer, errdefer)
- Comptime programming and generic functions
- C library integration and FFI
- ZLS configuration and editor integration
- Performance profiling and optimization
- Common troubleshooting and debugging

**Use when:** Creating Zig projects, configuring build systems, writing Zig code, managing dependencies, cross-compiling, or troubleshooting Zig-specific issues.

### `/modal-dev` - Modal.com Serverless Platform

**When to use:** Modal apps, GPU workloads, serverless functions, web endpoints, scheduled jobs

**Capabilities:**
- Modal app structure and function decorators
- GPU selection and optimization (T4, A10G, A100, H100, L40S)
- Image building with pip_install, apt_install, uv_pip_install
- Volume management for persistent storage
- Secret management and environment variables
- Web endpoints (ASGI, WSGI, FastAPI integration)
- Scheduled jobs (Cron, Period)
- Parallel execution with .map() and .starmap()
- Resource management and cost optimization
- Deployment workflows and CLI commands
- Troubleshooting common issues

**Use when:** Deploying ML models, building serverless APIs, running GPU workloads, creating scheduled jobs, or any Modal.com development.

### `/tui-development` - Terminal User Interfaces

**When to use:** Terminal apps, CLI tools with interactive UIs, dashboards, TUI development

**Capabilities:**
- **Go + Charm.sh ecosystem:**
  - Bubble Tea (Elm-inspired framework)
  - Lip Gloss (styling and layout)
  - Bubbles (pre-built components)
  - Harmonica (animations)
  - Glamour (markdown rendering)
- **Rust + Ratatui:**
  - Widget-based UI construction
  - Layout system with constraints
  - Event handling and input
  - Stateful widgets
  - Crossterm/termion backends
- Architecture patterns (MVC, message passing)
- State management and navigation
- Performance optimization
- Cross-platform compatibility
- Testing strategies

**Use when:** Building terminal applications, interactive CLIs, monitoring dashboards, file managers, or any text-based user interface.

### `/secure-networking` - Secure & Resilient Networking

**When to use:** VPNs, mTLS, secure connectivity, NAT traversal, network security

**Capabilities:**
- **VPN & Overlay Networks:**
  - Tailscale (WireGuard mesh VPN)
  - WireGuard configuration
  - Zero-config networking
- **Resilient Connectivity:**
  - mosh (Mobile Shell) for unstable networks
  - Connection resilience patterns
  - SSH alternatives
- **Service Security:**
  - Mutual TLS (mTLS) implementation
  - Certificate management (cert-manager, cfssl, step-ca)
  - Zero-trust architectures
- **NAT Traversal:**
  - STUN/TURN protocols
  - Hole punching techniques
  - Peer-to-peer connectivity
- Security best practices and threat modeling
- Network resilience patterns (retries, circuit breakers)
- Implementation across languages (Go, Python, Rust, Node.js)

**Use when:** Setting up VPNs, implementing mTLS, building resilient networked services, NAT traversal, or any secure networking task.

### `/ios-native-dev` - iOS Native Development

**When to use:** iOS apps, SwiftUI, UIKit, Xcode projects, Apple platforms

**Capabilities:**
- **Modern iOS development (iOS 17+, Xcode 15+):**
  - SwiftUI 5.0+ (primary UI framework)
  - Swift 6.0+ with strict concurrency
  - UIKit integration when needed
- **Architecture & Patterns:**
  - MVVM with Observation framework
  - State management (@State, @Observable, @Environment)
  - Dependency injection patterns
- **Modern Features:**
  - NavigationStack for type-safe navigation
  - SwiftData for persistence
  - Swift Charts for visualization
  - Async/await and structured concurrency
- **Integration:**
  - UIKit wrapping (UIViewRepresentable)
  - SwiftUI in UIKit (UIHostingController)
  - Third-party library integration
- Testing (Swift Testing, XCTest, UI tests)
- Performance optimization
- App architecture and project structure
- Common patterns and best practices

**Use when:** Building iOS apps, working with SwiftUI or UIKit, implementing iOS features, architecting iOS solutions, or iOS-specific development.

## How to Use Skills

### Explicit Activation
When you encounter a task that matches a skill's domain, mention it:
- "I need to set up a Zig project" → I'll use `/zig-dev`
- "Help me deploy this to Modal" → I'll use `/modal-dev`
- "Build a terminal dashboard" → I'll use `/tui-development`

### Auto-Detection
Skills are automatically activated when working with relevant files or technologies:
- Working with `.zig` files → `/zig-dev` activates
- Working with Modal code → `/modal-dev` activates
- Building terminal UIs → `/tui-development` activates

### Skill Composition
Multiple skills can work together:
- `/zig-dev` + `/secure-networking` for a Zig-based VPN client
- `/modal-dev` + `/secure-networking` for secure Modal endpoints
- `/tui-development` + `/secure-networking` for a mosh-like terminal application

### Best Practice
**Always activate the relevant skill at the start of specialized work** to ensure comprehensive, expert-level guidance throughout the task.
