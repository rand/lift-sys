# Best Practices: Prompt-to-IR Refinement

This guide provides best practices, tips, and common patterns for effective use of the lift-sys prompt-to-IR refinement system.

## Table of Contents
- [Writing Effective Prompts](#writing-effective-prompts)
- [Resolving Ambiguities](#resolving-ambiguities)
- [Session Management](#session-management)
- [Error Handling](#error-handling)
- [Performance Tips](#performance-tips)
- [Team Workflows](#team-workflows)

---

## Writing Effective Prompts

### Start Simple, Iterate

**✅ Good:**
```
"A function that validates email addresses"
```

**❌ Avoid:**
```
"A complex email validation function that handles RFC 5322 specifications,
supports international domains, validates MX records, and returns detailed
error messages with custom exception types..."
```

**Why:** The system will identify what's missing and guide you through filling in details. Starting simple reduces initial ambiguities and makes the refinement process clearer.

### Include Key Constraints Upfront

**✅ Good:**
```
"A function that sorts a list of integers in ascending order, handling empty lists"
```

**❌ Avoid:**
```
"A function that sorts"
```

**Why:** Mentioning data types and edge cases upfront helps the system generate more accurate typed holes.

### Use Domain-Specific Language

**✅ Good:**
```
"A REST endpoint that creates a user account with email and password"
```

**❌ Avoid:**
```
"Something to make users"
```

**Why:** Clear technical terminology reduces ambiguity and produces better AI assists.

### Specify Expected Behavior

**✅ Good:**
```
"A function that parses JSON, returns None on invalid input"
```

**❌ Avoid:**
```
"A function that does JSON stuff"
```

**Why:** Explicit behavior constraints translate directly to assertions in the IR.

---

## Resolving Ambiguities

### Hole Resolution Order

**Recommended sequence:**

1. **Function/module name** - Sets the context for everything else
2. **Input parameter names and types** - Establishes the signature
3. **Return type** - Completes the signature
4. **Constraints and assertions** - Adds safety guarantees
5. **Effects** - Documents side effects

**Example:**
```python
# Step 1: Name
client.resolve_hole(session_id, "hole_function_name", "validate_email")

# Step 2: Parameters
client.resolve_hole(session_id, "hole_param_name", "email")
client.resolve_hole(session_id, "hole_param_type", "str")

# Step 3: Return type
client.resolve_hole(session_id, "hole_return_type", "bool")

# Step 4: Constraints
client.resolve_hole(session_id, "hole_constraint", "len(email) > 0")
```

### Using AI Assists Effectively

**Always review suggestions:**
```python
assists = client.get_assists(session_id)
for assist in assists.assists:
    print(f"Hole: {assist.hole_id}")
    print(f"Context: {assist.context}")
    print(f"Suggestions: {assist.suggestions}")
    # Review and pick the best one, or provide custom resolution
```

**When to override suggests:**
- Suggestions don't match your domain
- You have specific naming conventions
- Business logic requires custom constraints

### Resolution Type Selection

Choose the appropriate resolution type:

- **`clarify_intent`** - For high-level ambiguities (What should this do?)
- **`refine_signature`** - For types, parameters, return values
- **`add_constraint`** - For preconditions, postconditions, invariants
- **`specify_effect`** - For side effects, I/O operations

**Example:**
```bash
# Intent clarification
uv run python -m lift_sys.cli session resolve \
  <session-id> hole_behavior "reject invalid emails" \
  --type clarify_intent

# Signature refinement
uv run python -m lift_sys.cli session resolve \
  <session-id> hole_return_type "bool" \
  --type refine_signature

# Constraint addition
uv run python -m lift_sys.cli session resolve \
  <session-id> hole_assertion "email is not None" \
  --type add_constraint
```

### Handling Dependent Holes

Some holes depend on others. If resolution doesn't reduce ambiguity count:

1. Check validation status: `session.current_draft.validation_status`
2. Review SMT results: `session.current_draft.smt_results`
3. Resolve dependencies first

**Example of dependency:**
```
hole_list_element_type depends on hole_list_parameter
→ Resolve hole_list_parameter first
```

---

## Session Management

### Session Lifecycle Best Practices

**1. One Prompt, One Session**
```python
# ✅ Good: Separate sessions for separate concerns
session1 = client.create_session(prompt="User authentication")
session2 = client.create_session(prompt="Data validation")

# ❌ Avoid: Combining multiple concerns
session = client.create_session(prompt="Auth and validation and logging...")
```

**2. Use Metadata for Organization**
```python
session = client.create_session(
    prompt="Calculate shipping cost",
    metadata={
        "project": "e-commerce",
        "feature": "checkout",
        "author": "alice@example.com",
        "sprint": "2025-Q4-S3"
    }
)
```

**3. Clean Up Completed Sessions**
```bash
# List old finalized sessions
uv run python -m lift_sys.cli session list --json \
  | jq '.[] | select(.status=="finalized") | .session_id'

# Delete them
for id in $(old_sessions); do
  uv run python -m lift_sys.cli session delete $id --yes
done
```

### Session Persistence

Sessions are stored server-side:
- Persist across restarts (if using persistent storage)
- Shared across all clients (Web, CLI, SDK)
- Include full refinement history

**Exporting sessions:**
```bash
# Save session state
uv run python -m lift_sys.cli session get <session-id> \
  --show-ir --json > session_backup.json

# Save finalized IR
uv run python -m lift_sys.cli session finalize <session-id> \
  --output finalized_ir.json
```

---

## Error Handling

### Common Errors and Solutions

#### "Session not found"

**Cause:** Session ID doesn't exist or was deleted

**Solution:**
```bash
# List all sessions
uv run python -m lift_sys.cli session list

# Verify session ID
uv run python -m lift_sys.cli session get <correct-id>
```

#### "Cannot finalize: unresolved holes"

**Cause:** Ambiguities still remain

**Solution:**
```python
session = client.get_session(session_id)
print(f"Remaining holes: {session.ambiguities}")

# Resolve each one
for hole_id in session.ambiguities:
    assists = client.get_assists(session_id)
    # Find assists for this hole and resolve
```

#### "Validation failed: contradictory constraints"

**Cause:** Resolved holes created logical contradiction

**Solution:**
```python
# Check SMT results
session = client.get_session(session_id)
if session.current_draft:
    for result in session.current_draft.smt_results:
        if result.get("status") == "unsat":
            print(f"Contradiction: {result}")

# Revise conflicting resolutions
```

### Defensive Programming

**Always check status:**
```python
def safe_finalize(client, session_id):
    session = client.get_session(session_id)

    if session.ambiguities:
        raise ValueError(
            f"Cannot finalize: {len(session.ambiguities)} holes remaining"
        )

    if session.current_draft.validation_status != "valid":
        raise ValueError(
            f"Invalid IR: {session.current_draft.validation_status}"
        )

    return client.finalize_session(session_id)
```

**Handle network errors:**
```python
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10)
)
def resilient_create_session(client, prompt):
    try:
        return client.create_session(prompt=prompt)
    except httpx.ConnectError:
        print("Connection failed, retrying...")
        raise
```

---

## Performance Tips

### Batch Operations

**Use async for concurrent operations:**
```python
import asyncio
from lift_sys.client import SessionClient

async def batch_create_sessions(prompts):
    client = SessionClient()

    # Create all sessions concurrently
    tasks = [
        client.acreate_session(prompt=p)
        for p in prompts
    ]

    sessions = await asyncio.gather(*tasks)
    return sessions

# Usage
prompts = ["Prompt 1", "Prompt 2", "Prompt 3"]
sessions = asyncio.run(batch_create_sessions(prompts))
```

### Minimize Round Trips

**❌ Inefficient:**
```python
for hole_id in ambiguities:
    assists = client.get_assists(session_id)  # Multiple calls
    # Resolve hole
```

**✅ Efficient:**
```python
assists = client.get_assists(session_id)  # Single call
assists_map = {a.hole_id: a for a in assists.assists}

for hole_id in ambiguities:
    suggestion = assists_map[hole_id].suggestions[0]
    # Resolve hole
```

### Cache Session Data

**For read-heavy workflows:**
```python
class SessionCache:
    def __init__(self, client):
        self.client = client
        self.cache = {}

    def get_session(self, session_id, ttl=60):
        cached = self.cache.get(session_id)
        if cached and time.time() - cached["timestamp"] < ttl:
            return cached["session"]

        session = self.client.get_session(session_id)
        self.cache[session_id] = {
            "session": session,
            "timestamp": time.time()
        }
        return session
```

---

## Team Workflows

### Collaborative Refinement

**Pattern: Multiple team members refining different sessions**

1. Each developer creates sessions for their features
2. Use metadata to track ownership:
   ```python
   client.create_session(
       prompt="User registration flow",
       metadata={"owner": "alice", "reviewer": "bob"}
   )
   ```
3. Team lead reviews and finalizes:
   ```bash
   # List sessions needing review
   uv run python -m lift_sys.cli session list --json \
     | jq '.[] | select(.metadata.owner=="alice")'
   ```

### CI/CD Integration

**Pattern: Automated spec generation in pipelines**

```bash
#!/bin/bash
# .github/workflows/generate-specs.sh

# Create session from feature description
SESSION_ID=$(uv run python -m lift_sys.cli session create \
  --prompt "$FEATURE_DESCRIPTION" \
  --json | jq -r '.session_id')

# Auto-resolve common patterns
uv run python -m lift_sys.cli session resolve \
  $SESSION_ID hole_language "python"

# Check if ready
HOLES=$(uv run python -m lift_sys.cli session get $SESSION_ID --json \
  | jq '.ambiguities | length')

if [ "$HOLES" -gt 0 ]; then
  echo "⚠️  $HOLES ambiguities require manual resolution"
  exit 1
fi

# Finalize and save
uv run python -m lift_sys.cli session finalize $SESSION_ID \
  --output specs/feature_$FEATURE_ID.json

echo "✓ Spec generated: specs/feature_$FEATURE_ID.json"
```

### Code Review Integration

**Pattern: Spec review before code review**

1. Developer creates and refines spec
2. Commits finalized IR to repo
3. Reviewer inspects IR for correctness:
   ```bash
   # Review the spec
   cat specs/feature_123.json | jq '.intent, .signature, .assertions'

   # Generate code from spec
   uv run lift-sys forward --ir specs/feature_123.json

   # Review generated code
   ```

### Template-Based Workflows

**Pattern: Reusable spec templates**

```python
TEMPLATES = {
    "crud_endpoint": {
        "prompt_template": "A REST endpoint to {action} {resource}",
        "default_resolutions": {
            "hole_http_method": "POST",
            "hole_response_type": "json",
            "hole_auth_required": "true"
        }
    }
}

def create_from_template(template_name, **kwargs):
    template = TEMPLATES[template_name]
    prompt = template["prompt_template"].format(**kwargs)

    session = client.create_session(prompt=prompt)

    # Apply default resolutions
    for hole_id, value in template["default_resolutions"].items():
        if hole_id in session.ambiguities:
            session = client.resolve_hole(
                session_id=session.session_id,
                hole_id=hole_id,
                resolution_text=value
            )

    return session

# Usage
session = create_from_template(
    "crud_endpoint",
    action="create",
    resource="user account"
)
```

---

## Summary Checklist

### Before Creating a Session
- [ ] Prompt is clear and specific
- [ ] Key constraints are mentioned
- [ ] Expected behavior is described
- [ ] Metadata is prepared (project, owner, etc.)

### During Refinement
- [ ] Review AI assists before resolving
- [ ] Resolve holes in logical order (name → signature → constraints)
- [ ] Check validation status after each resolution
- [ ] Monitor SMT results for contradictions

### Before Finalizing
- [ ] All ambiguities resolved
- [ ] Validation status is "valid"
- [ ] No contradictory constraints
- [ ] IR reviewed for correctness

### After Finalization
- [ ] IR exported and saved
- [ ] Session cleaned up (if no longer needed)
- [ ] IR integrated into downstream workflow

---

## Additional Resources

- [Workflow Guides](WORKFLOW_GUIDES.md) - Detailed step-by-step tutorials
- [API Documentation](API_SESSION_MANAGEMENT.md) - Complete API reference
- [FAQ](FAQ.md) - Common questions and answers
- [IR Design](IR_DESIGN.md) - Intermediate representation structure

For questions or issues, see [GitHub Issues](https://github.com/rand/lift-sys/issues).
