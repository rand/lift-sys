"""
Test Modal IR generation endpoint with a simple request.
"""

import json
import time

import requests

# Modal dev endpoint (from modal serve)
MODAL_ENDPOINT = "https://rand--generate-dev.modal.run"

# Simple IR JSON schema (matching lift_sys IR format)
IR_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "rationale": {"type": "string"},
            },
            "required": ["summary"],
        },
        "signature": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "pattern": "^[a-z_][a-z0-9_]*$"},
                "parameters": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "type_hint": {"type": "string"},
                        },
                        "required": ["name", "type_hint"],
                    },
                },
                "returns": {"type": "string"},
            },
            "required": ["name", "parameters"],
        },
    },
    "required": ["intent", "signature"],
}

# Simple test prompt
TEST_PROMPT = "Create a function called add that takes two integers a and b, and returns their sum as an integer"

print("=" * 80)
print("Testing Modal IR Generation (Dev Endpoint)")
print("=" * 80)
print(f"\nEndpoint: {MODAL_ENDPOINT}")
print(f"\nPrompt: {TEST_PROMPT}")
print("\nSending request...")

# Prepare request
payload = {
    "prompt": TEST_PROMPT,
    "schema": IR_JSON_SCHEMA,
    "max_tokens": 1024,
    "temperature": 0.3,
}

# Send request with timing
start_time = time.time()
try:
    response = requests.post(
        MODAL_ENDPOINT,
        json=payload,
        timeout=180,  # 3 minute timeout for cold start
    )
    elapsed_time = time.time() - start_time

    print(f"\nResponse Status: {response.status_code}")
    print(f"Response Time: {elapsed_time:.2f}s")

    if response.status_code == 200:
        result = response.json()
        print("\n" + "=" * 80)
        print("RESULT:")
        print("=" * 80)
        print(json.dumps(result, indent=2))

        if result.get("ir_json"):
            print("\n✅ Success! Generated valid IR:")
            print(json.dumps(result["ir_json"], indent=2))
            print(f"\nTokens used: {result.get('tokens_used', 'N/A')}")
            print(f"Generation time: {result.get('generation_time_ms', 'N/A')}ms")
            print(f"Finish reason: {result.get('finish_reason', 'N/A')}")
        else:
            print(f"\n❌ Failed: {result.get('error', 'No IR generated')}")
    else:
        print(f"\n❌ HTTP Error: {response.status_code}")
        print(f"Response: {response.text}")

except requests.exceptions.Timeout:
    elapsed_time = time.time() - start_time
    print(f"\n❌ Request timed out after {elapsed_time:.2f}s")
except requests.exceptions.RequestException as e:
    elapsed_time = time.time() - start_time
    print(f"\n❌ Request failed after {elapsed_time:.2f}s: {e}")
except Exception as e:
    elapsed_time = time.time() - start_time
    print(f"\n❌ Unexpected error after {elapsed_time:.2f}s: {e}")

print("\n" + "=" * 80)
print("Test Complete")
print("=" * 80)
