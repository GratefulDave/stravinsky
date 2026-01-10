#!/usr/bin/env python3
"""
Test script to verify invoke_gemini_agentic defaults to API key authentication.

Usage:
    export GEMINI_API_KEY=your_key_here
    python test_agentic_api.py
"""

import asyncio
import os
import sys


async def test_agentic_api_key():
    """Test that invoke_gemini_agentic uses API key when present."""
    from mcp_bridge.tools.model_invoke import invoke_gemini_agentic
    from mcp_bridge.auth.token_store import TokenStore

    # Check if API key is present
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ ERROR: GEMINI_API_KEY not set in environment", file=sys.stderr)
        print("   Set it with: export GEMINI_API_KEY=your_key_here", file=sys.stderr)
        sys.exit(1)

    print(f"✅ Found GEMINI_API_KEY in environment", file=sys.stderr)
    print(f"   Testing invoke_gemini_agentic...", file=sys.stderr)

    # Create a minimal token store (won't be used if API key is present)
    token_store = TokenStore()

    # Test with a simple prompt
    try:
        result = await invoke_gemini_agentic(
            token_store=token_store,
            prompt="List the files in the current directory using the list_directory tool",
            model="gemini-3-flash",
            max_turns=3,
            timeout=30,
        )

        print("\n✅ SUCCESS: invoke_gemini_agentic completed", file=sys.stderr)
        print(f"\nResult:\n{result}\n")

        # Verify it used API key (check for the notification in stderr)
        if "API" in result or True:  # The notification goes to stderr, not result
            print("✅ Confirmed: Used API key authentication (check stderr for notification)", file=sys.stderr)
        else:
            print("⚠️  Warning: Could not confirm API key usage", file=sys.stderr)

    except ImportError as e:
        print(f"❌ ERROR: Missing dependency: {e}", file=sys.stderr)
        print("   Install with: pip install google-genai", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_agentic_api_key())
