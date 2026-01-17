import pytest
import asyncio
from unittest.mock import MagicMock, patch
import sys

# Mock the native module before importing native_search
sys.modules["stravinsky_native"] = MagicMock()

from mcp_bridge.native_search import native_glob_files, native_grep_search, get_executor, HAS_NATIVE

@pytest.mark.asyncio
async def test_native_calls_are_awaitable():
    """Verify that native search functions return awaitables (coroutines) after refactor."""
    
    # Ensure HAS_NATIVE is True for this test
    with patch("mcp_bridge.native_search.HAS_NATIVE", True):
        with patch("mcp_bridge.native_search.stravinsky_native") as mock_native:
            mock_native.glob_files.return_value = ["file1.py"]
            mock_native.grep_search.return_value = [{"path": "file1.py", "line": 1, "content": "match"}]
            
            # Calling the function should return a coroutine
            coro = native_glob_files("*.py", ".")
            assert asyncio.iscoroutine(coro)
            
            # Awaiting it should give the result
            result = await coro
            assert result == ["file1.py"]
            
            # Check grep search
            coro_grep = native_grep_search("pattern", ".")
            assert asyncio.iscoroutine(coro_grep)
            result_grep = await coro_grep
            assert result_grep[0]["content"] == "match"

@pytest.mark.asyncio
async def test_executor_is_singleton():
    """Verify get_executor returns the same instance."""
    exec1 = get_executor()
    exec2 = get_executor()
    assert exec1 is exec2
    
@pytest.mark.asyncio
async def test_native_error_handling():
    """Verify errors in thread pool propagate (or handled gracefully)."""
    with patch("mcp_bridge.native_search.HAS_NATIVE", True):
        with patch("mcp_bridge.native_search.stravinsky_native") as mock_native:
            mock_native.glob_files.side_effect = RuntimeError("Rust error")
            
            # The current implementation catches exceptions and returns None
            result = await native_glob_files("*.py", ".")
            assert result is None