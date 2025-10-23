#!/usr/bin/env python3
"""
Warm-up script for Modal inference endpoint (Python version).

Purpose: Pre-load the 32B model to avoid 7-minute cold starts during testing/benchmarks

Usage:
    python scripts/modal/warmup_modal.py                    # Warm up and wait
    python scripts/modal/warmup_modal.py --async            # Warm up in background
    python scripts/modal/warmup_modal.py --check            # Check if warm

Cold start times:
    - First time: ~7 minutes (model loading + torch compilation)
    - With torch cache: ~5 minutes (model loading, cached compilation)
    - With eager mode (VLLM_EAGER=1): ~5 minutes (model loading, no compilation)

After warm-up, requests complete in 2-10 seconds.
"""

import argparse
import asyncio
import os
import sys
import time

try:
    import httpx
except ImportError:
    print("❌ Error: httpx not installed")
    print("   Install with: uv add httpx")
    sys.exit(1)


# Configuration
WARMUP_URL = os.getenv("MODAL_WARMUP_URL", "https://rand--warmup.modal.run")
TIMEOUT = 600  # 10 minutes


async def warmup_endpoint(async_mode: bool = False, check_only: bool = False) -> dict:
    """
    Warm up the Modal inference endpoint.

    Args:
        async_mode: If True, return immediately after starting request
        check_only: If True, quick check if endpoint is warm (30s timeout)

    Returns:
        Response dict with status, model_loaded, model, ready_for_requests
    """
    timeout = 30 if check_only else TIMEOUT

    print(f"🚀 {'Checking' if check_only else 'Warming up'} Modal inference endpoint...")
    print(f"   Endpoint: {WARMUP_URL}")
    print(f"   Timeout: {timeout}s")
    print()

    if async_mode and not check_only:
        print("⏳ Starting warm-up in background...")
        print("   (Script will continue running until warm-up completes)")
        print()

    start = time.time()

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            if not check_only:
                # Show progress for long-running warm-up
                print("⏳ Sending warm-up request (may take 5-7 minutes on cold start)...")
                sys.stdout.flush()

            response = await client.get(WARMUP_URL)
            elapsed = time.time() - start

            if response.status_code == 200:
                data = response.json()

                if check_only:
                    print(f"✅ Endpoint is warm! (responded in {elapsed:.1f}s)")
                else:
                    print()
                    print("✅ Modal endpoint is warm and ready!")
                    print()
                    print("📊 Warm-up Statistics:")
                    print(f"   HTTP Status: {response.status_code}")
                    print(f"   Response Time: {elapsed:.1f}s")
                    print()
                    print("📄 Response:")
                    print(f"   Status: {data.get('status')}")
                    print(f"   Model: {data.get('model')}")
                    print(f"   Model Loaded: {data.get('model_loaded')}")
                    print(f"   Ready: {data.get('ready_for_requests')}")
                    print()
                    print("✓ Ready for fast inference (2-10s per request)")

                return data
            else:
                print("❌ Warm-up failed!")
                print(f"   HTTP Status: {response.status_code}")
                print(f"   Response: {response.text}")
                sys.exit(1)

    except httpx.TimeoutException:
        elapsed = time.time() - start
        if check_only:
            print(f"⏳ Endpoint is cold (timed out after {elapsed:.1f}s)")
            print("   Run without --check to warm up")
            sys.exit(1)
        else:
            print()
            print(f"❌ Warm-up request timed out after {elapsed:.1f}s")
            print("   This may indicate:")
            print("   - Model is still loading (wait longer)")
            print("   - Network issues")
            print("   - Endpoint is down")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Warm-up request failed: {e}")
        sys.exit(1)


async def main():
    parser = argparse.ArgumentParser(
        description="Warm up Modal inference endpoint to avoid cold starts"
    )
    parser.add_argument(
        "--async", dest="async_mode", action="store_true", help="Run warm-up in background"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Quick check if endpoint is warm (30s timeout)",
    )

    args = parser.parse_args()

    await warmup_endpoint(async_mode=args.async_mode, check_only=args.check)


if __name__ == "__main__":
    asyncio.run(main())
