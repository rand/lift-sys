"""API routes for ICS (Integrated Context Studio) semantic analysis."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from lift_sys.nlp.pipeline import SemanticAnalysisPipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ics", tags=["ICS"])

# Global pipeline instance (lazy-loaded)
_pipeline: SemanticAnalysisPipeline | None = None


def get_pipeline() -> SemanticAnalysisPipeline:
    """Get or create the global NLP pipeline instance."""
    global _pipeline
    if _pipeline is None:
        logger.info("Creating SemanticAnalysisPipeline instance")
        _pipeline = SemanticAnalysisPipeline()
    return _pipeline


# ============================================================================
# Request/Response Schemas
# ============================================================================


class AnalyzeRequest(BaseModel):
    """Request for semantic analysis."""

    text: str = Field(..., description="Natural language specification text to analyze")
    options: dict[str, Any] = Field(
        default_factory=dict,
        description="Analysis options (include_confidence, detect_holes, etc.)",
    )


class AnalyzeResponse(BaseModel):
    """Response from semantic analysis."""

    model_config = {"populate_by_name": True}

    entities: list[dict[str, Any]]
    relationships: list[dict[str, Any]]
    modal_operators: list[dict[str, Any]] = Field(alias="modalOperators")
    constraints: list[dict[str, Any]]
    effects: list[dict[str, Any]]
    assertions: list[dict[str, Any]]
    ambiguities: list[dict[str, Any]]
    contradictions: list[dict[str, Any]]
    typed_holes: list[dict[str, Any]] = Field(alias="typedHoles")
    confidence_scores: dict[str, float] = Field(alias="confidenceScores")


# ============================================================================
# Routes
# ============================================================================


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_text(request: AnalyzeRequest) -> AnalyzeResponse:
    """Analyze natural language text and return semantic analysis.

    This endpoint performs comprehensive semantic analysis using:
    - spaCy for NLP (tokenization, POS, NER, dependencies)
    - HuggingFace Transformers for advanced NER
    - Pattern matching for modal operators and typed holes
    - Heuristics for ambiguity and constraint detection

    **Example Request**:
    ```json
    {
      "text": "The system must validate user input before processing.",
      "options": {
        "include_confidence": true,
        "detect_holes": true
      }
    }
    ```

    **Example Response**:
    ```json
    {
      "entities": [
        {
          "id": "entity-0",
          "type": "TECHNICAL",
          "text": "system",
          "from": 4,
          "to": 10,
          "confidence": 0.85
        }
      ],
      "modalOperators": [
        {
          "id": "modal-0",
          "modality": "necessity",
          "text": "must",
          "from": 11,
          "to": 15,
          "scope": "sentence"
        }
      ],
      ...
    }
    ```

    Args:
        request: Analysis request with text and options

    Returns:
        Semantic analysis results

    Raises:
        HTTPException: If text is empty or analysis fails
    """
    if not request.text or len(request.text.strip()) == 0:
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    if len(request.text) > 50000:  # 50k character limit
        raise HTTPException(
            status_code=400,
            detail="Text too long (max 50,000 characters)",
        )

    try:
        pipeline = get_pipeline()
        analysis = pipeline.analyze(request.text)
        return AnalyzeResponse(**analysis)
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Semantic analysis failed: {str(e)}",
        ) from e


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Health check for ICS API.

    Returns:
        Status message
    """
    try:
        pipeline = get_pipeline()
        # Trigger initialization if needed
        pipeline._ensure_initialized()
        return {"status": "healthy", "models": "loaded"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}
