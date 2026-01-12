"""
Test: FileWatcher initialization without semantic index

This test verifies the fix for the silent failure bug where start_file_watcher()
would fail silently if semantic_index() was not called first.

Expected Behavior:
1. Calling start_file_watcher() without an index should raise ValueError
2. After creating an index with semantic_index(), start_file_watcher() should work

Test Scenarios:
- Test 1: No index exists -> ValueError raised
- Test 2: Index created -> start_file_watcher() succeeds
- Test 3: Verify error message is helpful
"""

import asyncio
import os
import shutil
import tempfile
import time
from pathlib import Path


def setup_test_project():
    """Create a temporary test project directory with sample Python files."""
    test_dir = tempfile.mkdtemp(prefix="test_filewatcher_")

    # Create sample Python files
    files = {
        "main.py": """
def main():
    print("Hello, World!")
    
if __name__ == "__main__":
    main()
""",
        "utils.py": """
def add(a, b):
    return a + b

def multiply(a, b):
    return a * b
""",
        "config.py": """
DEBUG = True
API_URL = "https://api.example.com"
""",
    }

    for filename, content in files.items():
        filepath = Path(test_dir) / filename
        filepath.write_text(content)

    return test_dir


def cleanup_test_project(test_dir):
    """Remove test project and all ChromaDB files."""
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)

    # Clean up ChromaDB directory
    chroma_dir = Path(test_dir).parent / "chroma_data"
    if chroma_dir.exists():
        shutil.rmtree(chroma_dir)


def test_start_watcher_without_index():
    """
    Test 1: Starting file watcher without index should raise ValueError

    This tests the fix for the silent failure bug.
    """
    print("\n" + "=" * 70)
    print("TEST 1: Start File Watcher Without Index")
    print("=" * 70)

    test_dir = setup_test_project()
    print(f"Created test project: {test_dir}")

    try:
        # Import the semantic search module
        try:
            from mcp_bridge.tools.semantic_search import (
                start_file_watcher,
                stop_file_watcher,
                semantic_index,
                semantic_stats,
            )
        except ImportError as e:
            print(f"⚠️  WARNING: Cannot import semantic_search module: {e}")
            print("This test requires the mcp_bridge package to be installed.")
            print("Skipping test.")
            cleanup_test_project(test_dir)
            import pytest

            pytest.skip(f"Cannot import semantic_search module: {e}")

        print("\n1. Attempting to start file watcher WITHOUT creating index first...")
        print(f"   Project path: {test_dir}")

        # This should raise ValueError
        error_raised = False
        error_message = ""

        try:
            watcher = start_file_watcher(test_dir, provider="ollama", debounce_seconds=1.0)
            print("   ❌ FAIL: No error was raised!")
            print("   Expected: ValueError")
            print("   Got: No exception (silent failure)")

        except ValueError as e:
            error_raised = True
            error_message = str(e)
            print(f"   ✅ PASS: ValueError raised as expected")
            print(f"   Error message: {error_message}")

        except Exception as e:
            print(f"   ❌ FAIL: Wrong exception type")
            print(f"   Expected: ValueError")
            print(f"   Got: {type(e).__name__}: {e}")

        # Verify error message is helpful
        if error_raised:
            print("\n2. Verifying error message is helpful...")
            expected_keywords = ["semantic_index", "index", "first", "before"]
            found_keywords = [kw for kw in expected_keywords if kw.lower() in error_message.lower()]

            if len(found_keywords) >= 2:
                print(f"   ✅ PASS: Error message contains helpful keywords: {found_keywords}")
            else:
                print(f"   ⚠️  WARNING: Error message might not be clear enough")
                print(f"   Found keywords: {found_keywords}")
                print(f"   Expected at least 2 of: {expected_keywords}")

        cleanup_test_project(test_dir)

        if error_raised:
            print("\n✅ TEST 1 PASSED: ValueError raised when starting watcher without index")
            assert True  # Explicit pass for pytest
        else:
            print("\n❌ TEST 1 FAILED: No ValueError raised")
            assert False, "No ValueError raised when starting watcher without index"

    except Exception as e:
        print(f"\n❌ TEST 1 FAILED with unexpected error: {e}")
        import traceback

        traceback.print_exc()
        cleanup_test_project(test_dir)
        assert False, f"Unexpected error: {e}"


