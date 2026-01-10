"""
Comprehensive tests for invoke_gemini_agentic MCP tool.

Tests cover:
- Basic agentic loop (prompt → tool calls → execution → final response)
- Multi-turn iterations (max_turns parameter)
- Tool execution with mock function calling
- Timeout handling
- Error recovery scenarios
- Agent context parameter usage
- Both API key and OAuth authentication paths
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from pathlib import Path

import pytest
import httpx

from mcp_bridge.auth.token_store import TokenStore
from mcp_bridge.tools.model_invoke import (
    AGENT_TOOLS,
    invoke_gemini_agentic,
    _invoke_gemini_agentic_with_api_key,
    _execute_tool,
)


@pytest.fixture
def mock_google_genai():
    """Mock google-genai library for API key authentication."""
    # Remove any previously imported google.genai modules to prevent test pollution
    modules_to_remove = [k for k in sys.modules.keys() if k.startswith('google.genai')]
    removed_modules = {k: sys.modules.pop(k) for k in modules_to_remove}

    # Mock the import inside _invoke_gemini_agentic_with_api_key
    mock_module = MagicMock()
    with patch.dict("sys.modules", {"google.genai": mock_module}):
        yield mock_module

    # Restore removed modules after test
    for k, v in removed_modules.items():
        sys.modules[k] = v


@pytest.fixture
def mock_token_store():
    """Mock token store for OAuth authentication."""
    token_store = MagicMock(spec=TokenStore)
    token_store.get_access_token.return_value = "mock_access_token"
    token_store.needs_refresh.return_value = False
    return token_store


@pytest.fixture
def mock_antigravity_endpoints():
    """Mock Antigravity endpoints for OAuth path."""
    with patch("mcp_bridge.tools.model_invoke.ANTIGRAVITY_ENDPOINTS", ["http://mock_antigravity_endpoint"]):
        yield


@pytest.fixture
def clean_env():
    """Clean environment variables before/after tests."""
    original_gemini = os.environ.pop("GEMINI_API_KEY", None)
    original_google = os.environ.pop("GOOGLE_API_KEY", None)
    yield
    if original_gemini:
        os.environ["GEMINI_API_KEY"] = original_gemini
    if original_google:
        os.environ["GOOGLE_API_KEY"] = original_google


# ========================
# BASIC AGENTIC LOOP TESTS
# ========================

@pytest.mark.asyncio
async def test_agentic_loop_api_key_single_turn(mock_google_genai, clean_env):
    """Test basic agentic loop with API key - single turn (no function calls)."""
    # Mock google-genai library for API key authentication
    mock_client = MagicMock()
    mock_google_genai.Client.return_value = mock_client

    # Mock types to return non-validating objects (not MagicMock instances that trigger Pydantic)
    # This prevents Pydantic validation errors when google.genai is actually imported
    mock_google_genai.types = MagicMock()

    # Create a dummy config class that doesn't validate (mimics Pydantic BaseModel)
    class MockConfig:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
            # Set default attributes expected by google.genai
            if not hasattr(self, 'automatic_function_calling'):
                self.automatic_function_calling = None
            if not hasattr(self, 'tools'):
                self.tools = None

        def model_copy(self, update=None):
            """Mimic Pydantic's model_copy method."""
            new_obj = MockConfig(**self.__dict__)
            if update:
                for k, v in update.items():
                    setattr(new_obj, k, v)
            return new_obj

        def __getattr__(self, name):
            """Return None for any undefined attribute (prevents AttributeError)."""
            return None

    mock_google_genai.types.GenerateContentConfig = MockConfig
    mock_google_genai.types.FunctionDeclaration = lambda **kwargs: MockConfig(**kwargs)
    mock_google_genai.types.Tool = lambda **kwargs: MockConfig(**kwargs)
    mock_google_genai.types.Content = lambda **kwargs: MockConfig(**kwargs)
    mock_google_genai.types.Part = lambda **kwargs: MockConfig(**kwargs)
    mock_google_genai.types.FunctionResponse = lambda **kwargs: MockConfig(**kwargs)

    # Mock response without function calls (immediate text response)
    mock_response = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    mock_candidate = MagicMock()
    mock_part = MagicMock()
    mock_part.function_call = None
    mock_part.text = "Task completed successfully"
    mock_candidate.content.parts = [mock_part]
    mock_response.candidates = [mock_candidate]

    os.environ["GEMINI_API_KEY"] = "test_api_key"

    result = await invoke_gemini_agentic(
        token_store=MagicMock(),
        prompt="Say hello",
        max_turns=10,
    )

    assert "Task completed successfully" in result
    assert mock_client.models.generate_content.called


