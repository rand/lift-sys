"""Unit tests for forward mode code synthesizer.

Tests cover:
- Configuration handling
- Prompt generation from IR
- Constraint compilation
- Request payload generation
"""

import pytest

from lift_sys.forward_mode.synthesizer import CodeSynthesizer, SynthesizerConfig
from lift_sys.ir.models import (
    AssertClause,
    IntentClause,
    IntermediateRepresentation,
    Metadata,
    Parameter,
    SigClause,
)


@pytest.mark.unit
class TestCodeSynthesizer:
    """Unit tests for CodeSynthesizer class."""

    def test_synthesizer_config_creation(self):
        """Test SynthesizerConfig creation."""
        config = SynthesizerConfig(
            model_endpoint="http://localhost:8001",
            temperature=0.7,
        )

        assert config.model_endpoint == "http://localhost:8001"
        assert config.temperature == 0.7

    def test_synthesizer_initialization(self):
        """Test CodeSynthesizer initialization."""
        config = SynthesizerConfig(model_endpoint="http://localhost:8001")
        synthesizer = CodeSynthesizer(config)

        assert synthesizer.runtime is not None
        assert synthesizer.config == config
        assert synthesizer.config.model_endpoint == "http://localhost:8001"

    def test_generate_request_payload(self, simple_ir):
        """Test generation of request payload from IR."""
        config = SynthesizerConfig(
            model_endpoint="http://localhost:8001",
            temperature=0.5,
        )
        synthesizer = CodeSynthesizer(config)

        payload = synthesizer.generate(simple_ir)

        assert "endpoint" in payload
        assert "temperature" in payload
        assert "prompt" in payload
        assert payload["endpoint"] == "http://localhost:8001"
        assert payload["temperature"] == 0.5

    def test_prompt_contains_intent(self, simple_ir):
        """Test that generated prompt contains intent information."""
        config = SynthesizerConfig(model_endpoint="http://localhost:8001")
        synthesizer = CodeSynthesizer(config)

        payload = synthesizer.generate(simple_ir)
        prompt = payload["prompt"]

        assert "intent" in prompt
        assert simple_ir.intent.summary in str(prompt["intent"])

    def test_prompt_contains_signature(self, simple_ir):
        """Test that generated prompt contains signature information."""
        config = SynthesizerConfig(model_endpoint="http://localhost:8001")
        synthesizer = CodeSynthesizer(config)

        payload = synthesizer.generate(simple_ir)
        prompt = payload["prompt"]

        assert "signature" in prompt
        sig = prompt["signature"]
        assert sig["name"] == simple_ir.signature.name

    def test_prompt_contains_constraints(self, simple_ir):
        """Test that generated prompt contains constraints from assertions."""
        config = SynthesizerConfig(model_endpoint="http://localhost:8001")
        synthesizer = CodeSynthesizer(config)

        payload = synthesizer.generate(simple_ir)
        prompt = payload["prompt"]

        assert "constraints" in prompt
        constraints = prompt["constraints"]
        assert len(constraints) >= len(simple_ir.assertions)

    def test_compile_constraints_from_assertions(self, simple_ir):
        """Test constraint compilation from assertions."""
        config = SynthesizerConfig(model_endpoint="http://localhost:8001")
        synthesizer = CodeSynthesizer(config)

        constraints = synthesizer.compile_constraints(simple_ir)

        assert len(constraints) >= len(simple_ir.assertions)

        # Should have constraint for each assertion
        for assertion in simple_ir.assertions:
            assert any(assertion.predicate in str(c) for c in constraints)

    def test_generate_with_complex_ir(self, complex_ir):
        """Test generation with complex IR including effects."""
        config = SynthesizerConfig(model_endpoint="http://localhost:8001")
        synthesizer = CodeSynthesizer(config)

        payload = synthesizer.generate(complex_ir)

        assert payload is not None
        assert "prompt" in payload
        prompt = payload["prompt"]

        # Should include effects information if present
        assert "intent" in prompt
        assert "signature" in prompt

    def test_generate_with_no_assertions(self):
        """Test generation with IR that has no assertions."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="test"),
            signature=SigClause(
                name="test",
                parameters=[Parameter(name="x", type_hint="int")],
                returns="int",
            ),
            effects=[],
            assertions=[],
            metadata=Metadata(origin="test"),
        )

        config = SynthesizerConfig(model_endpoint="http://localhost:8001")
        synthesizer = CodeSynthesizer(config)

        payload = synthesizer.generate(ir)

        assert payload is not None
        assert "prompt" in payload
        # Should still generate prompt even without assertions
        assert "constraints" in payload["prompt"]

    def test_temperature_in_payload(self):
        """Test that temperature is correctly set in payload."""
        test_temps = [0.0, 0.3, 0.7, 1.0]

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="test"),
            signature=SigClause(name="test", parameters=[], returns="int"),
            effects=[],
            assertions=[],
            metadata=Metadata(origin="test"),
        )

        for temp in test_temps:
            config = SynthesizerConfig(
                model_endpoint="http://localhost:8001",
                temperature=temp,
            )
            synthesizer = CodeSynthesizer(config)
            payload = synthesizer.generate(ir)

            assert payload["temperature"] == temp

    def test_endpoint_in_payload(self):
        """Test that endpoint is correctly set in payload."""
        endpoints = [
            "http://localhost:8001",
            "http://api.example.com/generate",
            "https://llm.service.io/v1/complete",
        ]

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="test"),
            signature=SigClause(name="test", parameters=[], returns="int"),
            effects=[],
            assertions=[],
            metadata=Metadata(origin="test"),
        )

        for endpoint in endpoints:
            config = SynthesizerConfig(
                model_endpoint=endpoint,
                temperature=0.7,
            )
            synthesizer = CodeSynthesizer(config)
            payload = synthesizer.generate(ir)

            assert payload["endpoint"] == endpoint

    def test_multiple_parameters_in_signature(self):
        """Test handling of multiple parameters in signature."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="test"),
            signature=SigClause(
                name="multi_param",
                parameters=[
                    Parameter(name="a", type_hint="int"),
                    Parameter(name="b", type_hint="str"),
                    Parameter(name="c", type_hint="float"),
                ],
                returns="dict",
            ),
            effects=[],
            assertions=[],
            metadata=Metadata(origin="test"),
        )

        config = SynthesizerConfig(model_endpoint="http://localhost:8001")
        synthesizer = CodeSynthesizer(config)

        payload = synthesizer.generate(ir)
        prompt = payload["prompt"]
        sig = prompt["signature"]

        assert len(sig["parameters"]) == 3
        assert sig["parameters"][0]["name"] == "a"
        assert sig["parameters"][1]["name"] == "b"
        assert sig["parameters"][2]["name"] == "c"

    def test_multiple_assertions_in_constraints(self):
        """Test handling of multiple assertions in constraints."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="test"),
            signature=SigClause(
                name="test",
                parameters=[Parameter(name="x", type_hint="int")],
                returns="int",
            ),
            effects=[],
            assertions=[
                AssertClause(predicate="x > 0"),
                AssertClause(predicate="x < 100"),
                AssertClause(predicate="result >= x"),
            ],
            metadata=Metadata(origin="test"),
        )

        config = SynthesizerConfig(model_endpoint="http://localhost:8001")
        synthesizer = CodeSynthesizer(config)

        constraints = synthesizer.compile_constraints(ir)

        assert len(constraints) >= 3

    def test_config_default_temperature(self):
        """Test that SynthesizerConfig has reasonable default temperature."""
        config = SynthesizerConfig(model_endpoint="http://localhost:8001")

        # Should have some default temperature
        assert hasattr(config, "temperature")
        assert config.temperature is not None
        assert 0.0 <= config.temperature <= 2.0

    def test_generate_is_idempotent(self, simple_ir):
        """Test that multiple generate calls produce consistent results."""
        config = SynthesizerConfig(model_endpoint="http://localhost:8001", temperature=0.0)
        synthesizer = CodeSynthesizer(config)

        payload1 = synthesizer.generate(simple_ir)
        payload2 = synthesizer.generate(simple_ir)

        # Should generate same structure (though content might vary)
        assert payload1["endpoint"] == payload2["endpoint"]
        assert payload1["temperature"] == payload2["temperature"]
        assert "prompt" in payload1 and "prompt" in payload2

    def test_parameter_type_hints_preserved(self):
        """Test that parameter type hints are preserved in prompt."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="test"),
            signature=SigClause(
                name="typed_func",
                parameters=[
                    Parameter(name="x", type_hint="int", description="integer input"),
                    Parameter(name="y", type_hint="list[str]", description="string list"),
                ],
                returns="dict[str, int]",
            ),
            effects=[],
            assertions=[],
            metadata=Metadata(origin="test"),
        )

        config = SynthesizerConfig(model_endpoint="http://localhost:8001")
        synthesizer = CodeSynthesizer(config)

        payload = synthesizer.generate(ir)
        sig = payload["prompt"]["signature"]
        params = sig["parameters"]

        assert params[0]["type_hint"] == "int"
        assert params[1]["type_hint"] == "list[str]"
        assert sig["returns"] == "dict[str, int]"