def test_start_watcher_with_index():
    """
    Test 2: Starting file watcher AFTER creating index should work

    This verifies the normal workflow works correctly.
    """
    print("\n" + "=" * 70)
    print("TEST 2: Start File Watcher With Index")
    print("=" * 70)

    test_dir = setup_test_project()
    print(f"Created test project: {test_dir}")

    try:
        # Import the semantic search module
        try:
            from mcp_bridge.tools.semantic_search import (
                start_file_watcher,
                stop_file_watcher,
                semantic_index,
                semantic_stats,
            )
        except ImportError as e:
            print(f"⚠️  WARNING: Cannot import semantic_search module: {e}")
            print("This test requires the mcp_bridge package to be installed.")
            print("Skipping test.")
            cleanup_test_project(test_dir)
            import pytest

            pytest.skip(f"Cannot import semantic_search module: {e}")

        print("\n1. Creating semantic index first...")
        print(f"   Project path: {test_dir}")

        try:
            # Create the index
            result = semantic_index(test_dir, provider="ollama")
            print(f"   ✅ Index created successfully")
            print(f"   Result: {result}")

        except Exception as e:
            print(f"   ❌ FAIL: Error creating index: {e}")
            cleanup_test_project(test_dir)
            assert False, f"Error creating index: {e}"

        print("\n2. Checking index stats...")
        try:
            stats = semantic_stats(test_dir)
            print(f"   Total chunks: {stats.get('total_chunks', 0)}")
            print(f"   Files indexed: {stats.get('files_indexed', 0)}")

            if stats.get("total_chunks", 0) > 0:
                print(f"   ✅ Index has content")
            else:
                print(f"   ⚠️  WARNING: Index appears empty")

        except Exception as e:
            print(f"   ⚠️  WARNING: Could not get stats: {e}")

        print("\n3. Starting file watcher...")
        try:
            watcher = start_file_watcher(test_dir, provider="ollama", debounce_seconds=1.0)
            print(f"   ✅ PASS: File watcher started successfully")
            print(f"   Watcher object: {watcher}")

            # Verify watcher is running
            if hasattr(watcher, "is_running") and callable(watcher.is_running):
                if watcher.is_running():
                    print(f"   ✅ Watcher is running")
                else:
                    print(f"   ⚠️  WARNING: Watcher reports not running")

            # Stop the watcher
            print("\n4. Stopping file watcher...")
            stop_file_watcher(test_dir)
            print(f"   ✅ File watcher stopped")

            cleanup_test_project(test_dir)
            print("\n✅ TEST 2 PASSED: File watcher works correctly after indexing")
            assert True  # Explicit pass for pytest

        except ValueError as e:
            print(f"   ❌ FAIL: ValueError raised even after creating index")
            print(f"   Error: {e}")
            cleanup_test_project(test_dir)
            assert False, f"ValueError raised even after creating index: {e}"

        except Exception as e:
            print(f"   ❌ FAIL: Unexpected error: {e}")
            import traceback

            traceback.print_exc()
            cleanup_test_project(test_dir)
            assert False, f"Unexpected error: {e}"

    except Exception as e:
        print(f"\n❌ TEST 2 FAILED with unexpected error: {e}")
        import traceback

        traceback.print_exc()
        cleanup_test_project(test_dir)
        assert False, f"Unexpected error: {e}"