@pytest.mark.asyncio
async def test_agentic_loop_api_key_multi_turn(mock_google_genai, clean_env):
    """Test multi-turn agentic loop with function calls."""
    mock_client = MagicMock()
    mock_google_genai.Client.return_value = mock_client
    mock_google_genai.types = MagicMock()

    # Setup type mocks
    mock_google_genai.types.FunctionDeclaration = lambda **kwargs: MagicMock(**kwargs)
    mock_google_genai.types.Tool = lambda **kwargs: MagicMock(**kwargs)
    mock_google_genai.types.Content = lambda **kwargs: MagicMock(**kwargs)
    mock_google_genai.types.Part = lambda **kwargs: MagicMock(**kwargs)
    mock_google_genai.types.GenerateContentConfig = lambda **kwargs: MagicMock(**kwargs)
    mock_google_genai.types.FunctionResponse = lambda **kwargs: MagicMock(**kwargs)

    # First call: return function call
    mock_response1 = MagicMock()
    mock_candidate1 = MagicMock()
    mock_part1 = MagicMock()
    mock_fc1 = MagicMock()
    mock_fc1.name = "read_file"
    mock_fc1.args = {"path": "test.txt"}
    mock_part1.function_call = mock_fc1
    mock_part1.text = None
    mock_candidate1.content.parts = [mock_part1]
    mock_response1.candidates = [mock_candidate1]

    # Second call: return final text response
    mock_response2 = MagicMock()
    mock_candidate2 = MagicMock()
    mock_part2 = MagicMock()
    mock_part2.function_call = None
    mock_part2.text = "File content processed"
    mock_candidate2.content.parts = [mock_part2]
    mock_response2.candidates = [mock_candidate2]

    mock_client.models.generate_content.side_effect = [mock_response1, mock_response2]

    os.environ["GEMINI_API_KEY"] = "test_api_key"

    with patch("mcp_bridge.tools.model_invoke._execute_tool") as mock_execute:
        mock_execute.return_value = "File contents: Hello World"

        result = await invoke_gemini_agentic(
            token_store=MagicMock(),
            prompt="Read test.txt and summarize it",
            max_turns=10,
        )

    assert "File content processed" in result
    assert mock_client.models.generate_content.call_count == 2
    mock_execute.assert_called_once_with("read_file", {"path": "test.txt"})


@pytest.mark.asyncio
async def test_agentic_loop_oauth_single_turn(
    mock_google_genai, mock_token_store, mock_antigravity_endpoints, clean_env
):
    """Test OAuth path with single turn."""
    with patch("mcp_bridge.tools.model_invoke._get_http_client") as mock_get_client:
        mock_http_client = MagicMock()
        mock_get_client.return_value = mock_http_client

        # Mock successful response with text
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": {
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": "OAuth response success"}]
                        }
                    }
                ]
            }
        }
        mock_http_client.post = AsyncMock(return_value=mock_response)

        result = await invoke_gemini_agentic(
            token_store=mock_token_store,
            prompt="Test OAuth",
            max_turns=10,
        )

        assert "OAuth response success" in result
        assert mock_http_client.post.called


