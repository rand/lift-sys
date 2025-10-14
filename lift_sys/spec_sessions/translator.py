"""Natural language to IR translation service."""

from __future__ import annotations

import re
from typing import Any

from ..forward_mode.synthesizer import CodeSynthesizer
from ..forward_mode.xgrammar_translator import XGrammarIRTranslator
from ..ir.models import (
    AssertClause,
    EffectClause,
    HoleKind,
    IntentClause,
    IntermediateRepresentation,
    Metadata,
    Parameter,
    SigClause,
    TypedHole,
)
from ..ir.parser import IRParser
from ..providers.base import BaseProvider
from .models import IRDraft


class PromptToIRTranslator:
    """Converts natural language prompts to IR drafts with ambiguity detection."""

    def __init__(
        self,
        synthesizer: CodeSynthesizer | None = None,
        parser: IRParser | None = None,
        provider: BaseProvider | None = None,
    ):
        self.synthesizer = synthesizer
        self.parser = parser or IRParser()
        self.provider = provider
        self.xgrammar_translator = XGrammarIRTranslator(provider) if provider else None

    async def translate(
        self,
        prompt: str,
        context: IntermediateRepresentation | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> IRDraft:
        """
        Translate a natural language prompt into an IR draft.

        Args:
            prompt: Natural language description of desired functionality
            context: Optional existing IR to refine
            metadata: Optional metadata to attach to the IR

        Returns:
            IRDraft with initial IR structure and detected ambiguities
        """
        # If we have xgrammar translator, use it for structured generation
        if self.xgrammar_translator:
            ir = await self._translate_with_xgrammar(prompt, context)
        elif self.synthesizer:
            # Fallback to synthesizer if available
            ir = await self._translate_with_llm(prompt, context)
        else:
            # Final fallback: rule-based translation
            ir = self._translate_rule_based(prompt, context)

        # Detect ambiguities and create holes
        holes = self._detect_ambiguities(ir, prompt)
        ir = self._inject_holes(ir, holes)

        # Create draft
        draft = IRDraft(
            version=1 if not context else (len(context.typed_holes()) + 1),
            ir=ir,
            validation_status="incomplete" if holes else "pending",
            ambiguities=[h.identifier for h in holes],
            metadata=metadata or {},
        )

        return draft

    async def _translate_with_xgrammar(
        self,
        prompt: str,
        context: IntermediateRepresentation | None,
    ) -> IntermediateRepresentation:
        """Use xgrammar translator for constrained IR generation."""
        if not self.xgrammar_translator:
            raise ValueError("XGrammar translator not initialized")

        # If refining existing IR, incorporate context into prompt
        if context:
            refined_prompt = f"""Refine this existing specification:

Current specification:
{self.parser.dumps(context)}

User's refinement request:
{prompt}

Generate an improved IR that incorporates the refinement."""
            return await self.xgrammar_translator.translate(refined_prompt)

        # Fresh generation
        return await self.xgrammar_translator.translate(prompt)

    async def _translate_with_llm(
        self,
        prompt: str,
        context: IntermediateRepresentation | None,
    ) -> IntermediateRepresentation:
        """Use LLM to translate prompt to IR structure (fallback method)."""
        # This is a fallback when xgrammar is not available
        # In practice, this would use the synthesizer to generate IR
        # For now, fall back to rule-based
        return self._translate_rule_based(prompt, context)

    def _translate_rule_based(
        self,
        prompt: str,
        context: IntermediateRepresentation | None,
    ) -> IntermediateRepresentation:
        """Rule-based translation for when LLM is not available."""
        if context:
            # Start with existing IR
            return context

        # Extract function name (look for keywords like "function", "method", or infer from text)
        func_name = self._extract_function_name(prompt)

        # Extract parameters (look for patterns like "takes X" or "accepts Y")
        parameters = self._extract_parameters(prompt)

        # Extract return type (look for patterns like "returns X")
        return_type = self._extract_return_type(prompt)

        # Create basic IR structure
        ir = IntermediateRepresentation(
            intent=IntentClause(summary=prompt[:200].strip()),  # Use first 200 chars as summary
            signature=SigClause(
                name=func_name,
                parameters=parameters,
                returns=return_type,
            ),
            effects=self._extract_effects(prompt),
            assertions=self._extract_assertions(prompt),
            metadata=Metadata(origin="prompt", language="python"),
        )

        return ir

    def _extract_function_name(self, prompt: str) -> str:
        """Extract function name from prompt using heuristics."""
        # Look for "function/method called X"
        patterns = [
            r"(?:function|method|procedure|routine)\s+(?:called|named)\s+['\"]?(\w+)['\"]?",
            r"create\s+(?:a\s+)?['\"]?(\w+)['\"]?\s+(?:function|method)",
            r"implement\s+['\"]?(\w+)['\"]?",
        ]

        for pattern in patterns:
            match = re.search(pattern, prompt, re.IGNORECASE)
            if match:
                return match.group(1)

        # Default: generate generic name
        return "generated_function"

    def _extract_parameters(self, prompt: str) -> list[Parameter]:
        """Extract parameters from prompt using heuristics."""
        parameters = []

        # Look for patterns like "takes X" or "accepts Y"
        param_patterns = [
            r"takes\s+(?:a\s+)?(\w+)\s+(?:named\s+)?['\"]?(\w+)['\"]?",
            r"accepts\s+(?:a\s+)?(\w+)\s+['\"]?(\w+)['\"]?",
            r"parameter\s+['\"]?(\w+)['\"]?\s+of\s+type\s+(\w+)",
            r"input\s+['\"]?(\w+)['\"]?\s*:\s*(\w+)",
        ]

        for pattern in param_patterns:
            matches = re.finditer(pattern, prompt, re.IGNORECASE)
            for match in matches:
                if len(match.groups()) == 2:
                    type_hint, name = match.groups()
                    parameters.append(Parameter(name=name, type_hint=type_hint))

        return parameters

    def _extract_return_type(self, prompt: str) -> str | None:
        """Extract return type from prompt using heuristics."""
        patterns = [
            r"returns?\s+(?:a\s+)?(?:an\s+)?(\w+)(?:\s|$)",
            r"produces?\s+(?:a\s+)?(?:an\s+)?(\w+)(?:\s|$)",
            r"outputs?\s+(?:a\s+)?(?:an\s+)?(\w+)(?:\s|$)",
        ]

        for pattern in patterns:
            match = re.search(pattern, prompt, re.IGNORECASE)
            if match:
                ret_type = match.group(1)
                # Filter out common non-type words
                if ret_type.lower() not in ["a", "an", "the", "type", "value"]:
                    return ret_type

        return None

    def _extract_effects(self, prompt: str) -> list[EffectClause]:
        """Extract side effects from prompt."""
        effects = []

        # Look for effect indicators
        effect_keywords = [
            (r"writes?\s+to\s+(.*?)(?:\.|$)", "Writes to {0}"),
            (r"reads?\s+from\s+(.*?)(?:\.|$)", "Reads from {0}"),
            (r"modif(?:ies|y)\s+(.*?)(?:\.|$)", "Modifies {0}"),
            (r"logs?\s+(.*?)(?:\.|$)", "Logs {0}"),
            (r"sends?\s+(.*?)(?:\.|$)", "Sends {0}"),
            (r"calls?\s+(.*?)(?:\.|$)", "Calls {0}"),
        ]

        for pattern, template in effect_keywords:
            matches = re.finditer(pattern, prompt, re.IGNORECASE)
            for match in matches:
                description = template.format(match.group(1).strip())
                effects.append(EffectClause(description=description))

        return effects

    def _extract_assertions(self, prompt: str) -> list[AssertClause]:
        """Extract assertions from prompt."""
        assertions = []

        # Look for assertion indicators
        assertion_patterns = [
            (r"must\s+(?:be\s+)?(.+?)(?:\.|$)", "Must be {0}"),
            (r"should\s+(?:be\s+)?(.+?)(?:\.|$)", "Should be {0}"),
            (r"requires?\s+(?:that\s+)?(.+?)(?:\.|$)", "Requires {0}"),
            (r"ensures?\s+(?:that\s+)?(.+?)(?:\.|$)", "Ensures {0}"),
            (r"guarantees?\s+(?:that\s+)?(.+?)(?:\.|$)", "Guarantees {0}"),
            (r"invariant:\s*(.+?)(?:\.|$)", "{0}"),
        ]

        for pattern, template in assertion_patterns:
            matches = re.finditer(pattern, prompt, re.IGNORECASE)
            for match in matches:
                predicate = template.format(match.group(1).strip())
                assertions.append(AssertClause(predicate=predicate))

        return assertions

    def _detect_ambiguities(
        self,
        ir: IntermediateRepresentation,
        original_prompt: str,
    ) -> list[TypedHole]:
        """Detect ambiguous or under-specified parts of the IR."""
        holes: list[TypedHole] = []

        # Check for missing parameter types
        for param in ir.signature.parameters:
            if not param.type_hint or param.type_hint == "unknown":
                holes.append(
                    TypedHole(
                        identifier=f"{param.name}_type",
                        type_hint="type",
                        description=f"Specify type for parameter '{param.name}'",
                        kind=HoleKind.SIGNATURE,
                    )
                )

        # Check for missing return type
        if not ir.signature.returns:
            holes.append(
                TypedHole(
                    identifier="return_type",
                    type_hint="type",
                    description="Specify return type",
                    kind=HoleKind.SIGNATURE,
                )
            )

        # Check for vague intent
        if len(ir.intent.summary.split()) < 5:
            holes.append(
                TypedHole(
                    identifier="detailed_intent",
                    type_hint="string",
                    description="Provide more detailed description of intent",
                    kind=HoleKind.INTENT,
                )
            )

        # Check for missing assertions (common requirement)
        if len(ir.assertions) == 0:
            # Look for numeric types in parameters
            has_numeric = any(
                param.type_hint in ["int", "float", "number"] for param in ir.signature.parameters
            )
            if has_numeric:
                holes.append(
                    TypedHole(
                        identifier="input_constraints",
                        type_hint="assertion",
                        description="Specify constraints on numeric inputs (e.g., positive, range)",
                        kind=HoleKind.ASSERTION,
                    )
                )

        # Check for unspecified side effects if keywords suggest them
        effect_keywords = ["write", "read", "modify", "log", "send", "call", "save", "load"]
        has_effect_keywords = any(keyword in original_prompt.lower() for keyword in effect_keywords)
        if has_effect_keywords and len(ir.effects) == 0:
            holes.append(
                TypedHole(
                    identifier="side_effects",
                    type_hint="effect",
                    description="Clarify side effects or external interactions",
                    kind=HoleKind.EFFECT,
                )
            )

        return holes

    def _inject_holes(
        self,
        ir: IntermediateRepresentation,
        holes: list[TypedHole],
    ) -> IntermediateRepresentation:
        """Inject typed holes into appropriate IR clauses."""
        # Group holes by kind
        intent_holes = [h for h in holes if h.kind == HoleKind.INTENT]
        sig_holes = [h for h in holes if h.kind == HoleKind.SIGNATURE]
        effect_holes = [h for h in holes if h.kind == HoleKind.EFFECT]
        assertion_holes = [h for h in holes if h.kind == HoleKind.ASSERTION]

        # Update IR with holes
        ir.intent.holes.extend(intent_holes)
        ir.signature.holes.extend(sig_holes)

        # Add effect holes
        if effect_holes:
            for hole in effect_holes:
                ir.effects.append(EffectClause(description=hole.description, holes=[hole]))

        # Add assertion holes
        if assertion_holes:
            for hole in assertion_holes:
                ir.assertions.append(AssertClause(predicate=hole.description, holes=[hole]))

        return ir

    def fill_hole(
        self,
        draft: IRDraft,
        hole_id: str,
        resolution_text: str,
    ) -> IRDraft:
        """
        Apply a hole resolution to create a new draft.

        Args:
            draft: Current IR draft
            hole_id: Identifier of the hole to fill
            resolution_text: User-provided resolution

        Returns:
            New IRDraft with hole resolved and version incremented
        """
        ir = draft.ir

        # Find the hole
        hole = None
        for h in ir.typed_holes():
            if h.identifier == hole_id:
                hole = h
                break

        if not hole:
            # Hole not found, return draft unchanged
            return draft

        # Apply resolution based on hole kind
        new_ir = self._apply_resolution(ir, hole, resolution_text)

        # Create new draft
        remaining_holes = [h.identifier for h in new_ir.typed_holes()]
        new_draft = IRDraft(
            version=draft.version + 1,
            ir=new_ir,
            validation_status="incomplete" if remaining_holes else "pending",
            smt_results=[],
            ambiguities=remaining_holes,
        )

        return new_draft

    def _apply_resolution(
        self,
        ir: IntermediateRepresentation,
        hole: TypedHole,
        resolution: str,
    ) -> IntermediateRepresentation:
        """Apply a resolution to an IR by removing the hole and updating the IR."""
        # We need to work with the existing IR object since it's part of the draft
        # Remove the hole from all clauses
        ir.intent.holes = [h for h in ir.intent.holes if h.identifier != hole.identifier]
        ir.signature.holes = [h for h in ir.signature.holes if h.identifier != hole.identifier]

        for effect in ir.effects:
            effect.holes = [h for h in effect.holes if h.identifier != hole.identifier]

        for assertion in ir.assertions:
            assertion.holes = [h for h in assertion.holes if h.identifier != hole.identifier]

        # Apply the resolution based on hole kind
        if hole.kind == HoleKind.SIGNATURE:
            # Update signature with resolved information
            if hole.identifier == "return_type":
                # Use dataclass replace to update
                ir.signature.returns = resolution
            elif "type" in hole.identifier:
                # Parameter type resolution
                param_name = hole.identifier.replace("_type", "")
                for param in ir.signature.parameters:
                    if param.name == param_name:
                        param.type_hint = resolution

        elif hole.kind == HoleKind.INTENT:
            # Enhance intent with resolution
            if ir.intent.rationale:
                ir.intent.rationale += f"\n{resolution}"
            else:
                ir.intent.rationale = resolution

        elif hole.kind == HoleKind.EFFECT:
            # Add effect with resolution
            ir.effects.append(EffectClause(description=resolution))

        elif hole.kind == HoleKind.ASSERTION:
            # Add assertion with resolution
            ir.assertions.append(AssertClause(predicate=resolution))

        return ir


__all__ = ["PromptToIRTranslator"]
