"""
Model invocation tools for Gemini and OpenAI.

These tools use OAuth tokens from the token store to authenticate
API requests to external model providers.
"""

import time

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
    before_sleep=lambda retry_state: print(f"Rate limited or server error, retrying in {retry_state.next_action.sleep} seconds...")
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
    access_token = await _ensure_valid_token(token_store, "gemini")

    # Gemini API endpoint with OAuth
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        **ANTIGRAVITY_HEADERS,  # Include Antigravity headers
    }

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        },
    }
    
    # Add thinking budget if supported by model/API
    if thinking_budget > 0:
        # For Gemini 2.0+ Thinking models
        payload["generationConfig"]["thinkingConfig"] = {
            "includeThoughts": True,
            "tokenLimit": thinking_budget
        }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=120.0,
        )
        
        if response.status_code == 401:
            raise ValueError(
                "Gemini authentication expired. "
                "Run: python -m mcp_bridge.auth.cli login gemini"
            )
        
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


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception(is_retryable_exception),
    before_sleep=lambda retry_state: print(f"Rate limited or server error, retrying in {retry_state.next_action.sleep} seconds...")
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
