"""
Model invocation tools for Gemini and OpenAI.

These tools use OAuth tokens from the token store to authenticate
API requests to external model providers.
"""

import asyncio
import logging
import os
import time
import uuid
import base64
import json as json_module

logger = logging.getLogger(__name__)


def _summarize_prompt(prompt: str, max_length: int = 120) -> str:
    """
    Generate a short summary of the prompt for logging.

    Args:
        prompt: The full prompt text
        max_length: Maximum characters to include in summary

    Returns:
        Truncated prompt suitable for logging (single line, max_length chars)
    """
    if not prompt:
        return "(empty prompt)"

    # Normalize whitespace: collapse newlines and multiple spaces
    clean = " ".join(prompt.split())

    if len(clean) <= max_length:
        return clean

    return clean[:max_length] + "..."


# Cache for Codex instructions (fetched from GitHub)
_CODEX_INSTRUCTIONS_CACHE = {}
_CODEX_INSTRUCTIONS_RELEASE_TAG = "rust-v0.77.0"  # Update as needed


async def _fetch_codex_instructions(model: str = "gpt-5.2-codex") -> str:
    """
    Fetch official Codex instructions from GitHub.
    Caches results to avoid repeated fetches.
    """
    import httpx

    if model in _CODEX_INSTRUCTIONS_CACHE:
        return _CODEX_INSTRUCTIONS_CACHE[model]

    # Map model to prompt file
    prompt_file_map = {
        "gpt-5.2-codex": "gpt-5.2-codex_prompt.md",
        "gpt-5.1-codex": "gpt_5_codex_prompt.md",
        "gpt-5.1-codex-max": "gpt_5_codex_max_prompt.md",
    }

    prompt_file = prompt_file_map.get(model, "gpt-5.2-codex_prompt.md")
    url = f"https://raw.githubusercontent.com/openai/codex/{_CODEX_INSTRUCTIONS_RELEASE_TAG}/codex-rs/core/{prompt_file}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
            instructions = response.text
            _CODEX_INSTRUCTIONS_CACHE[model] = instructions
            return instructions
    except Exception as e:
        logger.error(f"Failed to fetch Codex instructions: {e}")
        # Return basic fallback instructions
        return "You are Codex, based on GPT-5. You are running as a coding agent."


