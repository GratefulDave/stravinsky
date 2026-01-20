#!/usr/bin/env python3
"""
PostToolUse hook for Claude rate limit detection.

Monitors model invocation responses for Claude-specific rate limit indicators
and updates the provider state tracker accordingly.
"""

import json
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from routing import get_provider_tracker
except ImportError:
    get_provider_tracker = None  # type: ignore


logger = logging.getLogger(__name__)

# Claude rate limit indicators
CLAUDE_RATE_LIMIT_PATTERNS = [
    "rate limit",
    "rate_limit_error",
    "too many requests",
    "429",
    "quota exceeded",
    "rate-limited",
    "overloaded_error",
]


def detect_claude_rate_limit(tool_result: str | dict) -> bool:
    """
    Detect if a tool result indicates Claude rate limiting.

    Args:
        tool_result: Tool result string or dict

    Returns:
        True if rate limit detected, False otherwise
    """
    # Convert result to searchable string
    if isinstance(tool_result, dict):
        search_text = json.dumps(tool_result).lower()
    else:
        search_text = str(tool_result).lower()

    # Check for rate limit patterns
    for pattern in CLAUDE_RATE_LIMIT_PATTERNS:
        if pattern in search_text:
            logger.info(f"[ClaudeLimitsHook] Detected rate limit pattern: {pattern}")
            return True

    return False


def main() -> None:
    """Process PostToolUse hook event."""
    try:
        # Read hook input from stdin
        hook_input = json.loads(sys.stdin.read())

        tool_name = hook_input.get("tool_name", "")
        tool_result = hook_input.get("tool_result", "")

        # Only monitor invoke tools (Claude uses default Claude models)
        # We're looking for rate limits from the main Claude context
        # This is different from invoke_openai/invoke_gemini which are explicit
        if not any(
            keyword in tool_name.lower() for keyword in ["invoke", "chat", "generate", "complete"]
        ):
            # Not a model invocation tool - skip
            sys.exit(0)

        # Check for rate limit indicators
        if detect_claude_rate_limit(tool_result):
            logger.warning("[ClaudeLimitsHook] Claude rate limit detected")

            if get_provider_tracker and callable(get_provider_tracker):
                tracker = get_provider_tracker()
                if tracker:
                    tracker.mark_rate_limited("claude", duration=300, reason="Claude rate limit")
                    logger.info("[ClaudeLimitsHook] Marked Claude as rate-limited (300s cooldown)")

                    print(
                        "\n⚠️ Claude Rate Limit Detected\n"
                        "→ Routing future requests to OpenAI/Gemini for 5 minutes\n",
                        file=sys.stderr,
                    )
            else:
                logger.debug(
                    "[ClaudeLimitsHook] Provider tracker not available, skipping state update"
                )

        sys.exit(0)

    except Exception as e:
        # Log error but don't block
        logger.error(f"[ClaudeLimitsHook] Error: {e}", exc_info=True)
        print(f"[ClaudeLimitsHook] Warning: {e}", file=sys.stderr)
        sys.exit(0)  # Exit 0 to not block execution


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    main()
