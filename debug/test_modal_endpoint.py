"""
Test Modal inference endpoint end-to-end.

This script:
1. Tests health endpoint
2. Sends real IR generation requests
3. Measures cold start and warm latency
4. Validates output against IR schema
5. Documents performance characteristics
"""

import asyncio
import json
import time
from typing import Any

import httpx

from lift_sys.ir.schema import IR_JSON_SCHEMA

# Modal endpoint URLs
HEALTH_URL = "https://rand--health.modal.run"
GENERATE_URL = "https://rand--generate.modal.run"


def validate_ir_against_schema(ir_json: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Validate generated IR against the schema.

    Returns:
        (is_valid, list_of_errors)
    """
    errors = []

    # Check required top-level fields
    if "intent" not in ir_json:
        errors.append("Missing required field: intent")
    elif "summary" not in ir_json["intent"]:
        errors.append("Missing required field: intent.summary")

    if "signature" not in ir_json:
        errors.append("Missing required field: signature")
    else:
        sig = ir_json["signature"]
        if "name" not in sig:
            errors.append("Missing required field: signature.name")
        if "parameters" not in sig:
            errors.append("Missing required field: signature.parameters")

    # Validate signature.name pattern (snake_case)
    if "signature" in ir_json and "name" in ir_json["signature"]:
        import re

        name = ir_json["signature"]["name"]
        if not re.match(r"^[a-z_][a-z0-9_]*$", name):
            errors.append(f"Invalid function name pattern: {name} (must be snake_case)")

    return len(errors) == 0, errors


async def test_health_endpoint():
    """Test that health endpoint is responding."""
    print("\n" + "=" * 70)
    print("TEST 1: Health Endpoint")
    print("=" * 70)

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            start = time.time()
            response = await client.get(HEALTH_URL)
            latency = (time.time() - start) * 1000

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Health check passed ({latency:.0f}ms)")
                print(f"   Model: {data.get('model')}")
                print(f"   GPU: {data.get('gpu')}")
                print(f"   Status: {data.get('status')}")
                return True
            else:
                print(f"❌ Health check failed: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False


async def test_ir_generation(prompt: str, test_name: str, is_warmup: bool = False):
    """
    Test IR generation with a specific prompt.

    Args:
        prompt: Natural language specification
        test_name: Name of the test for reporting
        is_warmup: If True, this is a warmup request (don't report detailed stats)

    Returns:
        (success, latency_ms, result_dict)
    """
    if not is_warmup:
        print("\n" + "=" * 70)
        print(f"TEST: {test_name}")
        print("=" * 70)
        print(f"Prompt: {prompt}")
        print()

    request_body = {
        "prompt": prompt,
        "schema": IR_JSON_SCHEMA,
        "max_tokens": 2048,
        "temperature": 0.3,
        "top_p": 0.95,
    }

    async with httpx.AsyncClient(timeout=180.0) as client:  # 3 min timeout for cold start
        try:
            start = time.time()
            response = await client.post(GENERATE_URL, json=request_body)
            latency = (time.time() - start) * 1000

            if response.status_code != 200:
                print(f"❌ HTTP {response.status_code}: {response.text[:200]}")
                return False, latency, None

            result = response.json()

            # Check for errors in response
            if "error" in result:
                print(f"❌ Generation error: {result['error']}")
                if "raw_output" in result:
                    print(f"   Raw output: {result['raw_output'][:200]}...")
                return False, latency, result

            # Extract IR JSON
            ir_json = result.get("ir_json")
            if not ir_json:
                print("❌ No ir_json in response")
                return False, latency, result

            # Validate against schema
            is_valid, errors = validate_ir_against_schema(ir_json)

            if not is_warmup:
                # Report results
                print(f"⏱️  Latency: {latency:.0f}ms ({latency / 1000:.2f}s)")
                print(f"📊 Tokens: {result.get('tokens_used', 'N/A')}")
                print(f"🏁 Finish reason: {result.get('finish_reason', 'N/A')}")
                print()

                if is_valid:
                    print("✅ VALID IR generated!")
                    print("\nGenerated IR:")
                    print(json.dumps(ir_json, indent=2))
                else:
                    print("❌ INVALID IR - Schema validation errors:")
                    for error in errors:
                        print(f"   - {error}")
                    print("\nGenerated IR (invalid):")
                    print(json.dumps(ir_json, indent=2))

            return is_valid, latency, result

        except Exception as e:
            if not is_warmup:
                print(f"❌ Request failed: {e}")
            return False, 0, None


async def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("MODAL ENDPOINT E2E TESTING")
    print("=" * 70)
    print(f"Health URL: {HEALTH_URL}")
    print(f"Generate URL: {GENERATE_URL}")

    # Test 1: Health check
    health_ok = await test_health_endpoint()
    if not health_ok:
        print("\n❌ Health check failed. Aborting tests.")
        return

    # Test 2: First request (cold start)
    print("\n" + "=" * 70)
    print("TEST 2: Cold Start - Simple Function")
    print("=" * 70)
    print("This will trigger model loading. Expect 30-60s latency.")
    print()

    prompt1 = "Create a function to validate email addresses"
    success1, latency1, result1 = await test_ir_generation(prompt1, "Cold Start Test")

    if success1:
        print("\n✅ Cold start successful!")
        print(f"   Total time: {latency1 / 1000:.2f}s")
    else:
        print("\n❌ Cold start failed")

    # Test 3: Warm request (model already loaded)
    print("\n" + "=" * 70)
    print("TEST 3: Warm Request - Different Function")
    print("=" * 70)
    print("Model should be warm. Expect <5s latency.")
    print()

    prompt2 = "Create a function that calculates the factorial of a number"
    success2, latency2, result2 = await test_ir_generation(prompt2, "Warm Request Test")

    if success2:
        print("\n✅ Warm request successful!")
        print(f"   Latency: {latency2 / 1000:.2f}s")
    else:
        print("\n❌ Warm request failed")

    # Test 4: Another warm request to verify consistency
    print("\n" + "=" * 70)
    print("TEST 4: Second Warm Request - Complex Function")
    print("=" * 70)
    print()

    prompt3 = "Create a function to parse JSON with error handling and validation"
    success3, latency3, result3 = await test_ir_generation(prompt3, "Second Warm Request")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    total_tests = 3
    passed_tests = sum([success1, success2, success3])

    print(f"Tests passed: {passed_tests}/{total_tests}")
    print()
    print("Performance Metrics:")
    print(f"  Cold start latency: {latency1 / 1000:.2f}s")
    print(f"  Warm request 1:     {latency2 / 1000:.2f}s")
    print(f"  Warm request 2:     {latency3 / 1000:.2f}s")
    print()

    if passed_tests == total_tests:
        print("✅ ALL TESTS PASSED!")
        print("\nKey Findings:")
        print("- Modal endpoint is operational")
        print("- Constrained IR generation working")
        print("- Schema validation passing")
        print(f"- Cold start: ~{latency1 / 1000:.0f}s")
        print(f"- Warm requests: ~{(latency2 + latency3) / 2000:.1f}s average")
    else:
        print(f"❌ {total_tests - passed_tests} test(s) failed")
        print("\nNext Steps:")
        print("1. Review error messages above")
        print("2. Check Modal logs: modal app logs lift-sys-inference")
        print("3. Verify schema compatibility")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
