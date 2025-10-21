"""
Node-Signature Interface (H6)

Contract between Pydantic AI graph nodes and DSPy signatures.

This module defines the core abstraction for graph nodes that execute DSPy signatures,
enabling type-safe, composable, and optimizable LLM-powered workflows.

Design Principles:
1. Type Safety: Generic over StateT for compile-time checking
2. Async-First: All execution is async for parallel node execution
3. DSPy Integration: Nodes wrap DSPy signatures for declarative LLM tasks
4. Pydantic AI Integration: Nodes conform to Graph expectations

Resolution for Hole H6: NodeSignatureInterface
Status: Implementation
Phase: 1 (Week 1)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    Protocol,
    TypeAlias,
    TypeVar,
    runtime_checkable,
)

import dspy
from pydantic import BaseModel

if TYPE_CHECKING:
    from typing import TypeAlias

# Type variables for generic state and signature
StateT = TypeVar("StateT", bound=BaseModel)
SignatureT = TypeVar("SignatureT")


@dataclass
class RunContext(Generic[StateT]):
    """
    Execution context passed to nodes during graph execution.

    Provides access to:
    - Current graph state
    - Execution metadata (execution_id, user_id, etc.)
    - Provenance tracking
    - Node configuration
    """

    state: StateT
    execution_id: str
    user_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    provenance: list[dict[str, Any]] = field(default_factory=list)

    def add_provenance(self, node_name: str, signature_name: str, **kwargs: Any) -> None:
        """Add provenance entry for this node execution."""
        self.provenance.append(
            {
                "node": node_name,
                "signature": signature_name,
                "execution_id": self.execution_id,
                **kwargs,
            }
        )


class End:
    """
    Sentinel value indicating graph execution should terminate.

    Example:
        async def run(self, ctx: RunContext[MyState]) -> NextNode[MyState]:
            if ctx.state.is_complete:
                return End()
            return NextStepNode()
    """

    pass


# Type alias for next node or termination
# Using string literal for forward reference to avoid circular dependency
NextNode: TypeAlias = "BaseNode[StateT] | End"


@runtime_checkable
class BaseNode(Protocol, Generic[StateT]):
    """
    Protocol defining the interface between graph nodes and DSPy signatures.

    All graph nodes must implement this protocol to:
    1. Declare which DSPy signature they execute
    2. Extract inputs from graph state for the signature
    3. Update state based on signature results
    4. Determine the next node in the graph

    Type Parameters:
        StateT: Pydantic model representing the graph state

    Example:
        class ExtractIntentNode(BaseNode[ForwardModeState]):
            signature = NLToIntent

            def extract_inputs(self, state: ForwardModeState) -> dict:
                return {
                    "prompt": state.prompt,
                    "domain_context": state.context.get("domain", "")
                }

            def update_state(
                self,
                state: ForwardModeState,
                result: dspy.Prediction
            ) -> None:
                state.intent_summary = result.intent_summary
                state.success_criteria = result.success_criteria

            async def run(
                self,
                ctx: RunContext[ForwardModeState]
            ) -> Union[BaseNode[ForwardModeState], End]:
                # Execute signature
                inputs = self.extract_inputs(ctx.state)
                prediction = self.signature(**inputs)

                # Update state
                self.update_state(ctx.state, prediction)

                # Track provenance
                ctx.add_provenance(
                    node_name=self.__class__.__name__,
                    signature_name=self.signature.__name__,
                    inputs=inputs,
                    outputs=prediction.to_dict()
                )

                # Determine next node
                return GenerateSignatureNode()
    """

    # Class-level signature declaration - using Any for DSPy compatibility
    signature: Any  # type[dspy.Signature] but DSPy types not fully typed

    @abstractmethod
    def extract_inputs(self, state: StateT) -> dict[str, Any]:
        """
        Extract inputs from graph state for the DSPy signature.

        Args:
            state: Current graph state

        Returns:
            Dictionary of inputs matching signature's InputFields

        Example:
            def extract_inputs(self, state: MyState) -> dict:
                return {
                    "prompt": state.user_prompt,
                    "context": state.domain_context
                }
        """
        ...

    @abstractmethod
    def update_state(self, state: StateT, result: dspy.Prediction) -> None:
        """
        Update graph state based on signature execution results.

        Args:
            state: Current graph state (mutated in place)
            result: Prediction from DSPy signature execution

        Example:
            def update_state(self, state: MyState, result: dspy.Prediction) -> None:
                state.extracted_intent = result.intent_summary
                state.constraints = result.success_criteria
        """
        ...

    @abstractmethod
    async def run(self, ctx: RunContext[StateT]) -> BaseNode[StateT] | End:
        """
        Execute the node: run signature, update state, determine next node.

        Args:
            ctx: Execution context with state and metadata

        Returns:
            Next node to execute, or End() to terminate

        Standard implementation pattern:
            async def run(self, ctx: RunContext[StateT]) -> Union[BaseNode[StateT], End]:
                # 1. Extract inputs
                inputs = self.extract_inputs(ctx.state)

                # 2. Execute signature
                result = await self._execute_signature(inputs)

                # 3. Update state
                self.update_state(ctx.state, result)

                # 4. Track provenance
                ctx.add_provenance(
                    node_name=self.__class__.__name__,
                    signature_name=self.signature.__name__,
                    confidence=getattr(result, 'confidence', None)
                )

                # 5. Route to next node
                return self._determine_next_node(ctx.state)
        """
        ...


class AbstractBaseNode(ABC, Generic[StateT]):
    """
    Abstract base class providing default implementations for BaseNode protocol.

    Subclass this instead of implementing BaseNode directly for convenience.

    Provides:
    - Default async signature execution with error handling
    - Provenance tracking helper
    - Configurable DSPy module wrapper (ChainOfThought, Predict, ReAct)

    Example:
        class MyNode(AbstractBaseNode[MyState]):
            signature = MySignature

            def extract_inputs(self, state: MyState) -> dict:
                return {"input": state.user_input}

            def update_state(self, state: MyState, result: dspy.Prediction) -> None:
                state.output = result.output

            async def _determine_next_node(
                self,
                state: MyState
            ) -> Union[BaseNode[MyState], End]:
                if state.is_complete:
                    return End()
                return NextNode()
    """

    signature: Any  # type[dspy.Signature] but DSPy not fully typed
    module_type: Any = dspy.Predict  # Default to Predict

    def __init__(self, module_type: Any = None) -> None:
        """
        Initialize node with optional module type override.

        Args:
            module_type: DSPy module to use (Predict, ChainOfThought, ReAct, etc.)
        """
        if module_type is not None:
            self.module_type = module_type
        self._module: Any = self.module_type(self.signature)

    @abstractmethod
    def extract_inputs(self, state: StateT) -> dict[str, Any]:
        """Extract inputs from state for signature."""
        ...

    @abstractmethod
    def update_state(self, state: StateT, result: dspy.Prediction) -> None:
        """Update state with signature results."""
        ...

    @abstractmethod
    async def _determine_next_node(self, state: StateT) -> BaseNode[StateT] | End:
        """Determine which node to execute next based on state."""
        ...

    async def _execute_signature(self, inputs: dict[str, Any]) -> dspy.Prediction:
        """
        Execute the DSPy signature with error handling.

        Args:
            inputs: Dictionary of inputs for signature

        Returns:
            Prediction result from signature execution

        Raises:
            ValueError: If signature execution fails
        """
        try:
            # Execute signature via configured module
            result = await self._module(**inputs)
            return result
        except Exception as e:
            raise ValueError(f"Signature execution failed: {e}") from e

    async def run(self, ctx: RunContext[StateT]) -> BaseNode[StateT] | End:
        """
        Standard run implementation following the protocol.

        Subclasses typically don't need to override this unless they need
        custom execution logic.
        """
        # Extract inputs from state
        inputs = self.extract_inputs(ctx.state)

        # Execute signature
        result = await self._execute_signature(inputs)

        # Update state with results
        self.update_state(ctx.state, result)

        # Track provenance
        ctx.add_provenance(
            node_name=self.__class__.__name__,
            signature_name=self.signature.__name__,
            inputs=inputs,
            outputs=result.to_dict() if hasattr(result, "to_dict") else str(result),
        )

        # Determine next node
        return await self._determine_next_node(ctx.state)


# Example concrete implementations for documentation/testing


class ExampleSignature(dspy.Signature):  # type: ignore[misc]
    """Example signature for testing."""

    prompt: str = dspy.InputField(desc="User input")
    result: str = dspy.OutputField(desc="Processing result")


class ExampleState(BaseModel):
    """Example state for testing."""

    user_input: str = ""
    processed_output: str = ""
    is_complete: bool = False


class ExampleNode(AbstractBaseNode[ExampleState]):
    """Example node implementation for testing and documentation."""

    signature = ExampleSignature

    def extract_inputs(self, state: ExampleState) -> dict[str, Any]:
        return {"prompt": state.user_input}

    def update_state(self, state: ExampleState, result: dspy.Prediction) -> None:
        state.processed_output = result.result
        state.is_complete = True

    async def _determine_next_node(self, state: ExampleState) -> BaseNode[ExampleState] | End:
        return End()
