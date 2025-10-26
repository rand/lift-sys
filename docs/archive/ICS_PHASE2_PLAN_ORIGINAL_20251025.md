# ICS Phase 2 Implementation Plan: Backend NLP Pipeline

**Date**: 2025-10-25
**Status**: Planning
**Phase**: 2 of 7

---

## Overview

Phase 2 replaces the mock semantic analysis (frontend-only pattern matching) with a real backend NLP pipeline using spaCy, HuggingFace Transformers, and DSPy signatures.

**Goals**:
1. Implement backend semantic analysis pipeline
2. Create FastAPI endpoints for analysis
3. Add WebSocket streaming for real-time feedback
4. Connect frontend to backend
5. Support all semantic element types from Phase 1

---

## Architecture Design

### NLP Pipeline Components

```
User types text in frontend
  ↓
Frontend → POST /api/ics/analyze (HTTP) or WS /api/ics/stream (WebSocket)
  ↓
Backend: Semantic Analysis Pipeline
  ├─ 1. spaCy NLP Processing (tokenization, POS, dependencies)
  ├─ 2. HuggingFace NER (dslim/bert-large-NER for entities)
  ├─ 3. DSPy Signatures (structured extraction)
  │   ├─ EntityExtractor
  │   ├─ ConstraintDetector
  │   ├─ ModalOperatorDetector
  │   ├─ AmbiguityDetector
  │   └─ RelationshipExtractor
  ├─ 4. Typed Hole Detection (??? pattern)
  ├─ 5. Semantic Analysis Aggregation
  └─ 6. Response Generation
  ↓
Frontend: Update SemanticAnalysis store → Trigger decorations update
```

### Technology Stack

**NLP Libraries**:
- **spaCy 3.7+**: Core NLP (tokenization, POS tagging, dependency parsing, NER)
- **HuggingFace Transformers**: Advanced NER models
  - Primary: `dslim/bert-large-NER` (PERSON, ORG, LOC, MISC)
  - Fallback: spaCy's built-in NER
- **DSPy 3.0+**: Structured prompting for LLM-based extraction

**Backend Framework**:
- **FastAPI**: REST API endpoints
- **WebSockets**: Real-time streaming
- **Pydantic v2**: Data validation

**Already Installed** (from pyproject.toml):
- ✅ spacy>=3.7.0
- ✅ transformers>=4.57.0
- ✅ dspy>=3.0.3
- ✅ torch>=2.8.0
- ✅ sentence-transformers>=5.1.1

---

## Implementation Plan

### Phase 2.1: Core NLP Pipeline

**Files to Create**:
1. `lift_sys/nlp/__init__.py` - NLP module init
2. `lift_sys/nlp/pipeline.py` - Main semantic analysis pipeline
3. `lift_sys/nlp/entity_extractor.py` - Entity extraction (spaCy + HuggingFace)
4. `lift_sys/nlp/constraint_detector.py` - Constraint detection
5. `lift_sys/nlp/modal_detector.py` - Modal operator detection
6. `lift_sys/nlp/ambiguity_detector.py` - Ambiguity detection
7. `lift_sys/nlp/relationship_extractor.py` - Relationship extraction

**Tasks**:
- [x] Create nlp module structure
- [ ] Implement spaCy pipeline initialization
- [ ] Load HuggingFace NER model (dslim/bert-large-NER)
- [ ] Implement entity extraction with confidence scores
- [ ] Implement constraint detection (temporal, conditional)
- [ ] Implement modal operator detection (must, should, may)
- [ ] Implement ambiguity detection
- [ ] Implement relationship extraction (causal, temporal, dependency)
- [ ] Aggregate results into SemanticAnalysis format

### Phase 2.2: DSPy Signatures

**Files to Create**:
1. `lift_sys/dspy_signatures/semantic_extraction.py` - DSPy signatures for semantic analysis