# Model name mapping: user-friendly names -> Antigravity API model IDs
# Per API spec: https://github.com/NoeFabris/opencode-antigravity-auth/blob/main/docs/ANTIGRAVITY_API_SPEC.md
# VERIFIED GEMINI MODELS (as of 2026-01):
#   - gemini-3-flash, gemini-3-pro-high, gemini-3-pro-low
# NOTE: Claude models should use Anthropic API directly, NOT Antigravity
GEMINI_MODEL_MAP = {
    # Antigravity verified Gemini models (pass-through)
    "gemini-3-pro-low": "gemini-3-pro-low",
    "gemini-3-pro-high": "gemini-3-pro-high",
    "gemini-3-flash": "gemini-3-flash",
    # Aliases for convenience
    "gemini-flash": "gemini-3-flash",
    "gemini-pro": "gemini-3-pro-low",
    "gemini-3-pro": "gemini-3-pro-low",
    "gemini": "gemini-3-pro-low",  # Default gemini alias
    # Legacy mappings (redirect to Antigravity models)
    "gemini-2.0-flash": "gemini-3-pro-low",
    "gemini-2.0-flash-001": "gemini-3-pro-low",
    "gemini-2.0-pro": "gemini-3-pro-low",
    "gemini-2.0-pro-exp": "gemini-3-pro-high",
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
from ..auth.oauth import (
    refresh_access_token as gemini_refresh,
    ANTIGRAVITY_HEADERS,
    ANTIGRAVITY_ENDPOINTS,
    ANTIGRAVITY_DEFAULT_PROJECT_ID,
    ANTIGRAVITY_API_VERSION,
)
from ..auth.openai_oauth import refresh_access_token as openai_refresh
from ..hooks.manager import get_hook_manager

# ========================
# SESSION & HTTP MANAGEMENT
# ========================

# Session cache for thinking signature persistence across multi-turn conversations
# Key: conversation_key (or "default"), Value: session UUID
_SESSION_CACHE: dict[str, str] = {}

# Pooled HTTP client for connection reuse
_HTTP_CLIENT: httpx.AsyncClient | None = None

# Rate limiting: Max 5 concurrent Gemini requests to prevent burst rate limits
_GEMINI_SEMAPHORE: asyncio.Semaphore | None = None


def _get_session_id(conversation_key: str | None = None) -> str:
    """
    Get or create persistent session ID for thinking signature caching.

    Per Antigravity API: session IDs must persist across multi-turn to maintain
    thinking signature cache. Creating new UUID per call breaks this.

    Args:
        conversation_key: Optional key to scope session (e.g., per-agent)

    Returns:
        Stable session UUID for this conversation
    """
    import uuid as uuid_module  # Local import workaround

    key = conversation_key or "default"
    if key not in _SESSION_CACHE:
        _SESSION_CACHE[key] = str(uuid_module.uuid4())
    return _SESSION_CACHE[key]


def clear_session_cache() -> None:
    """Clear session cache (for thinking recovery on error)."""
    _SESSION_CACHE.clear()


async def _get_http_client() -> httpx.AsyncClient:
    """
    Get or create pooled HTTP client for connection reuse.

    Reusing a single client across requests improves performance
    by maintaining connection pools.
    """
    global _HTTP_CLIENT
    if _HTTP_CLIENT is None or _HTTP_CLIENT.is_closed:
        _HTTP_CLIENT = httpx.AsyncClient(timeout=120.0)
    return _HTTP_CLIENT


def _get_gemini_semaphore() -> asyncio.Semaphore:
    """
    Get or create semaphore for Gemini API rate limiting.

    Limits concurrent Gemini requests to prevent burst rate limits (429 errors).
    Max 5 concurrent requests balances throughput with API quota constraints.
    """
    global _GEMINI_SEMAPHORE
    if _GEMINI_SEMAPHORE is None:
        _GEMINI_SEMAPHORE = asyncio.Semaphore(5)
    return _GEMINI_SEMAPHORE


def _extract_gemini_response(data: dict) -> str:
    """
    Extract text from Gemini response, handling thinking blocks.

    Per Antigravity API, responses may contain:
    - text: Regular response text
    - thought: Thinking block content (when thinkingConfig enabled)
    - thoughtSignature: Signature for caching (ignored)

    Args:
        data: Raw API response JSON

    Returns:
        Extracted text, with thinking blocks formatted as <thinking>...</thinking>
    """
    try:
        # Unwrap the outer "response" envelope if present
        inner_response = data.get("response", data)
        candidates = inner_response.get("candidates", [])

        if not candidates:
            return "No response generated"

        content = candidates[0].get("content", {})
        parts = content.get("parts", [])

        if not parts:
            return "No response parts"

        text_parts = []
        thinking_parts = []

        for part in parts:
            if "thought" in part:
                thinking_parts.append(part["thought"])
            elif "text" in part:
                text_parts.append(part["text"])
            # Skip thoughtSignature parts

        # Combine results
        result = "".join(text_parts)

        # Prepend thinking blocks if present
        if thinking_parts:
            thinking_content = "".join(thinking_parts)
            result = f"<thinking>\n{thinking_content}\n</thinking>\n\n{result}"

        return result if result.strip() else "No response generated"

    except (KeyError, IndexError, TypeError) as e:
        return f"Error parsing response: {e}"


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
                f"Token refresh failed: {e}. Run: python -m mcp_bridge.auth.cli login {provider}"
            )

    access_token = token_store.get_access_token(provider)
    if not access_token:
        raise ValueError(
            f"Not authenticated with {provider}. "
            f"Run: python -m mcp_bridge.auth.cli login {provider}"
        )

    return access_token


def is_retryable_exception(e: Exception) -> bool:
    """
    Check if an exception is retryable (5xx only, NOT 429).

    429 (Rate Limit) errors should fail fast - retrying makes the problem worse
    by adding more requests to an already exhausted quota. The semaphore prevents
    these in the first place, but if one slips through, we shouldn't retry.
    """
    if isinstance(e, httpx.HTTPStatusError):
        # Only retry server errors (5xx), not rate limits (429)
        return 500 <= e.response.status_code < 600
    return False


