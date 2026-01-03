"""
Model invocation tools for Gemini and OpenAI.

These tools use OAuth tokens from the token store to authenticate
API requests to external model providers.
"""

import logging
import time

logger = logging.getLogger(__name__)

# Model name mapping: user-friendly names -> actual API model IDs
# Claude Code uses internal names like 'gemini-3-flash' but the API requires 'gemini-2.0-flash-001'
GEMINI_MODEL_MAP = {
    # Flash models
    "gemini-3-flash": "gemini-2.0-flash-001",
    "gemini-2.0-flash": "gemini-2.0-flash-001",
    "gemini-2.0-flash-exp": "gemini-2.0-flash-exp",
    "gemini-flash": "gemini-2.0-flash-001",
    # Pro models
    "gemini-3-pro": "gemini-2.0-pro-exp",
    "gemini-2.0-pro": "gemini-2.0-pro-exp",
    "gemini-pro": "gemini-2.0-pro-exp",
    # Thinking models
    "gemini-2.0-flash-thinking": "gemini-2.0-flash-thinking-exp-01-21",
    "gemini-thinking": "gemini-2.0-flash-thinking-exp-01-21",
}

def resolve_gemini_model(model: str) -> str:
    """Resolve a user-friendly model name to the actual API model ID."""
    return GEMINI_MODEL_MAP.get(model, model)  # Pass through if not in map

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
)

from ..auth.token_store import TokenStore
from ..auth.oauth import refresh_access_token as gemini_refresh, ANTIGRAVITY_HEADERS
from ..auth.openai_oauth import refresh_access_token as openai_refresh
from ..hooks.manager import get_hook_manager


async def _ensure_valid_token(token_store: TokenStore, provider: str) -> str:
    """
    Get a valid access token, refreshing if needed.
    
    Args:
        token_store: Token store
        provider: Provider name
        
    Returns:
        Valid access token
        
    Raises:
        ValueError: If not authenticated
    """
    # Check if token needs refresh (with 5 minute buffer)
    if token_store.needs_refresh(provider, buffer_seconds=300):
        token = token_store.get_token(provider)
        
        if not token or not token.get("refresh_token"):
            raise ValueError(
                f"Not authenticated with {provider}. "
                f"Run: python -m mcp_bridge.auth.cli login {provider}"
            )
        
        try:
            if provider == "gemini":
                result = gemini_refresh(token["refresh_token"])
            elif provider == "openai":
                result = openai_refresh(token["refresh_token"])
            else:
                raise ValueError(f"Unknown provider: {provider}")
            
            # Update stored token
            token_store.set_token(
                provider=provider,
                access_token=result.access_token,
                refresh_token=result.refresh_token or token["refresh_token"],
                expires_at=time.time() + result.expires_in,
            )
            
            return result.access_token
        except Exception as e:
            raise ValueError(
                f"Token refresh failed: {e}. "
                f"Run: python -m mcp_bridge.auth.cli login {provider}"
            )
    
    access_token = token_store.get_access_token(provider)
    if not access_token:
        raise ValueError(
            f"Not authenticated with {provider}. "
            f"Run: python -m mcp_bridge.auth.cli login {provider}"
        )
    
    return access_token


