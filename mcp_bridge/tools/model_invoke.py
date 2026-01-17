"""
Model invocation tools for Gemini and OpenAI.

These tools use OAuth tokens from the token store to authenticate
API requests to external model providers.
"""

import asyncio
import base64
import json as json_module
import logging
import os
import time
import uuid

from mcp_bridge.config.rate_limits import get_rate_limiter, get_gemini_time_limiter

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

# ==============================================
# GEMINI AUTH MODE STATE (OAuth-first with 429 fallback)
# ==============================================
# When OAuth gets a 429 rate limit, we switch to API-only mode for 5 minutes.
# After 5 minutes, we automatically retry OAuth.
_GEMINI_OAUTH_429_TIMESTAMP: float | None = None  # Timestamp of last 429
_OAUTH_COOLDOWN_SECONDS = 300  # 5 minutes


def _get_gemini_api_key() -> str | None:
    """Get Gemini API key from environment (loaded from ~/.stravinsky/.env)."""
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def _set_api_only_mode(reason: str = "429 rate limit"):
    """Switch to API-only mode after OAuth rate limit (5-minute cooldown)."""
    global _GEMINI_OAUTH_429_TIMESTAMP
    _GEMINI_OAUTH_429_TIMESTAMP = time.time()
    logger.warning(f"[Gemini] Switching to API-only mode: {reason}")
    import sys

    print(
        f"⚠️ GEMINI: OAuth rate-limited (429). "
        f"Using API key for 5 minutes (will retry OAuth at {time.strftime('%H:%M:%S', time.localtime(_GEMINI_OAUTH_429_TIMESTAMP + _OAUTH_COOLDOWN_SECONDS))}).",
        file=sys.stderr,
    )


def _is_api_only_mode() -> bool:
    """
    Check if we're in API-only mode (5-minute cooldown after 429).

    Returns True if:
    - 429 occurred AND
    - Less than 5 minutes have elapsed

    Automatically resets to OAuth mode after 5 minutes.
    """
    global _GEMINI_OAUTH_429_TIMESTAMP

    if _GEMINI_OAUTH_429_TIMESTAMP is None:
        return False

    elapsed = time.time() - _GEMINI_OAUTH_429_TIMESTAMP

    if elapsed >= _OAUTH_COOLDOWN_SECONDS:
        # Cooldown expired - reset to OAuth mode
        logger.info(
            f"[Gemini] 5-minute cooldown expired (elapsed: {elapsed:.0f}s). Retrying OAuth."
        )
        _GEMINI_OAUTH_429_TIMESTAMP = None
        return False

    # Still in cooldown
    remaining = _OAUTH_COOLDOWN_SECONDS - elapsed
    logger.debug(f"[Gemini] API-only mode active ({remaining:.0f}s remaining)")
    return True


def reset_gemini_auth_mode():
    """Reset to OAuth-first mode. Call this to manually reset cooldown."""
    global _GEMINI_OAUTH_429_TIMESTAMP
    _GEMINI_OAUTH_429_TIMESTAMP = None
    logger.info("[Gemini] Reset to OAuth-first mode")


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
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from ..auth.oauth import (
    ANTIGRAVITY_DEFAULT_PROJECT_ID,
    ANTIGRAVITY_ENDPOINTS,
    ANTIGRAVITY_HEADERS,
)
from ..auth.oauth import (
    refresh_access_token as gemini_refresh,
)
from ..auth.openai_oauth import refresh_access_token as openai_refresh
from ..auth.token_store import TokenStore
from ..hooks.manager import get_hook_manager

# ========================
# SESSION & HTTP MANAGEMENT
# ========================

# Session cache for thinking signature persistence across multi-turn conversations
# Key: conversation_key (or "default"), Value: session UUID
_SESSION_CACHE: dict[str, str] = {}

# Pooled HTTP client for connection reuse
_HTTP_CLIENT: httpx.AsyncClient | None = None

# Per-model semaphores for async rate limiting (uses config from ~/.stravinsky/config.json)
_GEMINI_SEMAPHORES: dict[str, asyncio.Semaphore] = {}


