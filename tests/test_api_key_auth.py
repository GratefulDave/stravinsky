"""
Test script for Gemini API key authentication.

Run this after setting GEMINI_API_KEY in .env to verify API key auth works.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_bridge.tools.model_invoke import invoke_gemini
from mcp_bridge.auth.token_store import TokenStore


async def test_api_key_auth():
    """Test Gemini invocation with API key authentication."""

    # Load .env file
    from dotenv import load_dotenv
    load_dotenv()

    # Check if API key is set
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

    if not api_key:
        print("❌ No GEMINI_API_KEY or GOOGLE_API_KEY found in environment")
        print("   Set one of these in your .env file and try again")
        return False

    print(f"✅ Found API key: {api_key[:20]}...{api_key[-4:]}")
    print("\n🧪 Testing Gemini API key authentication...\n")

    # Create a token store (won't be used for API key auth)
    token_store = TokenStore()

    try:
        # Test simple prompt
        response = await invoke_gemini(
            token_store=token_store,
            prompt="Say 'API key authentication works!' and nothing else.",
            model="gemini-3-flash",
            temperature=0.0,
            max_tokens=50,
        )

        print(f"✅ Response: {response}")

        if "API key" in response or "authentication" in response or "works" in response:
            print("\n✅ SUCCESS: API key authentication is working!")
            return True
        else:
            print("\n⚠️  Got response but content unexpected")
            return False

    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_oauth_fallback():
    """Test that OAuth fallback works when no API key is set."""

    # Temporarily remove API key
    original_gemini = os.environ.pop("GEMINI_API_KEY", None)
    original_google = os.environ.pop("GOOGLE_API_KEY", None)

    print("\n🧪 Testing OAuth fallback (no API key)...\n")

    token_store = TokenStore()

    try:
        # This should fail with "Not authenticated" if no OAuth tokens
        response = await invoke_gemini(
            token_store=token_store,
            prompt="Test",
            model="gemini-3-flash",
        )

        print(f"✅ OAuth response: {response}")
        print("✅ OAuth authentication is working!")
        return True

    except ValueError as e:
        if "Not authenticated" in str(e):
            print("✅ Correctly fell back to OAuth (not authenticated)")
            print("   Run 'stravinsky-auth login gemini' to set up OAuth")
            return True
        else:
            print(f"❌ Unexpected error: {e}")
            return False

    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

    finally:
        # Restore API keys
        if original_gemini:
            os.environ["GEMINI_API_KEY"] = original_gemini
        if original_google:
            os.environ["GOOGLE_API_KEY"] = original_google


async def main():
    """Run all tests."""
    print("=" * 60)
    print("  GEMINI AUTHENTICATION TEST SUITE")
    print("=" * 60)

    # Test 1: API key authentication
    test1_passed = await test_api_key_auth()

    # Test 2: OAuth fallback
    test2_passed = await test_oauth_fallback()

    print("\n" + "=" * 60)
    print("  TEST RESULTS")
    print("=" * 60)
    print(f"  API Key Auth:    {'✅ PASS' if test1_passed else '❌ FAIL'}")
    print(f"  OAuth Fallback:  {'✅ PASS' if test2_passed else '❌ FAIL'}")
    print("=" * 60)

    return test1_passed and test2_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