def is_retryable_exception(e: Exception) -> bool:
    """Check if an exception is retryable (429 or 5xx)."""
    if isinstance(e, httpx.HTTPStatusError):
        return e.response.status_code == 429 or 500 <= e.response.status_code < 600
    return False

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception(is_retryable_exception),
    before_sleep=lambda retry_state: logger.info(f"Rate limited or server error, retrying in {retry_state.next_action.sleep} seconds...")
)
async def invoke_gemini(
    token_store: TokenStore,
    prompt: str,
    model: str = "gemini-3-flash",
    temperature: float = 0.7,
    max_tokens: int = 4096,
    thinking_budget: int = 0,
) -> str:
    """
    Invoke a Gemini model with the given prompt.

    Uses OAuth authentication with Antigravity credentials.

    Args:
        token_store: Token store for OAuth credentials
        prompt: The prompt to send to Gemini
        model: Gemini model to use
        temperature: Sampling temperature (0.0-2.0)
        max_tokens: Maximum tokens in response

    Returns:
        The model's response text.

    Raises:
        ValueError: If not authenticated with Gemini
        httpx.HTTPStatusError: If API request fails
    """
    # Execute pre-model invoke hooks
    params = {
        "prompt": prompt,
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "thinking_budget": thinking_budget,
    }
    hook_manager = get_hook_manager()
    params = await hook_manager.execute_pre_model_invoke(params)
    
    # Update local variables from possibly modified params
    prompt = params["prompt"]
    model = params["model"]
    temperature = params["temperature"]
    max_tokens = params["max_tokens"]
    thinking_budget = params["thinking_budget"]

    access_token = await _ensure_valid_token(token_store, "gemini")

    # Resolve user-friendly model name to actual API model ID
    api_model = resolve_gemini_model(model)

    # Reference implementation uses endpoint fallback order
    ANTIGRAVITY_ENDPOINTS = [
        "https://daily-cloudcode-pa.sandbox.googleapis.com",   # dev
        "https://autopush-cloudcode-pa.sandbox.googleapis.com", # staging
        "https://cloudcode-pa.googleapis.com",                  # prod
    ]
    
    # Generate session ID and project ID per reference
    import uuid
    session_id = str(uuid.uuid4())
    project_id = "rising-fact-p41fc"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        **ANTIGRAVITY_HEADERS,  # Include Antigravity headers
    }

    # Build inner request payload
    inner_payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        },
        "sessionId": session_id,
    }
    
    # Add thinking budget if supported by model/API
    if thinking_budget > 0:
        # For Gemini 2.0+ Thinking models
        inner_payload["generationConfig"]["thinkingConfig"] = {
            "includeThoughts": True,
            "tokenLimit": thinking_budget
        }
    
    # Wrap request body per reference implementation
    wrapped_payload = {
        "project": project_id,
        "model": api_model,
        "userAgent": "antigravity",
        "requestId": f"invoke-{uuid.uuid4()}",
        "request": inner_payload,
    }

    # Try endpoints in fallback order
    response = None
    last_error = None
    
    for endpoint in ANTIGRAVITY_ENDPOINTS:
        # Reference uses: {endpoint}/v1internal:generateContent (NOT /models/{model})
        api_url = f"{endpoint}/v1internal:generateContent"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    api_url,
                    headers=headers,
                    json=wrapped_payload,
                    timeout=120.0,
                )
                
                if response.status_code == 401:
                    raise ValueError(
                        "Gemini authentication expired. "
                        "Run: python -m mcp_bridge.auth.cli login gemini"
                    )
                
                # If we got a non-retryable response, use it
                if response.status_code < 500 and response.status_code != 429:
                    break
                    
        except httpx.TimeoutException as e:
            last_error = e
            continue
        except Exception as e:
            last_error = e
            continue
    
    if response is None:
        raise ValueError(f"All Antigravity endpoints failed: {last_error}")
    
    response.raise_for_status()
    data = response.json()

    # Extract text from response
    try:
        candidates = data.get("candidates", [])
        if candidates:
            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if parts:
                return parts[0].get("text", "")
        return "No response generated"
    except (KeyError, IndexError) as e:
        return f"Error parsing response: {e}"


# ========================
# AGENTIC FUNCTION CALLING
# ========================

# Tool definitions for background agents
AGENT_TOOLS = [
    {
        "functionDeclarations": [
            {
                "name": "read_file",
                "description": "Read the contents of a file. Returns the file contents as text.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Absolute or relative path to the file"
                        }
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "list_directory",
                "description": "List files and directories in a path",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Directory path to list"
                        }
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "grep_search",
                "description": "Search for a pattern in files using ripgrep. Returns matching lines with file paths and line numbers.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "The search pattern (regex)"
                        },
                        "path": {
                            "type": "string",
                            "description": "Directory or file to search in"
                        }
                    },
                    "required": ["pattern", "path"]
                }
            },
            {
                "name": "write_file",
                "description": "Write content to a file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the file to write"
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write to the file"
                        }
                    },
                    "required": ["path", "content"]
                }
            }
        ]
    }
]


