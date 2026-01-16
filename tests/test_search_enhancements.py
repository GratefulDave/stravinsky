"""Tests for search enhancements."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from mcp_bridge.tools.search_enhancements import multi_query_search, decomposed_search, enhanced_search

# Mock the TokenStore to avoid actual keyring usage
@pytest.fixture
def mock_token_store():
    with patch("mcp_bridge.auth.token_store.TokenStore") as mock:
        yield mock

@pytest.mark.asyncio
async def test_multi_query_search(mock_token_store):
    # Patch invoke_gemini where it is defined, because search_enhancements imports it
    with patch("mcp_bridge.tools.model_invoke.invoke_gemini", new_callable=AsyncMock) as mock_gemini, \
         patch("mcp_bridge.tools.search_enhancements.get_store") as mock_get_store, \
         patch("mcp_bridge.tools.search_enhancements._check_index_exists", return_value=True):
        
        mock_gemini.return_value = "query 1\nquery 2"
        
        mock_store = MagicMock()
        mock_store.search = AsyncMock(return_value=[
            {"file": "test.py", "lines": "1-10", "language": "python", "code_preview": "code", "relevance": 0.9}
        ])
        mock_get_store.return_value = mock_store
        
        result = await multi_query_search("original query")
        
        # Verify result contains the found item
        assert "Found 1 results" in result or "Found 3 results" in result # Depending on deduplication
        assert "test.py:1-10" in result
        assert mock_gemini.called

@pytest.mark.asyncio
async def test_decomposed_search(mock_token_store):
    with patch("mcp_bridge.tools.model_invoke.invoke_gemini", new_callable=AsyncMock) as mock_gemini, \
         patch("mcp_bridge.tools.search_enhancements.get_store") as mock_get_store, \
         patch("mcp_bridge.tools.search_enhancements._check_index_exists", return_value=True):
        
        mock_gemini.return_value = "subquery 1\nsubquery 2"
        
        mock_store = MagicMock()
        # Return different results for each call?
        mock_store.search = AsyncMock(return_value=[
             {"file": "sub1.py", "lines": "10", "language": "python", "code_preview": "c1", "relevance": 0.8}
        ])
        mock_get_store.return_value = mock_store
        
        result = await decomposed_search("complex query")
        
        assert "Decomposed 'complex query' into 2 parts" in result
        assert "### Sub-query: subquery 1" in result
        assert "sub1.py:10" in result

@pytest.mark.asyncio
async def test_enhanced_search_auto():
    with patch("mcp_bridge.tools.search_enhancements.decomposed_search", new_callable=AsyncMock) as mock_decompose, \
         patch("mcp_bridge.tools.search_enhancements.multi_query_search", new_callable=AsyncMock) as mock_multi:
        
        mock_decompose.return_value = "decomposed result"
        mock_multi.return_value = "multi result"
        
        # Long query -> decompose
        long_query = "this is a very long query that should trigger decomposition mode because it has many words"
        result = await enhanced_search(long_query, mode="auto")
        assert result == "decomposed result"
        
        # Short query -> multi
        short_query = "simple query"
        result = await enhanced_search(short_query, mode="auto")
        assert result == "multi result"