async def _invoke_gemini_with_api_key(
    api_key: str,
    prompt: str,
    model: str = "gemini-3-flash",
    temperature: float = 0.7,
    max_tokens: int = 4096,
    thinking_budget: int = 0,
    image_path: str | None = None,
) -> str:
    """
    Invoke Gemini using API key authentication (google-genai library).

    This is an alternative to OAuth authentication that uses the official
    google-genai Python library with a simple API key.

    Args:
        api_key: Gemini API key (from GEMINI_API_KEY or GOOGLE_API_KEY env var)
        prompt: The prompt to send to Gemini
        model: Gemini model to use (e.g., "gemini-2.0-flash-exp")
        temperature: Sampling temperature (0.0-2.0)
        max_tokens: Maximum tokens in response
        thinking_budget: Tokens reserved for internal reasoning (if supported)
        image_path: Optional path to image/PDF for vision analysis

    Returns:
        The model's response text.

    Raises:
        ImportError: If google-genai library is not installed
        ValueError: If API request fails
    """
    try:
        from google import genai
    except ImportError:
        raise ImportError(
            "google-genai library not installed. Install with: pip install google-genai"
        )

    # Map stravinsky model names to google-genai model names
    # google-genai uses different model naming (e.g., "gemini-2.0-flash-exp")
    model_map = {
        "gemini-3-flash": "gemini-2.0-flash-exp",
        "gemini-3-pro-low": "gemini-2.0-flash-exp",
        "gemini-3-pro-high": "gemini-exp-1206",  # Experimental model
        "gemini-flash": "gemini-2.0-flash-exp",
        "gemini-pro": "gemini-2.0-flash-exp",
        "gemini-3-pro": "gemini-2.0-flash-exp",
        "gemini": "gemini-2.0-flash-exp",
    }
    genai_model = model_map.get(model, model)  # Pass through if not in map

    try:
        # Initialize client with API key
        client = genai.Client(api_key=api_key)

        # Build generation config
        config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }

        # Add thinking budget if supported (experimental feature)
        if thinking_budget > 0:
            config["thinking_config"] = {
                "thinking_budget": thinking_budget,
            }

        # Build contents - text prompt plus optional image
        contents = [prompt]

        # Add image data for vision analysis
        if image_path:
            from pathlib import Path

            image_file = Path(image_path)
            if image_file.exists():
                # google-genai supports direct file path or base64
                # For simplicity, use the file path directly
                contents.append(image_file)
                logger.info(f"[API_KEY] Added vision data: {image_path}")

        # Generate content
        response = client.models.generate_content(
            model=genai_model,
            contents=contents,
            config=config,
        )

        # Extract text from response
        if hasattr(response, 'text'):
            return response.text
        elif hasattr(response, 'candidates') and response.candidates:
            # Fallback: extract from candidates
            candidate = response.candidates[0]
            if hasattr(candidate, 'content'):
                parts = candidate.content.parts
                text_parts = [part.text for part in parts if hasattr(part, 'text')]
                return "".join(text_parts) if text_parts else "No response generated"

        return "No response generated"

    except Exception as e:
        logger.error(f"API key authentication failed: {e}")
        raise ValueError(f"Gemini API key request failed: {e}")


