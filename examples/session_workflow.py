"""Example: Complete prompt-to-IR refinement workflow using Python SDK.

This example demonstrates the full session lifecycle:
1. Create a session from a natural language prompt
2. Review ambiguities (typed holes)
3. Get assist suggestions
4. Resolve holes iteratively
5. Finalize the session to get validated IR

Usage:
    uv run python examples/session_workflow.py
"""
from __future__ import annotations

import sys
from typing import List

from lift_sys.client import SessionClient, PromptSession


def print_session_status(session: PromptSession) -> None:
    """Print current session status."""
    print(f"\n{'='*60}")
    print(f"Session: {session.session_id[:12]}...")
    print(f"Status: {session.status}")
    print(f"Draft Version: {session.current_draft.version if session.current_draft else 0}")
    print(f"Validation: {session.current_draft.validation_status if session.current_draft else 'N/A'}")
    print(f"Unresolved Holes: {len(session.ambiguities)}")
    print(f"{'='*60}\n")


def main() -> int:
    """Run the example workflow."""
    # Initialize client
    print("Initializing session client...")
    client = SessionClient(base_url="http://localhost:8000")

    # Step 1: Create session from prompt
    print("\n[Step 1] Creating session from natural language prompt...")
    prompt = "A function that takes two integers and returns their sum"
    print(f"Prompt: \"{prompt}\"")

    try:
        session = client.create_session(
            prompt=prompt,
            metadata={"example": "session_workflow", "language": "python"}
        )
        print(f"✓ Session created: {session.session_id}")
        print_session_status(session)
    except Exception as e:
        print(f"✗ Error creating session: {e}")
        return 1

    # Step 2: Review ambiguities
    print("[Step 2] Reviewing ambiguities...")
    if session.ambiguities:
        print(f"Found {len(session.ambiguities)} holes to resolve:")
        for i, hole_id in enumerate(session.ambiguities, 1):
            print(f"  {i}. {hole_id}")
    else:
        print("✓ No ambiguities found!")
        return 0

    # Step 3: Get assist suggestions
    print("\n[Step 3] Getting assist suggestions...")
    try:
        assists = client.get_assists(session.session_id)
        print(f"✓ Retrieved {len(assists.assists)} assists")

        for assist in assists.assists:
            print(f"\n  Hole: {assist.hole_id}")
            print(f"  Context: {assist.context}")
            if assist.suggestions:
                print(f"  Suggestions: {', '.join(assist.suggestions)}")
    except Exception as e:
        print(f"✗ Error getting assists: {e}")

    # Step 4: Resolve holes interactively
    print("\n[Step 4] Resolving holes...")

    # Example resolutions (in a real scenario, these might come from user input)
    resolutions = {
        "hole_function_name": "add",
        "hole_param1_name": "a",
        "hole_param1_type": "int",
        "hole_param2_name": "b",
        "hole_param2_type": "int",
        "hole_return_type": "int",
    }

    for hole_id in list(session.ambiguities):  # Create copy to avoid modification during iteration
        if hole_id in resolutions:
            resolution = resolutions[hole_id]
            print(f"\n  Resolving '{hole_id}' with '{resolution}'...")

            try:
                session = client.resolve_hole(
                    session_id=session.session_id,
                    hole_id=hole_id,
                    resolution_text=resolution,
                    resolution_type="clarify_intent"
                )
                print(f"  ✓ Resolved ({len(session.ambiguities)} remaining)")
            except Exception as e:
                print(f"  ✗ Error resolving hole: {e}")
                continue

    print_session_status(session)

    # Step 5: Finalize if all holes resolved
    if session.ambiguities:
        print(f"[Step 5] Cannot finalize: {len(session.ambiguities)} holes remaining")
        print("\nRemaining holes:")
        for hole_id in session.ambiguities:
            print(f"  - {hole_id}")
        return 1
    else:
        print("[Step 5] Finalizing session...")
        try:
            result = client.finalize_session(session.session_id)
            print("✓ Session finalized successfully!")
            print("\nFinal IR:")
            print("-" * 60)

            # Pretty print the IR
            ir = result.ir
            print(f"\nIntent: {ir.get('intent', {}).get('summary', 'N/A')}")

            sig = ir.get('signature', {})
            params = sig.get('parameters', [])
            param_str = ', '.join([f"{p['name']}: {p['type_hint']}" for p in params])
            returns = sig.get('returns', 'void')
            print(f"Signature: {sig.get('name', 'unknown')}({param_str}) -> {returns}")

            effects = ir.get('effects', [])
            if effects:
                print(f"\nEffects:")
                for effect in effects:
                    print(f"  - {effect.get('description', 'N/A')}")

            assertions = ir.get('assertions', [])
            if assertions:
                print(f"\nAssertions:")
                for assertion in assertions:
                    pred = assertion.get('predicate', 'N/A')
                    rat = assertion.get('rationale')
                    print(f"  - {pred}")
                    if rat:
                        print(f"    ({rat})")

            print("-" * 60)
            print("\n✓ Workflow complete!")
            return 0

        except Exception as e:
            print(f"✗ Error finalizing session: {e}")
            return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nWorkflow interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        sys.exit(1)
