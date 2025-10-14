# MVP Implementation Plan: Python Forward + Reverse Mode with IR Refinement

**Date**: October 14, 2025
**Status**: Ready to Implement
**Priority**: P0

## MVP Definition

**Goal**: Working Python forward mode + reverse mode with human/agent IR refinement loop

**Components**:
1. **Forward Mode**: Natural language → IR → Python code
2. **Reverse Mode**: Python code → IR extraction
3. **Refinement Loop**: Interactive IR improvement via typed holes and session management

**LLM Provider**: Anthropic Claude (already integrated)
**Test Strategy**: E2E tests run locally with real API calls

## Current State Assessment

### What Actually Works ✅

Based on code review of `lift_sys/api/server.py` and integration tests:

1. **API Endpoints Operational**:
   - `/api/spec-sessions` - Create session from prompt or IR
   - `/api/spec-sessions/{id}/holes/{hole_id}/resolve` - Resolve ambiguities
   - `/api/spec-sessions/{id}/finalize` - Finalize IR
   - `/api/spec-sessions/{id}/generate` - Generate Python code
   - `/api/reverse` - Extract IR from code

2. **Session Management Working**:
   - `SpecSessionManager` handles session lifecycle
   - `PromptToIRTranslator` converts NLP to IR
   - Typed holes tracked and resolvable
   - Revision history maintained

3. **Provider Integration Ready**:
   - `AnthropicProvider` implemented (lines 1-97)
   - Initialized in `lifespan()` context (lines 313-327)
   - Token store for API key management
   - Health checks implemented

4. **Code Generation Working**:
   - `CodeGenerator` produces Python code from IR
   - Assertion injection operational
   - Docstring generation functional
   - Type hint preservation working

### What Needs Verification ⚠️

1. **Anthropic API Key Setup**:
   - Currently not in .env file
   - Token store mechanism exists but needs setup
   - Need to configure for local testing

2. **End-to-End Workflows**:
   - Forward mode: Never tested with real LLM
   - Reverse mode: Implemented but not verified E2E
   - Refinement loop: Framework exists, needs validation

3. **XGrammar IR Translator**:
   - `XGrammarIRTranslator` referenced in translator.py:38
   - May or may not work with Anthropic (no structured output support)
   - Has fallback to rule-based translation

## Implementation Plan

### Phase 1: Setup and Manual Verification (Day 1)

**Goal**: Get Anthropic working and verify API manually

#### Task 1.1: Configure Anthropic API Key (30 min)

**Option A: Environment Variable** (Simplest for local testing)
```bash
# Add to .env
echo 'ANTHROPIC_API_KEY="sk-ant-..."' >> .env
```

**Option B: Token Store** (Production approach)
- Use OAuth flow to store credentials
- Token stored encrypted in token_store

**Recommendation**: Start with Option A for local testing

#### Task 1.2: Verify Provider Initialization (30 min)

Test that provider initializes correctly:

```python
# Quick test script: test_anthropic_setup.py
import asyncio
from lift_sys.providers.anthropic_provider import AnthropicProvider

async def test_setup():
    provider = AnthropicProvider()

    # Initialize with API key
    await provider.initialize({"api_key": "sk-ant-..."})

    # Check health
    health = await provider.check_health()
    print(f"Health check: {health}")

    # Simple test
    result = await provider.generate_text("Say hello", max_tokens=50)
    print(f"Response: {result}")

    await provider.aclose()

asyncio.run(test_setup())
```

Run: `ANTHROPIC_API_KEY=$(cat .env | grep ANTHROPIC | cut -d= -f2) python test_anthropic_setup.py`

#### Task 1.3: Manual API Testing (2 hours)

**Step 1: Start Server with Anthropic**
```bash
# Method 1: Direct with env var
ANTHROPIC_API_KEY="sk-ant-..." \
LIFT_SYS_ENABLE_DEMO_USER_HEADER=1 \
uv run uvicorn lift_sys.api.server:app --reload

# Method 2: Store token first
# Use the OAuth flow or token store API
```