@retry(
    stop=stop_after_attempt(2),  # Reduced from 5 to 2 attempts
    wait=wait_exponential(multiplier=2, min=10, max=120),  # Longer waits: 10s → 20s → 40s
    retry=retry_if_exception(is_retryable_exception),
    before_sleep=lambda retry_state: logger.info(
        f"Server error, retrying in {retry_state.next_action.sleep} seconds..."
    ),
)
async def invoke_gemini(
    token_store: TokenStore,
    prompt: str,
    model: str = "gemini-3-flash",
    temperature: float = 0.7,
    max_tokens: int = 4096,
    thinking_budget: int = 0,
    image_path: str | None = None,
) -> str:
    """
    Invoke a Gemini model with the given prompt.

    Supports two authentication methods (API key takes precedence):
    1. API Key: Set GEMINI_API_KEY or GOOGLE_API_KEY in environment
    2. OAuth: Use Google OAuth via Antigravity (requires stravinsky-auth login gemini)

    Supports vision API for image/PDF analysis when image_path is provided.

    Args:
        token_store: Token store for OAuth credentials
        prompt: The prompt to send to Gemini
        model: Gemini model to use
        temperature: Sampling temperature (0.0-2.0)
        max_tokens: Maximum tokens in response
        thinking_budget: Tokens reserved for internal reasoning
        image_path: Optional path to image/PDF for vision analysis (token optimization)

    Returns:
        The model's response text.

    Raises:
        ValueError: If not authenticated with Gemini
        httpx.HTTPStatusError: If API request fails
    """
    logger.info(f"[DEBUG] invoke_gemini called, uuid module check: {uuid}")
    # Execute pre-model invoke hooks
    params = {
        "prompt": prompt,
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "thinking_budget": thinking_budget,
        "token_store": token_store,  # Pass for hooks that need model access
        "provider": "gemini",  # Identify which provider is being called
    }
    hook_manager = get_hook_manager()
    params = await hook_manager.execute_pre_model_invoke(params)

    # Update local variables from possibly modified params
    prompt = params["prompt"]
    model = params["model"]
    temperature = params["temperature"]
    max_tokens = params["max_tokens"]
    thinking_budget = params["thinking_budget"]

    # Extract agent context for logging (may be passed via params or original call)
    agent_context = params.get("agent_context", {})
    agent_type = agent_context.get("agent_type", "direct")
    task_id = agent_context.get("task_id", "")
    description = agent_context.get("description", "")
    prompt_summary = _summarize_prompt(prompt)

    # Log with agent context and prompt summary
    logger.info(f"[{agent_type}] → {model}: {prompt_summary}")

    # USER-VISIBLE NOTIFICATION (stderr) - Shows when Gemini is invoked
    import sys
    task_info = f" task={task_id}" if task_id else ""
    desc_info = f" | {description}" if description else ""
    print(f"🔮 GEMINI: {model} | agent={agent_type}{task_info}{desc_info}", file=sys.stderr)

    # Check for API key authentication (takes precedence over OAuth)
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if api_key:
        logger.info(f"[{agent_type}] Using API key authentication (GEMINI_API_KEY)")
        return await _invoke_gemini_with_api_key(
            api_key=api_key,
            prompt=prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            thinking_budget=thinking_budget,
            image_path=image_path,
        )

    # Fallback to OAuth authentication (Antigravity)
    logger.info(f"[{agent_type}] Using OAuth authentication (Antigravity)")
    # Acquire semaphore to limit concurrent Gemini requests (prevents 429 rate limits)
    semaphore = _get_gemini_semaphore()
    async with semaphore:
        access_token = await _ensure_valid_token(token_store, "gemini")

        # Resolve user-friendly model name to actual API model ID
        api_model = resolve_gemini_model(model)

        # Use persistent session ID for thinking signature caching
        session_id = _get_session_id()
        project_id = os.getenv("STRAVINSKY_ANTIGRAVITY_PROJECT_ID", ANTIGRAVITY_DEFAULT_PROJECT_ID)

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            **ANTIGRAVITY_HEADERS,  # Include Antigravity headers
        }

        # Build inner request payload
        # Per API spec: contents must include role ("user" or "model")

        # Build parts list - text prompt plus optional image
        parts = [{"text": prompt}]

        # Add image data for vision analysis (token optimization for multimodal)
        if image_path:
            import base64
            from pathlib import Path

            image_file = Path(image_path)
            if image_file.exists():
                # Determine MIME type
                suffix = image_file.suffix.lower()
                mime_types = {
                    ".png": "image/png",
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".gif": "image/gif",
                    ".webp": "image/webp",
                    ".pdf": "application/pdf",
                }
                mime_type = mime_types.get(suffix, "image/png")

                # Read and base64 encode
                image_data = base64.b64encode(image_file.read_bytes()).decode("utf-8")

                # Add inline image data for Gemini Vision API
                parts.append({
                    "inlineData": {
                        "mimeType": mime_type,
                        "data": image_data,
                    }
                })
                logger.info(f"[multimodal] Added vision data: {image_path} ({mime_type})")

        inner_payload = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
            "sessionId": session_id,
        }

        # Add thinking budget if supported by model/API
        if thinking_budget > 0:
            # For Gemini 2.0+ Thinking models
            # Per Antigravity API: use "thinkingBudget", NOT "tokenLimit"
            inner_payload["generationConfig"]["thinkingConfig"] = {
                "includeThoughts": True,
                "thinkingBudget": thinking_budget,
            }

        # Wrap request body per reference implementation
        try:
            import uuid as uuid_module  # Local import workaround for MCP context issue

            request_id = f"invoke-{uuid_module.uuid4()}"
        except Exception as e:
            logger.error(f"UUID IMPORT FAILED: {e}")
            raise RuntimeError(f"CUSTOM ERROR: UUID import failed: {e}")

        wrapped_payload = {
            "project": project_id,
            "model": api_model,
            "userAgent": "antigravity",
            "requestId": request_id,
            "request": inner_payload,
        }

        # Get pooled HTTP client for connection reuse
        client = await _get_http_client()

        # Try endpoints in fallback order with thinking recovery
        response = None
        last_error = None
        max_retries = 2  # For thinking recovery

        for retry_attempt in range(max_retries):
            for endpoint in ANTIGRAVITY_ENDPOINTS:
                # Reference uses: {endpoint}/v1internal:generateContent (NOT /models/{model})
                api_url = f"{endpoint}/v1internal:generateContent"

                try:
                    response = await client.post(
                        api_url,
                        headers=headers,
                        json=wrapped_payload,
                        timeout=120.0,
                    )

                    # 401/403 might be endpoint-specific, try next endpoint
                    if response.status_code in (401, 403):
                        logger.warning(
                            f"[Gemini] Endpoint {endpoint} returned {response.status_code}, trying next"
                        )
                        last_error = Exception(f"{response.status_code} from {endpoint}")
                        continue

                    # Check for thinking-related errors that need recovery
                    if response.status_code in (400, 500):
                        error_text = response.text.lower()
                        if "thinking" in error_text or "signature" in error_text:
                            logger.warning(
                                f"[Gemini] Thinking error detected, clearing session cache and retrying"
                            )
                            clear_session_cache()
                            # Update session ID for retry
                            wrapped_payload["request"]["sessionId"] = _get_session_id()
                            last_error = Exception(f"Thinking error: {response.text[:200]}")
                            break  # Break inner loop to retry with new session

                    # If we got a non-retryable response (success or 4xx client error), use it
                    if response.status_code < 500 and response.status_code != 429:
                        break

                except httpx.TimeoutException as e:
                    last_error = e
                    continue
                except Exception as e:
                    last_error = e
                    continue
            else:
                # Inner loop completed without break - no thinking recovery needed
                break

            # If we broke out of inner loop for thinking recovery, continue outer retry loop
            if response and response.status_code in (400, 500):
                continue
            break

        if response is None:
            # FALLBACK: Try Claude sonnet-4.5 for agents that support it
            agent_context = params.get("agent_context", {})
            agent_type = agent_context.get("agent_type", "unknown")

            if agent_type in ("dewey", "explore", "document_writer", "multimodal"):
                logger.warning(f"[{agent_type}] Gemini failed, falling back to Claude sonnet-4.5")
                try:
                    import subprocess
                    fallback_result = subprocess.run(
                        ["claude", "-p", prompt, "--model", "sonnet", "--output-format", "text"],
                        capture_output=True,
                        text=True,
                        timeout=120,
                        cwd=os.getcwd(),
                    )
                    if fallback_result.returncode == 0 and fallback_result.stdout.strip():
                        return fallback_result.stdout.strip()
                except Exception as fallback_error:
                    logger.error(f"Fallback to Claude also failed: {fallback_error}")

            raise ValueError(f"All Antigravity endpoints failed: {last_error}")

        response.raise_for_status()
        data = response.json()

        # Extract text from response using thinking-aware parser
        return _extract_gemini_response(data)


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
                            "description": "Absolute or relative path to the file",
                        }
                    },
                    "required": ["path"],
                },
            },
            {
                "name": "list_directory",
                "description": "List files and directories in a path",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Directory path to list"}
                    },
                    "required": ["path"],
                },
            },
            {
                "name": "grep_search",
                "description": "Search for a pattern in files using ripgrep. Returns matching lines with file paths and line numbers.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "The search pattern (regex)"},
                        "path": {"type": "string", "description": "Directory or file to search in"},
                    },
                    "required": ["pattern", "path"],
                },
            },
            {
                "name": "write_file",
                "description": "Write content to a file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to the file to write"},
                        "content": {
                            "type": "string",
                            "description": "Content to write to the file",
                        },
                    },
                    "required": ["path", "content"],
                },
            },
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
                timeout=30,
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
    access_token = await _ensure_valid_token(token_store, "gemini")
    api_model = resolve_gemini_model(model)

    # Use persistent session ID for this conversation
    session_id = _get_session_id(conversation_key="agentic")

    # Project ID from environment or default
    project_id = os.getenv("STRAVINSKY_ANTIGRAVITY_PROJECT_ID", ANTIGRAVITY_DEFAULT_PROJECT_ID)

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        **ANTIGRAVITY_HEADERS,
    }

    # Initialize conversation
    contents = [{"role": "user", "parts": [{"text": prompt}]}]

    # Get pooled HTTP client for connection reuse
    client = await _get_http_client()

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
        import uuid as uuid_module  # Local import workaround

        wrapped_payload = {
            "project": project_id,
            "model": api_model,
            "userAgent": "antigravity",
            "requestId": f"agent-{uuid_module.uuid4()}",
            "request": inner_payload,
        }

        # Try endpoints in fallback order
        response = None
        last_error = None

        for endpoint in ANTIGRAVITY_ENDPOINTS:
            # Reference uses: {endpoint}/v1internal:generateContent (NOT /models/{model})
            api_url = f"{endpoint}/v1internal:generateContent"

            try:
                response = await client.post(
                    api_url,
                    headers=headers,
                    json=wrapped_payload,
                    timeout=float(timeout),
                )

                # 401/403 might be endpoint-specific, try next endpoint
                if response.status_code in (401, 403):
                    logger.warning(
                        f"[AgenticGemini] Endpoint {endpoint} returned {response.status_code}, trying next"
                    )
                    last_error = Exception(f"{response.status_code} from {endpoint}")
                    continue

                # If we got a non-retryable response (success or 4xx client error), use it
                if response.status_code < 500 and response.status_code != 429:
                    break

                logger.warning(
                    f"[AgenticGemini] Endpoint {endpoint} returned {response.status_code}, trying next"
                )

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

        # Extract response - unwrap outer "response" envelope if present
        inner_response = data.get("response", data)
        candidates = inner_response.get("candidates", [])
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

            logger.info(f"[AgenticGemini] Turn {turn + 1}: Executing {func_name}")
            result = _execute_tool(func_name, func_args)

            # Add model's response and function result to conversation
            contents.append({"role": "model", "parts": [{"functionCall": function_call}]})
            contents.append(
                {
                    "role": "user",
                    "parts": [
                        {"functionResponse": {"name": func_name, "response": {"result": result}}}
                    ],
                }
            )
        else:
            # No function call, return text response
            return text_response or "Task completed"

    return "Max turns reached without final response"


