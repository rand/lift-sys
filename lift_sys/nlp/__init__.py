"""NLP module for semantic analysis of natural language specifications.

This module provides the backend NLP pipeline for the ICS (Integrated Context Studio),
replacing the frontend mock analysis with real spaCy + HuggingFace + DSPy processing.

Components:
- pipeline: Main semantic analysis pipeline orchestrator
- entity_extractor: Extract entities using spaCy + HuggingFace NER
- constraint_detector: Detect temporal and conditional constraints
- modal_detector: Detect modal operators (must, should, may, cannot)
- ambiguity_detector: Detect ambiguous phrasing needing clarification
- relationship_extractor: Extract relationships between entities

See docs/ics/ICS_PHASE2_PLAN.md for architecture details.
"""

from lift_sys.nlp.pipeline import SemanticAnalysisPipeline

__all__ = ["SemanticAnalysisPipeline"]