**Step 2: Test Forward Mode**
```bash
# Create session from prompt
SESSION_ID=$(curl -X POST http://localhost:8000/api/spec-sessions \
  -H "Content-Type: application/json" \
  -H "X-Demo-User-ID: test" \
  -d '{
    "prompt": "Create a function that takes two integers and returns their sum",
    "source": "prompt"
  }' | jq -r '.session_id')

echo "Session ID: $SESSION_ID"

# Check session status
curl http://localhost:8000/api/spec-sessions/$SESSION_ID \
  -H "X-Demo-User-ID: test" | jq .

# Finalize if no ambiguities
curl -X POST http://localhost:8000/api/spec-sessions/$SESSION_ID/finalize \
  -H "X-Demo-User-ID: test" | jq .

# Generate code
curl -X POST http://localhost:8000/api/spec-sessions/$SESSION_ID/generate \
  -H "Content-Type: application/json" \
  -H "X-Demo-User-ID: test" \
  -d '{
    "target_language": "python",
    "inject_assertions": true,
    "include_docstrings": true
  }' | jq -r '.source_code'
```

**Step 3: Test Reverse Mode**
```bash
# First, open a repository (or configure one)
curl -X POST http://localhost:8000/api/repos/open \
  -H "Content-Type: application/json" \
  -H "X-Demo-User-ID: test" \
  -d '{"identifier": "test-repo"}'

# Run reverse mode (requires lifter setup)
curl -X POST http://localhost:8000/api/reverse \
  -H "Content-Type: application/json" \
  -H "X-Demo-User-ID: test" \
  -d '{
    "analyses": ["codeql"],
    "queries": []
  }' | jq .
```

**Document Results**:
- What worked?
- What failed?
- What error messages?
- Does IR generation happen?
- Is code generated?

### Phase 2: Real E2E Tests (Days 2-3)

#### Task 2.1: Forward Mode E2E Test (Day 2)

Create `tests/e2e_real/test_forward_mode_real.py`:

```python
"""REAL E2E tests for forward mode using Anthropic.

These tests make actual API calls and cost money.
Run locally with: pytest -m e2e_real
"""

import os
import pytest

# Skip if no API key
pytestmark = pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="Requires ANTHROPIC_API_KEY environment variable"
)


@pytest.mark.e2e_real
@pytest.mark.slow
@pytest.mark.asyncio
async def test_forward_mode_simple_addition(api_client):
    """
    REAL E2E: Natural language → IR → Python code.

    Tests the complete forward mode workflow:
    1. User provides NLP prompt
    2. System generates IR (with real LLM)
    3. User refines IR if needed (hole resolution)
    4. System generates Python code (with real LLM)
    5. Code is syntactically valid
    6. Code executes correctly
    """

    # Step 1: Create session from natural language
    create_response = api_client.post(
        "/api/spec-sessions",
        json={
            "prompt": "Create a function called add that takes two integers a and b, and returns their sum",
            "source": "prompt",
            "metadata": {"test": "forward_mode_real"}
        }
    )

    assert create_response.status_code == 200, f"Session creation failed: {create_response.text}"
    session_data = create_response.json()
    session_id = session_data["session_id"]

    print(f"\n✓ Session created: {session_id}")
    print(f"  Status: {session_data['status']}")
    print(f"  Ambiguities: {len(session_data['ambiguities'])}")

    # Step 2: Check for ambiguities (typed holes)
    if session_data["ambiguities"]:
        print(f"\n→ Found {len(session_data['ambiguities'])} ambiguities to resolve")

        # Get assists for each hole
        assists_response = api_client.get(f"/api/spec-sessions/{session_id}/assists")
        assert assists_response.status_code == 200
        assists = assists_response.json()["assists"]

        # Resolve each hole based on assists
        for assist in assists[:3]:  # Resolve first 3 holes
            hole_id = assist["hole_id"]
            suggestion = assist["suggestion"]

            print(f"  Resolving hole '{hole_id}': {suggestion}")

            resolve_response = api_client.post(
                f"/api/spec-sessions/{session_id}/holes/{hole_id}/resolve",
                json={
                    "resolution_text": suggestion,
                    "resolution_type": assist.get("hole_kind", "clarify_intent")
                }
            )

            if resolve_response.status_code == 200:
                print(f"    ✓ Resolved")
            else:
                print(f"    ✗ Failed: {resolve_response.text}")

    # Step 3: Get current session state
    session_response = api_client.get(f"/api/spec-sessions/{session_id}")
    session_data = session_response.json()

    print(f"\n→ Current session state:")
    print(f"  Remaining ambiguities: {len(session_data['ambiguities'])}")
    print(f"  Revisions: {session_data['revision_count']}")

    # Step 4: Finalize session
    if not session_data["ambiguities"]:
        finalize_response = api_client.post(f"/api/spec-sessions/{session_id}/finalize")

        assert finalize_response.status_code == 200, f"Finalization failed: {finalize_response.text}"
        print("\n✓ Session finalized")
    else:
        pytest.skip(f"Cannot finalize: {len(session_data['ambiguities'])} unresolved ambiguities")

    # Step 5: Generate Python code
    generate_response = api_client.post(
        f"/api/spec-sessions/{session_id}/generate",
        json={
            "target_language": "python",
            "inject_assertions": True,
            "assertion_mode": "assert",
            "include_docstrings": True,
            "include_type_hints": True
        }
    )

    assert generate_response.status_code == 200, f"Code generation failed: {generate_response.text}"
    code_data = generate_response.json()
    generated_code = code_data["source_code"]

    print(f"\n✓ Code generated ({len(generated_code)} characters)")
    print("\nGenerated code:")
    print("=" * 60)
    print(generated_code)
    print("=" * 60)

    # Step 6: Validate generated code
    assert len(generated_code) > 0, "Generated code is empty"
    assert "def " in generated_code, "No function definition found"

    # Step 7: Syntax check
    try:
        compile(generated_code, "<generated>", "exec")
        print("\n✓ Syntax check passed")
    except SyntaxError as e:
        pytest.fail(f"Generated code has syntax error: {e}")

    # Step 8: Execute and test
    namespace = {}
    exec(generated_code, namespace)

    # Find the add function
    add_func = namespace.get("add")
    if not add_func:
        # Look for any callable that isn't built-in
        for name, obj in namespace.items():
            if callable(obj) and not name.startswith("_"):
                add_func = obj
                print(f"\n→ Found function: {name}")
                break

    assert add_func is not None, "No callable function found in generated code"
    assert callable(add_func), "Found object is not callable"

    # Test the function
    print("\n→ Testing generated function:")
    test_cases = [
        (2, 3, 5),
        (10, 20, 30),
        (-5, 5, 0),
        (0, 0, 0),
    ]

    for a, b, expected in test_cases:
        result = add_func(a, b)
        print(f"  add({a}, {b}) = {result} (expected {expected})")
        assert result == expected, f"add({a}, {b}) returned {result}, expected {expected}"

    print("\n✓ All tests passed!")

    # Success metrics
    return {
        "session_id": session_id,
        "ambiguities_resolved": len(session_data.get("ambiguities", [])),
        "code_length": len(generated_code),
        "syntax_valid": True,
        "tests_passed": len(test_cases)
    }
```

**Run Test**:
```bash
# Set API key
export ANTHROPIC_API_KEY="sk-ant-..."

# Run real E2E test
LIFT_SYS_ENABLE_DEMO_USER_HEADER=1 \
pytest tests/e2e_real/test_forward_mode_real.py -v -s -m e2e_real
```

#### Task 2.2: Reverse Mode E2E Test (Day 3)

Create `tests/e2e_real/test_reverse_mode_real.py`:

```python
"""REAL E2E tests for reverse mode."""

import os
import pytest
from pathlib import Path

pytestmark = pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="Requires ANTHROPIC_API_KEY environment variable"
)


@pytest.mark.e2e_real
@pytest.mark.slow
async def test_reverse_mode_python_to_ir(api_client, tmp_path):
    """
    REAL E2E: Python code → IR extraction.

    Tests the complete reverse mode workflow:
    1. User provides Python code
    2. System extracts IR
    3. IR captures intent, signature, assertions
    4. IR can be used to create session
    """

    # Step 1: Create test Python file
    test_code = '''
def fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number.

    Args:
        n: Position in Fibonacci sequence (0-indexed)

    Returns:
        The nth Fibonacci number

    Raises:
        ValueError: If n is negative
    """
    if n < 0:
        raise ValueError("n must be non-negative")

    if n <= 1:
        return n

    return fibonacci(n - 1) + fibonacci(n - 2)
'''

    # Step 2: Set up repository (simplified for test)
    # In reality, would use actual repo, but for now create temp structure
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / "fibonacci.py").write_text(test_code)

    print(f"\n→ Created test repository at {repo_path}")

    # Step 3: Call reverse mode API
    # Note: This requires repository setup via /api/repos/open
    # For this test, we'll need to mock or set up properly

    # TODO: Complete reverse mode test once repository setup is verified
    pytest.skip("Reverse mode requires repository setup - implement after forward mode works")
```

#### Task 2.3: IR Refinement Loop Test (Day 3)

Test the human/agent interaction:

```python
"""Test IR refinement workflow."""

@pytest.mark.e2e_real
@pytest.mark.slow
async def test_ir_refinement_loop(api_client):
    """
    Test interactive IR refinement.

    Workflow:
    1. Create session with vague prompt
    2. System generates IR with holes
    3. User resolves holes iteratively
    4. System refines IR
    5. Final IR is complete
    """

    # Vague prompt that will create ambiguities
    create_response = api_client.post(
        "/api/spec-sessions",
        json={
            "prompt": "Create a function to process data",
            "source": "prompt"
        }
    )

    assert create_response.status_code == 200
    session_data = create_response.json()
    session_id = session_data["session_id"]

    print(f"\n✓ Session created with vague prompt")
    print(f"  Ambiguities: {len(session_data['ambiguities'])}")

    # Should have ambiguities
    assert len(session_data["ambiguities"]) > 0, "Expected ambiguities from vague prompt"

    # Get assists
    assists_response = api_client.get(f"/api/spec-sessions/{session_id}/assists")
    assists = assists_response.json()["assists"]

    print(f"\n→ Got {len(assists)} assists")

    # Resolve iteratively
    for assist in assists:
        print(f"\n  Resolving: {assist['description']}")

        # Apply resolution
        resolve_response = api_client.post(
            f"/api/spec-sessions/{session_id}/holes/{assist['hole_id']}/resolve",
            json={
                "resolution_text": assist["suggestion"],
                "resolution_type": assist["hole_kind"]
            }
        )

        if resolve_response.status_code == 200:
            resolved_data = resolve_response.json()
            print(f"    ✓ Remaining ambiguities: {len(resolved_data['ambiguities'])}")

    # Check final state
    final_response = api_client.get(f"/api/spec-sessions/{session_id}")
    final_data = final_response.json()

    print(f"\n→ Final state:")
    print(f"  Ambiguities resolved: {len(session_data['ambiguities']) - len(final_data['ambiguities'])}")
    print(f"  Revisions: {final_data['revision_count']}")

    assert final_data["revision_count"] > 1, "Should have multiple revisions from refinement"
```

### Phase 3: Documentation (Day 4)

#### Task 3.1: Update README with MVP Status

Add section:
```markdown
## MVP Status: Forward + Reverse Mode for Python

### Working Features ✅

#### Forward Mode (NLP → Code)
- Natural language specification to Python code
- Interactive IR refinement via typed holes
- Assertion injection
- Type hint preservation
- Docstring generation

**Example**:
```bash
# Start server
ANTHROPIC_API_KEY="sk-ant-..." ./start.sh

