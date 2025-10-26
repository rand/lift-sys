# ICS Phase 2 Implementation Plan: Constraint Propagation & AI Chat

**Date**: 2025-10-26
**Status**: Planning
**Prerequisites**: Phase 1 complete, Backend NLP pipeline ready

---

## Overview

Phase 2 adds interactive constraint propagation visualization, solution space narrowing, and an AI chat assistant for refinement and analysis.

**Goals**:
1. Visualize constraint propagation when holes are resolved
2. Show solution space narrowing in real-time
3. Add AI chat assistant with semantic commands
4. Enhance backend with relationship/effects/assertions detection

---

## Architecture

### Component Structure

```
ICS View (existing)
├── SemanticEditor (existing)
├── TypedHolePanel (existing)
├── ConstraintPanel (existing)
└── NEW: AI Chat Panel
    ├── Chat interface
    ├── Command parser (/refine, /analyze)
    └── LLM integration (Claude via API)

Store Updates (Zustand)
├── resolveHole() - NEW: Trigger constraint propagation
├── propagateConstraints() - NEW: Calculate impact
├── narrowSolutionSpace() - NEW: Update hole solution spaces
└── addChatMessage() - NEW: Chat history

Visualization (NEW)
├── ConstraintPropagationView
│   ├── Animated constraint flow
│   ├── Affected holes highlight
│   └── Solution space reduction display
└── SolutionSpaceNarrowingView
    ├── Before/after comparison
    ├── Constraint satisfaction status
    └── Refinement suggestions
```

---

## Phase 2.1: Constraint Propagation Visualization

### User Story
"When I resolve a hole, I want to see which other holes are affected and how their solution spaces narrow."

### Implementation

**1. Store: Add Constraint Propagation Logic**

File: `frontend/src/stores/icsStore.ts`

```typescript
// Add to ICSStore interface
interface ICSStore {
  // ... existing fields
  constraintPropagationHistory: ConstraintPropagationEvent[];

  // New actions
  propagateConstraints: (resolvedHoleId: string) => void;
  narrowSolutionSpace: (holeId: string, constraints: Constraint[]) => void;
}

// Implement propagateConstraints
propagateConstraints: (resolvedHoleId) => {
  const hole = state.semanticAnalysis.typedHoles.find(h => h.id === resolvedHoleId);
  if (!hole) return;

  // Find affected holes (blocked by this hole)
  const affectedHoles = state.semanticAnalysis.typedHoles.filter(h =>
    hole.dependencies.blocks.includes(h.id)
  );

  // Calculate constraint propagation
  affectedHoles.forEach(affectedHole => {
    // Add constraints from resolved hole
    const newConstraints = hole.constraints.filter(c =>
      c.appliesTo.includes(affectedHole.id)
    );

    // Narrow solution space
    set(state => ({
      constraintPropagationHistory: [
        ...state.constraintPropagationHistory,
        {
          timestamp: Date.now(),
          sourceHole: resolvedHoleId,
          targetHole: affectedHole.id,
          addedConstraints: newConstraints,
          solutionSpaceReduction: calculateReduction(affectedHole, newConstraints),
        }
      ]
    }));

    // Update affected hole
    state.narrowSolutionSpace(affectedHole.id, newConstraints);
  });
}
```

**2. Component: ConstraintPropagationView**

File: `frontend/src/components/ics/ConstraintPropagationView.tsx`

```typescript
interface ConstraintPropagationViewProps {
  event: ConstraintPropagationEvent;
}

export function ConstraintPropagationView({ event }: Props) {
  return (
    <div className="constraint-propagation-animation">
      <div className="source-hole">
        {event.sourceHole} <CheckCircle className="resolved" />
      </div>

      <AnimatedArrow />

      <div className="target-hole">
        {event.targetHole}
        <Badge>{event.addedConstraints.length} constraints added</Badge>
      </div>

      <SolutionSpaceReduction reduction={event.solutionSpaceReduction} />
    </div>
  );
}
```

**3. Integration with TypedHolePanel**

When user clicks "Resolve" on a hole:
1. Mark hole as resolved
2. Trigger `propagateConstraints(holeId)`
3. Show propagation animation
4. Update affected holes in UI

### Acceptance Criteria
- [ ] Resolving a hole triggers constraint propagation
- [ ] Affected holes are visually highlighted
- [ ] Constraint additions are animated
- [ ] Solution space reduction is calculated and displayed
- [ ] History of propagation events is maintained

---

## Phase 2.2: Solution Space Narrowing Visualization

### User Story
"I want to see how my hole's solution space narrows as I add constraints or resolve dependencies."

### Implementation

**1. SolutionSpaceNarrowingView Component**