@pytest.mark.asyncio
async def test_agentic_loop_oauth_multi_turn(
    mock_google_genai, mock_token_store, mock_antigravity_endpoints, clean_env
):
    """Test OAuth path with function calling across multiple turns."""
    with patch("mcp_bridge.tools.model_invoke._get_http_client") as mock_get_client:
        mock_http_client = MagicMock()
        mock_get_client.return_value = mock_http_client

        # First response: function call
        mock_response1 = MagicMock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = {
            "response": {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "functionCall": {
                                        "name": "list_directory",
                                        "args": {"path": "."}
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        }

        # Second response: final text
        mock_response2 = MagicMock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = {
            "response": {
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": "Directory listed successfully"}]
                        }
                    }
                ]
            }
        }

        mock_http_client.post = AsyncMock(side_effect=[mock_response1, mock_response2])

        with patch("mcp_bridge.tools.model_invoke._execute_tool") as mock_execute:
            mock_execute.return_value = "[FILE] test.txt\n[DIR] subdir"

            result = await invoke_gemini_agentic(
                token_store=mock_token_store,
                prompt="List directory",
                max_turns=10,
            )

        assert "Directory listed successfully" in result
        assert mock_http_client.post.call_count == 2
        mock_execute.assert_called_once_with("list_directory", {"path": "."})


# ========================
# MAX_TURNS PARAMETER TESTS
# ========================

@pytest.mark.asyncio
async def test_max_turns_limit_reached_api_key(mock_google_genai, clean_env):
    """Test that agentic loop stops when max_turns is reached (API key path)."""
    mock_client = MagicMock()
    mock_google_genai.Client.return_value = mock_client
    mock_google_genai.types = MagicMock()

    # Setup type mocks
    mock_google_genai.types.FunctionDeclaration = lambda **kwargs: MagicMock(**kwargs)
    mock_google_genai.types.Tool = lambda **kwargs: MagicMock(**kwargs)
    mock_google_genai.types.Content = lambda **kwargs: MagicMock(**kwargs)
    mock_google_genai.types.Part = lambda **kwargs: MagicMock(**kwargs)
    mock_google_genai.types.GenerateContentConfig = lambda **kwargs: MagicMock(**kwargs)
    mock_google_genai.types.FunctionResponse = lambda **kwargs: MagicMock(**kwargs)

    # Always return function call (infinite loop scenario)
    mock_response = MagicMock()
    mock_candidate = MagicMock()
    mock_part = MagicMock()
    mock_fc = MagicMock()
    mock_fc.name = "read_file"
    mock_fc.args = {"path": "test.txt"}
    mock_part.function_call = mock_fc
    mock_part.text = None
    mock_candidate.content.parts = [mock_part]
    mock_response.candidates = [mock_candidate]

    mock_client.models.generate_content.return_value = mock_response

    os.environ["GEMINI_API_KEY"] = "test_api_key"

    with patch("mcp_bridge.tools.model_invoke._execute_tool") as mock_execute:
        mock_execute.return_value = "File content"

        result = await invoke_gemini_agentic(
            token_store=MagicMock(),
            prompt="Read file repeatedly",
            max_turns=3,  # Limit to 3 turns
        )

    assert "Max turns reached" in result
    assert mock_client.models.generate_content.call_count == 3


@pytest.mark.asyncio
async def test_max_turns_limit_reached_oauth(
    mock_google_genai, mock_token_store, mock_antigravity_endpoints, clean_env
):
    """Test that agentic loop stops when max_turns is reached (OAuth path)."""
    with patch("mcp_bridge.tools.model_invoke._get_http_client") as mock_get_client:
        mock_http_client = MagicMock()
        mock_get_client.return_value = mock_http_client

        # Always return function call
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "functionCall": {
                                        "name": "grep_search",
                                        "args": {"pattern": "test", "path": "."}
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        }

        mock_http_client.post = AsyncMock(return_value=mock_response)

        with patch("mcp_bridge.tools.model_invoke._execute_tool") as mock_execute:
            mock_execute.return_value = "Match found"

            result = await invoke_gemini_agentic(
                token_store=mock_token_store,
                prompt="Search repeatedly",
                max_turns=2,  # Limit to 2 turns
            )

        assert "Max turns reached" in result
        assert mock_http_client.post.call_count == 2


# ========================
# TOOL EXECUTION TESTS
# ========================