**Signatures to Implement**:
```python
class EntityExtractorSignature(dspy.Signature):
    """Extract semantic entities from text with type and confidence."""
    text = dspy.InputField(desc="Natural language specification text")
    entities = dspy.OutputField(desc="List of entities with type, text, confidence")

class ConstraintDetectorSignature(dspy.Signature):
    """Detect constraints and requirements."""
    text = dspy.InputField()
    constraints = dspy.OutputField(desc="Temporal, conditional, or logical constraints")

class ModalOperatorSignature(dspy.Signature):
    """Detect modal operators (necessity, possibility, prohibition)."""
    text = dspy.InputField()
    modals = dspy.OutputField(desc="Modal operators with modality type")

class AmbiguityDetectorSignature(dspy.Signature):
    """Detect ambiguous phrasing that needs clarification."""
    text = dspy.InputField()
    ambiguities = dspy.OutputField(desc="Ambiguous spans with suggestions")

class RelationshipExtractorSignature(dspy.Signature):
    """Extract relationships between entities."""
    text = dspy.InputField()
    entities = dspy.InputField(desc="Previously extracted entities")
    relationships = dspy.OutputField(desc="Causal, temporal, or dependency relationships")
```

**Tasks**:
- [ ] Implement DSPy signatures
- [ ] Configure DSPy with appropriate LLM (Anthropic Claude)
- [ ] Add caching for repeated analysis
- [ ] Add fallback logic if DSPy unavailable

### Phase 2.3: API Endpoints

**Files to Create/Modify**:
1. `lift_sys/api/routes/ics.py` - ICS-specific routes
2. `lift_sys/api/schemas.py` - Add ICS request/response schemas

**Endpoints to Implement**:

**POST /api/ics/analyze**
```python
{
  "text": "The system must validate user input before processing.",
  "options": {
    "include_confidence": true,
    "detect_holes": true
  }
}
```
Response: Full SemanticAnalysis JSON

**WebSocket /api/ics/stream**
```python
# Streaming updates as analysis progresses
{
  "type": "entities_found",
  "data": [...entities]
}
{
  "type": "constraints_found",
  "data": [...constraints]
}
{
  "type": "analysis_complete",
  "data": {...full_analysis}
}
```

**Tasks**:
- [ ] Create ICS API route module
- [ ] Implement POST /api/ics/analyze endpoint
- [ ] Implement WebSocket /api/ics/stream endpoint
- [ ] Add request validation with Pydantic
- [ ] Add error handling and logging
- [ ] Add rate limiting (if needed)

### Phase 2.4: Frontend Integration

**Files to Modify**:
1. `frontend/src/lib/ics/api.ts` - API client for backend
2. `frontend/src/components/ics/SemanticEditor.tsx` - Replace mock with real API

**Tasks**:
- [ ] Create API client module
- [ ] Implement HTTP client for /api/ics/analyze
- [ ] Implement WebSocket client for /api/ics/stream
- [ ] Replace `generateMockAnalysis` with API calls
- [ ] Add loading states
- [ ] Add error handling
- [ ] Add retry logic
- [ ] Add offline fallback (use mock if backend unavailable)

---

## Data Flow

### Request Flow (HTTP)

```typescript
// Frontend
const analysis = await analyzeText(text);
updateSemanticAnalysis(analysis);

// Backend
POST /api/ics/analyze
  ↓
NLPPipeline.analyze(text)
  ↓
- spaCy processing
- HuggingFace NER
- DSPy extraction
- Aggregation
  ↓
Return SemanticAnalysis JSON
```

### Streaming Flow (WebSocket)

```typescript
// Frontend
const ws = new WebSocket('ws://api/ics/stream');
ws.send({ text });

ws.onmessage = (event) => {
  const { type, data } = JSON.parse(event.data);
  if (type === 'entities_found') {
    updateEntities(data);
  }
  // ... handle other types
};

// Backend
@app.websocket("/api/ics/stream")
async def stream_analysis(websocket: WebSocket):
    await websocket.accept()
    text = await websocket.receive_json()

    # Stream results as they're computed
    entities = await extract_entities(text)
    await websocket.send_json({"type": "entities_found", "data": entities})

    constraints = await detect_constraints(text)
    await websocket.send_json({"type": "constraints_found", "data": constraints})

    # ... more streaming

    await websocket.send_json({"type": "analysis_complete"})
```

---

## Semantic Element Mapping

Map frontend types to backend extraction:

