"""
ProviderAdapter (H1): Integration layer between DSPy and Modal/SGLang providers

This module adapts lift-sys BaseProvider implementations (ModalProvider, etc.) to work
with DSPy's LM interface, enabling DSPy signatures to execute on Modal.com GPU workers
with XGrammar constraint support.

Design Principles:
1. Async-First: DSPy signatures execute async via nodes
2. XGrammar Preservation: Pass JSON schemas through to Modal/SGLang
3. Performance: Minimal overhead, target <10% latency increase
4. Resource Tracking: Integrate with ResourceLimits for token/call counting

Resolution for Hole H1: ProviderAdapter
Status: Implementation
Phase: 2 (Week 2)

Constraints from H6 (NodeSignatureInterface):
- MUST support async execution (nodes call provider via async run())
- MUST return dspy.Prediction objects
- MUST support ChainOfThought, Predict, ReAct modules

Constraints from H14 (ResourceLimits):
- MUST track token usage via ResourceUsage.add_tokens()
- MUST track LLM call counts via ResourceUsage.add_llm_call()
- SHOULD check limits before expensive calls
"""

from __future__ import annotations

import json
from typing import Any

import dspy
from pydantic import BaseModel, Field

from lift_sys.providers.base import BaseProvider


class ProviderConfig(BaseModel):
    """Configuration for ProviderAdapter behavior."""

    max_tokens: int = Field(default=2048, description="Maximum tokens to generate")
    temperature: float = Field(
        default=0.3, description="Sampling temperature (0.0 = deterministic)"
    )
    top_p: float = Field(default=0.95, description="Nucleus sampling parameter")
    use_xgrammar: bool = Field(
        default=True,
        description="Enable XGrammar constraint-based generation (requires structured_output support)",
    )
    track_resources: bool = Field(
        default=True, description="Track token usage and LLM call counts for ResourceLimits"
    )