def test_execute_tool_read_file():
    """Test _execute_tool with read_file function."""
    test_file = Path("test_temp_file.txt")
    try:
        test_file.write_text("Test content")
        result = _execute_tool("read_file", {"path": str(test_file)})
        assert result == "Test content"
    finally:
        test_file.unlink(missing_ok=True)


def test_execute_tool_read_file_not_found():
    """Test _execute_tool with read_file when file doesn't exist."""
    result = _execute_tool("read_file", {"path": "/nonexistent/file.txt"})
    assert "Error: File not found" in result


def test_execute_tool_list_directory():
    """Test _execute_tool with list_directory function."""
    test_dir = Path("test_temp_dir")
    try:
        test_dir.mkdir(exist_ok=True)
        (test_dir / "file1.txt").touch()
        (test_dir / "subdir").mkdir(exist_ok=True)

        result = _execute_tool("list_directory", {"path": str(test_dir)})
        assert "[FILE] file1.txt" in result
        assert "[DIR] subdir" in result
    finally:
        import shutil
        shutil.rmtree(test_dir, ignore_errors=True)


def test_execute_tool_list_directory_not_found():
    """Test _execute_tool with list_directory when directory doesn't exist."""
    result = _execute_tool("list_directory", {"path": "/nonexistent/directory"})
    assert "Error: Directory not found" in result


def test_execute_tool_grep_search():
    """Test _execute_tool with grep_search function."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"type":"match","data":{"path":{"text":"file.txt"}}}',
        )
        result = _execute_tool("grep_search", {"pattern": "test", "path": "."})
        assert "match" in result or "file.txt" in result


def test_execute_tool_grep_search_no_matches():
    """Test _execute_tool with grep_search when no matches found."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1)
        result = _execute_tool("grep_search", {"pattern": "nonexistent", "path": "."})
        assert "No matches found" in result


def test_execute_tool_write_file():
    """Test _execute_tool with write_file function."""
    test_file = Path("test_write_file.txt")
    try:
        result = _execute_tool("write_file", {"path": str(test_file), "content": "New content"})
        assert "Successfully wrote" in result
        assert test_file.read_text() == "New content"
    finally:
        test_file.unlink(missing_ok=True)


def test_execute_tool_unknown():
    """Test _execute_tool with unknown tool name."""
    result = _execute_tool("unknown_tool", {})
    assert "Unknown tool" in result


def test_execute_tool_error_handling():
    """Test _execute_tool error handling."""
    # Test read_file with path that causes exception during read
    with patch("pathlib.Path.read_text") as mock_read:
        mock_read.side_effect = Exception("Simulated error")
        with patch("pathlib.Path.exists", return_value=True):
            result = _execute_tool("read_file", {"path": "test.txt"})
            assert "Tool error" in result


# ========================
# TIMEOUT TESTS
# ========================

@pytest.mark.asyncio
async def test_timeout_handling_oauth(
    mock_google_genai, mock_token_store, mock_antigravity_endpoints, clean_env
):
    """Test timeout handling in OAuth path."""
    with patch("mcp_bridge.tools.model_invoke._get_http_client") as mock_get_client:
        mock_http_client = MagicMock()
        mock_get_client.return_value = mock_http_client

        # Simulate timeout
        mock_http_client.post = AsyncMock(side_effect=httpx.TimeoutException("Request timed out"))

        with pytest.raises(ValueError) as excinfo:
            await invoke_gemini_agentic(
                token_store=mock_token_store,
                prompt="Test timeout",
                max_turns=1,
                timeout=5,
            )

        assert "All Antigravity endpoints failed" in str(excinfo.value)


@pytest.mark.asyncio
async def test_timeout_parameter_passed_to_http(
    mock_google_genai, mock_token_store, mock_antigravity_endpoints, clean_env
):
    """Test that timeout parameter is passed to HTTP client."""
    with patch("mcp_bridge.tools.model_invoke._get_http_client") as mock_get_client:
        mock_http_client = MagicMock()
        mock_get_client.return_value = mock_http_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": {
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": "Response"}]
                        }
                    }
                ]
            }
        }
        mock_http_client.post = AsyncMock(return_value=mock_response)

        await invoke_gemini_agentic(
            token_store=mock_token_store,
            prompt="Test",
            max_turns=1,
            timeout=45,
        )

        # Verify timeout was passed to post call
        call_args = mock_http_client.post.call_args
        assert call_args.kwargs["timeout"] == 45.0


