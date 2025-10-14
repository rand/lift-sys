# Claude Development Guidelines

## 1. Agentic Work
**Default:** Beads framework (https://github.com/steveyegge/beads)

Use for all agentic work and sub-agents. Break tasks into discrete beads with clear I/O. Chain beads for workflows, maintain state between beads.

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

**Modal** → `@app.function(gpu="T4")`, volumes for persistence, Modal secrets

**Cloud Run** → Listen on PORT, multi-stage Dockerfile, Secret Manager, set concurrency

**WorkOS** → SSO (SAML/OAuth), Directory Sync, server-side API keys only

**Resend** → React Email templates, domain verification, batch sending

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

## 7. UI Development

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

## 8. Anti-Patterns
❌ Assume tech stack
❌ Skip shadcn blocks exploration
❌ Restructure shadcn components
❌ Use pip/poetry instead of uv
❌ Skip loading/error states
❌ Deploy without environment config
❌ Leave TODOs, mocks, or stubs
❌ Accept vague requirements without pushback
❌ Agree reflexively without critical analysis

## 9. Quick Reference

**Languages:** Python (uv), Zig, Rust (cargo), Go, C/C++ (CMake), TS (strict), Lean 4

**Cloud:** Workers/Modal (serverless), Cloud Run (containers), WorkOS (auth), Resend (email)

**UI:** shadcn blocks → shadcn components → custom (permission only), theme colors from https://ui.shadcn.com/themes

**Workflow:** Requirements → Confirm → Map flows → shadcn blocks → Implement

**When in doubt:** Ask questions, check shadcn blocks, test edge cases
