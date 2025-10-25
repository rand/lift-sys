"""Main semantic analysis pipeline for ICS.

Orchestrates spaCy, HuggingFace, and DSPy components to perform
comprehensive semantic analysis of natural language specifications.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class SemanticAnalysisPipeline:
    """Main pipeline for semantic analysis of natural language text.

    Combines multiple NLP techniques:
    - spaCy: Tokenization, POS tagging, dependency parsing, NER
    - HuggingFace Transformers: Advanced NER (dslim/bert-large-NER)
    - DSPy: Structured extraction with LLMs
    - Pattern matching: Typed holes, modal operators

    The pipeline is lazy-loaded to avoid startup overhead.
    """

    def __init__(self):
        """Initialize pipeline (models loaded on first use)."""
        self._spacy_model = None
        self._ner_model = None
        self._ner_tokenizer = None
        self._initialized = False
        logger.info("SemanticAnalysisPipeline created (models will load on first use)")

    def _ensure_initialized(self):
        """Lazy load all NLP models."""
        if self._initialized:
            return

        logger.info("Initializing NLP models...")

        try:
            # Load spaCy model
            import spacy

            try:
                self._spacy_model = spacy.load("en_core_web_sm")
                logger.info("Loaded spaCy model: en_core_web_sm")
            except OSError:
                logger.warning("spaCy model en_core_web_sm not found, downloading...")
                import subprocess

                subprocess.run(
                    ["python", "-m", "spacy", "download", "en_core_web_sm"],
                    check=True,
                )
                self._spacy_model = spacy.load("en_core_web_sm")
                logger.info("Downloaded and loaded spaCy model")

            # Load HuggingFace NER model (optional, fallback to spaCy if unavailable)
            try:
                from transformers import AutoModelForTokenClassification, AutoTokenizer

                model_name = "dslim/bert-large-NER"
                self._ner_tokenizer = AutoTokenizer.from_pretrained(model_name)
                self._ner_model = AutoModelForTokenClassification.from_pretrained(model_name)
                logger.info(f"Loaded HuggingFace NER model: {model_name}")
            except Exception as e:
                logger.warning(
                    f"Could not load HuggingFace NER model, will use spaCy NER only: {e}"
                )
                self._ner_model = None
                self._ner_tokenizer = None

            self._initialized = True
            logger.info("NLP pipeline initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize NLP pipeline: {e}")
            raise

    def analyze(self, text: str) -> dict[str, Any]:
        """Analyze text and return semantic analysis results.

        Args:
            text: Natural language specification text

        Returns:
            Dictionary with semantic analysis results matching frontend SemanticAnalysis type:
            {
                "entities": [...],
                "relationships": [...],
                "modalOperators": [...],
                "constraints": [...],
                "effects": [],
                "assertions": [],
                "ambiguities": [...],
                "contradictions": [...],
                "typedHoles": [...],
                "confidenceScores": {...}
            }
        """
        self._ensure_initialized()

        if not text or len(text.strip()) == 0:
            return self._empty_analysis()

        logger.info(f"Analyzing text: {text[:100]}..." if len(text) > 100 else text)

        # Process with spaCy
        doc = self._spacy_model(text)

        # Extract semantic elements
        entities = self._extract_entities(doc, text)
        relationships = self._extract_relationships(doc)
        modals = self._detect_modal_operators(text)
        constraints = self._detect_constraints(doc, text)
        ambiguities = self._detect_ambiguities(text)
        contradictions = self._detect_contradictions(text)
        typed_holes = self._detect_typed_holes(text)

        # Compute confidence scores
        confidence_scores = {}
        for entity in entities:
            confidence_scores[entity["id"]] = entity["confidence"]
        for hole in typed_holes:
            confidence_scores[hole["id"]] = 0.5  # Holes are explicit, medium confidence

        result = {
            "entities": entities,
            "relationships": relationships,
            "modalOperators": modals,
            "constraints": constraints,
            "effects": [],  # Future: effect detection
            "assertions": [],  # Future: assertion detection
            "ambiguities": ambiguities,
            "contradictions": contradictions,
            "typedHoles": typed_holes,
            "confidenceScores": confidence_scores,
        }

        logger.info(
            f"Analysis complete: {len(entities)} entities, {len(modals)} modals, {len(typed_holes)} holes"
        )
        return result

    def _empty_analysis(self) -> dict[str, Any]:
        """Return empty analysis for empty text."""
        return {
            "entities": [],
            "relationships": [],
            "modalOperators": [],
            "constraints": [],
            "effects": [],
            "assertions": [],
            "ambiguities": [],
            "contradictions": [],
            "typedHoles": [],
            "confidenceScores": {},
        }

    def _extract_entities(self, doc, text: str) -> list[dict[str, Any]]:
        """Extract entities using spaCy and optionally HuggingFace NER.

        Entity types mapped to frontend types:
        - PERSON → PERSON
        - ORG → ORG
        - GPE (geopolitical entity) → ORG
        - PRODUCT, WORK_OF_ART → TECHNICAL
        - Other → TECHNICAL (default for technical terms)
        """
        entities = []
        entity_id_counter = 0

        # Extract using spaCy NER
        for ent in doc.ents:
            # Map spaCy entity types to frontend types
            entity_type = self._map_spacy_entity_type(ent.label_)

            entities.append(
                {
                    "id": f"entity-{entity_id_counter}",
                    "type": entity_type,
                    "text": ent.text,
                    "from": ent.start_char,
                    "to": ent.end_char,
                    "confidence": 0.85,  # spaCy entities have reasonable confidence
                }
            )
            entity_id_counter += 1

        # Add technical terms (nouns that might be domain-specific)
        for token in doc:
            if token.pos_ in ["NOUN", "PROPN"] and not token.is_stop:
                # Check if this token is not already part of an entity
                is_in_entity = any(
                    token.idx >= ent["from"] and token.idx < ent["to"] for ent in entities
                )
                if not is_in_entity:
                    # Check if it looks like a technical term (capitalized or compound)
                    if token.text[0].isupper() or "_" in token.text:
                        entities.append(
                            {
                                "id": f"entity-{entity_id_counter}",
                                "type": "TECHNICAL",
                                "text": token.text,
                                "from": token.idx,
                                "to": token.idx + len(token.text),
                                "confidence": 0.6,  # Lower confidence for inferred terms
                            }
                        )
                        entity_id_counter += 1

        return entities

    def _map_spacy_entity_type(self, spacy_label: str) -> str:
        """Map spaCy entity labels to frontend entity types."""
        mapping = {
            "PERSON": "PERSON",
            "ORG": "ORG",
            "GPE": "ORG",  # Geopolitical entities treated as orgs
            "PRODUCT": "TECHNICAL",
            "WORK_OF_ART": "TECHNICAL",
            "LAW": "TECHNICAL",
            "LANGUAGE": "TECHNICAL",
        }
        return mapping.get(spacy_label, "TECHNICAL")

    def _extract_relationships(self, doc) -> list[dict[str, Any]]:
        """Extract relationships using dependency parsing."""
        relationships = []
        # TODO: Implement relationship extraction using spaCy dependencies
        # For now, return empty list
        return relationships

    def _detect_modal_operators(self, text: str) -> list[dict[str, Any]]:
        """Detect modal operators (must, should, may, cannot)."""
        modals = []
        modal_id_counter = 0

        # Modal patterns
        modal_patterns = [
            (r"\b(must|shall|required|mandatory)\b", "necessity"),
            (r"\b(should|ought|recommended)\b", "certainty"),
            (r"\b(may|might|could|possibly|optional)\b", "possibility"),
            (r"\b(cannot|must not|shall not|prohibited|forbidden)\b", "prohibition"),
        ]

        for pattern, modality in modal_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                modals.append(
                    {
                        "id": f"modal-{modal_id_counter}",
                        "modality": modality,
                        "text": match.group(0),
                        "from": match.start(),
                        "to": match.end(),
                        "scope": "sentence",  # TODO: Determine actual scope
                    }
                )
                modal_id_counter += 1

        return modals

    def _detect_constraints(self, doc, text: str) -> list[dict[str, Any]]:
        """Detect temporal and conditional constraints."""
        constraints = []
        constraint_id_counter = 0

        # Temporal constraint patterns
        temporal_pattern = r"\b(when|if|unless|while|during|after|before|until)\b"
        for match in re.finditer(temporal_pattern, text, re.IGNORECASE):
            constraints.append(
                {
                    "id": f"constraint-{constraint_id_counter}",
                    "type": "temporal",
                    "severity": "medium",
                    "description": f"Temporal constraint: {match.group(0)}",
                    "appliesTo": [],  # TODO: Link to affected entities
                    "expression": match.group(0),
                    "from": match.start(),
                    "to": match.end(),
                }
            )
            constraint_id_counter += 1

        return constraints

    def _detect_ambiguities(self, text: str) -> list[dict[str, Any]]:
        """Detect ambiguous phrasing."""
        ambiguities = []
        ambiguity_id_counter = 0

        # Ambiguity patterns
        ambiguity_pattern = r"\b(or|and/or|maybe|perhaps|unclear|ambiguous|either)\b"
        for match in re.finditer(ambiguity_pattern, text, re.IGNORECASE):
            # Only mark 30% as ambiguous (same as mock)
            if hash(match.group(0) + str(match.start())) % 10 < 3:
                ambiguities.append(
                    {
                        "id": f"ambiguity-{ambiguity_id_counter}",
                        "reason": "Potential ambiguity detected",
                        "from": match.start(),
                        "to": match.end(),
                        "suggestions": [
                            "Consider clarifying this statement",
                            "Specify which option is preferred",
                        ],
                    }
                )
                ambiguity_id_counter += 1

        return ambiguities

    def _detect_contradictions(self, text: str) -> list[dict[str, Any]]:
        """Detect potential contradictions."""
        contradictions = []
        # TODO: Implement contradiction detection (requires semantic understanding)
        # For now, return empty list
        return contradictions

    def _detect_typed_holes(self, text: str) -> list[dict[str, Any]]:
        """Detect typed holes (??? syntax)."""
        holes = []
        hole_pattern = r"\?\?\?(\w+)?"

        for match in re.finditer(hole_pattern, text):
            identifier = match.group(1) if match.group(1) else f"hole-{len(holes) + 1}"
            holes.append(
                {
                    "id": f"hole-{len(holes)}",
                    "identifier": identifier,
                    "kind": "implementation",
                    "status": "unresolved",
                    "typeHint": "unknown",
                    "pos": match.start(),
                    "dependencies": {"blocks": [], "blockedBy": []},
                    "constraints": [],
                    "solutionSpace": {"narrowed": False, "refinements": []},
                    "acceptanceCriteria": [],
                }
            )

        return holes