def _execute_tool(name: str, args: dict) -> str:
    """Execute a tool and return the result."""
    import os
    import subprocess
    from pathlib import Path
    
    try:
        if name == "read_file":
            path = Path(args["path"])
            if not path.exists():
                return f"Error: File not found: {path}"
            return path.read_text()
        
        elif name == "list_directory":
            path = Path(args["path"])
            if not path.exists():
                return f"Error: Directory not found: {path}"
            entries = []
            for entry in path.iterdir():
                entry_type = "DIR" if entry.is_dir() else "FILE"
                entries.append(f"[{entry_type}] {entry.name}")
            return "\n".join(entries) if entries else "(empty directory)"
        
        elif name == "grep_search":
            pattern = args["pattern"]
            search_path = args["path"]
            result = subprocess.run(
                ["rg", "--json", "-m", "50", pattern, search_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return result.stdout[:10000]  # Limit output size
            elif result.returncode == 1:
                return "No matches found"
            else:
                return f"Search error: {result.stderr}"
        
        elif name == "write_file":
            path = Path(args["path"])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(args["content"])
            return f"Successfully wrote {len(args['content'])} bytes to {path}"
        
        else:
            return f"Unknown tool: {name}"
    
    except Exception as e:
        return f"Tool error: {str(e)}"


async def invoke_gemini_agentic(
    token_store: TokenStore,
    prompt: str,
    model: str = "gemini-3-flash",
    max_turns: int = 10,
    timeout: int = 120,
) -> str:
    """
    Invoke Gemini with function calling for agentic tasks.
    
    This function implements a multi-turn agentic loop:
    1. Send prompt with tool definitions
    2. If model returns FunctionCall, execute the tool
    3. Send FunctionResponse back to model
    4. Repeat until model returns text or max_turns reached
    
    Args:
        token_store: Token store for OAuth credentials
        prompt: The task prompt
        model: Gemini model to use
        max_turns: Maximum number of tool-use turns
        timeout: Request timeout in seconds
        
    Returns:
        Final text response from the model
    """
    import uuid
    
    access_token = await _ensure_valid_token(token_store, "gemini")
    api_model = resolve_gemini_model(model)
    
    # Reference implementation uses endpoint fallback order
    ANTIGRAVITY_ENDPOINTS = [
        "https://daily-cloudcode-pa.sandbox.googleapis.com",   # dev
        "https://autopush-cloudcode-pa.sandbox.googleapis.com", # staging
        "https://cloudcode-pa.googleapis.com",                  # prod
    ]
    
    # Generate session ID for this conversation (per reference)
    session_id = str(uuid.uuid4())
    
    # Default project ID from reference
    project_id = "rising-fact-p41fc"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        **ANTIGRAVITY_HEADERS,
    }
    
    # Initialize conversation
    contents = [{"role": "user", "parts": [{"text": prompt}]}]
    
    for turn in range(max_turns):
        # Build inner request payload (what goes inside "request" wrapper)
        inner_payload = {
            "contents": contents,
            "tools": AGENT_TOOLS,
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 8192,
            },
            "sessionId": session_id,
        }
        
        # Wrap request body per reference implementation
        # From request.ts wrapRequestBody()
        wrapped_payload = {
            "project": project_id,
            "model": api_model,
            "userAgent": "antigravity",
            "requestId": f"agent-{uuid.uuid4()}",
            "request": inner_payload,
        }
        
        # Try endpoints in fallback order
        response = None
        last_error = None
        
        for endpoint in ANTIGRAVITY_ENDPOINTS:
            # Reference uses: {endpoint}/v1internal:generateContent (NOT /models/{model})
            api_url = f"{endpoint}/v1internal:generateContent"
            
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        api_url,
                        headers=headers,
                        json=wrapped_payload,
                        timeout=float(timeout),
                    )
                    
                    if response.status_code == 401:
                        raise ValueError("Gemini authentication expired")
                    
                    # If we got a response (even an error), don't try next endpoint
                    # unless it's a retryable error
                    if response.status_code < 500 and response.status_code != 429:
                        break
                    
                    logger.warning(f"[AgenticGemini] Endpoint {endpoint} returned {response.status_code}, trying next")
                    
            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(f"[AgenticGemini] Endpoint {endpoint} timed out, trying next")
                continue
            except Exception as e:
                last_error = e
                logger.warning(f"[AgenticGemini] Endpoint {endpoint} failed: {e}, trying next")
                continue
        
        if response is None:
            raise ValueError(f"All Antigravity endpoints failed: {last_error}")
        
        response.raise_for_status()
        data = response.json()
        
        # Extract response
        candidates = data.get("candidates", [])
        if not candidates:
            return "No response generated"
        
        content = candidates[0].get("content", {})
        parts = content.get("parts", [])
        
        if not parts:
            return "No response parts"
        
        # Check for function call
        function_call = None
        text_response = None
        
        for part in parts:
            if "functionCall" in part:
                function_call = part["functionCall"]
                break
            elif "text" in part:
                text_response = part["text"]
        
        if function_call:
            # Execute the function
            func_name = function_call.get("name")
            func_args = function_call.get("args", {})
            
            logger.info(f"[AgenticGemini] Turn {turn+1}: Executing {func_name}")
            result = _execute_tool(func_name, func_args)
            
            # Add model's response and function result to conversation
            contents.append({"role": "model", "parts": [{"functionCall": function_call}]})
            contents.append({
                "role": "user",
                "parts": [{
                    "functionResponse": {
                        "name": func_name,
                        "response": {"result": result}
                    }
                }]
            })
        else:
            # No function call, return text response
            return text_response or "Task completed"
    
    return "Max turns reached without final response"


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception(is_retryable_exception),
    before_sleep=lambda retry_state: logger.info(f"Rate limited or server error, retrying in {retry_state.next_action.sleep} seconds...")
)
async def invoke_openai(
    token_store: TokenStore,
    prompt: str,
    model: str = "gpt-5.2",
    temperature: float = 0.7,
    max_tokens: int = 4096,
    thinking_budget: int = 0,
) -> str:
    """
    Invoke an OpenAI model with the given prompt.

    Args:
        token_store: Token store for API key
        prompt: The prompt to send to OpenAI
        model: OpenAI model to use
        temperature: Sampling temperature (0.0-2.0)
        max_tokens: Maximum tokens in response

    Returns:
        The model's response text.

    Raises:
        ValueError: If not authenticated with OpenAI
        httpx.HTTPStatusError: If API request fails
    """
    # Execute pre-model invoke hooks
    params = {
        "prompt": prompt,
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "thinking_budget": thinking_budget,
    }
    hook_manager = get_hook_manager()
    params = await hook_manager.execute_pre_model_invoke(params)
    
    # Update local variables from possibly modified params
    prompt = params["prompt"]
    model = params["model"]
    temperature = params["temperature"]
    max_tokens = params["max_tokens"]
    thinking_budget = params["thinking_budget"]

    access_token = await _ensure_valid_token(token_store, "openai")

    # OpenAI Chat Completions API
    api_url = "https://api.openai.com/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
    }
    
    # Handle thinking budget for O1/O3 style models (GPT-5.2)
    if thinking_budget > 0:
        payload["max_completion_tokens"] = max_tokens + thinking_budget
        # For O1, temperature must be 1.0 or omitted usually, but we'll try to pass it
    else:
        payload["max_tokens"] = max_tokens

    async with httpx.AsyncClient() as client:
        response = await client.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=120.0,
        )
        
        if response.status_code == 401:
            raise ValueError(
                "OpenAI authentication failed. "
                "Run: python -m mcp_bridge.auth.cli login openai"
            )
        
        response.raise_for_status()

        data = response.json()

        # Extract text from response
        try:
            choices = data.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                return message.get("content", "")
            return "No response generated"
        except (KeyError, IndexError) as e:
            return f"Error parsing response: {e}"
