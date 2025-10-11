# Frequently Asked Questions (FAQ)

Common questions and answers about the lift-sys prompt-to-IR refinement system.

## Table of Contents
- [General Questions](#general-questions)
- [Session Management](#session-management)
- [Typed Holes and Ambiguities](#typed-holes-and-ambiguities)
- [AI Assists](#ai-assists)
- [Finalization and Validation](#finalization-and-validation)
- [Troubleshooting](#troubleshooting)
- [Advanced Usage](#advanced-usage)

---

## General Questions

### What is prompt-to-IR refinement?

Prompt-to-IR refinement is an iterative process where you start with a natural language description and progressively clarify ambiguities until you have a complete, formally verified intermediate representation (IR) that can be used for code generation.

**Key benefits:**
- Start with simple, natural language
- System identifies what's missing
- AI helps fill in gaps
- Get verified, type-safe specifications
- Multiple interfaces (Web, CLI, TUI, SDK)

### How is this different from traditional code generation?

| Traditional Code Gen | lift-sys Refinement |
|---------------------|---------------------|
| One-shot generation | Iterative refinement |
| Hope for the best | Explicit ambiguity resolution |
| No verification | SMT-backed validation |
| Black box | Transparent IR |
| Single interface | Web, CLI, TUI, SDK |

### When should I use this?

**Good use cases:**
- Specifying new features before implementation
- Creating test specifications
- Documenting existing code behavior
- Collaborative spec review
- CI/CD automation for spec generation

**Not ideal for:**
- Quick prototypes (use direct code generation)
- Well-defined specs (start with IR directly)
- Non-deterministic requirements

---

## Session Management

### What is a session?

A session is a stateful refinement process that tracks:
- Initial prompt or IR
- Current draft (evolving IR)
- Unresolved ambiguities (typed holes)
- Resolution history
- Validation status
- Metadata (project, owner, etc.)

Sessions persist server-side and can be accessed from any interface.

### How long do sessions last?

Sessions persist until explicitly deleted. They survive:
- Server restarts (with persistent storage)
- Client disconnections
- Browser tab closes

**Best practice:** Delete sessions after finalization to avoid clutter.

```bash
uv run python -m lift_sys.cli session delete <session-id>
```

### Can I resume a session later?

Yes! Sessions are persistent and can be resumed anytime:

**Web UI:**
- Sessions appear in sidebar
- Click to resume

**CLI:**
```bash
# List all sessions
uv run python -m lift_sys.cli session list

# Resume specific session
uv run python -m lift_sys.cli session get <session-id>
```

**SDK:**
```python
session = client.get_session(session_id)
# Continue resolving holes
```

### Can multiple people work on the same session?

Yes! Sessions are identified by ID and shared across all clients.

**Workflow:**
1. Alice creates session, shares ID with Bob
2. Bob resolves some holes
3. Alice continues from where Bob left off
4. Either can finalize

**Note:** No locking mechanism - last write wins. Use metadata to coordinate:
```python
client.create_session(
    prompt="...",
    metadata={"locked_by": "alice", "locked_at": "2025-10-11T12:00:00Z"}
)
```

### How do I organize sessions?

Use metadata for organization:

```python
client.create_session(
    prompt="User authentication",
    metadata={
        "project": "auth-service",
        "feature_id": "AUTH-123",
        "sprint": "2025-Q4",
        "owner": "alice",
        "priority": "high"
    }
)
```

Query by metadata (requires custom filtering in your code):
```python
all_sessions = client.list_sessions()
auth_sessions = [s for s in all_sessions.sessions
                 if s.metadata.get("project") == "auth-service"]
```

---

## Typed Holes and Ambiguities

### What is a typed hole?

A typed hole is a placeholder for missing or ambiguous information in the IR. It's represented as `?hole_name` and has a specific kind (Intent, Signature, Effect, Assertion).

**Example:**
```
Signature: ?hole_function_name(?hole_param: ?hole_param_type) -> ?hole_return_type
```

### What kinds of holes exist?

Holes are categorized by their purpose:

- **Intent holes**: Ambiguous goals or rationale
- **Signature holes**: Missing function names, parameter types, return types
- **Effect holes**: Unclear side effects (I/O, state changes)
- **Assertion holes**: Missing preconditions, postconditions, invariants

### Why do holes appear?

Holes appear when the system can't infer information from your prompt:

**Example prompt:**
```
"A function that processes data"
```

**Generated holes:**
- `hole_function_name` - What should it be called?
- `hole_data_type` - What kind of data?
- `hole_parameter_name` - What parameter name?
- `hole_processing_logic` - How should it process?
- `hole_return_type` - What does it return?

**Better prompt:**
```
"A function called 'validate' that takes a string email and returns bool"
```

**Reduced holes:**
- `hole_validation_logic` - How to validate?
- `hole_edge_cases` - What about empty strings?

### How do I know which holes to resolve first?

**Recommended order:**

1. **Identity**: Function/module names
2. **Structure**: Parameters and types
3. **Behavior**: Return types and logic
4. **Safety**: Constraints and assertions

**Dependency rule:** If resolving a hole doesn't reduce ambiguity count, resolve related holes first.

### Can I create my own holes?

Not directly. Holes are generated by the system based on:
- Prompt analysis
- IR parsing (in reverse mode)
- Resolution side effects (new holes from constraints)

**To influence holes:**
- Be more specific in prompts
- Use technical terminology
- Mention edge cases explicitly

---

## AI Assists

### What are assists?

Assists are AI-generated suggestions for resolving specific holes. They provide:
- Context about the hole
- Multiple resolution options
- Reasoning for suggestions

**Example:**
```json
{
  "hole_id": "hole_return_type",
  "context": "function returns validation result",
  "suggestions": ["bool", "Optional[bool]", "Result[bool, ValidationError]"]
}
```

### Are assists always correct?

No. Assists are suggestions based on context and common patterns. Always review:

**When to trust:**
- Suggestions match your domain
- Multiple suggestions are similar
- Context makes sense

**When to override:**
- Suggestions miss business logic
- Your naming conventions differ
- Domain-specific requirements exist

### How often should I request assists?

**Best practice:** Once per session, then cache results.

```python
# Get all assists upfront
assists = client.get_assists(session_id)
assists_map = {a.hole_id: a for a in assists.assists}

# Use cached assists during resolution
for hole_id in ambiguities:
    suggestions = assists_map[hole_id].suggestions
    # Pick one or provide custom resolution
```

**Why:** Assists are computed for the current session state. As you resolve holes, context changes and assists may become stale.

### Can I disable AI assists?

Yes. You can always provide custom resolutions without using assists:

```bash
uv run python -m lift_sys.cli session resolve \
  <session-id> hole_function_name "my_custom_name"
```

```python
session = client.resolve_hole(
    session_id=session_id,
    hole_id=hole_id,
    resolution_text="custom_value"
)
```

---

## Finalization and Validation

### When can I finalize a session?

You can finalize when:
- ✅ All ambiguities resolved (`session.ambiguities == []`)
- ✅ Validation status is "valid" (`session.current_draft.validation_status == "valid"`)
- ✅ No SMT contradictions

### What happens during finalization?

Finalization:
1. Checks for remaining ambiguities (fails if any exist)
2. Runs final SMT validation
3. Freezes the session (status changes to "finalized")
4. Returns the completed IR
5. Makes session read-only

### What if finalization fails?

Common failures:

**"Unresolved ambiguities"**
```python
session = client.get_session(session_id)
print(f"Remaining holes: {session.ambiguities}")
# Resolve each one
```

**"Validation failed"**
```python
# Check validation status
if session.current_draft.validation_status != "valid":
    print(f"Status: {session.current_draft.validation_status}")
    # Review SMT results
    for result in session.current_draft.smt_results:
        print(result)
```

### Can I reopen a finalized session?

No. Finalized sessions are read-only. To make changes:
1. Export the IR
2. Create a new session from IR (reverse mode)
3. Make refinements
4. Finalize again

```bash
# Export finalized IR
uv run python -m lift_sys.cli session finalize <old-id> --output ir.json

# Create new session from IR
uv run python -m lift_sys.cli session create --ir-file ir.json --source reverse_mode
```

### What do I do with the finalized IR?

Use the IR for downstream workflows:

**Code generation (forward mode):**
```bash
uv run lift-sys forward --ir finalized_ir.json --output generated.py
```

**Documentation:**
```bash
# Extract human-readable summary
cat finalized_ir.json | jq '.intent.summary'
```

**Testing:**
```bash
# Use assertions for test generation
cat finalized_ir.json | jq '.assertions'
```

---

## Troubleshooting

### "Connection refused" error

**Cause:** Backend API not running or unreachable.

**Solutions:**
```bash
# Start backend
./start.sh
# OR
uv run uvicorn lift_sys.api.server:app --reload

# Verify backend is running
curl http://localhost:8000/health
```

### Hole resolution doesn't reduce ambiguity count

**Cause:** Resolution created new holes or has dependencies.

**Solutions:**
1. Check validation status
2. Review SMT results for contradictions
3. Resolve dependency holes first
4. Try different resolution value

```python
session = client.get_session(session_id)
print(f"Validation: {session.current_draft.validation_status}")
print(f"SMT results: {session.current_draft.smt_results}")
```

### "Invalid resolution type" error

**Cause:** Using wrong resolution type for the hole kind.

**Solutions:**
Match resolution type to hole kind:
- Intent holes → `clarify_intent`
- Signature holes → `refine_signature`
- Effect holes → `specify_effect`
- Assertion holes → `add_constraint`

### Session state not updating in TUI

**Cause:** TUI doesn't auto-refresh.

**Solution:**
Press `Ctrl+L` to manually refresh session list and details.

### Finalization takes a long time

**Cause:** Complex IR with many assertions requires extensive SMT solving.

**Solutions:**
1. Be patient (SMT solving can be slow for complex constraints)
2. Simplify constraints if possible
3. Remove redundant assertions

---

## Advanced Usage

### Can I use sessions in CI/CD?

Yes! Sessions are designed for automation:

```bash
#!/bin/bash
# ci-generate-spec.sh

SESSION_ID=$(uv run python -m lift_sys.cli session create \
  --prompt "$FEATURE_SPEC" --json | jq -r '.session_id')

# Auto-resolve common patterns
for hole in hole_language hole_return_type; do
  uv run python -m lift_sys.cli session resolve $SESSION_ID $hole "python"
done

# Check readiness
HOLES=$(uv run python -m lift_sys.cli session get $SESSION_ID --json \
  | jq '.ambiguities | length')

if [ "$HOLES" -gt 0 ]; then
  echo "Manual resolution required"
  exit 1
fi

uv run python -m lift_sys.cli session finalize $SESSION_ID --output spec.json
```

### Can I batch process multiple prompts?

Yes! Use the Python SDK with async:

```python
import asyncio
from lift_sys.client import SessionClient

async def batch_process(prompts):
    client = SessionClient()

    # Create all sessions concurrently
    tasks = [client.acreate_session(prompt=p) for p in prompts]
    sessions = await asyncio.gather(*tasks)

    return sessions

prompts = ["Prompt 1", "Prompt 2", "Prompt 3"]
sessions = asyncio.run(batch_process(prompts))
```

### Can I extend the system with custom hole types?

Not directly in the current version. Hole types are defined by `HoleKind` in the IR model.

**Workaround:** Use metadata and conventions:
```python
# Custom "business logic" hole using metadata
session = client.resolve_hole(
    session_id=session_id,
    hole_id="hole_constraint",  # Standard constraint hole
    resolution_text="custom_business_rule_applies",
    resolution_type="add_constraint"
)
```

### How do I integrate with existing codebases?

Use reverse mode to start from existing code:

1. **Lift existing code to IR:**
   ```bash
   uv run python -m lift_sys.reverse \
     --repo /path/to/repo \
     --target-file src/module.py
   ```

2. **Create session from lifted IR:**
   ```bash
   uv run python -m lift_sys.cli session create \
     --ir-file lifted_ir.json \
     --source reverse_mode
   ```

3. **Refine and finalize:**
   ```bash
   # Resolve any ambiguities
   uv run python -m lift_sys.cli session finalize <session-id>
   ```

---

## Still Have Questions?

- **Documentation**: See [Workflow Guides](WORKFLOW_GUIDES.md) and [Best Practices](BEST_PRACTICES.md)
- **API Reference**: [API_SESSION_MANAGEMENT.md](API_SESSION_MANAGEMENT.md)
- **Examples**: Run `examples/session_workflow.py`
- **Issues**: [GitHub Issues](https://github.com/rand/lift-sys/issues)
- **Design Details**: [IR_DESIGN.md](IR_DESIGN.md)
