"""Integration tests for XGrammar IR translator."""

import json

import pytest

from lift_sys.forward_mode.xgrammar_translator import XGrammarIRTranslator
from lift_sys.providers.base import BaseProvider


class MockProvider(BaseProvider):
    """Mock provider for testing."""

    def __init__(self, response: str):
        super().__init__(name="mock", capabilities=None)
        self.response = response
        self.calls = []

    async def initialize(self, credentials: dict) -> None:
        pass

    async def generate_text(self, prompt: str, **kwargs) -> str:
        self.calls.append({"prompt": prompt, "kwargs": kwargs})
        return self.response

    async def generate_stream(self, prompt: str, **kwargs):
        yield self.response

    async def generate_structured(self, prompt: str, schema: dict, **kwargs) -> dict:
        raise NotImplementedError

    async def check_health(self) -> bool:
        return True

    @property
    def supports_streaming(self) -> bool:
        return False

    @property
    def supports_structured_output(self) -> bool:
        return False


@pytest.mark.asyncio
async def test_xgrammar_translator_simple_function():
    """Test translating a simple function specification."""
    # Valid IR JSON response
    ir_json = {
        "intent": {
            "summary": "Calculate the area of a circle given its radius",
            "rationale": "Needed for geometry calculations in the application",
        },
        "signature": {
            "name": "calculate_circle_area",
            "parameters": [
                {"name": "radius", "type_hint": "float", "description": "Circle radius"}
            ],
            "returns": "float",
        },
        "effects": [],
        "assertions": [
            {"predicate": "radius > 0", "rationale": "Radius must be positive"},
            {"predicate": "result > 0", "rationale": "Area must be positive"},
        ],
    }

    provider = MockProvider(json.dumps(ir_json))
    translator = XGrammarIRTranslator(provider)

    ir = await translator.translate("Write a function to calculate the area of a circle")

    # Verify IR structure
    assert ir.intent.summary == "Calculate the area of a circle given its radius"
    assert ir.signature.name == "calculate_circle_area"
    assert len(ir.signature.parameters) == 1
    assert ir.signature.parameters[0].name == "radius"
    assert ir.signature.parameters[0].type_hint == "float"
    assert ir.signature.returns == "float"
    assert len(ir.assertions) == 2
    assert ir.assertions[0].predicate == "radius > 0"

    # Verify metadata
    assert ir.metadata.language == "python"
    assert ir.metadata.origin == "xgrammar_generation"

    # Verify provenance
    assert ir.intent.provenance is not None
    assert ir.intent.provenance.source.value == "agent"
    assert ir.intent.provenance.confidence == 0.85


@pytest.mark.asyncio
async def test_xgrammar_translator_with_markdown():
    """Test handling markdown code blocks in response."""
    ir_json = {
        "intent": {"summary": "Validate an email address"},
        "signature": {
            "name": "validate_email",
            "parameters": [{"name": "email", "type_hint": "str"}],
            "returns": "bool",
        },
    }

    response = f"""Here's the IR:

```json
{json.dumps(ir_json, indent=2)}
```

This specification defines an email validation function."""

    provider = MockProvider(response)
    translator = XGrammarIRTranslator(provider)

    ir = await translator.translate("Validate email addresses")

    assert ir.intent.summary == "Validate an email address"
    assert ir.signature.name == "validate_email"


@pytest.mark.asyncio
async def test_xgrammar_translator_with_effects():
    """Test translating function with side effects."""
    ir_json = {
        "intent": {"summary": "Write user data to database"},
        "signature": {
            "name": "save_user",
            "parameters": [
                {"name": "user_id", "type_hint": "int"},
                {"name": "data", "type_hint": "dict[str, Any]"},
            ],
            "returns": "None",
        },
        "effects": [
            {"description": "Writes to database table 'users'"},
            {"description": "May raise DatabaseError if connection fails"},
        ],
        "assertions": [{"predicate": "user_id > 0"}],
    }

    provider = MockProvider(json.dumps(ir_json))
    translator = XGrammarIRTranslator(provider)

    ir = await translator.translate("Save user data to the database")

    assert len(ir.effects) == 2
    assert "database" in ir.effects[0].description.lower()
    assert len(ir.assertions) == 1


@pytest.mark.asyncio
async def test_xgrammar_translator_validation_error():
    """Test handling invalid JSON response."""
    # Invalid: missing required fields
    invalid_json = {"intent": {"summary": "Test"}}  # Missing signature

    provider = MockProvider(json.dumps(invalid_json))
    translator = XGrammarIRTranslator(provider)

    with pytest.raises(ValueError, match="Missing required field: signature"):
        await translator.translate("Test function")


@pytest.mark.asyncio
async def test_xgrammar_translator_retry_on_error():
    """Test retry mechanism on generation failure."""
    # First attempt fails, second succeeds
    valid_ir = {
        "intent": {"summary": "Test function"},
        "signature": {"name": "test_func", "parameters": [], "returns": "None"},
    }

    call_count = [0]

    class RetryProvider(MockProvider):
        async def generate_text(self, prompt: str, **kwargs) -> str:
            call_count[0] += 1
            if call_count[0] == 1:
                return "invalid json {"  # First attempt fails
            return json.dumps(valid_ir)  # Second attempt succeeds

    provider = RetryProvider("")
    translator = XGrammarIRTranslator(provider)

    ir = await translator.translate("Test", max_retries=3)

    assert call_count[0] == 2  # Should have made 2 attempts
    assert ir.signature.name == "test_func"


@pytest.mark.asyncio
async def test_xgrammar_translator_with_typed_holes():
    """Test handling typed holes in IR."""
    ir_json = {
        "intent": {
            "summary": "Process user input",
            "holes": [
                {
                    "identifier": "processing_method",
                    "type_hint": "string",
                    "description": "Clarify how to process the input",
                    "kind": "intent",
                }
            ],
        },
        "signature": {
            "name": "process_input",
            "parameters": [{"name": "input_data", "type_hint": "Any"}],
            "returns": "Any",
            "holes": [
                {
                    "identifier": "return_type",
                    "type_hint": "type",
                    "description": "Specify concrete return type",
                    "kind": "signature",
                }
            ],
        },
    }

    provider = MockProvider(json.dumps(ir_json))
    translator = XGrammarIRTranslator(provider)

    ir = await translator.translate("Process some input")

    assert len(ir.intent.holes) == 1
    assert ir.intent.holes[0].identifier == "processing_method"
    assert len(ir.signature.holes) == 1
    assert ir.signature.holes[0].identifier == "return_type"
