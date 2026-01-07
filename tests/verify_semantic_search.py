#!/usr/bin/env python3
"""
Semantic Search Verification Script

Run this script to verify that semantic_search is working correctly:
  uv run python tests/verify_semantic_search.py

This script performs 5 core tests and reports on the health of the
semantic search system.
"""

import asyncio
import sys
from pathlib import Path


async def main():
    """Run semantic search verification tests."""
    
    # Add project to path
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))
    
    from mcp_bridge.tools.semantic_search import (
        semantic_health,
        semantic_stats,
        semantic_search,
        get_store,
    )
    
    print("\n" + "=" * 70)
    print("SEMANTIC SEARCH VERIFICATION")
    print("=" * 70)
    
    project_path = str(project_root)
    provider = "ollama"
    tests_passed = 0
    tests_total = 5
    
    # Test 1: Health Check
    print("\n[1/5] Checking provider and database health...")
    try:
        health = await semantic_health(project_path, provider=provider)
        if "Online" in health:
            print("✅ PASS: Provider online and database accessible")
            tests_passed += 1
        else:
            print(f"⚠️  WARNING: {health}")
    except Exception as e:
        print(f"❌ FAIL: {type(e).__name__}: {e}")
    
    # Test 2: Statistics
    print("\n[2/5] Checking index statistics...")
    try:
        stats = await semantic_stats(project_path, provider=provider)
        if "Chunks indexed:" in stats:
            lines = stats.split("\n")
            chunks_line = [l for l in lines if "Chunks indexed:" in l]
            if chunks_line:
                print(f"✅ PASS: {chunks_line[0].strip()}")
                tests_passed += 1
            else:
                print("⚠️  WARNING: Could not parse chunk count")
        else:
            print("⚠️  WARNING: No chunks indexed")
    except Exception as e:
        print(f"❌ FAIL: {type(e).__name__}: {e}")
    
    # Test 3: Basic Search
    print("\n[3/5] Testing basic semantic search...")
    try:
        result = await semantic_search(
            query="authentication logic",
            project_path=project_path,
            n_results=3,
            provider=provider
        )
        
        if "Found" in result and "relevance:" in result:
            result_lines = result.split("\n")
            print(f"✅ PASS: {result_lines[0]}")
            tests_passed += 1
        else:
            print(f"⚠️  WARNING: Unexpected result format")
    except Exception as e:
        print(f"❌ FAIL: {type(e).__name__}: {e}")
    
    # Test 4: Multiple Queries
    print("\n[4/5] Testing multiple query types...")
    try:
        queries = [
            "OAuth authentication",
            "vector embeddings",
            "error handling",
        ]
        
        success_count = 0
        for query in queries:
            result = await semantic_search(
                query=query,
                project_path=project_path,
                n_results=2,
                provider=provider
            )
            if "Found" in result or "error" not in result.lower():
                success_count += 1
        
        if success_count == len(queries):
            print(f"✅ PASS: All {len(queries)} query types successful")
            tests_passed += 1
        else:
            print(f"⚠️  WARNING: {success_count}/{len(queries)} queries succeeded")
    except Exception as e:
        print(f"❌ FAIL: {type(e).__name__}: {e}")
    
    # Test 5: Database Access
    print("\n[5/5] Testing direct database access...")
    try:
        store = get_store(project_path, provider=provider)
        count = store.collection.count()
        if count > 0:
            print(f"✅ PASS: Database accessible ({count} documents)")
            tests_passed += 1
        else:
            print("⚠️  WARNING: Database is empty")
    except Exception as e:
        print(f"❌ FAIL: {type(e).__name__}: {e}")
    
    # Summary
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    print(f"Tests Passed: {tests_passed}/{tests_total}")
    
    if tests_passed == tests_total:
        print("\n✅ SUCCESS: Semantic search is working correctly!")
        print("\nSystem Status:")
        print("  - Search functionality: OPERATIONAL")
        print("  - Provider: ONLINE")
        print("  - Database: INITIALIZED")
        print("  - No exceptions detected")
        return 0
    elif tests_passed >= 3:
        print("\n⚠️  PARTIAL: Most tests passed, but some issues detected")
        print("See warnings above for details")
        return 1
    else:
        print("\n❌ FAILURE: Multiple tests failed")
        print("Please check the errors above and the documentation")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
