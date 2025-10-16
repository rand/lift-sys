"""Quick test to verify Anthropic provider setup.

This script tests:
1. Provider initialization with API key
2. Health check
3. Simple text generation

Run: uv run python test_anthropic_setup.py
"""

import asyncio
import os

from lift_sys.providers.anthropic_provider import AnthropicProvider


async def test_setup():
    """Test Anthropic provider setup."""
    print("=" * 60)
    print("Testing Anthropic Provider Setup")
    print("=" * 60)

    # Get API key from environment
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not found in environment")
        print("   Run: export ANTHROPIC_API_KEY=sk-ant-...")
        return False

    print(f"\n✓ API key found (length: {len(api_key)})")

    # Initialize provider
    print("\n→ Initializing AnthropicProvider...")
    provider = AnthropicProvider()

    try:
        await provider.initialize({"api_key": api_key})
        print("✓ Provider initialized")
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return False

    # Check health
    print("\n→ Running health check...")
    try:
        health = await provider.check_health()
        print(f"✓ Health check: {health}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        await provider.aclose()
        return False

    # Simple test generation
    print("\n→ Testing simple text generation...")
    try:
        result = await provider.generate_text(
            "Say 'Hello from LIFT System!' and nothing else.", max_tokens=50
        )
        print("✓ Response received:")
        print(f"  {result[:100]}...")
    except Exception as e:
        print(f"❌ Text generation failed: {e}")
        import traceback

        traceback.print_exc()
        await provider.aclose()
        return False

    # Test with system prompt
    print("\n→ Testing with system prompt...")
    try:
        result = await provider.generate_text(
            "What is 2 + 2?",
            system_prompt="You are a helpful math assistant. Answer concisely.",
            max_tokens=50,
        )
        print("✓ Response received:")
        print(f"  {result[:100]}...")
    except Exception as e:
        print(f"❌ System prompt test failed: {e}")
        await provider.aclose()
        return False

    # Cleanup
    await provider.aclose()
    print("\n✓ Provider closed")

    print("\n" + "=" * 60)
    print("✅ All tests passed! Anthropic provider is ready.")
    print("=" * 60)

    return True


if __name__ == "__main__":
    success = asyncio.run(test_setup())
    exit(0 if success else 1)