File: `frontend/src/components/ics/SolutionSpaceNarrowingView.tsx`

```typescript
interface SolutionSpaceNarrowingViewProps {
  hole: TypedHole;
  beforeConstraints: Constraint[];
  afterConstraints: Constraint[];
}

export function SolutionSpaceNarrowingView({ hole, beforeConstraints, afterConstraints }: Props) {
  const reductionPercentage = calculateReduction(beforeConstraints, afterConstraints);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Solution Space for {hole.identifier}</CardTitle>
      </CardHeader>
      <CardContent>
        {/* Before */}
        <div className="solution-space-before">
          <h4>Before</h4>
          <ConstraintList constraints={beforeConstraints} />
          <Badge>Possible solutions: {estimateSolutions(beforeConstraints)}</Badge>
        </div>

        {/* Arrow */}
        <ArrowRight className="transition-arrow" />

        {/* After */}
        <div className="solution-space-after">
          <h4>After</h4>
          <ConstraintList constraints={afterConstraints} />
          <Badge>Possible solutions: {estimateSolutions(afterConstraints)}</Badge>
        </div>

        {/* Reduction */}
        <Alert>
          <InfoIcon />
          <AlertDescription>
            Solution space reduced by {reductionPercentage}%
          </AlertDescription>
        </Alert>
      </CardContent>
    </Card>
  );
}
```

**2. Solution Space Estimation**

```typescript
function estimateSolutions(constraints: Constraint[]): number {
  // Heuristic estimation based on constraint types
  let baseSpace = 1000; // Initial solution space size

  constraints.forEach(constraint => {
    switch (constraint.type) {
      case 'temporal':
        baseSpace *= 0.7; // Reduces by 30%
        break;
      case 'conditional':
        baseSpace *= 0.5; // Reduces by 50%
        break;
      case 'logical':
        baseSpace *= 0.6; // Reduces by 40%
        break;
    }
  });

  return Math.max(1, Math.floor(baseSpace));
}

function calculateReduction(before: Constraint[], after: Constraint[]): number {
  const beforeSize = estimateSolutions(before);
  const afterSize = estimateSolutions(after);
  return Math.floor(((beforeSize - afterSize) / beforeSize) * 100);
}
```

### Acceptance Criteria
- [ ] Solution space size is estimated before/after constraint addition
- [ ] Reduction percentage is calculated and displayed
- [ ] Visual comparison shows constraint changes
- [ ] Works for all constraint types (temporal, conditional, logical)

---

## Phase 2.3: AI Chat Assistant

### User Story
"I want to chat with an AI to refine my specification and analyze semantic issues."

### Implementation

**1. Chat Component**

File: `frontend/src/components/ics/AIChatPanel.tsx`

```typescript
interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  command?: string; // /refine, /analyze
}

export function AIChatPanel() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const { semanticAnalysis } = useICSStore();

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage: Message = {
      id: nanoid(),
      role: 'user',
      content: input,
      timestamp: Date.now(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      // Parse command
      const command = parseCommand(input);

      // Send to backend
      const response = await sendChatMessage({
        message: input,
        command,
        context: {
          specification: semanticAnalysis,
          holes: semanticAnalysis.typedHoles,
          constraints: semanticAnalysis.constraints,
        },
      });

      const assistantMessage: Message = {
        id: nanoid(),
        role: 'assistant',
        content: response.content,
        timestamp: Date.now(),
        command: command,
      };

      setMessages(prev => [...prev, assistantMessage]);

      // Apply changes if command returns updates
      if (response.updates) {
        applySemanticUpdates(response.updates);
      }
    } catch (error) {
      console.error('Chat error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card className="ai-chat-panel">
      <CardHeader>
        <CardTitle>AI Assistant</CardTitle>
        <CardDescription>
          Use /refine or /analyze commands
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ScrollArea className="chat-messages">
          {messages.map(msg => (
            <ChatMessage key={msg.id} message={msg} />
          ))}
          {isLoading && <LoadingIndicator />}
        </ScrollArea>

        <div className="chat-input">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
            placeholder="Type a message or /command..."
          />
          <Button onClick={sendMessage} disabled={isLoading}>
            <SendIcon />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
```

**2. Command Parser**

```typescript
interface Command {
  type: 'refine' | 'analyze' | 'explain' | 'suggest' | null;
  args: string;
}

function parseCommand(input: string): Command {
  const commandPattern = /^\/(\w+)\s*(.*)$/;
  const match = input.match(commandPattern);

  if (!match) return { type: null, args: input };

  const [, command, args] = match;

  switch (command.toLowerCase()) {
    case 'refine':
      return { type: 'refine', args };
    case 'analyze':
      return { type: 'analyze', args };
    case 'explain':
      return { type: 'explain', args };
    case 'suggest':
      return { type: 'suggest', args };
    default:
      return { type: null, args: input };
  }
}
```

