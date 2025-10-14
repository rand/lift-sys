"""xgrammar-enhanced prompt to IR translation."""

from __future__ import annotations

import json
from typing import Any

from ..ir.models import (
    AssertClause,
    EffectClause,
    HoleKind,
    IntentClause,
    IntermediateRepresentation,
    Metadata,
    Parameter,
    Provenance,
    SigClause,
    TypedHole,
)
from ..ir.schema import IR_JSON_SCHEMA, get_prompt_for_ir_generation
from ..providers.base import BaseProvider


class XGrammarIRTranslator:
    """
    Translates natural language prompts to IR using xgrammar-constrained generation.

    This implementation uses JSON schema validation to ensure structured output.
    In production, this would integrate with xgrammar's actual constrained decoding,
    but for now it uses careful prompting + validation.
    """

    def __init__(self, provider: BaseProvider):
        """
        Initialize translator with LLM provider.

        Args:
            provider: LLM provider for generation
        """
        self.provider = provider
        self.schema = IR_JSON_SCHEMA

    async def translate(
        self,
        prompt: str,
        language: str = "python",
        max_retries: int = 3,
    ) -> IntermediateRepresentation:
        """
        Translate natural language prompt to IR.

        Args:
            prompt: User's natural language description
            language: Target programming language
            max_retries: Number of retries if generation fails

        Returns:
            Valid IntermediateRepresentation

        Raises:
            ValueError: If generation fails after max_retries
        """
        system_prompt = get_prompt_for_ir_generation(prompt)

        # Check if provider supports constrained generation (Modal with XGrammar)
        if (
            hasattr(self.provider, "generate_structured")
            and self.provider.capabilities.structured_output
        ):
            # Use constrained generation - guaranteed to match schema
            try:
                ir_json = await self.provider.generate_structured(
                    prompt=system_prompt,
                    schema=self.schema,
                    max_tokens=2000,
                    temperature=0.3,
                )

                # Convert to IR objects
                ir = self._json_to_ir(ir_json, language=language)

                # Add provenance
                ir = self._add_provenance(ir, prompt)

                return ir

            except Exception as e:
                raise ValueError(f"Failed to generate IR with constrained generation: {e}") from e

        # Fallback to text generation with retry logic for providers without structured output
        for attempt in range(max_retries):
            try:
                # Generate IR JSON using LLM
                response = await self.provider.generate_text(
                    prompt=system_prompt,
                    max_tokens=2000,
                    temperature=0.3,  # Lower temperature for more structured output
                )

                # Extract JSON from response (handle markdown code blocks)
                ir_json = self._extract_json(response)

                # Validate against schema
                self._validate_schema(ir_json)

                # Convert to IR objects
                ir = self._json_to_ir(ir_json, language=language)

                # Add provenance
                ir = self._add_provenance(ir, prompt)

                return ir

            except (json.JSONDecodeError, ValueError, KeyError) as e:
                if attempt == max_retries - 1:
                    raise ValueError(
                        f"Failed to generate valid IR after {max_retries} attempts. Last error: {e}"
                    ) from e
                # Retry with more explicit instructions
                system_prompt += (
                    f"\n\nPrevious attempt failed: {e}. Please ensure valid JSON output."
                )

        raise ValueError("Unexpected error in IR generation")

    def _extract_json(self, response: str) -> dict[str, Any]:
        """
        Extract JSON from LLM response, handling markdown code blocks.

        Args:
            response: Raw LLM response

        Returns:
            Parsed JSON dictionary

        Raises:
            json.JSONDecodeError: If no valid JSON found
        """
        # Try to parse directly first
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # Try to extract from markdown code block
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            if end != -1:
                json_str = response[start:end].strip()
                return json.loads(json_str)

        if "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end != -1:
                json_str = response[start:end].strip()
                return json.loads(json_str)

        # Try to find JSON object in response
        start = response.find("{")
        end = response.rfind("}") + 1
        if start != -1 and end > start:
            json_str = response[start:end]
            return json.loads(json_str)

        raise json.JSONDecodeError("No valid JSON found in response", response, 0)

    def _validate_schema(self, ir_json: dict[str, Any]) -> None:
        """
        Validate IR JSON against schema.

        Args:
            ir_json: JSON dictionary to validate

        Raises:
            ValueError: If validation fails
        """
        # Check required top-level fields
        if "intent" not in ir_json:
            raise ValueError("Missing required field: intent")
        if "signature" not in ir_json:
            raise ValueError("Missing required field: signature")

        # Validate intent
        intent = ir_json["intent"]
        if not isinstance(intent, dict):
            raise ValueError("intent must be an object")
        if "summary" not in intent:
            raise ValueError("intent.summary is required")
        if not isinstance(intent["summary"], str):
            raise ValueError("intent.summary must be a string")

        # Validate signature
        signature = ir_json["signature"]
        if not isinstance(signature, dict):
            raise ValueError("signature must be an object")
        if "name" not in signature:
            raise ValueError("signature.name is required")
        if "parameters" not in signature:
            raise ValueError("signature.parameters is required")
        if not isinstance(signature["parameters"], list):
            raise ValueError("signature.parameters must be an array")

        # Validate each parameter
        for param in signature["parameters"]:
            if not isinstance(param, dict):
                raise ValueError("Each parameter must be an object")
            if "name" not in param:
                raise ValueError("Parameter missing required field: name")
            if "type_hint" not in param:
                raise ValueError("Parameter missing required field: type_hint")

    def _json_to_ir(self, ir_json: dict[str, Any], language: str) -> IntermediateRepresentation:
        """
        Convert validated JSON to IR objects.

        Args:
            ir_json: Validated JSON dictionary
            language: Target programming language

        Returns:
            IntermediateRepresentation instance
        """
        # Parse intent
        intent_data = ir_json["intent"]
        intent = IntentClause(
            summary=intent_data["summary"],
            rationale=intent_data.get("rationale"),
            holes=self._parse_holes(intent_data.get("holes", [])),
        )

        # Parse signature
        sig_data = ir_json["signature"]
        parameters = [
            Parameter(
                name=p["name"],
                type_hint=p["type_hint"],
                description=p.get("description"),
            )
            for p in sig_data["parameters"]
        ]

        signature = SigClause(
            name=sig_data["name"],
            parameters=parameters,
            returns=sig_data.get("returns"),
            holes=self._parse_holes(sig_data.get("holes", [])),
        )

        # Parse effects
        effects = [
            EffectClause(
                description=e["description"],
                holes=self._parse_holes(e.get("holes", [])),
            )
            for e in ir_json.get("effects", [])
        ]

        # Parse assertions
        assertions = [
            AssertClause(
                predicate=a["predicate"],
                rationale=a.get("rationale"),
                holes=self._parse_holes(a.get("holes", [])),
            )
            for a in ir_json.get("assertions", [])
        ]

        # Parse metadata
        metadata_data = ir_json.get("metadata", {})
        metadata = Metadata(
            source_path=metadata_data.get("source_path"),
            language=language,
            origin=metadata_data.get("origin", "xgrammar_generation"),
            evidence=metadata_data.get("evidence", []),
        )

        return IntermediateRepresentation(
            intent=intent,
            signature=signature,
            effects=effects,
            assertions=assertions,
            metadata=metadata,
        )

    def _parse_holes(self, holes_data: list[dict[str, Any]]) -> list[TypedHole]:
        """Parse typed holes from JSON."""
        return [
            TypedHole(
                identifier=h["identifier"],
                type_hint=h["type_hint"],
                description=h.get("description", ""),
                constraints=h.get("constraints", {}),
                kind=HoleKind(h.get("kind", "intent")),
            )
            for h in holes_data
        ]

    def _add_provenance(
        self, ir: IntermediateRepresentation, original_prompt: str
    ) -> IntermediateRepresentation:
        """
        Add provenance information to IR clauses.

        Args:
            ir: IR to enhance
            original_prompt: Original user prompt

        Returns:
            IR with provenance added
        """
        provenance = Provenance.from_agent(
            author="xgrammar_translator",
            confidence=0.85,  # High confidence from constrained generation
            metadata={
                "method": "xgrammar_constrained_generation",
                "original_prompt": original_prompt[:200],  # Store truncated prompt
            },
        )

        # Add provenance to clauses
        ir.intent.provenance = provenance
        ir.signature.provenance = provenance

        for effect in ir.effects:
            effect.provenance = provenance

        for assertion in ir.assertions:
            assertion.provenance = provenance

        return ir


__all__ = ["XGrammarIRTranslator"]
