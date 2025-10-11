# Workflow Guides: Prompt-to-IR Refinement

This guide demonstrates the complete workflow for iterative prompt refinement across all lift-sys interfaces: Web UI, CLI, TUI, and Python SDK.

## Table of Contents
- [Overview](#overview)
- [Web UI Workflow](#web-ui-workflow)
- [CLI Workflow](#cli-workflow)
- [TUI Workflow](#tui-workflow)
- [Python SDK Workflow](#python-sdk-workflow)
- [Common Patterns](#common-patterns)
- [Troubleshooting](#troubleshooting)

---

## Overview

The prompt-to-IR refinement workflow allows you to:
1. **Start with natural language** - Describe your intent in plain English
2. **Review ambiguities** - See what information is missing or unclear (typed holes)
3. **Refine iteratively** - Resolve ambiguities one at a time with AI assistance
4. **Get validated IR** - Receive a complete, verified intermediate representation
5. **Generate code** - Use the IR for downstream code synthesis

### Key Concepts

- **Session**: A stateful refinement process from prompt to validated IR
- **Typed Hole**: A placeholder for missing/ambiguous information (e.g., `hole_return_type`)
- **Ambiguity**: An unresolved typed hole that needs clarification
- **Assist**: AI-generated suggestion for resolving a hole
- **Draft**: A version of the IR during refinement (increases with each resolution)
- **Finalization**: The act of marking a session complete and extracting the final IR

---

## Web UI Workflow

### Prerequisites
- Backend and frontend running: `./start.sh`
- Navigate to http://localhost:5173

### Step 1: Access Prompt Workbench

```
1. Click "Prompt Workbench" in the navigation bar
2. You'll see a split-pane interface:
   - Left: Session list and prompt input
   - Right: IR preview and ambiguity resolution
```

### Step 2: Create a Session

```
1. In the "Enter prompt" textarea, type:
   "A function that calculates the factorial of a non-negative integer"

2. Click "Create Session" button
3. The system generates an initial IR with typed holes
4. Ambiguities appear in the right pane as colored badges
```

**Example Output:**
```
Session created: a8f3c9d7-...
Status: active
Ambiguities: 4
- hole_function_name
- hole_parameter_name
- hole_parameter_type
- hole_return_type
```

### Step 3: Review Assists

```
1. Click "Get Assists" button
2. AI suggestions appear below each ambiguity:

   hole_function_name:
   • factorial
   • compute_factorial

   hole_return_type:
   • int
   • Optional[int]
```

### Step 4: Resolve Ambiguities

```
1. Click on an ambiguity badge (e.g., "hole_function_name")
2. Input field appears
3. Type resolution: "factorial"
4. Click "Resolve" or press Enter
5. The IR updates in real-time
6. Ambiguity count decreases
```

**Iteration Process:**
```
Iteration 1: hole_function_name → "factorial"
  Remaining: 3 ambiguities

Iteration 2: hole_parameter_name → "n"
  Remaining: 2 ambiguities

Iteration 3: hole_parameter_type → "int"
  Remaining: 1 ambiguity

Iteration 4: hole_return_type → "int"
  Remaining: 0 ambiguities ✓
```

### Step 5: Finalize and Export

```
1. Once all ambiguities resolved, "Finalize Session" button becomes active
2. Click "Finalize Session"
3. Validated IR appears in the preview
4. Copy IR for use in forward mode synthesis
```

### Step 6: Session Management

```
- View all sessions in the left sidebar
- Click any session to resume refinement
- Sessions persist across page reloads
- Delete completed sessions with trash icon
```

---

## CLI Workflow

### Prerequisites
- Backend running on port 8000
- CLI installed: `uv sync`

### Step 1: Create a Session from Prompt

```bash
uv run python -m lift_sys.cli session create \
  --prompt "A function that validates email addresses using regex" \
  --json
```

**Output:**
```json
{
  "session_id": "b7e2a1f6-4c8d-4e9a-b3f1-9d8c7e6a5b4c",
  "status": "active",
  "source": "prompt",
  "ambiguities": [
    "hole_function_name",
    "hole_parameter_name",
    "hole_return_type",
    "hole_regex_pattern"
  ]
}
```

### Step 2: List All Sessions

```bash
uv run python -m lift_sys.cli session list --json
```

**Output:**
```json
[
  {
    "session_id": "b7e2a1f6-...",
    "status": "active",
    "source": "prompt",
    "ambiguities_count": 4,
    "created_at": "2025-10-11T12:00:00Z"
  }
]
```

### Step 3: Get Session Details

```bash
uv run python -m lift_sys.cli session get b7e2a1f6-... --show-ir --json
```

**Output:**
```json
{
  "session_id": "b7e2a1f6-...",
  "status": "active",
  "ambiguities": ["hole_function_name", "..."],
  "ir": {
    "intent": {
      "summary": "Validate email addresses",
      "holes": ["hole_regex_pattern"]
    },
    "signature": {
      "name": "?hole_function_name",
      "parameters": [
        {"name": "?hole_parameter_name", "type_hint": "str"}
      ],
      "returns": "?hole_return_type"
    }
  }
}
```

### Step 4: Get AI Assists

```bash
uv run python -m lift_sys.cli session assists b7e2a1f6-... --json
```

**Output:**
```json
[
  {
    "hole_id": "hole_function_name",
    "suggestions": ["validate_email", "is_valid_email"],
    "context": "function name"
  },
  {
    "hole_id": "hole_return_type",
    "suggestions": ["bool", "Optional[bool]"],
    "context": "return type annotation"
  }
]
```

### Step 5: Resolve Holes Iteratively

```bash
# Resolve function name
uv run python -m lift_sys.cli session resolve \
  b7e2a1f6-... \
  hole_function_name \
  "validate_email" \
  --json

# Resolve parameter name
uv run python -m lift_sys.cli session resolve \
  b7e2a1f6-... \
  hole_parameter_name \
  "email" \
  --json

# Resolve return type
uv run python -m lift_sys.cli session resolve \
  b7e2a1f6-... \
  hole_return_type \
  "bool" \
  --type refine_signature \
  --json
```

**Output (after each resolution):**
```json
{
  "session_id": "b7e2a1f6-...",
  "status": "active",
  "ambiguities": ["hole_regex_pattern"]  // Decreases each time
}
```

### Step 6: Finalize Session

```bash
uv run python -m lift_sys.cli session finalize \
  b7e2a1f6-... \
  --output finalized_ir.json
```

**Output:**
```
✓ IR saved to finalized_ir.json
✓ Session finalized successfully!
```

### Step 7: Use Finalized IR

```bash
# View the IR
cat finalized_ir.json

# Use in forward mode
uv run python -m lift_sys.forward \
  --ir finalized_ir.json \
  --output generated_code.py
```

---

## TUI Workflow

### Prerequisites
- Backend running on port 8000
- TUI installed: `uv sync`

### Step 1: Launch TUI

```bash
uv run python -m lift_sys.main
```

### Step 2: Navigate to Prompt Refinement

```
1. Press Tab to cycle through tabs
2. Select "Prompt Refinement" tab
3. You'll see:
   - Top: Prompt input field
   - Middle: Sessions list
   - Bottom: Active session details
```

### Step 3: Create a Session

```
1. Click or Tab to prompt input field
2. Type: "A function to parse JSON with error handling"
3. Press Ctrl+Enter to submit
4. Status message appears: "Created session abc123..."
5. Session appears in sessions list
```

**Screen Output:**
```
╭─ Prompt Refinement ─────────────────────────────────╮
│ Prompt: A function to parse JSON with error handling│
│ [Create Session]                                     │
├─ Sessions ──────────────────────────────────────────┤
│ • abc123... (active) - 5 ambiguities                │
├─ Active Session ────────────────────────────────────┤
│ Session: abc123...                                   │
│ Status: active                                       │
│ Ambiguities: 5                                       │
│ - hole_function_name                                 │
│ - hole_parameter_name                                │
│ - hole_return_type                                   │
│ - hole_error_type                                    │
│ - hole_exception_handling                            │
╰──────────────────────────────────────────────────────╯
```

### Step 4: List and Select Sessions

```
1. Press Ctrl+L to refresh sessions list
2. Use arrow keys to navigate sessions
3. Press Enter to select a session
4. Session details appear in bottom pane
```

### Step 5: Resolve Holes (via API/CLI)

```
Note: Hole resolution in TUI currently delegates to API or CLI.
The TUI displays the current state and ambiguities.

Use CLI in another terminal:
$ uv run python -m lift_sys.cli session resolve abc123... hole_function_name "parse_json"

Then refresh TUI with Ctrl+L to see updated state.
```

### Step 6: Monitor Progress

```
The TUI automatically shows:
- Updated ambiguity count
- Current draft version
- Validation status
- Remaining holes

Status updates in real-time as you resolve holes externally.
```

---

## Python SDK Workflow

### Prerequisites
- Backend running on port 8000
- SDK installed: `uv sync`

### Complete Example Script

```python
#!/usr/bin/env python3
"""Complete workflow using Python SDK."""
from lift_sys.client import SessionClient

def main():
    # Initialize client
    client = SessionClient(base_url="http://localhost:8000")

    # Step 1: Create session from prompt
    print("Creating session...")
    session = client.create_session(
        prompt="A function that sorts a list of dictionaries by a given key",
        metadata={"project": "data-processing", "author": "user@example.com"}
    )
    print(f"✓ Session created: {session.session_id}")
    print(f"  Ambiguities: {len(session.ambiguities)}")

    # Step 2: Get AI assists
    print("\nGetting assist suggestions...")
    assists = client.get_assists(session.session_id)
    for assist in assists.assists:
        print(f"  {assist.hole_id}:")
        for suggestion in assist.suggestions[:2]:
            print(f"    • {suggestion}")

    # Step 3: Define resolutions (normally from user input)
    resolutions = {
        "hole_function_name": "sort_dicts",
        "hole_list_parameter_name": "items",
        "hole_key_parameter_name": "sort_key",
        "hole_return_type": "list",
    }

    # Step 4: Resolve holes iteratively
    print("\nResolving ambiguities...")
    for hole_id, resolution in resolutions.items():
        if hole_id in session.ambiguities:
            print(f"  Resolving {hole_id} → {resolution}")
            session = client.resolve_hole(
                session_id=session.session_id,
                hole_id=hole_id,
                resolution_text=resolution,
                resolution_type="refine_signature"
            )
            print(f"    ✓ Remaining: {len(session.ambiguities)}")

    # Step 5: Check if ready to finalize
    if session.ambiguities:
        print(f"\n✗ Cannot finalize: {len(session.ambiguities)} holes remaining")
        print("  Remaining holes:")
        for hole_id in session.ambiguities:
            print(f"    - {hole_id}")
        return 1

    # Step 6: Finalize session
    print("\nFinalizing session...")
    result = client.finalize_session(session.session_id)
    print("✓ Session finalized!")

    # Step 7: Extract and use IR
    ir = result.ir
    print("\nFinal IR:")
    print(f"  Intent: {ir['intent']['summary']}")

    sig = ir['signature']
    params = ', '.join([f"{p['name']}: {p['type_hint']}" for p in sig['parameters']])
    print(f"  Signature: {sig['name']}({params}) -> {sig['returns']}")

    # Save IR to file
    import json
    with open("finalized_ir.json", "w") as f:
        json.dump(ir, f, indent=2)
    print("\n✓ IR saved to finalized_ir.json")

    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
```

### Running the Script

```bash
uv run python workflow_example.py
```

**Output:**
```
Creating session...
✓ Session created: f3d8c2a1-...
  Ambiguities: 4

Getting assist suggestions...
  hole_function_name:
    • sort_dicts
    • sort_dict_list
  hole_return_type:
    • list
    • List[dict]

Resolving ambiguities...
  Resolving hole_function_name → sort_dicts
    ✓ Remaining: 3
  Resolving hole_list_parameter_name → items
    ✓ Remaining: 2
  Resolving hole_key_parameter_name → sort_key
    ✓ Remaining: 1
  Resolving hole_return_type → list
    ✓ Remaining: 0

Finalizing session...
✓ Session finalized!

Final IR:
  Intent: Sort a list of dictionaries by a given key
  Signature: sort_dicts(items: list, sort_key: str) -> list

✓ IR saved to finalized_ir.json
```

### Async Example

```python
import asyncio
from lift_sys.client import SessionClient

async def async_workflow():
    client = SessionClient(base_url="http://localhost:8000")

    # Concurrent operations
    tasks = [
        client.acreate_session(prompt=f"Function {i}"),
        client.acreate_session(prompt=f"Function {i+1}"),
        client.acreate_session(prompt=f"Function {i+2}"),
    ]

    sessions = await asyncio.gather(*tasks)
    print(f"Created {len(sessions)} sessions concurrently")

    # List all sessions
    response = await client.alist_sessions()
    print(f"Total sessions: {len(response.sessions)}")

asyncio.run(async_workflow())
```

---

## Common Patterns

### Pattern 1: Batch Session Creation

```python
from lift_sys.client import SessionClient

def create_sessions_from_file(prompts_file: str):
    client = SessionClient()
    sessions = []

    with open(prompts_file) as f:
        for line in f:
            prompt = line.strip()
            if prompt:
                session = client.create_session(prompt=prompt)
                sessions.append(session)
                print(f"Created: {session.session_id} ({len(session.ambiguities)} holes)")

    return sessions
```

### Pattern 2: Automated Resolution with Defaults

```python
def auto_resolve_common_holes(client, session_id, defaults):
    """Automatically resolve holes that match known patterns."""
    session = client.get_session(session_id)

    for hole_id in list(session.ambiguities):
        # Check if we have a default resolution
        for pattern, resolution in defaults.items():
            if pattern in hole_id:
                session = client.resolve_hole(
                    session_id=session_id,
                    hole_id=hole_id,
                    resolution_text=resolution
                )
                print(f"Auto-resolved: {hole_id} → {resolution}")
                break

    return session

# Usage
defaults = {
    "return_type": "None",
    "parameter_type": "str",
    "exception": "ValueError"
}
session = auto_resolve_common_holes(client, session_id, defaults)
```

### Pattern 3: Reverse Mode IR Refinement

```bash
# Start with existing code
uv run python -m lift_sys.cli session create \
  --ir-file existing_spec.json \
  --source reverse_mode \
  --json

# Refine the lifted IR
uv run python -m lift_sys.cli session resolve <session-id> hole_assertion "x > 0"
```

### Pattern 4: CI/CD Integration

```bash
#!/bin/bash
# ci-refine-spec.sh

SESSION_ID=$(uv run python -m lift_sys.cli session create \
  --prompt "$SPEC_PROMPT" \
  --json | jq -r '.session_id')

# Auto-resolve with defaults
uv run python -m lift_sys.cli session resolve $SESSION_ID hole_language "python"
uv run python -m lift_sys.cli session resolve $SESSION_ID hole_return_type "None"

# Finalize
uv run python -m lift_sys.cli session finalize $SESSION_ID --output spec.json

# Use in next CI step
uv run lift-sys forward --ir spec.json --output generated.py
```

---

## Troubleshooting

### Issue: "Session not found"

**Symptoms:**
```
Error: Session abc123... not found
```

**Solutions:**
1. Verify session ID: `uv run python -m lift_sys.cli session list`
2. Check if session was deleted
3. Ensure backend is running and accessible

### Issue: "Cannot finalize: unresolved holes"

**Symptoms:**
```
Error: Cannot finalize session with 3 unresolved ambiguities
```

**Solutions:**
1. List remaining holes: `uv run python -m lift_sys.cli session get <id>`
2. Resolve each hole systematically
3. Check assists for suggestions: `uv run python -m lift_sys.cli session assists <id>`

### Issue: Connection refused

**Symptoms:**
```
Error: [Errno 61] Connection refused
```

**Solutions:**
1. Start backend: `./start.sh` or `uv run uvicorn lift_sys.api.server:app --reload`
2. Verify port 8000 is available: `lsof -i :8000`
3. Check firewall settings

### Issue: Ambiguity not resolving

**Symptoms:**
- Hole resolution succeeds but ambiguity count doesn't decrease

**Possible causes:**
1. Resolution created a new hole
2. Invalid resolution triggered re-analysis
3. Dependent holes need resolution first

**Solutions:**
1. Check validation status: `session.current_draft.validation_status`
2. Review SMT results for contradictions
3. Try resolving dependencies first

### Issue: Session state not updating in TUI

**Symptoms:**
- TUI shows old ambiguity count after resolution

**Solutions:**
1. Press `Ctrl+L` to manually refresh
2. Check WebSocket connection
3. Verify session_id matches

---

## Next Steps

- **Read API Documentation**: See `docs/API_SESSION_MANAGEMENT.md` for complete API reference
- **Run Example Script**: Try `examples/session_workflow.py` for a working demonstration
- **Explore Frontend**: Visit the Prompt Workbench at http://localhost:5173
- **Review Design**: Read `docs/IR_DESIGN.md` for IR structure details

For questions or issues, see [GitHub Issues](https://github.com/rand/lift-sys/issues).
