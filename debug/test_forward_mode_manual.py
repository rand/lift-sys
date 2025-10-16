"""Manual test of forward mode workflow.

This script tests the complete forward mode workflow:
1. Create session from natural language prompt
2. Check session status for ambiguities
3. Finalize session
4. Generate Python code
5. Validate and execute the generated code
"""

import asyncio

import httpx

API_BASE = "http://localhost:8000"
HEADERS = {"Content-Type": "application/json", "x-demo-user": "test"}


async def test_forward_mode():
    """Test forward mode workflow."""
    print("=" * 70)
    print("MANUAL FORWARD MODE TEST")
    print("=" * 70)

    async with httpx.AsyncClient(timeout=120.0) as client:
        # Step 1: Create session from prompt
        print("\n→ Step 1: Creating session from natural language prompt...")
        prompt = (
            "Create a function called add that takes two integers a and b, and returns their sum"
        )

        create_response = await client.post(
            f"{API_BASE}/api/spec-sessions",
            headers=HEADERS,
            json={"prompt": prompt, "source": "prompt"},
        )

        print(f"   Status: {create_response.status_code}")

        if create_response.status_code != 200:
            print(f"   Error: {create_response.text}")
            return False

        session_data = create_response.json()
        session_id = session_data["session_id"]

        print(f"   ✓ Session created: {session_id}")
        print(f"   Status: {session_data.get('status')}")
        print(f"   Ambiguities: {len(session_data.get('ambiguities', []))}")

        if session_data.get("current_ir"):
            print(f"   IR generated: {len(session_data['current_ir'])} characters")

        # Step 2: Get session details
        print("\n→ Step 2: Getting session details...")

        get_response = await client.get(
            f"{API_BASE}/api/spec-sessions/{session_id}", headers=HEADERS
        )

        if get_response.status_code != 200:
            print(f"   Error: {get_response.text}")
            return False

        session_data = get_response.json()
        print("   ✓ Session retrieved")
        print(f"   Ambiguities: {len(session_data.get('ambiguities', []))}")
        print(f"   Revisions: {session_data.get('revision_count', 0)}")

        # Step 3: Resolve ambiguities
        ambiguities = session_data.get("ambiguities", [])

        if ambiguities:
            print(f"\n→ Step 3: Resolving {len(ambiguities)} ambiguities...")

            # Get assists for resolution
            assists_response = await client.get(
                f"{API_BASE}/api/spec-sessions/{session_id}/assists", headers=HEADERS
            )

            if assists_response.status_code == 200:
                assists = assists_response.json().get("assists", [])
                print(f"   Got {len(assists)} assists")

                # Resolve each ambiguity with assist suggestion
                for assist in assists[:5]:  # Limit to first 5
                    hole_id = assist["hole_id"]
                    suggestion = assist.get("suggestion", "Use default value")

                    resolve_response = await client.post(
                        f"{API_BASE}/api/spec-sessions/{session_id}/holes/{hole_id}/resolve",
                        headers=HEADERS,
                        json={
                            "resolution_text": suggestion,
                            "resolution_type": assist.get("hole_kind", "clarify_intent"),
                        },
                    )

                    if resolve_response.status_code == 200:
                        print(f"   ✓ Resolved hole '{hole_id}'")
                    else:
                        print(f"   ✗ Failed to resolve hole '{hole_id}': {resolve_response.text}")

        # Step 4: Finalize session
        print("\n→ Step 4: Finalizing session...")

        finalize_response = await client.post(
            f"{API_BASE}/api/spec-sessions/{session_id}/finalize", headers=HEADERS
        )

        if finalize_response.status_code != 200:
            print(f"   Error: {finalize_response.text}")
            return False

        print("   ✓ Session finalized")

        # Step 5: Generate code
        print("\n→ Step 5: Generating Python code...")

        generate_response = await client.post(
            f"{API_BASE}/api/spec-sessions/{session_id}/generate",
            headers=HEADERS,
            json={
                "target_language": "python",
                "inject_assertions": True,
                "include_docstrings": True,
                "include_type_hints": True,
            },
        )

        print(f"   Status: {generate_response.status_code}")

        if generate_response.status_code != 200:
            print(f"   Error: {generate_response.text}")
            return False

        code_data = generate_response.json()
        generated_code = code_data.get("source_code", "")

        print(f"   ✓ Code generated: {len(generated_code)} characters")

        # Step 6: Display generated code
        print("\n" + "=" * 70)
        print("GENERATED CODE")
        print("=" * 70)
        print(generated_code)
        print("=" * 70)

        # Step 7: Validate syntax
        print("\n→ Step 6: Validating generated code...")

        if not generated_code:
            print("   ❌ Generated code is empty!")
            return False

        try:
            compile(generated_code, "<generated>", "exec")
            print("   ✓ Syntax check passed")
        except SyntaxError as e:
            print(f"   ❌ Syntax error: {e}")
            return False

        # Step 8: Execute and test
        print("\n→ Step 7: Executing generated code...")

        namespace = {}
        try:
            exec(generated_code, namespace)
            print("   ✓ Code executed successfully")
        except Exception as e:
            print(f"   ❌ Execution error: {e}")
            return False

        # Find the add function
        add_func = namespace.get("add")
        if not add_func:
            # Look for any callable
            for name, obj in namespace.items():
                if callable(obj) and not name.startswith("_"):
                    add_func = obj
                    print(f"   Found function: {name}")
                    break

        if not add_func:
            print("   ❌ No callable function found!")
            return False

        # Test the function
        print("\n→ Step 8: Testing generated function...")

        test_cases = [
            (2, 3, 5),
            (10, 20, 30),
            (-5, 5, 0),
            (0, 0, 0),
        ]

        all_passed = True
        for a, b, expected in test_cases:
            try:
                result = add_func(a, b)
                status = "✓" if result == expected else "❌"
                print(f"   {status} add({a}, {b}) = {result} (expected {expected})")
                if result != expected:
                    all_passed = False
            except Exception as e:
                print(f"   ❌ add({a}, {b}) raised {e}")
                all_passed = False

        if all_passed:
            print("\n" + "=" * 70)
            print("✅ ALL TESTS PASSED!")
            print("=" * 70)
            return True
        else:
            print("\n" + "=" * 70)
            print("❌ SOME TESTS FAILED")
            print("=" * 70)
            return False


if __name__ == "__main__":
    success = asyncio.run(test_forward_mode())
    exit(0 if success else 1)
