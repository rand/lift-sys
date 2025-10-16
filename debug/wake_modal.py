#!/usr/bin/env python3
"""Wake up the Modal endpoint with a simple request."""

import asyncio

import httpx


async def main():
    print("Waking up Modal endpoint (this may take 30-60s for cold start)...")

    async with httpx.AsyncClient(timeout=180.0) as client:
        try:
            response = await client.post(
                "https://rand--generate.modal.run",
                json={
                    "prompt": "Create a simple function",
                    "schema": {"type": "object"},
                    "max_tokens": 50,
                    "temperature": 0.3,
                },
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:500]}")

            if response.status_code == 200:
                print("\n✅ Modal endpoint is awake!")
                return True
            else:
                print("\n❌ Unexpected response")
                return False

        except Exception as e:
            print(f"\n❌ Error: {e}")
            return False


if __name__ == "__main__":
    asyncio.run(main())