**3. Backend Chat Endpoint**

File: `lift_sys/api/routes/ics.py`

```python
from anthropic import Anthropic

anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

class ChatRequest(BaseModel):
    message: str
    command: Optional[dict] = None
    context: dict  # Specification, holes, constraints

class ChatResponse(BaseModel):
    content: str
    updates: Optional[dict] = None  # Semantic analysis updates

@router.post("/ics/chat")
async def chat_with_ai(request: ChatRequest) -> ChatResponse:
    """AI chat assistant for specification refinement."""

    # Build prompt based on command type
    if request.command and request.command.get("type") == "refine":
        system_prompt = """You are an AI assistant helping refine a software specification.
        Analyze the current specification and suggest improvements to:
        - Clarify ambiguous requirements
        - Add missing constraints
        - Resolve typed holes
        - Improve precision
        """
    elif request.command and request.command.get("type") == "analyze":
        system_prompt = """You are an AI assistant analyzing a software specification.
        Identify:
        - Potential contradictions
        - Missing requirements
        - Ambiguous phrasing
        - Unresolved dependencies
        """
    else:
        system_prompt = "You are a helpful AI assistant for software specification editing."

    # Include context
    context_str = f"""
    Current Specification:
    {request.context.get('specification', {})}

    Typed Holes: {len(request.context.get('holes', []))}
    Constraints: {len(request.context.get('constraints', []))}
    """

    # Call Claude API
    response = anthropic_client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=2000,
        system=system_prompt,
        messages=[
            {"role": "user", "content": f"{context_str}\n\nUser: {request.message}"}
        ]
    )

    assistant_message = response.content[0].text

    # TODO: Parse assistant response for semantic updates
    # (e.g., suggested constraints, hole resolutions)

    return ChatResponse(content=assistant_message, updates=None)
```

### Commands

**`/refine [topic]`**
- Suggest refinements to specification
- Propose additional constraints
- Identify ambiguities

**`/analyze`**
- Comprehensive analysis of current spec
- List issues (contradictions, ambiguities, missing requirements)
- Suggest next steps

**`/explain [entity/hole/constraint]`**
- Explain what a semantic element means
- Show related elements
- Provide context

**`/suggest`**
- Suggest next hole to resolve
- Recommend constraint additions
- Propose refactorings

### Acceptance Criteria
- [ ] Chat UI component renders
- [ ] Messages send to backend
- [ ] Claude API integration works
- [ ] Commands parsed correctly
- [ ] /refine returns suggestions
- [ ] /analyze returns analysis
- [ ] Chat history persisted in store
- [ ] Loading states handled
- [ ] Error handling graceful

---

## Phase 2.4: Backend Enhancements

### Relationship Extraction

**File**: `lift_sys/nlp/relationship_extractor.py`

```python
from typing import List, Dict, Any
import spacy

def extract_relationships(doc: spacy.tokens.Doc) -> List[Dict[str, Any]]:
    """Extract relationships using dependency parsing."""
    relationships = []
    relationship_id_counter = 0

    for token in doc:
        # Causal relationships (causes, triggers, leads to)
        if token.dep_ in ["nsubj", "nsubjpass"] and token.head.lemma_ in ["cause", "trigger", "lead"]:
            relationships.append({
                "id": f"rel-{relationship_id_counter}",
                "type": "causal",
                "source": token.text,
                "target": [child.text for child in token.head.children if child.dep_ == "dobj"],
                "confidence": 0.7,
            })
            relationship_id_counter += 1

        # Temporal relationships (precedes, follows, when)
        if token.dep_ == "advcl" and token.head.dep_ in ["ROOT", "nsubj"]:
            relationships.append({
                "id": f"rel-{relationship_id_counter}",
                "type": "temporal",
                "source": token.head.text,
                "target": token.text,
                "confidence": 0.6,
            })
            relationship_id_counter += 1

        # Dependency relationships (requires, depends on)
        if token.lemma_ in ["require", "depend", "need"]:
            relationships.append({
                "id": f"rel-{relationship_id_counter}",
                "type": "dependency",
                "source": [child.text for child in token.children if child.dep_ == "nsubj"],
                "target": [child.text for child in token.children if child.dep_ in ["dobj", "pobj"]],
                "confidence": 0.8,
            })
            relationship_id_counter += 1

    return relationships
```

### Effects Detection

**File**: `lift_sys/nlp/effects_detector.py`