| Frontend Type | Backend Method | Technology |
|---------------|----------------|------------|
| Entity (TECHNICAL, PERSON, ORG, FUNCTION) | entity_extractor.extract() | spaCy NER + HuggingFace |
| Constraint (temporal, conditional) | constraint_detector.detect() | spaCy + DSPy |
| ModalOperator (necessity, possibility) | modal_detector.detect() | Regex + DSPy |
| Ambiguity | ambiguity_detector.detect() | DSPy + heuristics |
| Contradiction | contradiction_detector.detect() | DSPy |
| TypedHole (???) | Regex pattern matching | Regex |
| Relationship | relationship_extractor.extract() | spaCy dependencies + DSPy |

---

## Testing Strategy

### Unit Tests
- `tests/nlp/test_entity_extractor.py`
- `tests/nlp/test_constraint_detector.py`
- `tests/nlp/test_modal_detector.py`
- `tests/api/routes/test_ics.py`

### Integration Tests
- End-to-end: Frontend → API → NLP → Response
- WebSocket streaming test
- Error handling test

### Test Data
- Use Phase 1 mock patterns as test cases
- Add edge cases (empty text, very long text, special characters)

---

## Performance Considerations

**spaCy Model Loading**:
- Load models at startup (not per-request)
- Use small models for speed (en_core_web_sm)
- Cache model in memory

**HuggingFace Model**:
- Load once at startup
- Use GPU if available (Modal.com GPU workers)
- Batch processing for multiple texts

**DSPy Caching**:
- Cache LLM responses for identical inputs
- Use DSPy's built-in caching

**WebSocket**:
- Limit concurrent connections
- Add timeouts (30s max per analysis)
- Stream partial results (don't wait for everything)

**Expected Latency**:
- spaCy: ~50-100ms
- HuggingFace NER: ~200-500ms
- DSPy extraction: ~1-2s (depends on LLM)
- **Total**: ~2-3s for full analysis

---

## Configuration

### Environment Variables

```bash
# .env
NLP_MODEL=en_core_web_sm  # spaCy model
NER_MODEL=dslim/bert-large-NER  # HuggingFace model
DSPY_LLM=anthropic/claude-3-5-sonnet-20241022
DSPY_CACHE_DIR=.cache/dspy
MAX_TEXT_LENGTH=10000  # characters
ANALYSIS_TIMEOUT=30  # seconds
```

### spaCy Model Installation

```bash
# Install during deployment
uv run python -m spacy download en_core_web_sm
```

---

## Deployment

### Modal.com Setup

```python
# lift_sys/nlp/modal_app.py
import modal

nlp_image = (
    modal.Image.debian_slim()
    .pip_install_from_pyproject("pyproject.toml")
    .run_commands("python -m spacy download en_core_web_sm")
)

app = modal.App("lift-sys-nlp")

@app.function(
    image=nlp_image,
    gpu="T4",  # GPU for HuggingFace models
    timeout=60,
)
def analyze_text(text: str) -> dict:
    from lift_sys.nlp.pipeline import SemanticAnalysisPipeline

    pipeline = SemanticAnalysisPipeline()
    return pipeline.analyze(text)
```

---

## Phase 2 Success Criteria

- [ ] spaCy pipeline operational
- [ ] HuggingFace NER extracting entities
- [ ] DSPy signatures extracting constraints/modals/ambiguities
- [ ] API endpoint returning SemanticAnalysis JSON
- [ ] WebSocket streaming working
- [ ] Frontend connected to backend
- [ ] All Phase 1 semantic element types supported
- [ ] Latency < 5s for typical specifications (~500 words)
- [ ] Tests passing with real NLP pipeline

---

## Timeline

**Estimated Time**: 8-10 hours
- Phase 2.1 (NLP Pipeline): 4-5 hours
- Phase 2.2 (DSPy Signatures): 2-3 hours
- Phase 2.3 (API Endpoints): 1-2 hours
- Phase 2.4 (Frontend Integration): 1-2 hours

**Prioritization**:
1. Core NLP pipeline (entities first, then constraints)
2. API endpoint (HTTP first, WebSocket later)
3. Frontend integration
4. DSPy signatures (can start with simpler regex fallbacks)

---

## Next Steps

1. Create `lift_sys/nlp/` module
2. Implement entity extraction with spaCy + HuggingFace
3. Create API endpoint
4. Test end-to-end flow
5. Add remaining semantic element extractors
6. Optimize performance
7. Add WebSocket streaming

**Ready to start implementation!**