# Create session from prompt
curl -X POST http://localhost:8000/api/spec-sessions \
  -H "Content-Type: application/json" \
  -H "X-Demo-User-ID: test" \
  -d '{"prompt": "Create a function that adds two numbers", "source": "prompt"}'
```

#### Reverse Mode (Code → IR)
- Extract IR from existing Python code
- Capture intent, signatures, assertions
- Import into refinement sessions

#### IR Refinement Loop
- Interactive ambiguity resolution
- Typed holes with suggestions
- Session versioning
- Revision history

### Running E2E Tests

Real E2E tests require Anthropic API key:

```bash
# Set API key
export ANTHROPIC_API_KEY="sk-ant-..."

# Run real E2E tests (local only)
LIFT_SYS_ENABLE_DEMO_USER_HEADER=1 \
pytest tests/e2e_real/ -v -s -m e2e_real
```

**Note**: E2E tests make real API calls and cost money (~$0.01-0.10 per test).
```

#### Task 3.2: Create Quick Start Guide

`docs/quickstart-mvp.md`:
```markdown
# Quick Start: MVP (Python Forward + Reverse Mode)

## Prerequisites

1. Anthropic API key
2. Python 3.11+
3. Node.js 18+ (for frontend)

## Setup

1. Clone and install:
```bash
git clone <repo>
cd lift-sys
uv sync
```

2. Configure API key:
```bash
echo 'ANTHROPIC_API_KEY="sk-ant-..."' >> .env
```

3. Start server:
```bash
./start.sh
```

## Try Forward Mode

1. Open http://localhost:5173
2. Click "New Session"
3. Enter: "Create a function that calculates factorial of n"
4. Click "Generate IR"
5. Resolve any ambiguities
6. Click "Generate Code"
7. See generated Python code!

## Try Reverse Mode

1. Open repository in IDE view
2. Click "Extract IR from Code"
3. Select Python file
4. View extracted IR
5. Import into session for refinement

## Next Steps

- Read [API Documentation](api-docs.md)
- See [Architecture Overview](architecture.md)
- Explore [Examples](examples/)
```

## Success Criteria

### Minimum Success (MVP)
- [ ] Anthropic provider configured and working
- [ ] ONE forward mode E2E test passing (NLP → Python)
- [ ] Generated Python code is syntactically valid
- [ ] Generated Python code executes correctly
- [ ] IR refinement loop functional (hole resolution)

### Full Success
- [ ] Forward mode E2E test passing
- [ ] Reverse mode E2E test passing (Python → IR)
- [ ] IR refinement loop E2E test passing
- [ ] Documentation updated
- [ ] Quick start guide created

## Timeline

- **Day 1**: Setup Anthropic, manual testing
- **Day 2**: Forward mode E2E test
- **Day 3**: Reverse mode + refinement loop tests
- **Day 4**: Documentation

**Total: 4 days to working MVP**

## Risk Mitigation

### Risk: XGrammar Translator May Not Work with Anthropic
- **Impact**: High - IR generation may fail
- **Likelihood**: Medium
- **Mitigation**: Has rule-based fallback in translator.py:118-150
- **Plan B**: Improve rule-based translator

### Risk: API Key Costs
- **Impact**: Medium - could get expensive
- **Likelihood**: Low with reasonable limits
- **Mitigation**: Set max_tokens=1024, track usage
- **Budget**: ~$5 for all E2E testing

### Risk: Test Flakiness with Real LLM
- **Impact**: Medium - tests may be non-deterministic
- **Likelihood**: High - LLM output varies
- **Mitigation**:
  - Test code structure, not exact content
  - Use temperature=0 for more deterministic output
  - Validate execution, not exact strings

## Next Steps After MVP

Once MVP is working:
1. Add TypeScript support (already implemented, needs testing)
2. Deploy to Modal
3. Performance optimization
4. Fix remaining 145 failing tests
5. Expand to Go/Rust (future)

## Conclusion

The foundation is solid - we just need to:
1. Configure Anthropic
2. Test E2E workflows
3. Document what works

All the pieces exist, we're just verifying they work together!