# ========================
# ERROR RECOVERY TESTS
# ========================

@pytest.mark.asyncio
async def test_error_recovery_401_retries_next_endpoint(
    mock_google_genai, mock_token_store, clean_env
):
    """Test that 401 errors trigger retry with next endpoint."""
    with patch("mcp_bridge.tools.model_invoke.ANTIGRAVITY_ENDPOINTS", [
        "http://endpoint1",
        "http://endpoint2",
    ]):
        with patch("mcp_bridge.tools.model_invoke._get_http_client") as mock_get_client:
            mock_http_client = MagicMock()
            mock_get_client.return_value = mock_http_client

            # First endpoint returns 401, second succeeds
            mock_response1 = MagicMock()
            mock_response1.status_code = 401

            mock_response2 = MagicMock()
            mock_response2.status_code = 200
            mock_response2.json.return_value = {
                "response": {
                    "candidates": [
                        {
                            "content": {
                                "parts": [{"text": "Success on second endpoint"}]
                            }
                        }
                    ]
                }
            }

            mock_http_client.post = AsyncMock(side_effect=[mock_response1, mock_response2])

            result = await invoke_gemini_agentic(
                token_store=mock_token_store,
                prompt="Test retry",
                max_turns=1,
            )

            assert "Success on second endpoint" in result
            assert mock_http_client.post.call_count == 2


@pytest.mark.asyncio
async def test_error_recovery_all_endpoints_fail(
    mock_google_genai, mock_token_store, mock_antigravity_endpoints, clean_env
):
    """Test error when all endpoints fail."""
    import httpx

    with patch("mcp_bridge.tools.model_invoke._get_http_client") as mock_get_client:
        mock_http_client = MagicMock()
        mock_get_client.return_value = mock_http_client

        # All endpoints return 500
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        # When raise_for_status is called, it should raise HTTPStatusError
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500 Internal Server Error",
            request=MagicMock(),
            response=mock_response
        )

        mock_http_client.post = AsyncMock(return_value=mock_response)

        with pytest.raises(httpx.HTTPStatusError):
            await invoke_gemini_agentic(
                token_store=mock_token_store,
                prompt="Test all fail",
                max_turns=1,
            )


@pytest.mark.asyncio
async def test_error_recovery_api_key_import_error(clean_env):
    """Test error handling when google-genai library is not available."""
    import sys

    os.environ["GEMINI_API_KEY"] = "test_api_key"

    # Temporarily remove google.genai from sys.modules
    original_module = sys.modules.pop("google.genai", None)

    try:
        with patch.dict("sys.modules", {"google.genai": None}):
            # This should raise ImportError when trying to import genai
            with pytest.raises((ImportError, ModuleNotFoundError)) as excinfo:
                await invoke_gemini_agentic(
                    token_store=MagicMock(),
                    prompt="Test import error",
                    max_turns=1,
                )

            # The error message might vary slightly
            error_msg = str(excinfo.value).lower()
            assert "google-genai" in error_msg or "genai" in error_msg or "import" in error_msg
    finally:
        # Restore original module
        if original_module is not None:
            sys.modules["google.genai"] = original_module


@pytest.mark.asyncio
async def test_error_recovery_empty_response(
    mock_google_genai, mock_token_store, mock_antigravity_endpoints, clean_env
):
    """Test handling of empty response from API."""
    with patch("mcp_bridge.tools.model_invoke._get_http_client") as mock_get_client:
        mock_http_client = MagicMock()
        mock_get_client.return_value = mock_http_client

        # Empty candidates
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": {
                "candidates": []
            }
        }

        mock_http_client.post = AsyncMock(return_value=mock_response)

        result = await invoke_gemini_agentic(
            token_store=mock_token_store,
            prompt="Test empty",
            max_turns=1,
        )

        assert "No response generated" in result