```python
def detect_effects(doc: spacy.tokens.Doc, text: str) -> List[Dict[str, Any]]:
    """Detect side effects and state changes."""
    effects = []
    effect_id_counter = 0

    # Effect patterns: "X sets Y", "X modifies Y", "X updates Y"
    effect_verbs = ["set", "modify", "update", "change", "alter", "assign"]

    for token in doc:
        if token.lemma_ in effect_verbs:
            # Find subject (what performs effect)
            subject = [child.text for child in token.children if child.dep_ == "nsubj"]
            # Find object (what is affected)
            obj = [child.text for child in token.children if child.dep_ == "dobj"]

            if subject and obj:
                effects.append({
                    "id": f"effect-{effect_id_counter}",
                    "trigger": subject[0],
                    "action": token.lemma_,
                    "target": obj[0],
                    "scope": "local",  # TODO: Determine scope
                })
                effect_id_counter += 1

    return effects
```

### Assertions Detection

**File**: `lift_sys/nlp/assertions_detector.py`

```python
def detect_assertions(doc: spacy.tokens.Doc, text: str) -> List[Dict[str, Any]]:
    """Detect assertions and invariants."""
    assertions = []
    assertion_id_counter = 0

    # Assertion patterns: "always", "never", "invariant", "guarantee"
    assertion_pattern = r"\b(always|never|invariant|guarantee|ensure|assert)\b"

    for match in re.finditer(assertion_pattern, text, re.IGNORECASE):
        # Extract surrounding context
        start = max(0, match.start() - 50)
        end = min(len(text), match.end() + 50)
        context = text[start:end]

        assertions.append({
            "id": f"assertion-{assertion_id_counter}",
            "kind": match.group(1).lower(),
            "condition": context,
            "from": match.start(),
            "to": match.end(),
        })
        assertion_id_counter += 1

    return assertions
```

### Integration into Pipeline

Update `lift_sys/nlp/pipeline.py`:

```python
def analyze(self, text: str) -> dict:
    # ... existing code ...

    # Add new extractions
    relationships = self._extract_relationships(doc)
    effects = self._detect_effects(doc, text)
    assertions = self._detect_assertions(doc, text)

    result = {
        # ... existing fields ...
        "relationships": relationships,  # NEW
        "effects": effects,              # NEW
        "assertions": assertions,        # NEW
    }

    return result
```

### Acceptance Criteria
- [ ] Relationship extraction works (causal, temporal, dependency)
- [ ] Effects detection identifies state changes
- [ ] Assertions detection finds invariants
- [ ] All integrated into `/ics/analyze` endpoint
- [ ] Frontend types updated to match

---

## Testing Strategy

### Unit Tests
- `tests/components/ConstraintPropagationView.test.tsx`
- `tests/components/SolutionSpaceNarrowingView.test.tsx`
- `tests/components/AIChatPanel.test.tsx`
- `tests/nlp/test_relationship_extractor.py`
- `tests/nlp/test_effects_detector.py`
- `tests/nlp/test_assertions_detector.py`

### Integration Tests
- Constraint propagation flow (resolve hole → propagate → update UI)
- Chat command execution (send /refine → backend → response → UI update)
- Backend enhancement integration (analyze → relationships/effects/assertions)

### E2E Tests (Playwright)
- User resolves hole, sees propagation animation
- User narrows solution space, sees reduction
- User chats with AI, gets suggestions
- User applies AI suggestions, specification updates

---

## Timeline

**Estimated Time**: 16-20 hours

- **Phase 2.1** (Constraint Propagation): 4-5 hours
- **Phase 2.2** (Solution Space Narrowing): 3-4 hours
- **Phase 2.3** (AI Chat Assistant): 6-8 hours
- **Phase 2.4** (Backend Enhancements): 3-4 hours

**Prioritization**:
1. Constraint propagation (core feature)
2. Backend enhancements (relationship/effects/assertions)
3. Solution space narrowing (builds on #1)
4. AI chat assistant (most complex, can iterate)

---

## Success Criteria

- [ ] Resolving a hole triggers visible constraint propagation
- [ ] Affected holes show solution space reduction
- [ ] AI chat assistant responds to commands
- [ ] /refine and /analyze commands work
- [ ] Backend extracts relationships, effects, assertions
- [ ] All Phase 2 features integrated into UI
- [ ] E2E tests passing for new features
- [ ] Performance acceptable (<3s for propagation, <5s for chat)

---

## Next Steps

1. Start with **Phase 2.1**: Constraint propagation visualization
2. Implement store logic for `propagateConstraints()`
3. Build `ConstraintPropagationView` component
4. Test with manual hole resolution
5. Move to Phase 2.2, 2.3, 2.4

**Ready to begin implementation!**
