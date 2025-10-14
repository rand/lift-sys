"""Semantically-enhanced code generation with context awareness.

This module extends XGrammarCodeGenerator to include semantic context
from the codebase, demonstrating the quality improvement that LSP-based
systems like ChatLSP would provide.
"""

from __future__ import annotations

from ..ir.models import IntermediateRepresentation
from ..providers.base import BaseProvider
from .generator import CodeGeneratorConfig, GeneratedCode
from .semantic_context import SemanticContextProvider
from .xgrammar_generator import XGrammarCodeGenerator


class SemanticCodeGenerator(XGrammarCodeGenerator):
    """
    Generates code with semantic context awareness.

    Extends XGrammarCodeGenerator to include codebase context (types,
    imports, conventions) in the generation prompt, improving quality.
    """

    def __init__(
        self,
        provider: BaseProvider,
        config: CodeGeneratorConfig | None = None,
        language: str = "python",
    ):
        """
        Initialize with provider, config, and language.

        Args:
            provider: LLM provider for generation
            config: Code generation configuration
            language: Target language (python, typescript, rust, go)
        """
        super().__init__(provider, config)
        self.language = language
        self.context_provider = SemanticContextProvider(language=language)

    async def generate(
        self,
        ir: IntermediateRepresentation,
        max_retries: int = 3,
    ) -> GeneratedCode:
        """
        Generate code with semantic context enhancement.

        This method overrides XGrammarCodeGenerator.generate() to inject
        semantic context into the implementation generation prompt.

        Args:
            ir: Intermediate representation to translate
            max_retries: Number of retries if generation fails

        Returns:
            GeneratedCode with semantically-enhanced implementation
        """
        # Get semantic context based on intent
        semantic_context = self.context_provider.get_context_for_intent(ir.intent.summary)

        # Store context for use in _generate_implementation
        self._current_semantic_context = semantic_context

        # Call parent generate method (which will use our overridden _generate_implementation)
        result = await super().generate(ir, max_retries)

        # Add semantic context to metadata
        result.metadata["semantic_context_used"] = True
        result.metadata["available_types"] = len(semantic_context.available_types)
        result.metadata["available_functions"] = len(semantic_context.available_functions)

        return result

    async def _generate_implementation(
        self,
        ir: IntermediateRepresentation,
        structure: dict,
        attempt: int,
    ) -> dict:
        """
        Generate implementation with semantic context.

        Overrides parent method to include codebase context in the prompt.

        Args:
            ir: IR to implement
            structure: Structural elements
            attempt: Current attempt number

        Returns:
            Implementation JSON
        """
        # Build enhanced prompt with semantic context
        from .code_schema import get_prompt_for_code_generation

        constraints = []
        for assertion in ir.assertions:
            constraint_text = assertion.predicate
            if assertion.rationale:
                constraint_text += f" ({assertion.rationale})"
            constraints.append(constraint_text)

        # Base prompt
        base_prompt = get_prompt_for_code_generation(
            ir_summary=ir.intent.summary,
            signature=structure["signature"],
            constraints=constraints,
        )

        # Add semantic context
        context_text = self._current_semantic_context.to_prompt_context()

        enhanced_prompt = f"""{base_prompt}

Codebase Context:
-----------------
{context_text}

Use the available types, functions, and patterns from the codebase context
to generate high-quality, idiomatic code that fits naturally with the existing
codebase.

Generate the implementation as valid JSON:"""

        # Add attempt-specific feedback
        if attempt > 0:
            enhanced_prompt += f"\n\nPrevious attempt {attempt} failed. Please ensure valid JSON output with all required fields."

        # Generate using LLM with enhanced prompt
        response = await self.provider.generate_text(
            prompt=enhanced_prompt,
            max_tokens=2000,
            temperature=0.3,
        )

        # Extract and return JSON
        return self._extract_json(response)


__all__ = ["SemanticCodeGenerator"]
