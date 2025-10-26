"""Relationship extraction using spaCy dependency parsing.

Phase 2 Enhancement: Extract structured relationships between entities
from natural language specifications using linguistic patterns and dependency trees.

Relationships capture semantic connections like:
- Dependencies: "X depends on Y", "X requires Y", "X uses Y"
- Creation: "X creates Y", "X generates Y", "X produces Y"
- Modification: "X modifies Y", "X updates Y", "X changes Y"
- Temporal: "X before Y", "X after Y", "X triggers Y"
- Causal: "X causes Y", "X results in Y", "if X then Y"
- Composition: "X contains Y", "X includes Y", "X is part of Y"
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


# Relationship type patterns (verb lemma → relationship type)
# NOTE: spaCy lemmatizer returns base forms (e.g., "use" not "uses")
RELATIONSHIP_PATTERNS = {
    # Dependencies
    "depend": "DEPENDS_ON",
    "require": "DEPENDS_ON",
    "need": "DEPENDS_ON",
    "rely": "DEPENDS_ON",
    "use": "USES",
    "utilize": "USES",
    "employ": "USES",
    # Creation
    "create": "PRODUCES",
    "generate": "PRODUCES",
    "produce": "PRODUCES",
    "make": "PRODUCES",
    "build": "PRODUCES",
    "construct": "PRODUCES",
    "initialize": "PRODUCES",
    # Modification
    "modify": "MODIFIES",
    "update": "MODIFIES",
    "change": "MODIFIES",
    "alter": "MODIFIES",
    "transform": "TRANSFORMS",
    "convert": "TRANSFORMS",
    # Temporal
    "precede": "PRECEDES",
    "follow": "FOLLOWS",
    "trigger": "TRIGGERS",
    # Causal
    "cause": "CAUSES",
    "result": "CAUSES",
    "lead": "CAUSES",
    # Composition
    "contain": "CONTAINS",
    "include": "CONTAINS",
    "comprise": "CONTAINS",
    # Operations
    "process": "OPERATES_ON",
    "validate": "OPERATES_ON",
    "check": "OPERATES_ON",
    "verify": "OPERATES_ON",
    "analyze": "OPERATES_ON",
    # Data flow
    "return": "RETURNS",
    "output": "RETURNS",
    "yield": "RETURNS",
    "save": "WRITES_TO",
    "write": "WRITES_TO",
    "store": "WRITES_TO",
    "read": "READS_FROM",
    "load": "READS_FROM",
    "fetch": "READS_FROM",
}


def extract_relationships(doc) -> list[dict[str, Any]]:
    """Extract relationships from spaCy doc using dependency parsing.

    Args:
        doc: spaCy Doc object with dependency parse

    Returns:
        List of relationship dictionaries with:
        - from_entity: source entity (string)
        - to_entity: target entity (string)
        - relationship_type: USES, PRODUCES, DEPENDS_ON, etc.
        - confidence: extraction confidence (0.0-1.0)
        - description: human-readable description
        - span: text span (start, end positions)
    """
    relationships = []
    relationship_id = 0

    # Extract subject-verb-object patterns
    for token in doc:
        # Look for verbs with both subject and object
        if token.pos_ == "VERB":
            # Find subject
            subjects = [child for child in token.children if child.dep_ in ("nsubj", "nsubjpass")]

            # Find objects
            objects = [
                child for child in token.children if child.dep_ in ("dobj", "obj", "pobj", "attr")
            ]

            # Also check prepositional phrases (e.g., "depends on")
            for child in token.children:
                if child.dep_ == "prep":
                    for grandchild in child.children:
                        if grandchild.dep_ == "pobj":
                            objects.append(grandchild)

            # Also look for coordinating conjunctions (e.g., "processes input and returns output")
            # This allows us to find additional verbs in a compound predicate
            for child in token.children:
                if child.dep_ == "conj" and child.pos_ == "VERB":
                    # Found a conjoined verb, check if it has objects
                    conj_objects = [
                        gc for gc in child.children if gc.dep_ in ("dobj", "obj", "pobj", "attr")
                    ]
                    # If conjoined verb has objects, process it separately
                    if conj_objects:
                        for conj_obj in conj_objects:
                            # Use same subjects as parent verb
                            for subj in subjects:
                                verb_lemma = child.lemma_.lower()
                                relationship_type = RELATIONSHIP_PATTERNS.get(
                                    verb_lemma, "RELATES_TO"
                                )
                                from_entity = _get_entity_text(subj)
                                to_entity = _get_entity_text(conj_obj)
                                confidence = 0.9 if verb_lemma in RELATIONSHIP_PATTERNS else 0.6
                                description = f"{from_entity} {child.text} {to_entity}"

                                relationships.append(
                                    {
                                        "id": f"rel-{relationship_id}",
                                        "from_entity": from_entity,
                                        "to_entity": to_entity,
                                        "relationship_type": relationship_type,
                                        "confidence": round(confidence, 2),
                                        "description": description,
                                        "span": {
                                            "start": child.idx,
                                            "end": child.idx + len(child.text),
                                        },
                                    }
                                )
                                relationship_id += 1

            # Create relationships for each subject-verb-object triple
            for subj in subjects:
                for obj in objects:
                    # Get base verb form for pattern matching
                    verb_lemma = token.lemma_.lower()

                    # Determine relationship type
                    relationship_type = RELATIONSHIP_PATTERNS.get(verb_lemma, "RELATES_TO")

                    # Extract entity text (handle compound nouns)
                    from_entity = _get_entity_text(subj)
                    to_entity = _get_entity_text(obj)

                    # Confidence based on pattern match and distance
                    confidence = 0.9 if verb_lemma in RELATIONSHIP_PATTERNS else 0.6
                    # Reduce confidence for long-distance dependencies
                    distance = abs(subj.i - obj.i)
                    if distance > 10:
                        confidence *= 0.8

                    # Create description
                    description = f"{from_entity} {token.text} {to_entity}"

                    relationships.append(
                        {
                            "id": f"rel-{relationship_id}",
                            "from_entity": from_entity,
                            "to_entity": to_entity,
                            "relationship_type": relationship_type,
                            "confidence": round(confidence, 2),
                            "description": description,
                            "span": {"start": token.idx, "end": token.idx + len(token.text)},
                        }
                    )
                    relationship_id += 1

    # Extract conditional patterns ("if X then Y")
    for i, token in enumerate(doc):
        if token.text.lower() == "if":
            # Find the condition clause
            condition_tokens = []
            then_idx = None

            # Look ahead for "then"
            for j in range(i + 1, min(i + 20, len(doc))):
                if doc[j].text.lower() == "then":
                    then_idx = j
                    condition_tokens = doc[i + 1 : j]
                    break

            if then_idx and condition_tokens:
                # Extract result clause
                result_tokens = doc[then_idx + 1 : min(then_idx + 15, len(doc))]

                # Simple extraction: first noun in condition → first noun in result
                cond_nouns = [t.text for t in condition_tokens if t.pos_ == "NOUN"]
                result_nouns = [t.text for t in result_tokens if t.pos_ == "NOUN"]

                if cond_nouns and result_nouns:
                    from_entity = cond_nouns[0]
                    to_entity = result_nouns[0]

                    relationships.append(
                        {
                            "id": f"rel-{relationship_id}",
                            "from_entity": from_entity,
                            "to_entity": to_entity,
                            "relationship_type": "CAUSES",
                            "confidence": 0.7,
                            "description": f"if {from_entity} then {to_entity}",
                            "span": {"start": token.idx, "end": result_tokens[-1].idx},
                        }
                    )
                    relationship_id += 1

    logger.debug(f"Extracted {len(relationships)} relationships")
    return relationships


def _get_entity_text(token) -> str:
    """Get text for an entity, handling compound nouns and modifiers.

    Args:
        token: spaCy token

    Returns:
        Full entity text including compounds and modifiers
    """
    # Get compound nouns (e.g., "user input" → "user_input")
    compounds = []

    # Look for compound children
    for child in token.children:
        if child.dep_ == "compound":
            compounds.append(child.text)

    # Look for adjective modifiers
    for child in token.children:
        if child.dep_ == "amod":
            compounds.append(child.text)

    # Combine in order
    if compounds:
        return "_".join(sorted(compounds, key=lambda x: x) + [token.text])
    else:
        return token.text


def deduplicate_relationships(relationships: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove duplicate relationships based on entity pairs.

    Args:
        relationships: List of relationship dictionaries

    Returns:
        Deduplicated list, keeping highest confidence for each pair
    """
    seen = {}
    for rel in relationships:
        key = (rel["from_entity"], rel["to_entity"], rel["relationship_type"])

        if key not in seen or rel["confidence"] > seen[key]["confidence"]:
            seen[key] = rel

    return list(seen.values())
