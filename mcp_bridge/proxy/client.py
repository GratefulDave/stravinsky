import os
import httpx
import logging
from typing import Any, Optional

logger = logging.getLogger("stravinsky.proxy_client")

PROXY_URL = os.getenv("STRAVINSKY_PROXY_URL", "http://127.0.0.1:8765")

async def proxy_invoke_gemini(
    prompt: str,
    model: str = "gemini-3-flash",
    temperature: float = 0.7,
    max_tokens: int = 8192,
    thinking_budget: int = 0,
    image_path: Optional[str] = None,
    agent_context: Optional[dict[str, Any]] = None
) -> str:
    """Routes Gemini invocation to the proxy server."""
    payload = {
        "prompt": prompt,
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "thinking_budget": thinking_budget,
        "image_path": image_path,
        "agent_context": agent_context
    }
    
    async with httpx.AsyncClient(timeout=130.0) as client:
        try:
            response = await client.post(f"{PROXY_URL}/v1/gemini/generate", json=payload)
            response.raise_for_status()
            return response.json()["response"]
        except Exception as e:
            logger.error(f"Proxy request failed: {e}")
            raise

async def proxy_invoke_openai(
    prompt: str,
    model: str = "gpt-5.2-codex",
    temperature: float = 0.7,
    max_tokens: int = 4096,
    thinking_budget: int = 0,
    reasoning_effort: str = "medium",
    agent_context: Optional[dict[str, Any]] = None
) -> str:
    """Routes OpenAI invocation to the proxy server."""
    payload = {
        "prompt": prompt,
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "thinking_budget": thinking_budget,
        "reasoning_effort": reasoning_effort,
        "agent_context": agent_context
    }
    
    async with httpx.AsyncClient(timeout=130.0) as client:
        try:
            response = await client.post(f"{PROXY_URL}/v1/openai/chat", json=payload)
            response.raise_for_status()
            return response.json()["response"]
        except Exception as e:
            logger.error(f"Proxy request failed: {e}")
            raise

def is_proxy_enabled() -> bool:
    """Checks if proxy usage is enabled via environment variable."""
    return os.getenv("STRAVINSKY_USE_PROXY", "false").lower() == "true"
