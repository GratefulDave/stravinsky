#!/usr/bin/env python3
"""Verify GEMINI_API_KEY is properly configured."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    # Load from ~/.stravinsky/.env (recommended location)
    stravinsky_env = Path.home() / ".stravinsky" / ".env"
    if stravinsky_env.exists():
        load_dotenv(stravinsky_env, override=True)
        print(f"✅ Loaded from: {stravinsky_env}")

    # Check for API key
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

    if key:
        print(f"✅ GEMINI_API_KEY found: {key[:20]}...{key[-4:]}")
        print(f"✅ Key length: {len(key)} characters")

        # Verify it starts with expected prefix
        if key.startswith("AIza"):
            print("✅ Key format valid (starts with 'AIza')")
        else:
            print("⚠️  Warning: Key doesn't start with 'AIza' (expected for Google API keys)")
    else:
        print("❌ GEMINI_API_KEY not found!")
        print("\nTo fix:")
        print("1. Create file: ~/.stravinsky/.env")
        print("2. Add line: GEMINI_API_KEY=your_key_here")
        print("3. Get key from: https://aistudio.google.com/app/apikey")
        print("\n⚠️  CRITICAL: Variable name is GEMINI_API_KEY (NOT GEMINI_API_TOKEN)")

except ImportError:
    print("❌ python-dotenv not installed")
    print("Run: uv pip install python-dotenv")