class ProviderAdapter:
    """
    Adapter between DSPy and lift-sys BaseProvider implementations.

    Enables DSPy signatures to execute on Modal.com GPU workers with XGrammar
    constraint support, while maintaining resource tracking and async execution.

    Usage:
        # Initialize with ModalProvider
        modal_provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
        await modal_provider.initialize({})

        adapter = ProviderAdapter(modal_provider)

        # Configure DSPy to use this adapter
        dspy.settings.configure(lm=adapter)

        # Execute signature
        signature = dspy.ChainOfThought(PromptToIR)
        result = await signature(prompt="Create a function to add two numbers")
        # result is dspy.Prediction with fields from signature

    Attributes:
        provider: Underlying BaseProvider (ModalProvider, etc.)
        config: Configuration for generation behavior
        supports_xgrammar: Whether provider supports XGrammar constraints

    Resource Tracking:
        If config.track_resources is enabled and a ResourceUsage tracker is set,
        the adapter will:
        - Call add_llm_call() for each generation request
        - Call add_tokens() with estimated token counts
        - Check ResourceEnforcer before expensive calls (future enhancement)
    """

    def __init__(self, provider: BaseProvider, config: ProviderConfig | None = None) -> None:
        """
        Initialize ProviderAdapter.

        Args:
            provider: BaseProvider instance (ModalProvider, AnthropicProvider, etc.)
            config: Optional configuration override (defaults to ProviderConfig())

        Raises:
            ValueError: If provider does not support required capabilities
        """
        self.provider = provider
        self.config = config or ProviderConfig()

        # Verify provider capabilities
        if self.config.use_xgrammar and not provider.capabilities.structured_output:
            raise ValueError(
                f"Provider '{provider.name}' does not support structured output "
                "required for XGrammar constraints. Set use_xgrammar=False or use "
                "a different provider."
            )

        # Resource tracking (optional, set via set_resource_tracker())
        self._resource_usage: Any | None = None  # ResourceUsage instance

    def set_resource_tracker(self, resource_usage: Any) -> None:
        """
        Set ResourceUsage tracker for token and call counting.

        Args:
            resource_usage: ResourceUsage instance from resource_limits.py
        """
        self._resource_usage = resource_usage

    @property
    def supports_xgrammar(self) -> bool:
        """Whether this provider supports XGrammar constraint-based generation."""
        return self.config.use_xgrammar and self.provider.capabilities.structured_output

    async def __call__(self, prompt: str, **kwargs: Any) -> dspy.Prediction:
        """
        Execute LLM call and return DSPy Prediction.

        This is the main interface method called by DSPy modules (Predict, ChainOfThought, etc.).

        Args:
            prompt: Formatted prompt from DSPy (includes signature fields, examples, etc.)
            **kwargs: Additional parameters
                - schema: Optional JSON schema for XGrammar constraints
                - max_tokens: Override default max_tokens
                - temperature: Override default temperature
                - signature: DSPy signature object (used to extract output fields)

        Returns:
            dspy.Prediction with fields extracted from LLM response

        Raises:
            ValueError: If LLM generation fails
            RuntimeError: If provider not initialized
        """
        # Track LLM call if resource tracking enabled
        if self.config.track_resources and self._resource_usage is not None:
            self._resource_usage.add_llm_call()

        # Extract parameters
        max_tokens = kwargs.get("max_tokens", self.config.max_tokens)
        temperature = kwargs.get("temperature", self.config.temperature)
        schema = kwargs.get("schema")
        signature = kwargs.get("signature")  # DSPy signature object

        try:
            # If XGrammar enabled and schema provided, use structured generation
            if self.supports_xgrammar and schema is not None:
                response_dict = await self.provider.generate_structured(
                    prompt=prompt,
                    schema=schema,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=self.config.top_p,
                )

                # Track tokens (estimate from structured output)
                if self.config.track_resources and self._resource_usage is not None:
                    estimated_tokens = self._estimate_tokens(response_dict)
                    self._resource_usage.add_tokens(estimated_tokens)

                # Convert dict response to dspy.Prediction
                return self._dict_to_prediction(response_dict, signature)

            # Otherwise, use text generation
            else:
                response_text = await self.provider.generate_text(
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=self.config.top_p,
                )

                # Track tokens (estimate from text length)
                if self.config.track_resources and self._resource_usage is not None:
                    estimated_tokens = len(response_text.split()) * 1.3  # Rough estimate
                    self._resource_usage.add_tokens(int(estimated_tokens))

                # Parse response and convert to dspy.Prediction
                return self._text_to_prediction(response_text, signature)

        except Exception as e:
            raise ValueError(f"Provider call failed: {e}") from e

    def _dict_to_prediction(self, response: dict, signature: Any = None) -> dspy.Prediction:
        """
        Convert structured dict response to dspy.Prediction.

        Args:
            response: Dict from provider's generate_structured()
            signature: Optional DSPy signature for field validation

        Returns:
            dspy.Prediction with fields from response
        """
        # DSPy Prediction is essentially a dict with attribute access
        # If signature provided, validate fields match output fields
        if signature is not None:
            output_fields = {field.input_variable for field in signature.output_fields}
            # Filter response to only include expected fields
            filtered_response = {k: v for k, v in response.items() if k in output_fields}
            return dspy.Prediction(**filtered_response)
        else:
            # No signature, use all fields
            return dspy.Prediction(**response)

    def _text_to_prediction(self, response: str, signature: Any = None) -> dspy.Prediction:
        """
        Convert text response to dspy.Prediction.

        Attempts to parse JSON from response. If successful, extracts fields.
        Otherwise, returns response as single "output" field.

        Args:
            response: Text from provider's generate_text()
            signature: Optional DSPy signature for field extraction

        Returns:
            dspy.Prediction with parsed fields
        """
        # Try to parse as JSON first
        try:
            parsed = json.loads(response)
            if isinstance(parsed, dict):
                return self._dict_to_prediction(parsed, signature)
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback: single "output" field
        # DSPy typically expects output fields to match signature
        if signature is not None and hasattr(signature, "output_fields"):
            # Use first output field name
            output_fields = list(signature.output_fields)
            if output_fields:
                field_name = output_fields[0].input_variable
                return dspy.Prediction(**{field_name: response})

        # Final fallback: generic "output" field
        return dspy.Prediction(output=response)

    def _estimate_tokens(self, response: dict) -> int:
        """
        Estimate token count from structured dict response.

        Uses rough heuristic: JSON length / 4 (average chars per token).

        Args:
            response: Dict response from structured generation

        Returns:
            Estimated token count
        """
        json_str = json.dumps(response)
        return len(json_str) // 4

    async def inspect_history(self, n: int = 1) -> list[dict[str, Any]]:
        """
        Inspect recent LLM call history.

        DSPy's LM interface optionally supports history inspection for debugging.
        This is a minimal implementation that could be extended with call logging.

        Args:
            n: Number of recent calls to return

        Returns:
            List of call records (currently empty, could be enhanced)
        """
        # TODO: Implement call history tracking if needed for debugging
        # For now, return empty list (DSPy doesn't require this)
        return []


__all__ = ["ProviderAdapter", "ProviderConfig"]