def _get_gemini_rate_limit(model: str) -> int:
    """
    Get configured rate limit for a Gemini model.

    Reads from ~/.stravinsky/config.json if available, otherwise uses defaults.

    Args:
        model: Gemini model name (e.g., "gemini-3-flash", "gemini-3-pro-high")

    Returns:
        Configured concurrency limit for this model
    """
    rate_limiter = get_rate_limiter()
    # Normalize model name to match config keys
    normalized = rate_limiter._normalize_model(model)
    return rate_limiter._limits.get(normalized, rate_limiter._limits.get("_default", 5))


def _get_gemini_semaphore(model: str) -> asyncio.Semaphore:
    """
    Get or create async semaphore for Gemini model rate limiting.

    Creates one semaphore per model type with limits from config.
    Limits can be customized in ~/.stravinsky/config.json:
    {
        "rate_limits": {
            "gemini-3-flash": 15,
            "gemini-3-pro-high": 8
        }
    }

    Args:
        model: Gemini model name

    Returns:
        asyncio.Semaphore with configured limit for this model
    """
    if model not in _GEMINI_SEMAPHORES:
        limit = _get_gemini_rate_limit(model)
        _GEMINI_SEMAPHORES[model] = asyncio.Semaphore(limit)
        logger.info(f"[RateLimit] Created semaphore for {model} with limit {limit}")
    return _GEMINI_SEMAPHORES[model]


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
    agent_context: dict | None = None,
) -> str:
    """
    Invoke Gemini using API key authentication (google-genai library).

    This is an alternative to OAuth authentication that uses the official
    google-genai Python library with a simple API key.

    Args:
        api_key: Gemini API key (from GEMINI_API_KEY or GOOGLE_API_KEY env var)
        prompt: The prompt to send to Gemini
        model: Gemini model to use (e.g., "gemini-3-flash-preview")
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
    # Pass through gemini-3-* models directly (Tier 3 benefits)
    model_map = {
        "gemini-3-flash": "gemini-3-flash-preview",  # Tier 3 model (not -exp)
        "gemini-3-flash-preview": "gemini-3-flash-preview",  # Pass through
        "gemini-3-pro-low": "gemini-3-flash-preview",
        "gemini-3-pro-high": "gemini-3-pro-preview",  # Tier 3 pro model
        "gemini-3-pro-preview": "gemini-3-pro-preview",  # Pass through
        "gemini-flash": "gemini-3-flash-preview",
        "gemini-pro": "gemini-3-pro-preview",
        "gemini-3-pro": "gemini-3-pro-preview",
        "gemini": "gemini-3-flash-preview",
    }
    genai_model = model_map.get(model, "gemini-3-flash-preview")  # Default to tier 3 flash

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

        # Track usage
        try:
            from mcp_bridge.metrics.cost_tracker import get_cost_tracker
            tracker = get_cost_tracker()
            if hasattr(response, "usage_metadata"):
                usage = response.usage_metadata
                agent_type = (agent_context or {}).get("agent_type", "unknown")
                task_id = (agent_context or {}).get("task_id", "")
                
                tracker.track_usage(
                    model=model,
                    input_tokens=usage.prompt_token_count,
                    output_tokens=usage.candidates_token_count,
                    agent_type=agent_type,
                    task_id=task_id
                )
        except Exception:
            pass

        # Extract text from response
        if hasattr(response, "text"):
            return response.text
        elif hasattr(response, "candidates") and response.candidates:
            # Fallback: extract from candidates
            candidate = response.candidates[0]
            if hasattr(candidate, "content"):
                parts = candidate.content.parts
                text_parts = [part.text for part in parts if hasattr(part, "text")]
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
    """
    from mcp_bridge.proxy.client import is_proxy_enabled, proxy_invoke_gemini

    if is_proxy_enabled():
        return await proxy_invoke_gemini(
            prompt=prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            thinking_budget=thinking_budget,
            image_path=image_path,
        )

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

    # Get API key from environment (loaded from ~/.stravinsky/.env)
    api_key = _get_gemini_api_key()
    import sys

    task_info = f" task={task_id}" if task_id else ""
    desc_info = f" | {description}" if description else ""

    # ==============================================
    # AUTH PRIORITY: OAuth first, API fallback on 429
    # ==============================================
    # 1. If API-only mode (after 429), use API key directly
    # 2. Otherwise, try OAuth first
    # 3. On 429 from OAuth, switch to API-only mode and retry

    # If we're in API-only mode (after a 429), use API key directly
    if _is_api_only_mode():
        if not api_key:
            raise ValueError(
                "OAuth rate-limited (429) and no API key available. "
                "Add GEMINI_API_KEY to ~/.stravinsky/.env"
            )

        # Calculate remaining cooldown time
        if _GEMINI_OAUTH_429_TIMESTAMP is not None:
            remaining = _OAUTH_COOLDOWN_SECONDS - (time.time() - _GEMINI_OAUTH_429_TIMESTAMP)
            remaining_mins = int(remaining // 60)
            remaining_secs = int(remaining % 60)
            cooldown_msg = f" (OAuth retry in {remaining_mins}m {remaining_secs}s)"
        else:
            cooldown_msg = ""

        # Check time-window rate limit (30 req/min)
        time_limiter = get_gemini_time_limiter()
        wait_time = time_limiter.acquire_visible("GEMINI", "API key")
        if wait_time > 0:
            await asyncio.sleep(wait_time)
            # Re-acquire after sleep
            wait_time = time_limiter.acquire_visible("GEMINI", "API key")

        print(
            f"🔑 GEMINI (API-only cooldown{cooldown_msg}): {model} | agent={agent_type}{task_info}{desc_info}",
            file=sys.stderr,
        )
        logger.info(f"[{agent_type}] Using API key (5-min cooldown after OAuth 429)")
        semaphore = _get_gemini_semaphore(model)
        async with semaphore:
            result = await _invoke_gemini_with_api_key(
                api_key=api_key,
                prompt=prompt,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                thinking_budget=thinking_budget,
                image_path=image_path,
                agent_context=agent_context,
            )
            # Prepend auth header for visibility in logs
            auth_header = f"[Auth: API key (5-min cooldown) | Model: {model}]\n\n"
            return auth_header + result

    # DEFAULT: Try OAuth first (Antigravity)

    # Check time-window rate limit (30 req/min)
    time_limiter = get_gemini_time_limiter()
    wait_time = time_limiter.acquire_visible("GEMINI", "OAuth")
    if wait_time > 0:
        await asyncio.sleep(wait_time)
        # Re-acquire after sleep
        wait_time = time_limiter.acquire_visible("GEMINI", "OAuth")

    print(
        f"🔮 GEMINI (OAuth): {model} | agent={agent_type}{task_info}{desc_info}",
        file=sys.stderr,
    )
    logger.info(f"[{agent_type}] Using OAuth authentication (Antigravity)")
    # Rate limit concurrent Gemini requests (configurable via ~/.stravinsky/config.json)
    semaphore = _get_gemini_semaphore(model)
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
                parts.append(
                    {
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": image_data,
                        }
                    }
                )
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
                                "[Gemini] Thinking error detected, clearing session cache and retrying"
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

        # ==============================================
        # 429 RATE LIMIT DETECTION: Fallback to API key
        # ==============================================
        # If OAuth got rate-limited (429), switch to API-only mode and retry with API key
        if response is not None and response.status_code == 429:
            api_key = _get_gemini_api_key()
            if api_key:
                _set_api_only_mode("OAuth rate-limited (429)")
                logger.info("[Gemini] Retrying with API key after OAuth 429")
                # Retry immediately with API key
                result = await _invoke_gemini_with_api_key(
                    api_key=api_key,
                    prompt=prompt,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    thinking_budget=thinking_budget,
                    image_path=image_path,
                    agent_context=agent_context,
                )
                # Prepend auth header for visibility
                auth_header = f"[Auth: API key (OAuth 429 fallback) | Model: {model}]\n\n"
                return auth_header + result
            else:
                # No API key available - raise clear error
                raise ValueError(
                    "OAuth rate-limited (429) and no API key available. "
                    "Add GEMINI_API_KEY to ~/.stravinsky/.env"
                )

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
                        result = fallback_result.stdout.strip()
                        # Prepend auth header for visibility
                        auth_header = f"[Auth: Claude fallback | Model: sonnet-4.5]\n\n"
                        return auth_header + result
                except Exception as fallback_error:
                    logger.error(f"Fallback to Claude also failed: {fallback_error}")

            raise ValueError(f"All Antigravity endpoints failed: {last_error}")

        response.raise_for_status()
        data = response.json()

        # Track usage
        try:
            from mcp_bridge.metrics.cost_tracker import get_cost_tracker
            tracker = get_cost_tracker()
            usage = data.get("usageMetadata", {})
            input_tokens = usage.get("promptTokenCount", 0)
            output_tokens = usage.get("candidatesTokenCount", 0)
            
            tracker.track_usage(
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                agent_type=agent_type,
                task_id=task_id
            )
        except Exception as e:
            logger.warning(f"Failed to track cost: {e}")

        # Extract text from response using thinking-aware parser
        result = _extract_gemini_response(data)

        # Prepend auth header for visibility in logs
        auth_header = f"[Auth: OAuth | Model: {model}]\n\n"
        return auth_header + result