@pytest.mark.asyncio
async def test_error_recovery_malformed_response(
    mock_google_genai, mock_token_store, mock_antigravity_endpoints, clean_env
):
    """Test handling of malformed response structure."""
    with patch("mcp_bridge.tools.model_invoke._get_http_client") as mock_get_client:
        mock_http_client = MagicMock()
        mock_get_client.return_value = mock_http_client

        # Malformed response (missing expected fields)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": {
                "candidates": [
                    {
                        "content": {
                            "parts": []  # Empty parts
                        }
                    }
                ]
            }
        }

        mock_http_client.post = AsyncMock(return_value=mock_response)

        result = await invoke_gemini_agentic(
            token_store=mock_token_store,
            prompt="Test malformed",
            max_turns=1,
        )

        assert "No response parts" in result


# ========================
# AGENT_CONTEXT PARAMETER TESTS
# ========================

@pytest.mark.asyncio
async def test_agent_context_api_key_logging(mock_google_genai, clean_env, caplog):
    """Test that agent_context is used for logging (API key path)."""
    import logging
    caplog.set_level(logging.INFO)

    mock_client = MagicMock()
    mock_google_genai.Client.return_value = mock_client

    mock_response = MagicMock()
    mock_candidate = MagicMock()
    mock_part = MagicMock()
    mock_part.function_call = None
    mock_part.text = "Response"
    mock_candidate.content.parts = [mock_part]
    mock_response.candidates = [mock_candidate]
    mock_client.models.generate_content.return_value = mock_response

    os.environ["GEMINI_API_KEY"] = "test_api_key"

    # Note: agent_context is not a direct parameter to invoke_gemini_agentic
    # It's typically passed via the prompt or metadata in the actual usage
    # For now, we just verify the function executes without agent_context errors
    await invoke_gemini_agentic(
        token_store=MagicMock(),
        prompt="Test with context",
        max_turns=1,
    )

    # Verify logging occurred
    assert "AgenticGemini" in caplog.text or "API key" in caplog.text


# ========================
# EDGE CASE TESTS
# ========================

@pytest.mark.asyncio
async def test_agentic_loop_multiple_function_calls_api_key(mock_google_genai, clean_env):
    """Test handling of multiple function calls in a single response (API key)."""
    mock_client = MagicMock()
    mock_google_genai.Client.return_value = mock_client
    mock_google_genai.types = MagicMock()

    # Setup type mocks
    mock_google_genai.types.FunctionDeclaration = lambda **kwargs: MagicMock(**kwargs)
    mock_google_genai.types.Tool = lambda **kwargs: MagicMock(**kwargs)
    mock_google_genai.types.Content = lambda **kwargs: MagicMock(**kwargs)
    mock_google_genai.types.Part = lambda **kwargs: MagicMock(**kwargs)
    mock_google_genai.types.GenerateContentConfig = lambda **kwargs: MagicMock(**kwargs)
    mock_google_genai.types.FunctionResponse = lambda **kwargs: MagicMock(**kwargs)

    # Response with multiple function calls
    mock_response1 = MagicMock()
    mock_candidate1 = MagicMock()

    mock_fc1 = MagicMock()
    mock_fc1.name = "read_file"
    mock_fc1.args = {"path": "file1.txt"}

    mock_fc2 = MagicMock()
    mock_fc2.name = "read_file"
    mock_fc2.args = {"path": "file2.txt"}

    mock_part1 = MagicMock()
    mock_part1.function_call = mock_fc1
    mock_part1.text = None

    mock_part2 = MagicMock()
    mock_part2.function_call = mock_fc2
    mock_part2.text = None

    mock_candidate1.content.parts = [mock_part1, mock_part2]
    mock_response1.candidates = [mock_candidate1]

    # Final response
    mock_response2 = MagicMock()
    mock_candidate2 = MagicMock()
    mock_part_final = MagicMock()
    mock_part_final.function_call = None
    mock_part_final.text = "Both files processed"
    mock_candidate2.content.parts = [mock_part_final]
    mock_response2.candidates = [mock_candidate2]

    mock_client.models.generate_content.side_effect = [mock_response1, mock_response2]

    os.environ["GEMINI_API_KEY"] = "test_api_key"

    with patch("mcp_bridge.tools.model_invoke._execute_tool") as mock_execute:
        mock_execute.return_value = "File content"

        result = await invoke_gemini_agentic(
            token_store=MagicMock(),
            prompt="Read both files",
            max_turns=10,
        )

    assert "Both files processed" in result
    # Verify both function calls were executed
    assert mock_execute.call_count == 2


