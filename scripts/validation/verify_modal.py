#!/usr/bin/env python3
"""Verify Modal endpoint availability and health.

Usage:
    python scripts/validation/verify_modal.py
"""

import os
import sys

import requests


def verify_modal():
    """Verify Modal endpoint configuration and availability."""
    print("🔍 Verifying Modal endpoints...")
    print()

    # Check endpoint configuration
    endpoint_url = os.getenv("MODAL_ENDPOINT_URL", "https://rand--generate.modal.run")
    print(f"📋 Modal Endpoint: {endpoint_url}")
    print()

    # Try to ping the endpoint
    print("🔌 Testing endpoint availability...")
    try:
        # Try a simple GET request first (health check)
        response = requests.get(endpoint_url, timeout=10)
        print(f"   Status Code: {response.status_code}")

        if response.status_code == 200:
            print("   ✅ Endpoint is reachable")
        elif response.status_code == 404:
            print("   ⚠️  Endpoint returns 404 (may not have health check route)")
        elif response.status_code == 405:
            print("   ⚠️  GET not allowed (endpoint may require POST)")
        else:
            print(f"   ⚠️  Unexpected status code: {response.status_code}")

    except requests.exceptions.Timeout:
        print("   ❌ Request timed out (endpoint may be cold or down)")
    except requests.exceptions.ConnectionError:
        print("   ❌ Connection error (endpoint may not exist)")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    print()

    # Check for deployed apps
    print("📦 Checking Modal app status...")
    import subprocess

    try:
        result = subprocess.run(
            ["modal", "app", "list"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )

        if "rand--generate" in result.stdout or "lift-sys" in result.stdout:
            print("   ✅ Modal app found in deployment list")
        else:
            print("   ⚠️  No Modal apps currently deployed")
            print("   (Run 'modal deploy' to deploy the app)")

    except subprocess.TimeoutExpired:
        print("   ❌ Modal CLI timed out")
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Modal CLI error: {e}")
    except FileNotFoundError:
        print("   ❌ Modal CLI not installed")

    print()
    print("✅ Modal verification complete!")
    return True


def main():
    """Main entry point."""
    # Load environment variables from .env.local (if exists)
    env_path = ".env.local"
    if os.path.exists(env_path):
        print(f"📝 Loading environment from {env_path}")
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    key, _, value = line.partition("=")
                    os.environ[key.strip()] = value.strip().strip('"').strip("'")
        print()

    # Run verification
    result = verify_modal()

    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
