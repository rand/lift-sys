"""Test FlashInfer installation by making a generation request."""

import json

import requests

ENDPOINT = "https://rand--generate-dev.modal.run"

# Simple test schema
test_schema = {
    "type": "object",
    "properties": {
        "intent": {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
            },
            "required": ["summary"],
        },
        "signature": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "pattern": "^[a-z_][a-z0-9_]*$"},
                "parameters": {"type": "array"},
                "returns": {"type": "string"},
            },
            "required": ["name", "parameters"],
        },
    },
    "required": ["intent", "signature"],
}

test_prompt = "Create a function called add that takes two integers a and b, and returns their sum"

print(f"Testing with prompt: {test_prompt}\n")
print("Calling Modal generate endpoint...")

response = requests.post(
    ENDPOINT,
    json={
        "prompt": test_prompt,
        "schema": test_schema,
        "max_tokens": 1024,
        "temperature": 0.3,
    },
)

result = response.json()
print("\n" + "=" * 70)
print("RESULT:")
print("=" * 70)
print(json.dumps(result, indent=2))

if result.get("ir_json"):
    print("\n✅ Success! Generated valid IR")
else:
    print(f"\n❌ Failed: {result.get('error')}")
