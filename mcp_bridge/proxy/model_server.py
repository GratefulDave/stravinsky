import logging
import os
import time
import uuid
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from mcp_bridge.auth.token_store import TokenStore
from mcp_bridge.tools.model_invoke import invoke_gemini, invoke_openai

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("stravinsky.proxy")

app = FastAPI(title="Stravinsky Model Proxy")


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start_time = time.time()
    logger.info(f"[{request_id}] {request.method} {request.url.path}")
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-Request-ID"] = request_id
    logger.info(f"[{request_id}] Completed in {process_time:.4f}s")
    return response


# Shared token store
_token_store = None


def get_token_store():
    global _token_store
    if _token_store is None:
        _token_store = TokenStore()
    return _token_store


class GeminiRequest(BaseModel):
    prompt: str
    model: str = "gemini-3-flash"
    temperature: float = 0.7
    max_tokens: int = 8192
    thinking_budget: int = 0
    image_path: str | None = None
    agent_context: dict[str, Any] | None = None


class GeminiAgenticRequest(BaseModel):
    prompt: str
    model: str = "gemini-3-flash"
    max_turns: int = 10
    timeout: int = 120


class OpenAIRequest(BaseModel):
    prompt: str
    model: str = "gpt-5.2-codex"
    temperature: float = 0.7
    max_tokens: int = 4096
    thinking_budget: int = 0
    reasoning_effort: str = "medium"
    agent_context: dict[str, Any] | None = None


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/v1/gemini/generate")
async def gemini_generate(request: GeminiRequest):
    """Proxy endpoint for Gemini generation."""
    try:
        token_store = get_token_store()
        # We need to ensure agent_context is passed correctly if invoke_gemini supports it
        # Based on previous read, invoke_gemini takes image_path, but agent_context
        # might be extracted from hooks or passed in params.
        # Actually, invoke_gemini extracts it from params.

        response = await invoke_gemini(
            token_store=token_store,
            prompt=request.prompt,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            thinking_budget=request.thinking_budget,
            image_path=request.image_path,
        )
        return {"response": response}
    except Exception as e:
        logger.error(f"Error in gemini_generate proxy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/v1/gemini/agentic")
async def gemini_agentic(request: GeminiAgenticRequest):
    """Proxy endpoint for Agentic Gemini."""
    try:
        from mcp_bridge.tools.model_invoke import invoke_gemini_agentic

        token_store = get_token_store()
        response = await invoke_gemini_agentic(
            token_store=token_store,
            prompt=request.prompt,
            model=request.model,
            max_turns=request.max_turns,
            timeout=request.timeout,
        )
        return {"response": response}
    except Exception as e:
        logger.error(f"Error in gemini_agentic proxy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/v1/openai/chat")
async def openai_chat(request: OpenAIRequest):
    """Proxy endpoint for OpenAI chat."""
    try:
        token_store = get_token_store()
        response = await invoke_openai(
            token_store=token_store,
            prompt=request.prompt,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            thinking_budget=request.thinking_budget,
            reasoning_effort=request.reasoning_effort,
        )
        return {"response": response}
    except Exception as e:
        logger.error(f"Error in openai_chat proxy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


def main():
    """Entry point for the proxy server."""
    # CRITICAL: Disable proxy usage within the proxy process to avoid infinite loops
    os.environ["STRAVINSKY_USE_PROXY"] = "false"

    port = int(os.getenv("STRAVINSKY_PROXY_PORT", 8765))
    host = os.getenv("STRAVINSKY_PROXY_HOST", "127.0.0.1")
    logger.info(f"Starting Stravinsky Model Proxy on {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
