# Claude Development Guidelines

## 1. Agentic Work
**Default:** Beads framework (https://github.com/steveyegge/beads)
- Use for all agentic work and sub-agents
- Break tasks into discrete beads with clear I/O
- Chain beads for workflows, maintain state between beads

## 2. Language Defaults

**Python:** `uv` (not pip/poetry)
```bash
uv init project && cd project
uv add package-name
uv run script.py
```

**Zig:** Latest stable, explicit allocators, comptime, `defer` for cleanup

**Rust:** `cargo`, ownership/borrowing, `Result`/`Option`, iterators > loops
- Apps: `anyhow`, Libraries: `thiserror`, Async: `tokio`

**Go:** Standard toolchain, small interfaces, explicit errors, table-driven tests

**C/C++:** CMake 3.20+
- C: C11/C17, `const`, avoid globals
- C++: C++17/20, RAII, smart pointers, STL algorithms

**TypeScript:** Strict mode, ESM, `async/await`, Vitest/Jest
```json
{"compilerOptions": {"strict": true, "target": "ES2022", "module": "ESNext"}}
```

**Lean:** Lean 4, mathlib4, readable tactics, `snake_case`

## 3. Cloud Integration

**AWS:** Lambda layers, S3 presigned URLs, DynamoDB single-table, IAM least privilege, Secrets Manager

**Cloudflare:** Workers (TypeScript), KV/R2/D1 bindings, `wrangler dev`

**Modal:** `@app.function(gpu="T4")`, volumes for persistence, Modal secrets

**Cloud Run:** Listen on PORT, multi-stage Dockerfile, Secret Manager, set concurrency

**WorkOS:** SSO (SAML/OAuth), Directory Sync, server-side API keys only

**Resend:** React Email templates, domain verification, batch sending

## 4. Design Inspiration
- **v0.dev:** Clean, minimal, purposeful contrast
- **Firebase:** High-density dashboards, clear hierarchy
- **Hex:** Complex data that's scannable, multi-pane layouts
- **Principle:** Data-rich but breathable, compact spacing

## 5. Project Start Protocol

### Requirements (ASK, don't assume)
1. **Functional:** Problem, users, features, workflows, edge cases
2. **Technical:** Language, framework, database, auth, integrations, performance
3. **Deploy:** Platform, domain, environments, CI/CD
4. **Constraints:** Budget, timeline, compliance, browser support
5. **Success:** Metrics, KPIs, definition of done

### Confirm Before Coding
```
Building [PROJECT]:
- Tech: [stack]
- Deploy: [platform] at [domain]
- Timeline: [dates]
- Success: [criteria]
Confirmed?
```

## 6. Experience Design Workflow

### 1. Map States (Graphviz)
- All user states and transitions
- Minimize dead ends
- Document edge cases

### 2. Identify Affordances
**PRIORITY ORDER:**
1. shadcn blocks (https://ui.shadcn.com/blocks) FIRST
2. shadcn components (https://ui.shadcn.com/) SECOND
3. Custom → ONLY with permission

Plan: loading (skeleton), errors (alerts)

### 3. Implementation (MANDATORY)
```
STEP 1: Browse https://ui.shadcn.com/blocks
STEP 2: Copy complete block
STEP 3: npx shadcn@latest add [components]
STEP 4: Customize ONLY colors/text/spacing
STEP 5: Add business logic
```

**STOP if not in shadcn blocks → ASK USER**

DO: Change colors, text, spacing
DON'T: Restructure, change composition, rewrite

## 7. Quick Reference

**Languages:** Python (uv), Zig, Rust (cargo), Go, C/C++ (CMake), TS (strict), Lean 4

**Cloud:** Workers/Modal (serverless), Cloud Run (containers), WorkOS (auth), Resend (email)

**UI:** shadcn blocks → shadcn components → custom (permission only)
- Colors: shadcn theme vars
- Tool: https://ui.shadcn.com/themes

**Workflow:** Requirements → Confirm → Map flows → shadcn blocks → Implement

## 8. Anti-Patterns
❌ Assume tech stack
❌ Skip shadcn blocks
❌ Restructure shadcn components
❌ Use pip/poetry (use uv)
❌ Skip loading/error states
❌ Deploy without env config

**When in doubt:** Ask questions, check shadcn blocks, test edge cases