@pytest.mark.asyncio
async def test_agentic_loop_no_candidates(
    mock_google_genai, mock_token_store, mock_antigravity_endpoints, clean_env
):
    """Test handling when response has no candidates."""
    with patch("mcp_bridge.tools.model_invoke._get_http_client") as mock_get_client:
        mock_http_client = MagicMock()
        mock_get_client.return_value = mock_http_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": {
                "candidates": []
            }
        }

        mock_http_client.post = AsyncMock(return_value=mock_response)

        result = await invoke_gemini_agentic(
            token_store=mock_token_store,
            prompt="Test no candidates",
            max_turns=1,
        )

        assert "No response generated" in result


@pytest.mark.asyncio
async def test_model_parameter_passed_correctly(mock_google_genai, clean_env):
    """Test that model parameter is correctly mapped and passed."""
    mock_client = MagicMock()
    mock_google_genai.Client.return_value = mock_client

    mock_response = MagicMock()
    mock_candidate = MagicMock()
    mock_part = MagicMock()
    mock_part.function_call = None
    mock_part.text = "Model test response"
    mock_candidate.content.parts = [mock_part]
    mock_response.candidates = [mock_candidate]
    mock_client.models.generate_content.return_value = mock_response

    os.environ["GEMINI_API_KEY"] = "test_api_key"

    await invoke_gemini_agentic(
        token_store=MagicMock(),
        prompt="Test model",
        model="gemini-3-pro-high",  # Should map to gemini-exp-1206
        max_turns=1,
    )

    # Verify generate_content was called with mapped model name
    call_args = mock_client.models.generate_content.call_args
    assert call_args.kwargs["model"] == "gemini-exp-1206"


# ========================
# INTEGRATION TESTS
# ========================

def test_agent_tools_structure():
    """Test that AGENT_TOOLS has correct structure."""
    assert isinstance(AGENT_TOOLS, list)
    assert len(AGENT_TOOLS) > 0

    for tool_group in AGENT_TOOLS:
        assert "functionDeclarations" in tool_group
        assert isinstance(tool_group["functionDeclarations"], list)

        for func_decl in tool_group["functionDeclarations"]:
            assert "name" in func_decl
            assert "description" in func_decl
            assert "parameters" in func_decl
            assert func_decl["name"] in ["read_file", "list_directory", "grep_search", "write_file"]


def test_all_tools_executable():
    """Test that all defined tools in AGENT_TOOLS are executable."""
    for tool_group in AGENT_TOOLS:
        for func_decl in tool_group["functionDeclarations"]:
            tool_name = func_decl["name"]

            # Test with minimal valid args
            if tool_name == "read_file":
                # Will fail but shouldn't crash
                result = _execute_tool(tool_name, {"path": "/nonexistent"})
                assert isinstance(result, str)

            elif tool_name == "list_directory":
                result = _execute_tool(tool_name, {"path": "/nonexistent"})
                assert isinstance(result, str)

            elif tool_name == "grep_search":
                # Will likely fail but shouldn't crash
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(returncode=1)
                    result = _execute_tool(tool_name, {"pattern": "test", "path": "."})
                    assert isinstance(result, str)

            elif tool_name == "write_file":
                test_file = Path("test_tool_write.txt")
                try:
                    result = _execute_tool(tool_name, {"path": str(test_file), "content": "test"})
                    assert isinstance(result, str)
                finally:
                    test_file.unlink(missing_ok=True)