def test_error_message_quality():
    """
    Test 3: Verify error message provides clear guidance

    Ensures developers get actionable error messages.
    """
    print("\n" + "=" * 70)
    print("TEST 3: Error Message Quality")
    print("=" * 70)

    test_dir = setup_test_project()
    print(f"Created test project: {test_dir}")

    try:
        from mcp_bridge.tools.semantic_search import start_file_watcher
    except ImportError as e:
        print(f"⚠️  WARNING: Cannot import semantic_search module: {e}")
        print("Skipping test.")
        cleanup_test_project(test_dir)
        import pytest

        pytest.skip(f"Cannot import semantic_search module: {e}")

    try:
        asyncio.run(start_file_watcher(test_dir, provider="ollama"))
    except ValueError as e:
        error_msg = str(e)
        print(f"\nError message:\n  '{error_msg}'")

        # Check for key elements of a good error message
        checks = {
            "Mentions semantic_index": "semantic_index" in error_msg.lower(),
            "Indicates requirement": any(
                word in error_msg.lower()
                for word in ["must", "need", "should", "required", "first"]
            ),
            "Provides solution": "semantic_index()" in error_msg,
            "Clear and actionable": len(error_msg) > 20 and len(error_msg) < 200,
        }

        print("\nError Message Quality Checks:")
        passed = 0
        for check, result in checks.items():
            status = "✅" if result else "❌"
            print(f"  {status} {check}: {result}")
            if result:
                passed += 1

        if passed >= 3:
            print(f"\n✅ TEST 3 PASSED: Error message quality is good ({passed}/4 checks)")
            cleanup_test_project(test_dir)
            assert True  # Explicit pass for pytest
        else:
            print(f"\n⚠️  TEST 3 PARTIAL: Error message could be improved ({passed}/4 checks)")
            cleanup_test_project(test_dir)
            assert passed >= 2, f"Error message quality too low ({passed}/4 checks)"

    except Exception as e:
        print(f"❌ TEST 3 FAILED: Wrong exception type: {type(e).__name__}")
        cleanup_test_project(test_dir)
        assert False, f"Wrong exception type: {type(e).__name__}"


def main():
    """Run all tests and report results."""
    print("=" * 70)
    print("FILE WATCHER NO-INDEX TEST SUITE")
    print("=" * 70)
    print("\nPurpose: Verify start_file_watcher() raises ValueError when no index exists")
    print("Fix: Prevents silent failures when users forget to call semantic_index()")

    # Check prerequisites
    print("\n" + "=" * 70)
    print("PREREQUISITES CHECK")
    print("=" * 70)

    prereqs_ok = True

    # Check Ollama
    import subprocess

    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ Ollama is running")
            if "nomic-embed-text" in result.stdout:
                print("✅ nomic-embed-text model is installed")
            else:
                print("⚠️  WARNING: nomic-embed-text model not found")
                print("   Install with: ollama pull nomic-embed-text")
                prereqs_ok = False
        else:
            print("❌ Ollama check failed")
            prereqs_ok = False
    except Exception as e:
        print(f"❌ Ollama not available: {e}")
        print("   Install from: https://ollama.ai")
        prereqs_ok = False

    # Check imports
    try:
        import chromadb

        print("✅ chromadb installed")
    except ImportError:
        print("❌ chromadb not installed")
        print("   Install with: uv pip install chromadb")
        prereqs_ok = False

    try:
        import watchdog

        print("✅ watchdog installed")
    except ImportError:
        print("❌ watchdog not installed")
        print("   Install with: uv pip install watchdog")
        prereqs_ok = False

    if not prereqs_ok:
        print("\n❌ Prerequisites not met. Please install required dependencies.")
        return False

    # Run tests
    results = {
        "Test 1: No Index -> ValueError": test_start_watcher_without_index(),
        "Test 2: With Index -> Success": test_start_watcher_with_index(),
        "Test 3: Error Message Quality": test_error_message_quality(),
    }

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for r in results.values() if r)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print("\n✅ ALL TESTS PASSED")
        print("\nThe fix successfully prevents silent failures when start_file_watcher()")
        print("is called without first running semantic_index().")
        return True
    else:
        print(f"\n❌ {total - passed} TEST(S) FAILED")
        print("\nThe fix may not be properly implemented or there may be other issues.")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
