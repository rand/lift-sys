# Claude Development Guidelines

> **Critical Success Principle**: Following these guidelines is not optional. Each section contains decision trees, mandatory checkpoints, and anti-patterns that protect against wasted time and technical debt.

---

## Table of Contents
1. [Core Workflow: Agentic Work](#1-core-workflow-agentic-work)
2. [Critical Thinking & Pushback](#2-critical-thinking--pushback)
3. [Language Stack & Tooling](#3-language-stack--tooling)
4. [Cloud Platforms & Infrastructure](#4-cloud-platforms--infrastructure)
5. [Project Initiation Protocol](#5-project-initiation-protocol)
6. [Testing & Validation](#6-testing--validation)
7. [Version Control & Git](#7-version-control--git)
8. [Frontend Development](#8-frontend-development)
9. [Skills System](#9-skills-system)
10. [Anti-Patterns & Violations](#10-anti-patterns--violations)
11. [Quick Reference](#11-quick-reference)

---

## 1. Core Workflow: Agentic Work

### Primary Framework: Beads

**Mandatory for**: All agentic work, sub-agents, multi-session tasks, complex workflows

**Framework URL**: https://github.com/steveyegge/beads

### Session Start Protocol

```bash
# STEP 1: Update beads CLI (MANDATORY at session start)
go install github.com/steveyegge/beads/cmd/bd@latest

# STEP 2: Verify installation
bd version

# STEP 3: If in existing project, import state
bd import -i .beads/issues.jsonl

# STEP 4: Check ready work
bd ready --json --limit 5
```

### Core Workflow Pattern

```mermaid
graph TD
    A[Session Start] --> B[Import State: bd import]
    B --> C[Check Ready Work: bd ready]
    C --> D{Have Ready Work?}
    D -->|Yes| E[Claim Task: bd update ID --status in_progress]
    D -->|No| F[Create New Work: bd create]
    E --> G[Execute & Discover]
    G --> H{Discover Sub-tasks?}
    H -->|Yes| I[File Immediately: bd create + bd dep add]
    H -->|No| J[Continue]
    I --> J
    J --> K{Task Complete?}
    K -->|Yes| L[Close: bd close ID --reason]
    K -->|No| M{Context Bloat?}
    M -->|Yes| N[/compact or /context]
    M -->|No| G
    L --> O[Export State: bd export]
    O --> P[Commit: git add + commit]
```

### Context Management (Critical Skill)

**ACTIVATE**: `/beads-context` skill when working with bd commands or multi-session work

**Strategic /context Usage** (Preserve State):
- Before working on complex issues
- After discovering significant new work
- Before major refactoring
- When switching between unrelated issues
- After resolving merge conflicts

**Strategic /compact Usage** (Compress State):
- After completing an issue
- After routine operations (bd list, bd show)
- When context approaches 75% full
- After bulk issue creation
- During long troubleshooting sessions

### Non-Negotiable Rules

1. **NEVER** leave TODO, mocks, or stubs → Either implement NOW or create explicit Beads issue
2. **ALWAYS** use `--json` flag with bd commands for parseable output
3. **ALWAYS** export state before ending session: `bd export -o .beads/issues.jsonl`
4. **ALWAYS** commit .beads/issues.jsonl to git for version control

---

## 2. Critical Thinking & Pushback

### When to Push Back (MANDATORY)

You MUST challenge these situations:

```
TRIGGER                          → RESPONSE
────────────────────────────────────────────────────────
Vague requirements              → "Let's clarify X, Y, Z first"
Poor tech choice                → "Consider [alternative] because [reason]"
Missing error handling          → "This needs error handling for [cases]"
Overly complex solution         → "Simpler approach: [alternative]"
Hidden architectural costs      → "This will cause [problem] because [reason]"
Scalability issues              → "This won't scale past [limit] due to [constraint]"
Security vulnerabilities        → "This exposes [risk]. Use [secure pattern] instead"
Missing edge cases              → "What happens when [edge case]?"
```

### Constructive Challenge Pattern

```
WRONG: "You're absolutely right!"
RIGHT: "Consider X because Y. Here's the tradeoff: [analysis]"

WRONG: "That won't work."
RIGHT: "That approach has [limitation]. Alternative: [solution] with [benefit]"
```

### Decision Framework

```
Question asked
    ↓
Is requirement clear?
    ├─ No → ASK for clarification
    ↓
Is tech choice optimal?
    ├─ No → SUGGEST better alternative with reasoning
    ↓
Are edge cases handled?
    ├─ No → FLAG missing cases
    ↓
Is solution maintainable?
    ├─ No → PROPOSE simpler approach
    ↓
Proceed with implementation
```

---

## 3. Language Stack & Tooling

### Python → UV (MANDATORY)

```bash
# CORRECT
uv init project && cd project
uv add package-name
uv run script.py

# WRONG - DO NOT USE
pip install package-name        # ❌
poetry add package-name         # ❌
```

**Skill**: No specific skill needed (standard workflow)

### Zig → Comprehensive Skill Required

**ACTIVATE**: `/zig-dev` skill for ANY Zig work

**Skill covers**:
- Project setup (build.zig, build.zig.zon)
- Memory management (allocators, defer, errdefer)
- Testing patterns
- Cross-compilation
- Comptime programming
- C library integration

**Standards**:
- Latest stable version (0.13.x+)
- Explicit allocators (never implicit allocation)
- Comptime for zero-cost abstractions
- defer/errdefer for cleanup

### Rust → Standard Patterns

```bash
cargo new project-name
cargo add anyhow thiserror tokio
```

**Standards**:
- Ownership/borrowing first
- `Result<T, E>` and `Option<T>` over exceptions
- Iterators over loops
- `anyhow` for applications, `thiserror` for libraries
- `tokio` for async runtime

**Skill**: No specific skill needed

### Go → TUI Development Skill Available

**ACTIVATE**: `/tui-development` for terminal UIs

**Standards**:
- Small interfaces (1-3 methods)
- Explicit error returns (not panic)
- Table-driven tests
- Standard toolchain (no custom build tools)

**TUI Framework**: Charm.sh (Bubble Tea + Lip Gloss + Bubbles)

### TypeScript → Strict Configuration

**Mandatory tsconfig.json**:
```json
{
  "compilerOptions": {
    "strict": true,
    "target": "ES2022",
    "module": "ESNext",
    "esModuleInterop": true,
    "skipLibCheck": false,
    "forceConsistentCasingInFileNames": true
  }
}
```

**Standards**:
- Strict mode (non-negotiable)
- async/await over promises
- ESM imports
- Vitest or Jest for testing

### Swift → iOS Native Skill Required

**ACTIVATE**: `/ios-native-dev` for iOS development

**Skill covers**:
- SwiftUI 5.0+ patterns
- Swift 6.0 concurrency
- MVVM architecture
- SwiftData, Charts, Navigation
- UIKit integration

**Standards**:
- SwiftUI first (UIKit only when necessary)
- Async/await over completion handlers
- Observation framework for state
- iOS 17.0+ minimum target

### C/C++ → Modern Standards

**Standards**:
- CMake 3.20+ for build
- C11/C17 or C++17/20
- RAII for resource management
- Smart pointers (shared_ptr, unique_ptr)
- STL algorithms over raw loops

### Lean → Proof Development

**Standards**:
- Lean 4 with mathlib4
- Readable tactics (avoid proof golf)
- snake_case naming
- Comprehensive documentation

---

## 4. Cloud Platforms & Infrastructure

### Modal.com → Comprehensive Skill Required

**ACTIVATE**: `/modal-dev` for ANY Modal work

**Skill covers**:
- App structure and decorators
- GPU selection (L40S recommended for cost/performance)
- Image building (uv_pip_install preferred)
- Volume management
- Web endpoints (FastAPI integration)
- Scheduled jobs
- Resource optimization

**Reference**: Check `docs/MODAL_REFERENCE.md` for project-specific patterns

**Best Practices**:
```python
# Image building - use uv_pip_install
image = modal.Image.debian_slim().uv_pip_install(
    "torch==2.1.0",
    "transformers==4.35.0"
)

# GPU selection - L40S for best cost/performance
@app.function(gpu="l40s")
def inference(input: str) -> str:
    ...

# Auto-shutdown for cost control
@app.function(gpu="l40s", timeout=300)
def batch_job():
    ...
```

**Examples**: https://github.com/modal-labs/modal-examples (tracks 01-14)

### Cloudflare Workers

**Standards**:
- TypeScript for worker code
- KV/R2/D1 bindings for storage
- `wrangler dev` for local development
- Environment variables via wrangler.toml

### AWS Best Practices

**Standards**:
- Lambda layers for shared dependencies
- S3 presigned URLs for temporary access
- DynamoDB single-table design
- IAM least privilege
- Secrets Manager for credentials

### Secure Networking → Comprehensive Skill Required

**ACTIVATE**: `/secure-networking` for VPN, mTLS, or network security

**Skill covers**:
- Tailscale (WireGuard mesh VPN)
- mosh (resilient SSH alternative)
- mTLS implementation
- NAT traversal (STUN/TURN)
- Zero-trust architectures
- Certificate management

**Use when**: Setting up VPNs, implementing service-to-service auth, building resilient networked services

### Cost Management (CRITICAL)

**MANDATORY: Spin down resources when not in use**

```bash
# Modal
modal app stop [app-name]
modal volume delete [unused-volume]

# AWS
aws ec2 stop-instances --instance-ids [id]  # Stop, don't terminate
aws ec2 describe-volumes --filters "Name=status,Values=available" | jq '.Volumes[].VolumeId'

# Terraform
terraform destroy -target=module.dev

# Cloud Run (auto-scales to zero, but set limits)
gcloud run services update SERVICE --max-instances=10
```

**Anti-Pattern**: Leaving GPU instances, databases, or load balancers running overnight/weekends in dev/test.

**Workflow**:
1. Start work → Deploy resources
2. End work → Stop/destroy resources
3. Set budget alerts
4. Tag resources: `environment: dev/test/prod`

---

## 5. Project Initiation Protocol

### STOP Before Coding

**DO NOT write code until completing this checklist:**

```
[ ] Functional Requirements
    - Problem statement clear?
    - Target users identified?
    - Core features listed?
    - User workflows mapped?
    - Edge cases documented?

[ ] Technical Requirements
    - Language/framework confirmed?
    - Database choice finalized?
    - Authentication method decided?
    - External integrations listed?
    - Performance requirements defined?

[ ] Deployment Requirements
    - Target platform confirmed?
    - Domain/hosting decided?
    - Environment strategy (dev/staging/prod)?
    - CI/CD pipeline required?

[ ] Constraints
    - Budget limits?
    - Timeline/milestones?
    - Compliance requirements (GDPR, HIPAA, etc.)?
    - Browser/device support?

[ ] Success Criteria
    - KPIs defined?
    - Metrics to track?
    - Definition of done?
```

### Confirmation Template

**ALWAYS use this confirmation before starting:**

```
Building [PROJECT NAME]:

Tech Stack:
- Language: [choice]
- Framework: [choice]
- Database: [choice]
- Auth: [choice]

Deployment:
- Platform: [choice]
- Domain: [if applicable]
- Environments: [dev/staging/prod]

Timeline:
- Start: [date]
- Milestones: [key dates]
- Launch: [target date]

Success Metrics:
- [metric 1]
- [metric 2]
- [metric 3]

Confirmed? Any adjustments needed?
```

### Decision Tree: When to Ask vs. Assume

```
User provides requirement
    ↓
Is tech stack specified?
    ├─ No → ASK for preferences
    ↓
Are integrations listed?
    ├─ No → ASK what services needed
    ↓
Is deployment platform clear?
    ├─ No → ASK where to deploy
    ↓
Are constraints documented?
    ├─ No → ASK about budget/timeline/compliance
    ↓
Proceed with confirmed plan
```

---

## 6. Testing & Validation

### MANDATORY: Testing Protocol

**CRITICAL RULE**: Read `.claude/testing-protocol.md` BEFORE running ANY validation tests

### The Golden Rules

1. **NEVER** run tests in background while making changes
2. **ALWAYS** kill background tests before making code changes
3. **ALWAYS** commit changes BEFORE starting validation tests
4. **ALWAYS** verify commit applied: `git log -1 --oneline`
5. **ALWAYS** use timestamped log files: `/tmp/test_$(date +%Y%m%d_%H%M%S).log`
6. **ALWAYS** check test timestamp vs commit timestamp before reporting

### Correct Test Sequence

```
CORRECT FLOW:
    Make changes
        ↓
    COMMIT changes (git add + commit)
        ↓
    VERIFY commit (git log -1)
        ↓
    KILL any background tests
        ↓
    START new test with timestamped log
        ↓
    WAIT for completion
        ↓
    CHECK test timestamp vs commit timestamp
        ↓
    Report results

WRONG FLOW (CAUSES WASTED HOURS):
    Make changes
        ↓
    Start test in background  ← ❌ NO!
        ↓
    Make more changes         ← ❌ Test now invalid!
        ↓
    Report test results       ← ❌ Results are stale!
```

### Timestamp Verification

**Before reporting any test results:**

```bash
# Check commit time
git log -1 --format="%ai"  # e.g., 2025-01-15 14:30:00

# Check test log time (in filename)
ls -lh /tmp/test_*.log

# Test time MUST be >= Commit time
# If test time < commit time → Test used old code → Invalid results
```

### Consequences of Violations

- Wasting hours debugging non-existent bugs
- False positive/negative results
- Degraded trust in testing process
- Rework and confusion

**IF IN DOUBT**: Kill tests, commit, restart tests.

---

## 7. Version Control & Git

### Branch Strategy (MANDATORY)

```
main              - Production-ready code ONLY
    ↓
feature/*         - New features (feature/modal-inference)
fix/*             - Bug fixes (fix/validation-edge-case)
refactor/*        - Code improvements (refactor/provider-interface)
docs/*            - Documentation (docs/api-guide)
```

### Workflow

```bash
# Start new work
git checkout -b feature/my-feature

# Work and commit frequently (atomic commits)
git add .
git commit -m "Clear, descriptive message"

# Push to remote
git push -u origin feature/my-feature

# Create PR when ready
gh pr create --title "Add feature" --body "Description"

# After approval, merge via PR
# Delete branch after merge
git branch -d feature/my-feature
```

### Commit Message Standards

```
GOOD:
✓ "Add user authentication with JWT tokens"
✓ "Fix validation error in signup form"
✓ "Refactor payment processing for clarity"

BAD:
✗ "update code"
✗ "fix bug"
✗ "WIP"
✗ "stuff"
```

### Protected Main Branch Rules

1. **NEVER** commit directly to main for features
2. **NEVER** force push to main or shared branches
3. **ALWAYS** use PRs for code review
4. **ALWAYS** require PR approval before merging
5. **ALWAYS** delete feature branches after merge

### Daily Sync Protocol

```bash
# Morning: Pull latest
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/new-work

# End of day: Push progress
git push origin feature/new-work

# Keep feature branch updated
git checkout feature/new-work
git rebase main  # or merge main if team prefers
```

---

## 8. Frontend Development

### shadcn/ui Component Library (MANDATORY)

**Decision Tree**:

```
Need UI component?
    ↓
Browse https://ui.shadcn.com/blocks first
    ↓
Found matching block?
    ├─ Yes → Copy UNCHANGED → Customize ONLY colors/text/spacing
    ↓
    └─ No → Check https://ui.shadcn.com/docs/components
           ↓
           Found component?
               ├─ Yes → Install: npx shadcn@latest add [component]
               ↓
               └─ No → STOP and ASK for permission before custom component
```

### Implementation Protocol

```
STEP 1: Browse blocks (https://ui.shadcn.com/blocks)
STEP 2: Copy complete block unchanged
STEP 3: Install dependencies: npx shadcn@latest add [components]
STEP 4: Customize ONLY:
        - Colors
        - Text content
        - Spacing (margins, padding)
STEP 5: Add business logic
```

### Loading & Error States (MANDATORY)

**ALWAYS plan these from the start:**

- Loading states → Use skeleton components
- Error states → Use alert components
- Empty states → Use empty state patterns

### What You CAN Change

✅ Colors (theme tokens)
✅ Text content
✅ Spacing (margins, padding)
✅ Icons
✅ Sizes (within component API)

### What You CANNOT Change Without Permission

❌ Component structure
❌ Component composition
❌ HTML hierarchy
❌ Event handler patterns
❌ Accessibility attributes

### Design Inspiration

**Study these for aesthetic guidance**:
- v0.dev (minimal, purposeful contrast)
- Firebase (high-density dashboards)
- Hex (scannable complexity)
- Principle (data-rich but breathable)

**Get theme colors**: https://ui.shadcn.com/themes

---

## 9. Skills System

### Skill Activation Protocol

**CRITICAL**: Skills are not optional for their domains. They represent concentrated expertise that prevents common pitfalls.

### Available Skills & Activation Triggers

| Skill | Activate When | Slash Command |
|-------|---------------|---------------|
| **Zig Development** | Working with .zig files, build.zig, comptime code, Zig project setup | `/zig-dev` |
| **Modal Serverless** | Modal app deployment, GPU workloads, serverless functions, web endpoints | `/modal-dev` |
| **TUI Development** | Terminal apps, CLI with interactive UI, dashboards in terminal | `/tui-development` |
| **Secure Networking** | VPN setup, mTLS, secure connectivity, NAT traversal, network security | `/secure-networking` |
| **iOS Native Dev** | iOS apps, SwiftUI, UIKit, Xcode projects, Apple platforms | `/ios-native-dev` |
| **Beads Context** | Beads issue tracking, multi-session tasks, context management, complex workflows | `/beads-context` |

### Automatic Activation

Skills auto-activate when:
- Working with files in their domain (.zig → /zig-dev)
- Using domain-specific tools (bd commands → /beads-context)
- Discussing domain topics (GPU selection → /modal-dev)

### Skill Composition

Multiple skills can work together:

```
Examples:
- /zig-dev + /secure-networking → Zig-based VPN client
- /modal-dev + /secure-networking → Secure Modal endpoints with mTLS
- /tui-development + /secure-networking → mosh-like terminal application
- /modal-dev + /beads-context → Long-running Modal jobs with issue tracking
```

### Skill Decision Tree

```
Starting specialized work?
    ↓
Is there a skill for this domain?
    ├─ Yes → ACTIVATE skill at start
    ↓
    └─ No → Proceed with standard guidelines
         ↓
         Discover domain-specific challenge?
             ↓
             Check if skill exists
                 ├─ Yes → ACTIVATE skill immediately
                 └─ No → Apply general principles
```

### When NOT to Use Skills

- General Python/TypeScript work (no skill needed)
- Basic git operations (covered in this doc)
- Simple frontend without specific frameworks (covered in Section 8)
- General debugging (unless tool-specific)

### Skills Quick Reference

**Zig** (`/zig-dev`):
- Project setup, build.zig configuration
- Memory management patterns (allocators, defer)
- Testing organization
- Cross-compilation
- Comptime programming
- C interop

**Modal** (`/modal-dev`):
- Function decorators and app structure
- GPU/CPU resource selection
- Image building strategies (uv_pip_install recommended)
- Volume and secret management
- Web endpoint setup (FastAPI)
- Scheduled jobs (Cron, Period)
- Cost optimization

**TUI** (`/tui-development`):
- Charm.sh ecosystem (Go): Bubble Tea, Lip Gloss, Bubbles
- Ratatui (Rust): Widget system, layouts
- Architecture patterns (MVC, message passing)
- State management
- Cross-platform compatibility

**Secure Networking** (`/secure-networking`):
- Tailscale setup and configuration
- mosh for resilient connections
- mTLS implementation
- Certificate management
- NAT traversal techniques
- Zero-trust architectures

**iOS** (`/ios-native-dev`):
- SwiftUI 5.0+ patterns
- Swift 6.0 concurrency
- MVVM architecture with Observation
- SwiftData persistence
- NavigationStack patterns
- UIKit integration when needed

**Beads Context** (`/beads-context`):
- bd CLI commands and workflows
- Dependency management (blocks, related, parent-child, discovered-from)
- Context preservation strategies (/context)
- Context compression strategies (/compact)
- Long-horizon task management
- Multi-session state persistence

---

## 10. Anti-Patterns & Violations

### Critical Violations (Will Waste Significant Time)

```
❌ NEVER: Run tests before committing changes
   → Causes: Hours of debugging stale code

❌ NEVER: Run tests in background while changing code
   → Causes: Invalid results, wasted debugging time

❌ NEVER: Report test results without verifying timestamps
   → Causes: False positives/negatives, confusion

❌ NEVER: Leave TODO, mocks, or stubs
   → Instead: Implement now OR create Beads issue

❌ NEVER: Commit directly to main for features
   → Instead: Use feature branches + PRs

❌ NEVER: Force push to main or shared branches
   → Causes: Lost work, broken history

❌ NEVER: Accept vague requirements without pushback
   → Causes: Rework, missed requirements
```

### Moderate Violations (Reduce Quality)

```
❌ Don't assume tech stack without confirmation
❌ Don't skip shadcn blocks exploration
❌ Don't restructure shadcn components
❌ Don't use pip/poetry instead of uv
❌ Don't skip loading/error states
❌ Don't deploy without environment config
❌ Don't agree reflexively without analysis
❌ Don't leave cloud resources running (dev/test)
❌ Don't start specialized work without skill activation
```

### Violation Severity Matrix

| Severity | Impact | Examples |
|----------|--------|----------|
| 🔴 Critical | Hours wasted | Test before commit, background tests, stale results |
| 🟡 High | Quality issues | No pushback, skip blocks, wrong package manager |
| 🟢 Medium | Tech debt | Missing error states, unoptimized resources |

### Recovery from Violations

**If you realize you violated a critical rule:**

1. **STOP** immediately
2. **ASSESS** the damage (what's invalid now?)
3. **RESET** to last known good state
4. **FOLLOW** the correct procedure from start
5. **DOCUMENT** what went wrong to prevent recurrence

---

## 11. Quick Reference

### Language Quick Commands

```bash
# Python
uv init project && cd project && uv add pkg && uv run script.py

# Zig (activate /zig-dev)
zig init && zig build && zig build test

# Rust
cargo new project && cargo add anyhow tokio && cargo build

# Go
go mod init project && go get package && go run .

# TypeScript
pnpm create vite@latest && pnpm install && pnpm dev
```

### Cloud Quick Commands

```bash
# Modal (activate /modal-dev)
modal app deploy && modal app stop [name]

# Cloudflare Workers
wrangler dev && wrangler deploy

# AWS Lambda
aws lambda create-function && aws lambda invoke
```

### Git Quick Commands

```bash
# Start work
git checkout -b feature/name

# Commit
git add . && git commit -m "message"

# Push
git push -u origin feature/name

# Create PR
gh pr create --title "Title" --body "Description"

# Clean up
git branch -d feature/name
```

### Beads Quick Commands

```bash
# Session start
go install github.com/steveyegge/beads/cmd/bd@latest
bd import -i .beads/issues.jsonl
bd ready --json --limit 5

# During work
bd create "Task" -t bug -p 1 --json
bd dep add bd-5 bd-3 --type blocks
bd update bd-5 --status in_progress --json

# Session end
bd close bd-5 --reason "Complete" --json
bd export -o .beads/issues.jsonl
git add .beads/issues.jsonl && git commit -m "Update issues"
```

### Testing Quick Commands

```bash
# Correct flow
git add . && git commit -m "Changes"
git log -1 --oneline  # Verify commit
pkill -f "test"       # Kill old tests
./run_tests.sh > /tmp/test_$(date +%Y%m%d_%H%M%S).log 2>&1 &
```

### UI Quick Reference

```bash
# Browse blocks
open https://ui.shadcn.com/blocks

# Install component
npx shadcn@latest add button

# Get theme
open https://ui.shadcn.com/themes
```

---

## Decision Framework Summary

### Master Decision Tree

```
New request received
    ↓
Is domain specialized?
    ├─ Yes → Activate relevant skill(s)
    ↓
Requirements clear?
    ├─ No → ASK for clarification
    ↓
Tech stack confirmed?
    ├─ No → CONFIRM with user
    ↓
Edge cases considered?
    ├─ No → CHALLENGE and FLAG
    ↓
Testing strategy?
    ├─ None → PLAN tests first
    ↓
Cloud resources needed?
    ├─ Yes → PLAN shutdown strategy
    ↓
Using Beads?
    ├─ Yes → Follow Beads workflow
    ↓
Making changes?
    ├─ Yes → Use feature branch
    ↓
Need to validate?
    ├─ Yes → Follow testing protocol
    ↓
Session ending?
    ├─ Yes → Export state, commit, clean up
    ↓
All checks passed
    ↓
Execute with confidence
```

---

## Enforcement Checklist

Before completing ANY task, verify:

```
[ ] Used appropriate skill for specialized work
[ ] Challenged vague requirements
[ ] Confirmed tech stack and deployment
[ ] Followed correct package manager (uv, cargo, etc.)
[ ] Used shadcn blocks before custom components
[ ] Planned loading/error states
[ ] Used feature branch (not direct to main)
[ ] Followed testing protocol (commit first!)
[ ] Managed context with /context or /compact
[ ] Cleaned up cloud resources
[ ] Exported Beads state (if using bd)
[ ] Committed and pushed changes
```

**If ANY checkbox is unchecked, stop and address it before continuing.**

---

## Conclusion

These guidelines exist to prevent common pitfalls that waste hours:

1. **Testing violations** → Hours debugging stale code
2. **Vague requirements** → Rework and missed features
3. **Wrong tools** → Dependency hell and conflicts
4. **Skipped skills** → Reinventing solved problems
5. **Direct to main** → Broken builds and lost work
6. **Running cloud resources** → Unexpected bills
7. **Missing context** → Lost state across sessions

**Follow the decision trees. Activate the skills. Challenge assumptions. Commit before testing. Clean up resources.**

The reward is high-quality, maintainable code delivered efficiently.
