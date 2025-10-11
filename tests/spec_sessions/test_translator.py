"""Unit tests for prompt-to-IR translator."""

from __future__ import annotations

import pytest

from lift_sys.ir.models import HoleKind, IntentClause, Parameter, SigClause
from lift_sys.spec_sessions.models import IRDraft
from lift_sys.spec_sessions.translator import PromptToIRTranslator


@pytest.mark.unit
class TestPromptToIRTranslator:
    """Tests for PromptToIRTranslator."""

    def test_create_translator(self):
        """Test creating a translator instance."""
        translator = PromptToIRTranslator()
        assert translator is not None
        assert translator.parser is not None

    def test_translate_simple_prompt(self):
        """Test translating a simple prompt to IR."""
        translator = PromptToIRTranslator()
        prompt = "Create a function that calculates factorial of n"

        draft = translator.translate(prompt)

        assert draft.version == 1
        assert draft.ir is not None
        assert (
            "factorial" in draft.ir.intent.summary.lower()
            or "factorial" in draft.ir.signature.name.lower()
        )

    def test_extract_function_name(self):
        """Test function name extraction."""
        translator = PromptToIRTranslator()

        # Test explicit function name
        prompt1 = "Create a function called calculate_sum"
        name1 = translator._extract_function_name(prompt1)
        assert name1 == "calculate_sum"

        # Test "implement X"
        prompt2 = "Implement process_data"
        name2 = translator._extract_function_name(prompt2)
        assert name2 == "process_data"

        # Test default when no name found
        prompt3 = "Do something useful"
        name3 = translator._extract_function_name(prompt3)
        assert name3 == "generated_function"

    def test_extract_parameters(self):
        """Test parameter extraction from prompt."""
        translator = PromptToIRTranslator()

        prompt = "Create a function that takes an integer n and accepts a string message"
        parameters = translator._extract_parameters(prompt)

        assert len(parameters) >= 1
        # Should extract at least one parameter
        param_names = {p.name for p in parameters}
        param_types = {p.type_hint for p in parameters}

        # Check we got reasonable extraction
        assert len(param_names) > 0
        assert len(param_types) > 0

    def test_extract_return_type(self):
        """Test return type extraction from prompt."""
        translator = PromptToIRTranslator()

        prompt1 = "Create a function that returns an integer"
        ret1 = translator._extract_return_type(prompt1)
        assert ret1 == "integer"

        prompt2 = "This function produces a string output"
        ret2 = translator._extract_return_type(prompt2)
        assert ret2 == "string"

        prompt3 = "No return type mentioned"
        ret3 = translator._extract_return_type(prompt3)
        assert ret3 is None

    def test_extract_effects(self):
        """Test effect extraction from prompt."""
        translator = PromptToIRTranslator()

        prompt = "This function writes to a file and logs the operation"
        effects = translator._extract_effects(prompt)

        assert len(effects) >= 1
        effect_descriptions = [e.description for e in effects]
        # Should detect file writing and logging
        assert any(
            "write" in desc.lower() or "file" in desc.lower() for desc in effect_descriptions
        )

    def test_extract_assertions(self):
        """Test assertion extraction from prompt."""
        translator = PromptToIRTranslator()

        prompt = "The input must be positive and the output should be non-zero"
        assertions = translator._extract_assertions(prompt)

        assert len(assertions) >= 1
        predicates = [a.predicate for a in assertions]
        # Should detect requirements
        assert any("positive" in pred.lower() for pred in predicates)

    def test_detect_ambiguities_missing_parameter_types(self):
        """Test detecting ambiguities when parameter types are missing."""
        translator = PromptToIRTranslator()

        # Create IR with parameters but no types
        from lift_sys.ir.models import IntermediateRepresentation, Metadata

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Test function"),
            signature=SigClause(
                name="test",
                parameters=[
                    Parameter(name="x", type_hint=""),
                    Parameter(name="y", type_hint="unknown"),
                ],
                returns="int",
            ),
            metadata=Metadata(origin="prompt"),
        )

        holes = translator._detect_ambiguities(ir, "Test function with x and y")

        # Should detect missing parameter types
        hole_ids = {h.identifier for h in holes}
        assert any("type" in hid for hid in hole_ids)

    def test_detect_ambiguities_missing_return_type(self):
        """Test detecting when return type is missing."""
        translator = PromptToIRTranslator()

        from lift_sys.ir.models import IntermediateRepresentation, Metadata

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Calculate something"),
            signature=SigClause(name="calculate", parameters=[], returns=None),
            metadata=Metadata(origin="prompt"),
        )

        holes = translator._detect_ambiguities(ir, "Calculate something")

        # Should detect missing return type
        assert any(h.identifier == "return_type" for h in holes)

    def test_detect_ambiguities_vague_intent(self):
        """Test detecting vague intent descriptions."""
        translator = PromptToIRTranslator()

        from lift_sys.ir.models import IntermediateRepresentation, Metadata

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Do stuff"),  # Very vague
            signature=SigClause(name="func", parameters=[], returns="void"),
            metadata=Metadata(origin="prompt"),
        )

        holes = translator._detect_ambiguities(ir, "Do stuff")

        # Should detect vague intent
        assert any(h.kind == HoleKind.INTENT for h in holes)

    def test_detect_ambiguities_missing_assertions(self):
        """Test detecting missing assertions for numeric inputs."""
        translator = PromptToIRTranslator()

        from lift_sys.ir.models import IntermediateRepresentation, Metadata

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Process number"),
            signature=SigClause(
                name="process",
                parameters=[Parameter(name="value", type_hint="int")],
                returns="int",
            ),
            assertions=[],  # No assertions
            metadata=Metadata(origin="prompt"),
        )

        holes = translator._detect_ambiguities(ir, "Process number")

        # Should detect missing input constraints
        assert any(h.kind == HoleKind.ASSERTION for h in holes)

    def test_detect_ambiguities_missing_effects(self):
        """Test detecting missing effects when keywords suggest them."""
        translator = PromptToIRTranslator()

        from lift_sys.ir.models import IntermediateRepresentation, Metadata

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Write data to database"),
            signature=SigClause(name="save", parameters=[], returns="void"),
            effects=[],  # No effects specified
            metadata=Metadata(origin="prompt"),
        )

        holes = translator._detect_ambiguities(ir, "Write data to database")

        # Should detect missing effects
        assert any(h.kind == HoleKind.EFFECT for h in holes)

    def test_inject_holes_into_ir(self):
        """Test injecting holes into IR clauses."""
        translator = PromptToIRTranslator()

        from lift_sys.ir.models import IntermediateRepresentation, Metadata, TypedHole

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="test", parameters=[], returns="void"),
            metadata=Metadata(origin="prompt"),
        )

        holes = [
            TypedHole(identifier="intent_hole", type_hint="string", kind=HoleKind.INTENT),
            TypedHole(identifier="sig_hole", type_hint="type", kind=HoleKind.SIGNATURE),
            TypedHole(identifier="effect_hole", type_hint="effect", kind=HoleKind.EFFECT),
            TypedHole(identifier="assert_hole", type_hint="assertion", kind=HoleKind.ASSERTION),
        ]

        updated_ir = translator._inject_holes(ir, holes)

        # Check holes were injected
        assert len(updated_ir.intent.holes) == 1
        assert len(updated_ir.signature.holes) == 1
        assert len(updated_ir.effects) >= 1  # Should have added effect with hole
        assert len(updated_ir.assertions) >= 1  # Should have added assertion with hole

    def test_translate_creates_draft_with_ambiguities(self):
        """Test that translate marks ambiguities in the draft."""
        translator = PromptToIRTranslator()

        # Very vague prompt should generate ambiguities
        prompt = "Do something"
        draft = translator.translate(prompt)

        # Should have detected ambiguities
        assert len(draft.ambiguities) > 0
        assert draft.validation_status == "incomplete"

    def test_fill_hole_parameter_type(self):
        """Test filling a parameter type hole."""
        translator = PromptToIRTranslator()

        from lift_sys.ir.models import IntermediateRepresentation, Metadata, TypedHole

        # Create IR with a parameter type hole
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Process data"),
            signature=SigClause(
                name="process",
                parameters=[Parameter(name="value", type_hint="")],
                returns="void",
                holes=[
                    TypedHole(
                        identifier="value_type",
                        type_hint="type",
                        description="Type for value parameter",
                        kind=HoleKind.SIGNATURE,
                    )
                ],
            ),
            metadata=Metadata(origin="prompt"),
        )

        draft = IRDraft(
            version=1, ir=ir, validation_status="incomplete", ambiguities=["value_type"]
        )

        # Fill the hole
        new_draft = translator.fill_hole(draft, "value_type", "int")

        # Check hole was filled
        assert new_draft.version == 2
        assert "value_type" not in new_draft.ambiguities
        # Parameter type should be updated
        assert new_draft.ir.signature.parameters[0].type_hint == "int"

    def test_fill_hole_return_type(self):
        """Test filling a return type hole."""
        translator = PromptToIRTranslator()

        from lift_sys.ir.models import IntermediateRepresentation, Metadata, TypedHole

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Calculate"),
            signature=SigClause(
                name="calculate",
                parameters=[],
                returns=None,
                holes=[
                    TypedHole(
                        identifier="return_type",
                        type_hint="type",
                        kind=HoleKind.SIGNATURE,
                    )
                ],
            ),
            metadata=Metadata(origin="prompt"),
        )

        draft = IRDraft(
            version=1, ir=ir, validation_status="incomplete", ambiguities=["return_type"]
        )

        new_draft = translator.fill_hole(draft, "return_type", "float")

        assert new_draft.ir.signature.returns == "float"
        assert "return_type" not in new_draft.ambiguities

    def test_fill_hole_adds_assertion(self):
        """Test filling an assertion hole."""
        translator = PromptToIRTranslator()

        from lift_sys.ir.models import IntermediateRepresentation, Metadata, TypedHole

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Process value"),
            signature=SigClause(
                name="process",
                parameters=[Parameter(name="x", type_hint="int")],
                returns="int",
            ),
            assertions=[],
            metadata=Metadata(origin="prompt"),
        )

        # Manually add assertion hole
        from lift_sys.ir.models import AssertClause

        assertion_hole = TypedHole(
            identifier="input_constraint",
            type_hint="assertion",
            description="Constraint on input",
            kind=HoleKind.ASSERTION,
        )
        ir.assertions.append(AssertClause(predicate="", holes=[assertion_hole]))

        draft = IRDraft(
            version=1, ir=ir, validation_status="incomplete", ambiguities=["input_constraint"]
        )

        new_draft = translator.fill_hole(draft, "input_constraint", "x > 0")

        # Should have added new assertion
        assert len(new_draft.ir.assertions) >= 1
        # Hole should be removed
        assert "input_constraint" not in new_draft.ambiguities

    def test_fill_nonexistent_hole_returns_unchanged(self):
        """Test that filling a non-existent hole returns draft unchanged."""
        translator = PromptToIRTranslator()

        from lift_sys.ir.models import IntentClause, IntermediateRepresentation, Metadata, SigClause

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="test", parameters=[], returns="void"),
            metadata=Metadata(origin="prompt"),
        )

        draft = IRDraft(version=1, ir=ir, validation_status="valid")

        new_draft = translator.fill_hole(draft, "nonexistent_hole", "some value")

        # Should return unchanged draft
        assert new_draft.version == draft.version

    def test_translate_with_context(self):
        """Test translating with existing IR context."""
        translator = PromptToIRTranslator()

        from lift_sys.ir.models import IntermediateRepresentation, Metadata

        # Existing IR
        context_ir = IntermediateRepresentation(
            intent=IntentClause(summary="Original intent"),
            signature=SigClause(name="original", parameters=[], returns="void"),
            metadata=Metadata(origin="prompt"),
        )

        prompt = "Add logging functionality"
        draft = translator.translate(prompt, context=context_ir)

        # Should use context as base
        assert draft.ir.signature.name == "original"