# ========================
# AGENTIC FUNCTION CALLING
# ========================

# Tool definitions for background agents
AGENT_TOOLS = [
    {
        "functionDeclarations": [
            {
                "name": "semantic_search",
                "description": "Search codebase with natural language query using semantic embeddings. ALWAYS use this FIRST before grep_search or read_file to find relevant files efficiently. Returns code snippets with file paths and relevance scores.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language search query (e.g., 'find authentication logic', 'PDF rendering code')",
                        },
                        "project_path": {
                            "type": "string",
                            "description": "Path to the project root (default: '.')",
                        },
                        "n_results": {
                            "type": "integer",
                            "description": "Maximum number of results to return (default: 10)",
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "hybrid_search",
                "description": "Hybrid search combining semantic similarity with structural AST pattern matching. Use when you need precise structural patterns (e.g., specific function signatures) combined with semantic relevance.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language search query (e.g., 'find authentication logic')",
                        },
                        "pattern": {
                            "type": "string",
                            "description": "Optional ast-grep pattern for structural matching (e.g., 'def $FUNC($$$):', 'async function $NAME($$$)')",
                        },
                        "project_path": {
                            "type": "string",
                            "description": "Path to the project root (default: '.')",
                        },
                        "n_results": {
                            "type": "integer",
                            "description": "Maximum number of results to return (default: 10)",
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "read_file",
                "description": "Read the contents of a file. Returns the file contents as text. USE ONLY AFTER semantic_search identifies the target file.",
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
                "description": "Search for a pattern in files using ripgrep. Returns matching lines with file paths and line numbers. USE ONLY for precise pattern matching AFTER semantic_search narrows down the search scope.",
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
    import subprocess
    from pathlib import Path

    try:
        if name == "semantic_search":
            # Import semantic_search function from tools
            import asyncio
            from .semantic_search import semantic_search

            # Extract args with defaults
            query = args.get("query")
            if not query:
                return "Error: 'query' parameter is required for semantic_search"

            project_path = args.get("project_path", ".")
            n_results = args.get("n_results", 10)

            # Run async function in sync context
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(
                semantic_search(
                    query=query,
                    project_path=project_path,
                    n_results=n_results,
                )
            )
            return result

        elif name == "hybrid_search":
            # Import hybrid_search function from tools
            import asyncio
            from .semantic_search import hybrid_search

            # Extract args with defaults
            query = args.get("query")
            if not query:
                return "Error: 'query' parameter is required for hybrid_search"

            pattern = args.get("pattern")
            project_path = args.get("project_path", ".")
            n_results = args.get("n_results", 10)

            # Run async function in sync context
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(
                hybrid_search(
                    query=query,
                    pattern=pattern,
                    project_path=project_path,
                    n_results=n_results,
                )
            )
            return result

        elif name == "read_file":
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


async def _invoke_gemini_agentic_with_api_key(
    api_key: str,
    prompt: str,
    model: str = "gemini-3-flash",
    max_turns: int = 10,
    timeout: int = 120,
) -> str:
    """
    Invoke Gemini with function calling using API key authentication (google-genai library).

    This implements a multi-turn agentic loop:
    1. Send prompt with tool definitions
    2. If model returns FunctionCall, execute the tool
    3. Send FunctionResponse back to model
    4. Repeat until model returns text or max_turns reached

    Args:
        api_key: Gemini API key (from GEMINI_API_KEY or GOOGLE_API_KEY env var)
        prompt: The task prompt
        model: Gemini model to use
        max_turns: Maximum number of tool-use turns
        timeout: Request timeout in seconds (currently unused by google-genai)

    Returns:
        Final text response from the model

    Raises:
        ImportError: If google-genai library is not installed
        ValueError: If API request fails
    """
    # USER-VISIBLE NOTIFICATION (stderr) - Shows agentic mode with API key
    import sys

    print(f"🔮 GEMINI (API/Agentic): {model} | max_turns={max_turns}", file=sys.stderr)

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        raise ImportError(
            "google-genai library not installed. Install with: pip install google-genai"
        )

    # Map stravinsky model names to google-genai model names
    # Pass through gemini-3-* models directly (Tier 3 benefits)
    model_map = {
        "gemini-3-flash": "gemini-3-flash-preview",  # Tier 3 model (not -exp)
        "gemini-3-flash-preview": "gemini-3-flash-preview",  # Pass through
        "gemini-3-pro-low": "gemini-3-flash-preview",
        "gemini-3-pro-high": "gemini-3-pro-preview",  # Tier 3 pro model
        "gemini-3-pro-preview": "gemini-3-pro-preview",  # Pass through
        "gemini-flash": "gemini-3-flash-preview",
        "gemini-pro": "gemini-3-pro-preview",
        "gemini-3-pro": "gemini-3-pro-preview",
        "gemini": "gemini-3-flash-preview",
    }
    genai_model = model_map.get(model, "gemini-3-flash-preview")  # Default to tier 3 flash

    # Initialize client with API key
    client = genai.Client(api_key=api_key)

    # Convert AGENT_TOOLS to google-genai format
    # google-genai expects tools as a list of Tool objects containing function_declarations
    function_declarations = []
    for tool_group in AGENT_TOOLS:
        for func_decl in tool_group.get("functionDeclarations", []):
            function_declarations.append(
                types.FunctionDeclaration(
                    name=func_decl["name"],
                    description=func_decl["description"],
                    parameters=func_decl["parameters"],
                )
            )

    # Wrap function declarations in a Tool object
    tools = [types.Tool(function_declarations=function_declarations)]

    # Initialize conversation with user message
    contents = [types.Content(role="user", parts=[types.Part(text=prompt)])]

    for turn in range(max_turns):
        try:
            # Generate content with tools
            response = client.models.generate_content(
                model=genai_model,
                contents=contents,
                config=types.GenerateContentConfig(
                    tools=tools,
                    temperature=0.7,
                    max_output_tokens=8192,
                ),
            )

            # Check if response has function calls
            if not response.candidates or not response.candidates[0].content.parts:
                return "No response generated"

            parts = response.candidates[0].content.parts
            function_calls = []
            text_parts = []

            for part in parts:
                if part.function_call:
                    function_calls.append(part.function_call)
                elif part.text:
                    text_parts.append(part.text)

            # If no function calls, return text response
            if not function_calls:
                result = "".join(text_parts)
                return result if result.strip() else "Task completed"

            # Execute function calls and prepare responses
            function_responses = []
            for func_call in function_calls:
                func_name = func_call.name
                func_args = dict(func_call.args) if func_call.args else {}

                logger.info(f"[AgenticGemini] Turn {turn + 1}: Executing {func_name}")
                result = _execute_tool(func_name, func_args)

                function_responses.append(
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=func_name,
                            response={"result": result},
                        )
                    )
                )

            # Add model's response to conversation
            contents.append(response.candidates[0].content)

            # Add function responses to conversation
            contents.append(
                types.Content(
                    role="user",
                    parts=function_responses,
                )
            )

        except Exception as e:
            logger.error(f"[AgenticGemini] Error in turn {turn + 1}: {e}")
            raise ValueError(f"Gemini API key request failed: {e}")

    return "Max turns reached without final response"


async def invoke_gemini_agentic(
    token_store: TokenStore,
    prompt: str,
    model: str = "gemini-3-flash",
    max_turns: int = 10,
    timeout: int = 120,
) -> str:
    """
    Invoke Gemini with function calling for agentic tasks.
    """
    from mcp_bridge.proxy.client import is_proxy_enabled, PROXY_URL

    if is_proxy_enabled():
        import httpx
        async with httpx.AsyncClient(timeout=float(timeout) + 10) as client:
            payload = {
                "prompt": prompt,
                "model": model,
                "max_turns": max_turns,
                "timeout": timeout
            }
            response = await client.post(f"{PROXY_URL}/v1/gemini/agentic", json=payload)
            response.raise_for_status()
            return response.json()["response"]

    import sys

    # Get API key from environment (loaded from ~/.stravinsky/.env)
    api_key = _get_gemini_api_key()

    # ==============================================
    # AUTH PRIORITY: OAuth first, API fallback on 429
    # ==============================================
    # 1. If API-only mode (after 429), use API key directly
    # 2. Otherwise, try OAuth first
    # 3. On 429 from OAuth, switch to API-only mode and retry

    # If we're in API-only mode (after a 429), use API key directly
    if _is_api_only_mode():
        if not api_key:
            raise ValueError(
                "OAuth rate-limited (429) and no API key available. "
                "Add GEMINI_API_KEY to ~/.stravinsky/.env"
            )

        # Calculate remaining cooldown time
        if _GEMINI_OAUTH_429_TIMESTAMP is not None:
            remaining = _OAUTH_COOLDOWN_SECONDS - (time.time() - _GEMINI_OAUTH_429_TIMESTAMP)
            remaining_mins = int(remaining // 60)
            remaining_secs = int(remaining % 60)
            cooldown_msg = f" (OAuth retry in {remaining_mins}m {remaining_secs}s)"
        else:
            cooldown_msg = ""

        # Check time-window rate limit (30 req/min)
        time_limiter = get_gemini_time_limiter()
        wait_time = time_limiter.acquire_visible("GEMINI", "API key")
        if wait_time > 0:
            await asyncio.sleep(wait_time)
            # Re-acquire after sleep
            wait_time = time_limiter.acquire_visible("GEMINI", "API key")

        print(
            f"🔑 GEMINI (API-only cooldown{cooldown_msg}/Agentic): {model} | max_turns={max_turns}",
            file=sys.stderr,
        )
        logger.info("[AgenticGemini] Using API key (5-min cooldown after OAuth 429)")
        result = await _invoke_gemini_agentic_with_api_key(
            api_key=api_key,
            prompt=prompt,
            model=model,
            max_turns=max_turns,
            timeout=timeout,
        )
        # Prepend auth header for visibility in logs
        auth_header = f"[Auth: API key (5-min cooldown, Agentic) | Model: {model}]\n\n"
        return auth_header + result

    # DEFAULT: Try OAuth first (Antigravity)
    logger.info("[AgenticGemini] Using OAuth authentication (Antigravity)")

    # Check time-window rate limit (30 req/min)
    time_limiter = get_gemini_time_limiter()
    wait_time = time_limiter.acquire_visible("GEMINI", "OAuth")
    if wait_time > 0:
        await asyncio.sleep(wait_time)
        # Re-acquire after sleep
        wait_time = time_limiter.acquire_visible("GEMINI", "OAuth")

    # USER-VISIBLE NOTIFICATION (stderr) - Shows agentic mode with OAuth
    import sys

    print(f"🔮 GEMINI (OAuth/Agentic): {model} | max_turns={max_turns}", file=sys.stderr)

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

        # ==============================================
        # 429 RATE LIMIT DETECTION: Fallback to API key
        # ==============================================
        # If OAuth got rate-limited (429), switch to API-only mode and retry
        if response is not None and response.status_code == 429:
            api_key = _get_gemini_api_key()
            if api_key:
                _set_api_only_mode("OAuth rate-limited (429) in agentic mode")
                logger.info("[AgenticGemini] Retrying with API key after OAuth 429")
                # Retry entire agentic call with API key
                result = await _invoke_gemini_agentic_with_api_key(
                    api_key=api_key,
                    prompt=prompt,
                    model=model,
                    max_turns=max_turns,
                    timeout=timeout,
                )
                # Prepend auth header for visibility
                auth_header = f"[Auth: API key (OAuth 429 fallback, Agentic) | Model: {model}]\n\n"
                return auth_header + result
            else:
                # No API key available - raise clear error
                raise ValueError(
                    "OAuth rate-limited (429) and no API key available. "
                    "Add GEMINI_API_KEY to ~/.stravinsky/.env"
                )

        if response is None:
            raise ValueError(f"All Antigravity endpoints failed: {last_error}")

        response.raise_for_status()
        data = response.json()

        # Extract response - unwrap outer "response" envelope if present
        inner_response = data.get("response", data)
        candidates = inner_response.get("candidates", [])
        if not candidates:
            auth_header = f"[Auth: OAuth (Agentic) | Model: {model}]\n\n"
            return auth_header + "No response generated"

        content = candidates[0].get("content", {})
        parts = content.get("parts", [])

        if not parts:
            auth_header = f"[Auth: OAuth (Agentic) | Model: {model}]\n\n"
            return auth_header + "No response parts"

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
            result = text_response or "Task completed"
            auth_header = f"[Auth: OAuth (Agentic) | Model: {model}]\n\n"
            return auth_header + result

    auth_header = f"[Auth: OAuth (Agentic) | Model: {model}]\n\n"
    return auth_header + "Max turns reached without final response"


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
    reasoning_effort: str = "medium",
) -> str:
    """
    Invoke an OpenAI model with the given prompt.
    """
    from mcp_bridge.proxy.client import is_proxy_enabled, proxy_invoke_openai

    if is_proxy_enabled():
        return await proxy_invoke_openai(
            prompt=prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            thinking_budget=thinking_budget,
            reasoning_effort=reasoning_effort,
        )

    # Execute pre-model invoke hooks
    params = {
        "prompt": prompt,
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "thinking_budget": thinking_budget,
        "reasoning_effort": reasoning_effort,
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
    reasoning_effort = params.get("reasoning_effort", "medium")

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
    logger.info("[invoke_openai] Got access token")

    # ChatGPT Backend API - Uses Codex Responses endpoint
    # Replicates opencode-openai-codex-auth plugin behavior
    api_url = "https://chatgpt.com/backend-api/codex/responses"

    # Extract account ID from JWT token
    logger.info("[invoke_openai] Extracting account ID from JWT")
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

    # Determine final effort
    # Legacy: thinking_budget > 0 implies high effort
    effort = "high" if thinking_budget > 0 else reasoning_effort

    # Request body matching opencode transformation
    payload = {
        "model": model,
        "store": False,  # Required by ChatGPT backend
        "stream": True,  # Always stream (handler converts to non-stream if needed)
        "instructions": instructions,
        "input": [{"role": "user", "content": prompt}],
        "reasoning": {"effort": effort, "summary": "auto"},
        "text": {"verbosity": "medium"},
        "include": ["reasoning.encrypted_content"],
    }

    # Stream the response and collect text
    text_chunks = []

    logger.info(f"[invoke_openai] Calling {api_url} with model {model}")
    logger.info(f"[invoke_openai] Payload keys: {list(payload.keys())}")
    logger.info(f"[invoke_openai] Instructions length: {len(instructions)}")

    try:
        async with (
            httpx.AsyncClient() as client,
            client.stream(
                "POST", api_url, headers=headers, json=payload, timeout=120.0
            ) as response,
        ):
            logger.info(f"[invoke_openai] Response status: {response.status_code}")
            if response.status_code == 401:
                raise ValueError("OpenAI authentication failed. Run: stravinsky-auth login openai")

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
        
        # Track estimated usage
        try:
            from mcp_bridge.metrics.cost_tracker import get_cost_tracker
            tracker = get_cost_tracker()
            # Estimate: 4 chars per token
            input_tokens = len(prompt) // 4
            output_tokens = len(result) // 4
            
            tracker.track_usage(
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                agent_type=agent_type,
                task_id=task_id
            )
        except Exception as e:
            logger.warning(f"Failed to track cost: {e}")

        if not result:
            return "No response generated"
        return result

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in invoke_openai: {e}")
        raise ValueError(f"Failed to invoke OpenAI: {e}")