@retry(
    stop=stop_after_attempt(2),  # Reduced from 5 to 2 attempts
    wait=wait_exponential(multiplier=2, min=10, max=120),  # Longer waits: 10s → 20s → 40s
    retry=retry_if_exception(is_retryable_exception),
    before_sleep=lambda retry_state: logger.info(
        f"Server error, retrying in {retry_state.next_action.sleep} seconds..."
    ),
)
async def invoke_openai(
    token_store: TokenStore,
    prompt: str,
    model: str = "gpt-5.2-codex",
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
        "token_store": token_store,  # Pass for hooks that need model access
        "provider": "openai",  # Identify which provider is being called
    }
    hook_manager = get_hook_manager()
    params = await hook_manager.execute_pre_model_invoke(params)

    # Update local variables from possibly modified params
    prompt = params["prompt"]
    model = params["model"]
    temperature = params["temperature"]
    max_tokens = params["max_tokens"]
    thinking_budget = params["thinking_budget"]

    # Extract agent context for logging (may be passed via params or original call)
    agent_context = params.get("agent_context", {})
    agent_type = agent_context.get("agent_type", "direct")
    task_id = agent_context.get("task_id", "")
    description = agent_context.get("description", "")
    prompt_summary = _summarize_prompt(prompt)

    # Log with agent context and prompt summary
    logger.info(f"[{agent_type}] → {model}: {prompt_summary}")

    # USER-VISIBLE NOTIFICATION (stderr) - Shows when OpenAI is invoked
    import sys
    task_info = f" task={task_id}" if task_id else ""
    desc_info = f" | {description}" if description else ""
    print(f"🧠 OPENAI: {model} | agent={agent_type}{task_info}{desc_info}", file=sys.stderr)

    access_token = await _ensure_valid_token(token_store, "openai")
    logger.info(f"[invoke_openai] Got access token")

    # ChatGPT Backend API - Uses Codex Responses endpoint
    # Replicates opencode-openai-codex-auth plugin behavior
    api_url = "https://chatgpt.com/backend-api/codex/responses"

    # Extract account ID from JWT token
    logger.info(f"[invoke_openai] Extracting account ID from JWT")
    try:
        parts = access_token.split(".")
        payload_b64 = parts[1]
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        jwt_payload = json_module.loads(base64.urlsafe_b64decode(payload_b64))
        account_id = jwt_payload.get("https://api.openai.com/auth", {}).get("chatgpt_account_id")
    except Exception as e:
        logger.error(f"Failed to extract account ID from JWT: {e}")
        account_id = None

    # Fetch official Codex instructions from GitHub
    instructions = await _fetch_codex_instructions(model)

    # Headers matching opencode-openai-codex-auth plugin
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",  # SSE stream
        "openai-beta": "responses=experimental",
        "openai-originator": "codex_cli_rs",
    }

    if account_id:
        headers["x-openai-account-id"] = account_id

    # Request body matching opencode transformation
    payload = {
        "model": model,
        "store": False,  # Required by ChatGPT backend
        "stream": True,  # Always stream (handler converts to non-stream if needed)
        "instructions": instructions,
        "input": [{"role": "user", "content": prompt}],
        "reasoning": {"effort": "high" if thinking_budget > 0 else "medium", "summary": "auto"},
        "text": {"verbosity": "medium"},
        "include": ["reasoning.encrypted_content"],
    }

    # Stream the response and collect text
    text_chunks = []

    logger.info(f"[invoke_openai] Calling {api_url} with model {model}")
    logger.info(f"[invoke_openai] Payload keys: {list(payload.keys())}")
    logger.info(f"[invoke_openai] Instructions length: {len(instructions)}")

    try:
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST", api_url, headers=headers, json=payload, timeout=120.0
            ) as response:
                logger.info(f"[invoke_openai] Response status: {response.status_code}")
                if response.status_code == 401:
                    raise ValueError(
                        "OpenAI authentication failed. Run: stravinsky-auth login openai"
                    )

                if response.status_code >= 400:
                    error_body = await response.aread()
                    error_text = error_body.decode("utf-8")
                    logger.error(f"OpenAI API error {response.status_code}: {error_text}")
                    logger.error(f"Request payload was: {payload}")
                    logger.error(f"Request headers were: {headers}")
                    raise ValueError(f"OpenAI API error {response.status_code}: {error_text}")

                # Parse SSE stream for text deltas
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_json = line[6:]  # Remove "data: " prefix
                        try:
                            data = json_module.loads(data_json)
                            event_type = data.get("type")

                            # Extract text deltas from SSE stream
                            if event_type == "response.output_text.delta":
                                delta = data.get("delta", "")
                                text_chunks.append(delta)

                        except json_module.JSONDecodeError:
                            pass  # Skip malformed JSON
                        except Exception as e:
                            logger.warning(f"Error processing SSE event: {e}")

        # Return collected text
        result = "".join(text_chunks)
        if not result:
            return "No response generated"
        return result

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in invoke_openai: {e}")
        raise ValueError(f"Failed to invoke OpenAI: {e}")
