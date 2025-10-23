# Product Requirements Document: Forward Mode
## Natural Language to Verified Code

**Version**: 1.0
**Date**: 2025-10-21
**Status**: Active
**Owner**: Codelift Team

**Parent Document**: [PRD_LIFT.md](PRD_LIFT.md)
**Related Documents**:
- [RFC_LIFT_ARCHITECTURE.md](RFC_LIFT_ARCHITECTURE.md) - Technical architecture
- [PRD_TYPED_HOLES.md](PRD_TYPED_HOLES.md) - Hole resolution details
- [PRD_INTERACTIVE_REFINEMENT.md](PRD_INTERACTIVE_REFINEMENT.md) - Refinement workflows

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [User Journey & Workflow](#2-user-journey--workflow)
3. [Functional Requirements](#3-functional-requirements)
4. [Non-Functional Requirements](#4-non-functional-requirements)
5. [Success Metrics](#5-success-metrics)
6. [Technical Architecture](#6-technical-architecture)
7. [User Experience Design](#7-user-experience-design)
8. [Dependencies & Integration](#8-dependencies--integration)

---

## 1. Executive Summary

### Vision

**Forward mode democratizes professional-quality code creation** by translating natural language descriptions into formally verified, executable code through a human-in-the-loop refinement process backed by constraint solving and typed holes.

### Problem Statement

Current AI coding tools suffer from three critical flaws:

1. **No Verification**: Generated code may be syntactically valid but semantically incorrect (edge cases missed, constraints violated)
2. **Black Box Generation**: Users don't understand why code was generated a certain way or what assumptions were made
3. **Binary Output**: Either the code works or it doesn't - no middle ground for iterative refinement

These limitations exclude semi-technical users (product managers, designers, technical writers) and create risk even for professional developers.

### Solution Overview

Forward mode addresses these flaws through a **five-stage pipeline**:

```
Natural Language Prompt
  ↓
[Stage 1: Intent Extraction] → IntentSpec (goals, roles, constraints)
  ↓
[Stage 2: Signature Generation] → SigClause (function signature with types)
  ↓
[Stage 3: Constraint Extraction] → FuncSpec (pre/post conditions, effects)
  ↓
[Stage 4: Hole Detection & Resolution] → Interactive refinement with user
  ↓
[Stage 5: Code Generation] → Verified, executable code
```

**Key Innovations**:
- **Typed Holes**: Explicit unknowns enable iterative refinement (6 kinds: term, type, spec, entity, function, module)
- **XGrammar Constraints**: Guarantees syntactic correctness during generation
- **SMT Verification**: Proves specifications are satisfiable before code generation
- **Best-of-N Sampling**: Generates multiple candidates, ranks by quality, returns best (N=3 default)
- **Dual-Provider Routing**: Best Available models (Anthropic/OpenAI/Google) for planning, Modal Inference for constrained generation

### Current Status (Q1 2025)

**Production Performance** (Modal L40S GPU + vLLM + XGrammar + Qwen2.5-Coder-7B):
- ✅ **80% compilation success rate** (goal: 90%)
- ✅ **60% execution success rate** (goal: 75%)
- ✅ **16s median end-to-end latency** (10.8s IR gen + 4.3s code gen)
- ✅ **$0.0029 cost per request** (highly cost-effective)
- ✅ **Multi-language support**: Python, TypeScript (initial languages)

**Infrastructure**:
- ✅ Modal.com serverless deployment
- ✅ Supabase session storage with Row-Level Security
- ✅ Multi-provider support (ADR 001: Dual-provider routing)
- ✅ XGrammar-constrained decoding for syntactic correctness

**Known Limitations**:
- Control flow (if/else) indentation bugs (~20% of failures)
- Semantic bugs that XGrammar can't prevent (type computing patterns)
- Retry effectiveness limited (feedback doesn't always fix semantic bugs)

### Target Users

**Primary**: Semi-technical contributors (product managers, designers, technical writers)
- Create features by describing intent in natural language
- Understand what code does through IntentSpec reverse-translation
- Iterate safely with typed holes and AI suggestions

**Secondary**: Professional developers
- Accelerate feature development with verified generation
- Understand and refactor legacy code (reverse mode integration)
- Trust output through formal verification

**Tertiary**: AI agents
- Programmatic API for autonomous code generation
- Verifiable, explainable output for compliance
- Typed contracts for inter-agent communication

---

## 2. User Journey & Workflow

### Journey 1: Semi-Technical User Creates a REST API

**Persona**: Sarah, Product Manager
**Goal**: Create a money transfer API endpoint for validation before engineering investment
**Context**: Has technical background but doesn't write production code daily

#### Step-by-Step Flow

**Step 1: User Input**

Sarah opens the lift web UI and types:

```
Create a REST API endpoint to transfer money between user accounts.
The sender must have sufficient balance. Both accounts must exist.
Transfers are atomic and logged for audit purposes.
```

**System Processing** (Stage 1 - Intent Extraction, ~3s):
- Uses DSPy signature `NLToIntent` (optimized via MIPROv2)
- Extracts: goals, roles, constraints, domain concepts
- Generates `IntentClause`

**Output to User**:
```yaml
Intent: "Enable secure money transfers between accounts"
Roles:
  - Sender: User initiating transfer
  - Recipient: User receiving funds
  - System: Platform executing transfer
Goals:
  - Transfer succeeds if sender has balance
  - Transfer is atomic (all-or-nothing)
  - All transfers logged for audit
Constraints:
  - Sender and recipient accounts exist
  - Sender balance >= transfer amount
  - Amount > 0
  - Sender != recipient
```

**User Action**: Sarah reviews intent, clicks "Looks Good" or edits if needed

---

**Step 2: Signature Generation** (Stage 2, ~2s)

**System Processing**:
- Uses DSPy signature `IntentToSignature`
- Infers function name, parameters, return type
- Identifies ambiguities as **typed holes**

**Output to User** (with holes highlighted):
```python
async def transfer(
    sender_id: UUID,
    recipient_id: UUID,
    amount: Money,
    ?idempotency_key: Optional[str] = None  # HOLE 1: Prevent duplicate transfers?
) -> Result[Transfer, TransferError]:
    """Transfer money between accounts."""
    ...
```

**User Interaction**: Sarah hovers over `?idempotency_key` hole

**System Shows**:
- **Hole Type**: `term` (missing parameter)
- **Type Constraint**: `Optional[str]`
- **Suggestion** (90% confidence):
  > "Include idempotency_key for safe retries. Network failures may cause retries. Idempotency prevents double-charging."
- **Alternatives**:
  - (70% confidence) "Omit - assume retries handled by infrastructure"
  - (50% confidence) "Add request_id UUID for deduplication"

**User Action**: Sarah clicks "Accept Suggestion"

**System Updates**: Hole filled, signature finalized:
```python
async def transfer(
    sender_id: UUID,
    recipient_id: UUID,
    amount: Money,
    idempotency_key: Optional[str] = None
) -> Result[Transfer, TransferError]:
    ...
```

---

**Step 3: Constraint Extraction** (Stage 3, ~3s)

**System Processing**:
- Uses DSPy signature `ConstraintExtraction`
- Generates formal pre/post conditions
- Encodes as SMT-LIB predicates for verification

**Output to User** (FuncSpec):
```yaml
Preconditions:
  - sender exists in accounts table
  - recipient exists in accounts table
  - sender != recipient
  - sender.balance >= amount
  - amount > 0

Postconditions:
  - sender.balance' = sender.balance - amount
  - recipient.balance' = recipient.balance + amount
  - Transfer record created in audit log
  - Idempotent: Same idempotency_key → same result

Effects:
  - Database: Write to accounts table, transfers table
  - Network: None
  - State: Modifies account balances

Assertions:
  - assert sender.balance >= amount, "Insufficient funds"
  - assert sender != recipient, "Cannot transfer to self"
  - assert amount > 0, "Amount must be positive"
```

**System Verification** (SMT Solver):
- Encodes constraints to Z3
- Checks satisfiability: ✅ SAT (no contradictions)
- No counterexamples

**User View**: Green checkmark "Constraints are valid ✓"

---

**Step 4: Code Generation** (Stage 5, ~4s)

**System Processing**:
- Uses XGrammar-constrained vLLM generation
- JSON schema derived from IR specification
- Best-of-N sampling (N=3): generates 3 candidates, ranks by quality
- Modal L40S GPU inference

**XGrammar Constraint** (excerpt):
```json
{
  "type": "object",
  "properties": {
    "function_name": {"const": "transfer"},
    "parameters": {
      "type": "array",
      "minItems": 4,
      "maxItems": 4,
      "items": [
        {"properties": {"name": {"const": "sender_id"}}},
        {"properties": {"name": {"const": "recipient_id"}}},
        {"properties": {"name": {"const": "amount"}}},
        {"properties": {"name": {"const": "idempotency_key"}}}
      ]
    },
    "assertions": {
      "type": "array",
      "minItems": 3
    }
  }
}
```

**Generated Code**:
```python
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import uuid
from datetime import datetime

router = APIRouter()

@router.post("/transfers")
async def transfer(
    sender_id: uuid.UUID,
    recipient_id: uuid.UUID,
    amount: int,  # cents
    idempotency_key: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Transfer money between accounts atomically."""

    # Validate inputs
    assert amount > 0, "Amount must be positive"
    assert sender_id != recipient_id, "Cannot transfer to self"

    # Check idempotency
    if idempotency_key:
        existing = await db.execute(
            select(Transfer).where(Transfer.idempotency_key == idempotency_key)
        )
        if existing.scalar_one_or_none():
            return existing.scalar_one().to_dict()

    # Begin transaction
    async with db.begin():
        # Lock accounts for update
        sender = await db.execute(
            select(Account).where(Account.id == sender_id).with_for_update()
        )
        sender = sender.scalar_one_or_none()
        if not sender:
            raise HTTPException(404, "Sender account not found")

        recipient = await db.execute(
            select(Account).where(Account.id == recipient_id).with_for_update()
        )
        recipient = recipient.scalar_one_or_none()
        if not recipient:
            raise HTTPException(404, "Recipient account not found")

        # Check balance
        assert sender.balance >= amount, "Insufficient funds"

        # Execute transfer
        sender.balance -= amount
        recipient.balance += amount

        # Create audit log
        transfer = Transfer(
            id=uuid.uuid4(),
            sender_id=sender_id,
            recipient_id=recipient_id,
            amount=amount,
            idempotency_key=idempotency_key,
            timestamp=datetime.utcnow()
        )
        db.add(transfer)
        await db.flush()

    return transfer.to_dict()
```

**Validation Results**:
- ✅ Compiles without errors
- ✅ Type checks pass (mypy)
- ✅ Execution tests: 5/5 scenarios pass
  - Normal transfer
  - Insufficient funds (raises exception)
  - Duplicate idempotency key (returns cached result)
  - Self-transfer (raises exception)
  - Non-existent accounts (raises exceptions)

---

**Step 5: Delivery**

**User View** (Split View):
- **Left Panel**: Original prompt + IntentSpec + FuncSpec
- **Right Panel**: Generated code with syntax highlighting
- **Bottom Panel**:
  - Test results (5/5 passed ✅)
  - Execution trace
  - Performance metrics (4.3s generation, $0.0029 cost)

**User Actions**:
- **Copy to Clipboard**: Code ready to paste
- **Download IR**: Save intermediate representation
- **Export to GitHub**: Create PR with IntentSpec as description
- **Refine Further**: Go back and adjust constraints

**Outcome**: Sarah created a production-ready API endpoint in **~16 seconds** with **zero manual coding**. All edge cases handled. Audit trail complete. Ready for engineering review.

---

### Journey 2: Professional Developer Accelerates Feature Work

**Persona**: Marcus, Senior Backend Engineer
**Goal**: Implement a complex validation function faster than manual coding
**Context**: Knows the domain, wants to skip boilerplate

#### Step-by-Step Flow

**Step 1: Precise Prompt**

Marcus types (more technical than Sarah):

```
Function: validate_email
Input: email: str
Returns: tuple[bool, Optional[str]]  # (is_valid, error_message)

Rules:
- Must contain exactly one @ symbol
- Local part (before @): 1-64 chars, alphanumeric + dots/hyphens
- Domain part (after @): valid DNS domain with at least one dot
- No leading/trailing dots in either part
- Case-insensitive comparison

Test cases:
- "user@example.com" → (True, None)
- "invalid.email" → (False, "Missing @ symbol")
- "@example.com" → (False, "Empty local part")
- "user@localhost" → (False, "Domain must have TLD")
```

**System Processing**: Extracts intent, generates signature, constraints

**Output** (no holes - prompt was precise):
```python
def validate_email(email: str) -> tuple[bool, Optional[str]]:
    """Validate email address format."""

    # Preconditions
    assert isinstance(email, str), "Email must be string"

    # Implementation (generated)
    ...

    # Postconditions
    assert isinstance(result, tuple), "Returns tuple"
    assert len(result) == 2, "Returns pair"
    assert isinstance(result[0], bool), "First element is bool"
```

**Validation**: SMT solver verifies constraints are satisfiable

**Code Generation** (Best-of-3):
```python
import re
from typing import Optional

def validate_email(email: str) -> tuple[bool, Optional[str]]:
    """
    Validate email address format.

    Rules:
    - Must contain exactly one @ symbol
    - Local part: 1-64 chars, alphanumeric + dots/hyphens
    - Domain part: valid DNS domain with at least one dot
    - No leading/trailing dots
    """
    if not isinstance(email, str):
        return (False, "Email must be a string")

    # Check for exactly one @
    if email.count('@') != 1:
        return (False, "Must contain exactly one @ symbol")

    local, domain = email.split('@')

    # Validate local part
    if not local or len(local) > 64:
        return (False, "Local part must be 1-64 characters")

    if local.startswith('.') or local.endswith('.'):
        return (False, "Local part cannot start or end with dot")

    if not re.match(r'^[a-zA-Z0-9.-]+$', local):
        return (False, "Local part contains invalid characters")

    # Validate domain part
    if not domain:
        return (False, "Empty domain part")

    if '.' not in domain:
        return (False, "Domain must have TLD")

    if domain.startswith('.') or domain.endswith('.'):
        return (False, "Domain cannot start or end with dot")

    if not re.match(r'^[a-zA-Z0-9.-]+$', domain):
        return (False, "Domain contains invalid characters")

    return (True, None)
```

**Test Results**:
```
✅ validate_email("user@example.com") == (True, None)
✅ validate_email("invalid.email") == (False, "Must contain exactly one @ symbol")
✅ validate_email("@example.com") == (False, "Local part must be 1-64 characters")
✅ validate_email("user@localhost") == (False, "Domain must have TLD")
All specified tests pass
```

**Outcome**: Marcus got a working, tested function in **10 seconds** that would have taken **10-15 minutes** to write manually. He can now focus on the interesting architectural decisions.

---

### Journey 3: Iterative Refinement with Multiple Holes

**Persona**: Alex, Technical Writer
**Goal**: Create example code for API documentation
**Context**: Understands the domain but not implementation details

#### Workflow Highlights

**Initial Prompt**:
```
Create a notification system that alerts users about important events.
Users can configure preferences. High-priority alerts bypass quiet hours.
```

**System Generates IR with 7 Holes**:
```yaml
Holes Detected:
1. ?notification_channel (term): Email, SMS, Push, Slack?
2. ?priority_levels (type): How many levels? What are they?
3. ?quiet_hours_definition (spec): User-defined or global?
4. ?preference_granularity (spec): Per-event-type? Per-channel?
5. ?delivery_guarantee (spec): At-least-once? Exactly-once?
6. ?retry_strategy (function): How to handle failures?
7. ?event_types (entity): What events trigger notifications?
```

**Interactive Resolution**:

Alex resolves holes one by one:

1. **?notification_channel**: Accepts suggestion "Multi-channel: SMS+Email for high, Email for normal, In-app for low"
2. **?priority_levels**: Custom input "3 levels: HIGH, NORMAL, LOW"
3. **?event_types**: Selects from catalog:
   - [x] OrderPlaced (NORMAL)
   - [x] PaymentFailed (HIGH)
   - [x] ShipmentDelivered (LOW)
   - [ ] InventoryLow (defers - leaves as hole)

**Constraint Propagation**:

After resolving #1 (channels), system automatically updates:
- `?delivery_guarantee` narrows to "Best-effort for SMS, at-least-once for Email/In-app"
- `?retry_strategy` updates suggestion to "SMS: 3 retries, Email: 5 retries, In-app: unlimited (lazy)"

**Partial Evaluation Preview**:

Alex clicks "Preview" to see behavior with remaining holes:

```python
# Scenario: PaymentFailed event for user Alice
priority = HIGH  # ✅ from event mapping
quiet_hours = FALSE  # ✅ high priority bypasses
channels = [SMS, Email]  # ✅ from multi-channel config
retry_strategy = ?retry_strategy  # ⏸️ Still a hole

# Trace shows: Function would retry SMS 3 times with exponential backoff
# AI updates suggestion confidence: 95% → "Exponential backoff: 1s, 2s, 4s, max 3 attempts"
```

**Final Output**: Code with placeholder comment for deferred hole:

```python
async def notify(user_id: UUID, event: Event, priority: Priority):
    # ... implementation for resolved parts ...

    # TODO: Handle InventoryLow event (hole: ?inventory_event_handling)
    # Suggestion: Batch notifications daily, send to warehouse managers only
    pass
```

**Outcome**: Alex got working notification code for 3 event types in **10 minutes** through interactive dialogue. One hole deferred for future work. Partial evaluation helped AI improve suggestions based on actual behavior traces.

---

## 3. Functional Requirements

### FR1: Natural Language Input Processing

**FR1.1 Prompt Acceptance**
- **Description**: Accept user prompts in natural language (English)
- **Input**: Plain text, 1-1000 words
- **Validation**: Check length, sanitize for injection attacks
- **Storage**: Store original prompt with session metadata

**FR1.2 Domain Context Support**
- **Description**: Accept optional context (existing code, related specs)
- **Input**: Additional text up to 10,000 words
- **Use Case**: "Create similar function to existing_func()"
- **Processing**: Concatenate with main prompt, mark as context in IR provenance

**FR1.3 Multi-Language Prompt Support** (Future)
- **Description**: Support prompts in languages beyond English
- **Target**: Spanish, French, German, Chinese, Japanese
- **Timeline**: Q2 2026

---

### FR2: Intent Extraction (Stage 1)

**FR2.1 IntentClause Generation**
- **Description**: Extract high-level intent from prompt
- **Output Fields**:
  - `summary`: 1-2 sentence description
  - `user_personas`: List of intended users/consumers
  - `success_criteria`: Conditions defining success
  - `domain_concepts`: Key entities mentioned
  - `goals`: What should be achieved
  - `constraints`: Limitations and requirements
- **Latency Target**: <5s median
- **Success Criterion**: 85%+ human agreement on extracted intent

**FR2.2 Role Identification**
- **Description**: Identify stakeholder roles (users, system components)
- **Output**: List of roles with descriptions
- **Example**: "Sender: User initiating transfer"

**FR2.3 Goal Extraction**
- **Description**: Extract high-level goals from prompt
- **Output**: Ordered list of goals (priority implicit in order)
- **Validation**: Goals must be non-contradictory

**FR2.4 Constraint Discovery**
- **Description**: Identify explicit and implicit constraints
- **Types**: Input constraints, output constraints, invariants, performance
- **Example**: "Sender balance >= amount" (explicit), "Transfer is atomic" (implicit → transaction)

---

### FR3: Signature Generation (Stage 2)

**FR3.1 Function Naming**
- **Description**: Generate Python-compliant function names
- **Rules**: snake_case, descriptive, no reserved keywords
- **Validation**: Check against Python builtins, common library names
- **Example**: "transfer_money" not "Transfer" or "transfer$"

**FR3.2 Parameter Inference**
- **Description**: Infer function parameters from intent
- **Output**: List of `Param` objects with:
  - `name`: Parameter name
  - `type_hint`: Python type annotation
  - `default`: Optional default value
  - `description`: Human-readable description
- **Type Inference**: Use domain concepts + success criteria
- **Example**: "sender must have balance" → `sender_id: UUID` parameter

**FR3.3 Return Type Inference**
- **Description**: Determine return type from goals/success criteria
- **Types Supported**: Primitives (int, str, bool), collections (list, dict), custom types, Result/Option types
- **Preference**: Use `Result[T, E]` for error-prone operations
- **Example**: Transfer operation → `Result[Transfer, TransferError]`

**FR3.4 Typed Hole Creation**
- **Description**: Mark ambiguities as typed holes (6 kinds)
- **Hole Kinds**:
  - `term`: Unknown value/expression (`?value`)
  - `type`: Unknown type (`?T`)
  - `spec`: Unknown specification (`?contract`)
  - `entity`: Unknown domain object (`?User`)
  - `function`: Unknown helper function (`?helper`)
  - `module`: Unknown dependency (`?lib`)
- **Hole Metadata**: Type constraint, dependencies, provenance, suggestions
- **Example**: Optional parameter → hole with `Optional[str]` type constraint

**FR3.5 Signature Validation**
- **Description**: Ensure generated signature is well-formed
- **Checks**: Valid Python syntax, no duplicate parameter names, return type specified
- **Action on Failure**: Generate new signature or raise validation error

---

### FR4: Constraint Extraction (Stage 3)

**FR4.1 Precondition Generation**
- **Description**: Extract conditions that must hold before execution
- **Sources**: Intent constraints, domain rules, parameter validation
- **Format**: Predicates over function inputs
- **Example**: `sender.balance >= amount` from "sender must have sufficient balance"

**FR4.2 Postcondition Generation**
- **Description**: Extract conditions that must hold after execution
- **Sources**: Goals, success criteria, state changes
- **Format**: Predicates over inputs and outputs
- **Example**: `sender.balance' = sender.balance - amount` from "transfer amount from sender"

**FR4.3 Invariant Detection**
- **Description**: Identify conditions that must hold throughout execution
- **Sources**: Domain constraints, implicit requirements
- **Example**: "Balance never negative" → `balance >= 0` (invariant)

**FR4.4 Effect Classification**
- **Description**: Categorize side effects
- **Categories**:
  - `Database`: Read/write operations
  - `Network`: HTTP requests, API calls
  - `Filesystem`: File operations
  - `State`: Modifies mutable state
  - `IO`: Console input/output
- **Granularity**: Specify which resources affected
- **Example**: "Database: Write to accounts, transfers tables"

**FR4.5 Assertion Generation**
- **Description**: Convert constraints to executable assertions
- **Format**: Python `assert` statements with error messages
- **Placement**: Preconditions at function start, postconditions before return
- **Example**: `assert amount > 0, "Amount must be positive"`

---

### FR5: Constraint Verification (Stage 3.5)

**FR5.1 SMT Encoding**
- **Description**: Encode constraints as SMT-LIB 2.6 predicates
- **Supported Theories**: Int, Real, Bool, Arrays, ADTs, Strings (limited)
- **Solver**: Z3 (primary), CVC5 (fallback)
- **Timeout**: 5s budget per query

**FR5.2 Satisfiability Checking**
- **Description**: Verify constraint set has at least one solution
- **Output**: SAT, UNSAT, or UNKNOWN
- **Action on SAT**: Proceed to code generation
- **Action on UNSAT**: Show counterexample, request constraint relaxation
- **Action on UNKNOWN**: Show warning, proceed with caution

**FR5.3 Counterexample Generation**
- **Description**: If UNSAT, generate concrete example showing conflict
- **Format**: Variable assignments demonstrating contradiction
- **Presentation**: Human-readable explanation + SMT trace
- **Example**: "Cannot satisfy: x > 10 AND x < 5. Counterexample: No value of x satisfies both."

**FR5.4 Constraint Simplification**
- **Description**: Remove redundant or implied constraints
- **Goal**: Reduce SMT query complexity
- **Technique**: Logical subsumption, implication chains
- **Example**: `x > 5 AND x > 3` → `x > 5` (3 implied)

---

### FR6: Hole Resolution (Stage 4)

**FR6.1 Hole Detection**
- **Description**: Identify all holes in generated IR
- **Search**: Traverse IR tree, find all `TypedHole` instances
- **Prioritization**: Dependency order (resolve dependencies first)
- **Output**: Ordered list of holes for user resolution

**FR6.2 AI Suggestion Generation**
- **Description**: Generate ranked suggestions for filling holes
- **Algorithm**:
  1. Collect in-scope candidates (variables, functions, types)
  2. Filter by type compatibility
  3. Check SMT entailment (does suggestion satisfy constraints?)
  4. Rank by similarity + usage priors + solver score
- **Output**: List of `Suggestion` objects with:
  - `value`: Proposed fill
  - `confidence`: 0.0-1.0 score
  - `rationale`: Why this suggestion
  - `constraints_satisfied`: Boolean
- **Target**: Top suggestion correct 60%+ of the time

**FR6.3 User Interaction**
- **Description**: Present holes to user for resolution
- **UI Elements**:
  - Hole list (sidebar)
  - Hole details (type, constraints, suggestions)
  - Accept/reject/custom actions
  - Split hole (break into sub-holes)
  - Defer hole (leave for later)
- **Keyboard Shortcuts**: Next hole (Tab), accept (Enter), custom (E)

**FR6.4 Constraint Propagation**
- **Description**: Update dependent holes when one is filled
- **Mechanism**:
  1. Detect dependencies via `links` field
  2. Recompute constraints for dependent holes
  3. Regenerate suggestions for affected holes
  4. Notify user of updates
- **Example**: Filling `?return_type` narrows `?parameter_types`

**FR6.5 Partial Evaluation**
- **Description**: Execute program with holes to show value flows
- **Technique**: Hazel-inspired hole closures (evaluate around holes)
- **Output**: Hole traces showing concrete values that flow through
- **Use Case**: "What would this function return if ?value = 42?"
- **Action**: Improve suggestions based on trace data

**FR6.6 Fill-and-Resume**
- **Description**: Apply hole fill without restarting entire pipeline
- **Optimization**: Only recompute affected IR nodes
- **Benefit**: Fast iteration (< 1s per hole resolution)

---

### FR7: Code Generation (Stage 5)

**FR7.1 XGrammar-Constrained Generation**
- **Description**: Generate syntactically valid code using XGrammar
- **Schema Source**: Derive JSON schema from IR specification
- **Constraints Enforced**:
  - Function name matches signature
  - Parameter names/types match
  - All assertions included
  - Return type matches
- **Decoder**: vLLM with XGrammar integration
- **Model**: Qwen2.5-Coder-7B (current), upgradeable to larger models

**FR7.2 Best-of-N Sampling**
- **Description**: Generate N candidates, select best
- **N Value**: 3 (default), configurable 1-10
- **Ranking Criteria**:
  - Compilation success (must compile)
  - Type check success (mypy)
  - Assertion coverage (all assertions present)
  - Code quality score (readability, complexity)
  - Execution test success (if tests available)
- **Selection**: Highest-scoring candidate
- **Fallback**: If all fail, retry with temperature adjustment

**FR7.3 Multi-Language Support**
- **Languages**: Python (primary), TypeScript (secondary)
- **Future**: Go, Rust, Java, C# (roadmap)
- **Language Selection**:
  - Auto-detect from domain context
  - User-specified in prompt or settings
  - Default to Python
- **Language-Specific Features**:
  - Python: Type hints, docstrings, assertions
  - TypeScript: Interfaces, generics, JSDoc

**FR7.4 Code Validation**
- **Stages**:
  1. **Syntax Check**: `compile(code, '<string>', 'exec')`
  2. **AST Parse**: `ast.parse(code)`
  3. **Type Check**: Run mypy (Python) or tsc (TypeScript)
  4. **Import Check**: Verify all imports available
  5. **Assertion Check**: Ensure all expected assertions present
- **Pass Criteria**: All stages pass
- **Action on Failure**: Attempt deterministic repair, then retry generation

**FR7.5 Deterministic AST Repair**
- **Description**: Fix common syntactic errors automatically
- **Repairs**:
  - Indentation errors → Fix with consistent 4-space indent
  - Missing imports → Add standard library imports
  - Trailing commas → Remove in single-line contexts
  - Parenthesis matching → Balance unmatched parens
- **Limit**: 3 repair attempts per candidate
- **Success Rate**: 60%+ of repairable errors fixed

**FR7.6 Execution Testing** (Optional)
- **Description**: Run generated code against test cases
- **Test Sources**:
  - Examples from IntentSpec
  - Edge cases from constraints
  - Auto-generated property tests
- **Isolation**: Sandboxed execution environment (Modal)
- **Timeout**: 5s per test
- **Failure Handling**: Include test results in validation report

---

### FR8: Provenance Tracking

**FR8.1 Provenance Chain Creation**
- **Description**: Record origin of every IR element
- **Provenance Fields**:
  - `source`: "user_prompt", "dspy_signature", "smt_solver", "inference", "user_input"
  - `timestamp`: When created
  - `actor`: User ID or system component
  - `justification`: Why this element exists
  - `confidence`: 0.0-1.0 score
- **Linkage**: Parent-child relationships between elements

**FR8.2 Alignment Map**
- **Description**: Map IntentSpec atoms → FuncSpec predicates
- **Format**: Bipartite graph with edges weighted by confidence
- **Use Case**: "Which code implements which goal?"
- **Drift Detection**: Flag when code diverges from intent

**FR8.3 Audit Trail Export**
- **Description**: Export complete provenance for compliance
- **Formats**: PDF, CSV, JSON
- **Contents**: All decisions, actors, timestamps, justifications
- **Use Case**: Regulatory audit, team review

---

### FR9: Session Management

**FR9.1 Session Creation**
- **Trigger**: User starts new forward mode flow
- **Initialization**: Create session with unique ID, store initial prompt
- **State**: Tracks IR, holes, resolutions, code, validation results

**FR9.2 Session Persistence**
- **Storage**: Supabase PostgreSQL
- **Schema**: `sessions`, `session_revisions`, `typed_holes`, `hole_resolutions`
- **RLS**: Row-Level Security for multi-user isolation
- **Durability**: Auto-save after each stage

**FR9.3 Session Resume**
- **Description**: Load and continue session from any stage
- **Use Case**: User leaves, returns later, picks up where left off
- **Constraint**: Cannot resume after finalization

**FR9.4 Revision Tracking**
- **Description**: Store all IR versions as session evolves
- **Granularity**: One revision per stage completion
- **Diff**: Show what changed between revisions
- **Undo**: Roll back to previous revision

**FR9.5 Session Export/Import**
- **Export**: Save session as JSON file
- **Import**: Load session from JSON
- **Use Case**: Share sessions, backup locally, version control

---

### FR10: Multi-Interface Support

**FR10.1 Web UI**
- **Framework**: React + Next.js + shadcn/ui
- **Features**: Visual IR editor, hole resolution wizard, split-view (IR ↔ Code)
- **Real-Time**: WebSocket updates for generation progress

**FR10.2 CLI**
- **Commands**: `lift generate`, `lift resolve`, `lift finalize`
- **Output**: JSON or formatted text
- **Scripting**: Pipe-friendly for automation

**FR10.3 TUI**
- **Framework**: Bubble Tea (Go) or Textual (Python)
- **Features**: Full-featured, keyboard-driven, works over SSH
- **Target Users**: Developers who live in terminal

**FR10.4 Python SDK**
- **Module**: `lift_sys.client.SessionClient`
- **Methods**: `create_session()`, `resolve_hole()`, `finalize_session()`
- **Type Safety**: Full type hints, Pydantic models

**FR10.5 REST API**
- **Endpoints**: `/api/generate`, `/api/sessions`, `/api/holes`, `/api/finalize`
- **Auth**: OAuth 2.0 + encrypted tokens
- **Rate Limiting**: Per-user quotas

---

### FR11: Error Handling & Recovery

**FR11.1 Stage Failure Recovery**
- **Description**: Handle failures at each pipeline stage gracefully
- **Strategies**:
  - **Intent Extraction Failure**: Request more specific prompt
  - **Signature Generation Failure**: Manual signature input fallback
  - **Constraint Verification Failure**: Show counterexample, relax constraints
  - **Code Generation Failure**: Retry with different parameters
- **User Feedback**: Clear error messages with actionable suggestions

**FR11.2 Retry Logic**
- **Triggers**: Compilation failure, type error, validation failure
- **Max Retries**: 5 attempts per stage
- **Strategy**:
  1. Retry with same parameters (transient errors)
  2. Retry with lower temperature (reduce randomness)
  3. Retry with feedback (include error in prompt)
  4. Retry with different model (if available)
  5. Give up, request user intervention
- **Success Rate**: 90%+ resolved within 5 retries

**FR11.3 Feedback Generation**
- **Description**: Convert validation errors to actionable feedback
- **Examples**:
  - Compilation error → "Syntax error on line 5: Missing colon after if statement"
  - Type error → "Expected int, got str for parameter amount"
  - Assertion missing → "Missing precondition assertion: sender.balance >= amount"
- **Incorporation**: Include feedback in retry prompt

**FR11.4 Graceful Degradation**
- **Description**: Provide partial results if full pipeline fails
- **Fallback Levels**:
  1. Complete IR + verified code ✅ (goal)
  2. Complete IR + unverified code ⚠️
  3. Partial IR with holes + no code ⏸️
  4. Intent extraction only + no IR ❌
- **User Choice**: Accept partial or retry

---

### FR12: Quality Assurance

**FR12.1 Code Quality Scoring**
- **Metrics**:
  - Readability: Cyclomatic complexity, line length, naming
  - Correctness: Assertion coverage, type completeness
  - Performance: Algorithmic complexity (if detectable)
  - Safety: No obvious security anti-patterns
- **Scoring**: 0-100 scale
- **Use Case**: Rank Best-of-N candidates

**FR12.2 Assertion Coverage**
- **Description**: Ensure all FuncSpec constraints present as assertions
- **Check**: Compare generated assertions to FuncSpec predicates
- **Minimum**: All preconditions and postconditions covered
- **Scoring**: Percentage of constraints with assertions

**FR12.3 Execution Validation**
- **Description**: Run generated code against test cases
- **Test Generation**: Auto-generate from examples + constraints
- **Isolation**: Sandboxed environment (Modal)
- **Reporting**: Pass/fail status, execution traces, coverage

---

## 4. Non-Functional Requirements

### NFR1: Performance

**NFR1.1 End-to-End Latency**
- **Current**: 16s median (10.8s IR gen + 4.3s code gen + 1s validation)
- **Target Q2 2025**: <15s median (90th percentile <25s)
- **Target Q4 2025**: <12s median (90th percentile <20s)
- **Measurement**: Histogram of E2E latencies, broken down by stage

**NFR1.2 Stage Latency Budgets**
| Stage | Current | Q2 2025 Target | Q4 2025 Target |
|-------|---------|----------------|----------------|
| Intent Extraction | ~3s | <3s | <2s |
| Signature Generation | ~2s | <2s | <1.5s |
| Constraint Extraction | ~3s | <3s | <2s |
| Hole Resolution | 0-300s (user-dependent) | N/A | N/A |
| Code Generation | ~4s | <4s | <3s |
| Validation | ~1s | <1s | <0.5s |
| **Total (excluding holes)** | ~16s | <15s | <12s |

**NFR1.3 Throughput**
- **Current**: 100 requests/hour (single L40S GPU)
- **Target Q2 2025**: 500 requests/hour (horizontal scaling)
- **Target Q4 2025**: 2000 requests/hour (optimized batching)

**NFR1.4 Suggestion Generation Latency**
- **Target**: <2s for 90% of hole suggestions
- **Measured**: Time from hole selection to suggestions displayed
- **Critical**: Must feel interactive, not sluggish

---

### NFR2: Success Rates & Quality

**NFR2.1 Compilation Success Rate**
- **Current**: 80%
- **Target Q2 2025**: 90%
- **Target Q4 2025**: 95%
- **Measurement**: % of generated code that compiles without errors

**NFR2.2 Execution Success Rate**
- **Current**: 60% (all) | 75% (compiled code)
- **Target Q2 2025**: 75% (all) | 85% (compiled)
- **Target Q4 2025**: 85% (all) | 95% (compiled)
- **Measurement**: % of compiled code that passes all test cases

**NFR2.3 Semantic Correctness**
- **Current**: 60% real execution success
- **Target Q2 2025**: 75%
- **Target Q4 2025**: 85%
- **Measurement**: Human evaluation of "does code match intent?"

**NFR2.4 Hole Suggestion Acceptance**
- **Target**: 60%+ of suggestions accepted without modification
- **Measurement**: Track user actions (accept/reject/modify)
- **Goal**: AI suggestions save time, not waste time

---

### NFR3: Cost

**NFR3.1 Cost Per Request**
- **Current**: $0.0029 (Modal L40S GPU)
- **Target Q2 2025**: <$0.005 (even with larger models)
- **Target Q4 2025**: <$0.003 (optimization + scale)
- **Breakdown**:
  - GPU inference: ~60% of cost
  - Database operations: ~20%
  - LLM API calls (if hybrid): ~20%

**NFR3.2 Cost Optimization Strategies**
- **Caching**: Cache IR fragments, solver results, common patterns
- **Batching**: Combine multiple requests when possible
- **Model Selection**: Use smaller models for simpler tasks
- **Tiered Solvers**: CSP (cheap) → SAT (medium) → SMT (expensive)

---

### NFR4: Scalability

**NFR4.1 Concurrent Users**
- **Target Q2 2025**: 100 concurrent sessions
- **Target Q4 2025**: 1000 concurrent sessions
- **Measurement**: Peak concurrent connections, no degradation

**NFR4.2 Session Storage**
- **Capacity**: 1M sessions (cumulative)
- **Retrieval**: <100ms query time for any session
- **Retention**: 90 days (free tier), unlimited (paid)

**NFR4.3 Horizontal Scaling**
- **API Servers**: Stateless, scale via replicas
- **GPU Workers**: Scale via Modal autoscaling (up to 100 GPUs)
- **Database**: Supabase scales transparently

---

### NFR5: Reliability & Availability

**NFR5.1 Uptime**
- **Target**: 99.9% uptime (< 9 hours downtime/year)
- **Monitoring**: Honeycomb, uptime checks every 60s
- **Alerting**: Page on-call if <99.5% in 24h window

**NFR5.2 Data Durability**
- **Sessions**: 99.999% durability (Supabase backups)
- **Backups**: Daily snapshots, 30-day retention
- **Zero Data Loss**: Replicated across multiple zones

**NFR5.3 Fault Tolerance**
- **GPU Failures**: Automatic retry on different GPU
- **API Failures**: Graceful degradation, return partial results
- **Database Failures**: Read replicas, failover <30s

---

### NFR6: Security & Privacy

**NFR6.1 Authentication**
- **Methods**: OAuth 2.0 (Google, GitHub, email)
- **Tokens**: Encrypted at rest, rotated every 30 days
- **Sessions**: Tied to authenticated user, RLS enforced

**NFR6.2 Authorization**
- **Model**: User owns sessions, can share read-only
- **Enforcement**: Supabase Row-Level Security policies
- **Admin**: Special role for support/debugging

**NFR6.3 Data Encryption**
- **In Transit**: TLS 1.3 for all API calls
- **At Rest**: Supabase encrypts database, Modal encrypts secrets
- **Secrets**: Never log API keys, tokens, or user code

**NFR6.4 Compliance**
- **GDPR**: User data deletion on request
- **SOC 2**: In progress (Q3 2025)
- **Audit Trail**: Full provenance for regulatory compliance

---

### NFR7: Observability

**NFR7.1 Logging**
- **Structured Logs**: JSON format, searchable fields
- **Levels**: DEBUG (development), INFO (production), ERROR (always)
- **Retention**: 30 days (Honeycomb)

**NFR7.2 Metrics**
- **System**: CPU, memory, GPU utilization, request rate
- **Business**: Success rates, latency percentiles, user engagement
- **Dashboards**: Real-time views in Honeycomb

**NFR7.3 Tracing**
- **Distributed**: OpenTelemetry traces across all services
- **Sampling**: 100% of errors, 10% of success (adjustable)
- **Visualization**: Flamegraphs, dependency graphs

**NFR7.4 Alerting**
- **Triggers**: Success rate drops >10%, latency >25s (P95), uptime <99.5%
- **Channels**: Email, Slack, PagerDuty (on-call)
- **Runbooks**: Documented procedures for each alert

---

## 5. Success Metrics

### Current Baseline (Q1 2025)

| Metric | Current | Q2 2025 Target | Q4 2025 Target |
|--------|---------|----------------|----------------|
| **Compilation Success** | 80% | 90% | 95% |
| **Execution Success** | 60% | 75% | 85% |
| **Median Latency** | 16s | <15s | <12s |
| **Cost Per Request** | $0.0029 | <$0.005 | <$0.003 |
| **Suggestion Acceptance** | N/A | 60% | 75% |
| **Intent Fidelity** | 70% | 85% | 90% |
| **User Satisfaction (NPS)** | N/A | >40 | >50 |

### Product Metrics

**PM1: Adoption**
- **Active Sessions/Day**: 50 (Q2) → 500 (Q4) → 5000 (Year 2)
- **Session Completion Rate**: >70% (user finalizes and exports code)
- **Repeat Usage**: 60%+ of users create 2+ sessions

**PM2: Engagement**
- **Time to First Code**: <5 minutes for 80% of users
- **Holes Resolved Per Session**: Average 3-5 (sweet spot)
- **User Satisfaction**: 8/10+ on "forward mode helped me create code"

**PM3: Quality**
- **Code Used in Production**: 40%+ of finalized sessions (self-reported)
- **Bug Reports**: <5% of finalized code has bugs found by user
- **Engineering Review Pass Rate**: 90%+ of code passes review without major changes

### Technical Metrics

**TM1: Pipeline Performance**
- **Stage Completion Rate**:
  - Intent Extraction: >95%
  - Signature Generation: >90%
  - Constraint Extraction: >85%
  - Code Generation: >80% (current) → >90% (target)
- **Retry Effectiveness**: 70%+ of retries succeed

**TM2: Constraint Verification**
- **Satisfiability Rate**: 80%+ of generated FuncSpecs are SAT
- **Solver Timeouts**: <10% of queries timeout (5s budget)
- **Counterexample Utility**: 90%+ of counterexamples lead to successful constraint refinement

**TM3: Hole Resolution**
- **Suggestion Quality**: Top-3 suggestions contain correct answer 85%+ of time
- **Suggestion Latency**: <2s for 90% of suggestions
- **Constraint Propagation Accuracy**: 95%+ of propagated constraints are correct

**TM4: Code Quality**
- **Type Coverage**: 90%+ of generated code has complete type hints
- **Assertion Coverage**: 85%+ of FuncSpec constraints have assertions
- **Readability Score**: Median Cyclomatic Complexity <5

### Business Metrics

**BM1: Value Delivery**
- **Time Saved**: 70% reduction vs. manual coding (self-reported)
- **Time to Value**: 50% of users get working code <10 minutes
- **Productivity Gain**: Users create 3x more features with lift vs. without

**BM2: User Satisfaction**
- **NPS**: >40 (Q2 2025), >50 (Q4 2025)
- **CSAT**: 8/10+ on "forward mode met my needs"
- **Feature Requests**: <10% of users request missing features (suggests completeness)

---

## 6. Technical Architecture

### Pipeline Overview

```
[User Input: Natural Language Prompt]
         ↓
┌─────────────────────────────────────────┐
│  Stage 1: Intent Extraction (DSPy)     │
│  - NLToIntent signature                 │
│  - Extract goals, roles, constraints    │
│  - Generate IntentClause                │
│  Latency: ~3s | Success: 95%            │
└─────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│  Stage 2: Signature Generation (DSPy)  │
│  - IntentToSignature signature          │
│  - Infer function name, params, return  │
│  - Create typed holes for ambiguities   │
│  - Generate SigClause                   │
│  Latency: ~2s | Success: 90%            │
└─────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│  Stage 3: Constraint Extraction (DSPy)  │
│  - ConstraintExtraction signature       │
│  - Generate pre/post conditions         │
│  - Classify effects                     │
│  - Generate FuncSpec                    │
│  Latency: ~3s | Success: 85%            │
└─────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│  Stage 3.5: Constraint Verification     │
│  - Encode FuncSpec to SMT-LIB           │
│  - Run Z3 solver (5s timeout)           │
│  - Generate counterexamples if UNSAT    │
│  Latency: <5s | SAT Rate: 80%           │
└─────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│  Stage 4: Hole Resolution (Interactive) │
│  - Detect all typed holes               │
│  - Generate AI suggestions per hole     │
│  - User resolves (accept/custom/defer)  │
│  - Constraint propagation               │
│  - Partial evaluation (optional)        │
│  Latency: 0-300s (user-dependent)       │
└─────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│  Stage 5: Code Generation (Modal)       │
│  - XGrammar-constrained vLLM            │
│  - JSON schema from IR                  │
│  - Best-of-N sampling (N=3)             │
│  - Generate Python/TypeScript code      │
│  Latency: ~4s | Compilation: 80%        │
└─────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│  Stage 6: Validation                    │
│  - Syntax check (compile)               │
│  - AST parse                            │
│  - Type check (mypy/tsc)                │
│  - Deterministic repair (if needed)     │
│  - Execution tests (optional)           │
│  Latency: ~1s | Execution: 60%          │
└─────────────────────────────────────────┘
         ↓
[Output: Verified Code + IR + Provenance]
```

### Key Components

**DSPy Signatures** (Systematic AI):
- Declarative specifications of LLM tasks
- Optimizable via MIPROv2 (automatic prompt engineering)
- Composable modules with type-safe inputs/outputs

**XGrammar Constrainer**:
- Guarantees syntactic correctness during decoding
- JSON schema derived from IR specification
- Near-zero overhead (99%+ token cache hit rate)

**Z3 SMT Solver**:
- Verifies constraint satisfiability
- Generates counterexamples for UNSAT constraints
- 5s timeout budget per query

**Typed Hole System**:
- 6 kinds: term, type, spec, entity, function, module
- Constraint propagation via dependency graph
- AI-assisted resolution with valid-fit suggestions

**Best-of-N Sampler**:
- Generates N candidates (default N=3)
- Ranks by compilation, type check, assertion coverage, quality
- Selects highest-scoring candidate

**Session Store** (Supabase):
- PostgreSQL with Row-Level Security
- Stores IR, holes, resolutions, revisions
- Real-time sync via WebSockets

**Dual-Provider Routing** (ADR 001):
- **Best Available Route**: Anthropic/OpenAI/Google for planning
- **Modal Inference Route**: vLLM + XGrammar for constrained generation
- Routing logic based on task requirements

### Data Flow

**1. User Prompt → Intent Extraction**:
```
POST /api/sessions {prompt: "..."}
  → DSPy NLToIntent signature
  → IntentClause stored in session
  → Response: {session_id, intent}
```

**2. Intent → Signature Generation**:
```
POST /api/sessions/{id}/signature
  → DSPy IntentToSignature signature
  → SigClause with typed holes
  → Response: {signature, holes: [...]}
```

**3. Signature → Constraint Extraction**:
```
POST /api/sessions/{id}/constraints
  → DSPy ConstraintExtraction signature
  → FuncSpec (pre/post/invariants/effects)
  → SMT encoding and verification
  → Response: {funcspec, satisfiable: true|false, counterexample?}
```

**4. Holes → Resolution**:
```
GET /api/sessions/{id}/holes
  → List of typed holes with suggestions
  → User resolves via PUT /api/holes/{hole_id}
  → Constraint propagation updates dependent holes
  → Repeat until all holes resolved or deferred
```

**5. Complete IR → Code Generation**:
```
POST /api/sessions/{id}/generate
  → Modal vLLM endpoint with XGrammar
  → Best-of-3 sampling
  → Validation (compile, type, AST)
  → Response: {code, validation: {...}, provenance: {...}}
```

---

## 7. User Experience Design

### UI Principles

**1. Progressive Disclosure**
- Start simple (just a prompt box)
- Reveal complexity as needed (holes appear when detected)
- Advanced options hidden by default

**2. Real-Time Feedback**
- Show progress bars during generation
- Live preview of IR as it builds
- Immediate validation results

**3. Clear Affordances**
- Holes visually distinct (yellow underline)
- Suggestions ranked and labeled
- Actions have obvious buttons (Accept, Custom, Defer)

**4. Explainability**
- Every suggestion has rationale
- Hovering shows constraints and dependencies
- Provenance traces available on demand

### Key UI Components

**Prompt Workbench**:
- Large text area for prompt input
- Optional context section (collapsible)
- Domain/language selectors
- "Generate" button (primary action)

**Intent Review Panel**:
- Editable IntentClause fields
- Inline editing for corrections
- "Approve" / "Revise" actions

**Signature View**:
- Syntax-highlighted function signature
- Holes shown with `?identifier` notation
- Parameter descriptions in tooltips

**Hole Resolution Wizard**:
- **Sidebar**: List of all holes (ordered by dependency)
- **Main Panel**: Current hole details
  - Type constraint
  - Dependencies (links to other holes)
  - AI suggestions (ranked)
  - Custom input field
- **Actions**: Accept, Custom, Split, Defer, Skip
- **Progress**: "3 of 7 holes resolved"

**IR/Code Split View**:
- **Left**: IR specification (IntentSpec + FuncSpec)
- **Right**: Generated code with syntax highlighting
- **Sync Scrolling**: Click IR element → highlight corresponding code
- **Tabs**: Switch between IR, Code, Provenance, Tests

**Validation Report**:
- ✅ Compilation status
- ✅ Type check status
- ✅ Assertion coverage
- ⚠️ Warnings (if any)
- 📊 Test results (if executed)

### Accessibility

**Keyboard Navigation**:
- Tab: Next hole
- Shift+Tab: Previous hole
- Enter: Accept suggestion
- E: Edit (custom input)
- D: Defer hole
- S: Split hole
- Ctrl+Z: Undo last action

**Screen Reader Support**:
- ARIA labels on all interactive elements
- Live regions for dynamic content
- Focus management (modal dialogs trap focus)

**Color Contrast**:
- WCAG 2.1 AA compliance (4.5:1 text, 3:1 UI)
- High contrast mode available
- Color not sole indicator (icons + labels)

---

## 8. Dependencies & Integration

### Internal Dependencies

**Reverse Mode Integration**:
- Forward mode uses reverse mode for example extraction
- Reverse mode provides context for similar functions
- Bi-directional workflow: Code → IR → Edit IR → Code

**Typed Holes System**:
- Forward mode generates holes
- Interactive refinement resolves holes
- Constraint propagation updates holes
- See [PRD_TYPED_HOLES.md](PRD_TYPED_HOLES.md)

**Session Management**:
- All forward mode state persisted to sessions
- Revision tracking for undo/redo
- Multi-user collaboration (future)
- See [API_SESSION_MANAGEMENT.md](docs/API_SESSION_MANAGEMENT.md)

**Validation Pipeline**:
- Shared between forward and reverse modes
- AST parsing, type checking, execution testing
- Deterministic repair for common errors

### External Dependencies

**LLM Providers** (ADR 001: Dual-Provider Routing):
- **Best Available Route**:
  - Anthropic Claude (planning, reasoning)
  - OpenAI GPT-4 (fallback)
  - Google Gemini (fallback)
- **Modal Inference Route**:
  - vLLM (inference engine)
  - XGrammar (constrained decoding)
  - Qwen2.5-Coder-7B (model)
- **Routing**: Task-dependent selection, automatic failover

**Modal.com**:
- Serverless GPU infrastructure (L40S)
- Container-based deployment
- Shared volumes for model weights
- Auto-scaling (up to 100 GPUs)

**Supabase**:
- PostgreSQL database (sessions, revisions, holes)
- Authentication (OAuth 2.0)
- Row-Level Security (multi-user isolation)
- Realtime (WebSocket subscriptions)

**Z3 SMT Solver**:
- Constraint verification
- Counterexample generation
- Bundled with lift-sys (no external dependency)

**Honeycomb** (Planned):
- Observability (traces, metrics, logs)
- OpenTelemetry integration
- Dashboards and alerts

### Integration Points

**GitHub**:
- Export finalized code as PR
- IntentSpec → PR description
- Provenance → PR comments

**IDEs** (Future):
- VS Code extension
- Inline prompt → IR → code
- Hover hints from provenance

**CI/CD** (Future):
- Validate generated code in CI
- Block PR if verification fails
- Automated testing of IR-derived code

---

## Appendix A: Example Scenarios

### Scenario 1: Password Validation Function

**Prompt**:
```
Create a function to validate password strength.
Must be at least 8 characters, contain uppercase, lowercase, number, and special character.
```

**Generated IR** (excerpt):
```yaml
Intent:
  Summary: "Validate password meets complexity requirements"
  Goals: ["Accept strong passwords", "Reject weak passwords"]
  Constraints: ["Length >= 8", "Has uppercase", "Has lowercase", "Has digit", "Has special char"]

Signature:
  name: validate_password_strength
  parameters: [{name: password, type: str}]
  returns: tuple[bool, Optional[str]]

FuncSpec:
  preconditions: ["isinstance(password, str)"]
  postconditions: [
    "result[0] == True -> len(password) >= 8",
    "result[0] == True -> has_uppercase(password)",
    "result[0] == True -> has_lowercase(password)",
    "result[0] == True -> has_digit(password)",
    "result[0] == True -> has_special(password)"
  ]
```

**Generated Code**:
```python
import re
from typing import Optional

def validate_password_strength(password: str) -> tuple[bool, Optional[str]]:
    """Validate password meets complexity requirements."""
    assert isinstance(password, str), "Password must be string"

    if len(password) < 8:
        return (False, "Password must be at least 8 characters")

    if not re.search(r'[A-Z]', password):
        return (False, "Password must contain uppercase letter")

    if not re.search(r'[a-z]', password):
        return (False, "Password must contain lowercase letter")

    if not re.search(r'\d', password):
        return (False, "Password must contain digit")

    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return (False, "Password must contain special character")

    return (True, None)
```

**Validation**: ✅ All checks pass, 100% execution success

---

### Scenario 2: Data Aggregation with Ambiguities

**Prompt**:
```
Aggregate user activity data by time period.
Calculate metrics like total events, unique users, average duration.
```

**Holes Generated**:
- `?time_period`: Hour, day, week, month?
- `?event_types`: What events to include?
- `?duration_unit`: Seconds, minutes, hours?
- `?aggregation_method`: Rolling window or fixed buckets?

**User Resolution**:
- Selects: Day (fixed buckets), All event types, Minutes
- AI suggests SQL query structure
- User accepts with minor modifications

**Outcome**: Working SQL query + Python wrapper function

---

## Appendix B: Performance Benchmarks

**Environment**: Modal L40S GPU, Qwen2.5-Coder-7B, vLLM + XGrammar

**Test Set**: 18 diverse prompts (Phase 2 + Phase 3 tests)

**Results** (as of Q1 2025):

| Stage | Median Latency | P95 Latency | Success Rate |
|-------|----------------|-------------|--------------|
| Intent Extraction | 2.8s | 4.1s | 95% |
| Signature Generation | 2.1s | 3.5s | 90% |
| Constraint Extraction | 2.9s | 4.8s | 87% |
| SMT Verification | 0.8s | 3.2s | 82% SAT |
| Code Generation | 4.3s | 6.7s | 80% compile |
| Validation | 0.9s | 1.4s | 75% execute |
| **End-to-End** | **16.2s** | **24.8s** | **60% E2E** |

**Breakdown of Failures**:
- 20% compilation failures (syntax errors)
- 13% type check failures (wrong types)
- 7% missing assertions (validation error)
- 20% semantic bugs (wrong logic, e.g. type computing)

**Cost Analysis**:
- GPU: $0.0018 per request (4.3s @ L40S pricing)
- Database: $0.0008 per request (Supabase operations)
- LLM APIs: $0.0003 per request (if using hybrid routing)
- **Total**: $0.0029 per request

---

## Appendix C: Roadmap Alignment

**Q1 2025 (COMPLETE ✅)**:
- Production-ready forward mode
- 80% compilation, 60% execution success
- Multi-provider support
- XGrammar-constrained generation
- Basic typed holes

**Q2 2025 (IN PROGRESS)**:
- IR 0.9 types & solvers (dependent types, refinements, Z3)
- DSPy migration (systematic AI optimization)
- Improved hole suggestions (constraint propagation)
- Target: 90% compilation, 75% execution

**Q3 2025**:
- Hole closures & partial evaluation (Hazel-inspired)
- Interactive refinement with live previews
- Advanced typed holes (6 kinds fully supported)
- Target: 95% compilation, 85% execution

**Q4 2025**:
- Surface syntax (Spec-IR) for human-friendly specs
- LSP server (hover, completion)
- VS Code extension
- Multi-language expansion (Go, Rust)

**2026**:
- Reverse mode AI enhancements
- Real-time collaboration
- Marketplace for templates
- Enterprise compliance features (SBOM, SLSA, OPA)

---

**Document Status**: Active
**Last Updated**: 2025-10-21
**Next Review**: Monthly or with major milestone changes
**Maintained By**: Product & Engineering Team
**Version History**:
- v1.0 (2025-10-21) - Initial comprehensive forward mode PRD
