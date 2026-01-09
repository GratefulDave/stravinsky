#!/usr/bin/env python3
"""
PostToolUse hook: Session Recovery (oh-my-opencode parity)

Detects API failures, thinking block errors, and rate limits.
Logs recovery events and provides guidance for auto-retry.

This hook monitors tool responses for error patterns and:
1. Logs errors to ~/.claude/state/recovery.jsonl
2. Injects recovery guidance when errors are detected
3. Tracks failure patterns for debugging

Exit codes:
- 0: Always (this hook only observes and logs)
"""

import json
import sys
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# State directory for recovery logs
STATE_DIR = Path.home() / ".claude" / "state"
RECOVERY_LOG = STATE_DIR / "recovery.jsonl"

# Error patterns to detect
ERROR_PATTERNS = {
    "thinking_block": [
        r"thinking block",
        r"extended thinking",
        r"thinking budget exceeded",
        r"thinking timeout",
    ],
    "rate_limit": [
        r"rate limit",
        r"too many requests",
        r"429",
        r"quota exceeded",
        r"throttl",
    ],
    "api_timeout": [
        r"timeout",
        r"timed out",
        r"connection reset",
        r"connection refused",
        r"ETIMEDOUT",
        r"ECONNRESET",
    ],
    "api_error": [
        r"API error",
        r"internal server error",
        r"500",
        r"502",
        r"503",
        r"504",
        r"service unavailable",
    ],
    "context_overflow": [
        r"context length",
        r"token limit",
        r"max tokens",
        r"context window",
        r"too long",
    ],
    "auth_error": [
        r"unauthorized",
        r"401",
        r"403",
        r"forbidden",
        r"authentication failed",
        r"token expired",
    ],
}

# Recovery suggestions for each error type
RECOVERY_SUGGESTIONS = {
    "thinking_block": """
**Thinking Block Error Detected**

The model's extended thinking was interrupted. Recovery options:
1. Retry the same request (often works on second attempt)
2. Break the task into smaller steps
3. Reduce thinking budget if explicitly set

Automatic retry recommended.
""",
    "rate_limit": """
**Rate Limit Hit**

You've hit the API rate limit. Recovery options:
1. Wait 30-60 seconds before retrying
2. Reduce parallel agent spawns
3. Use cheaper models (gemini-3-flash) for exploration

Exponential backoff recommended: wait 30s, then 60s, then 120s.
""",
    "api_timeout": """
**API Timeout**

The API request timed out. Recovery options:
1. Retry immediately (network glitch)
2. Check internet connection
3. Reduce request complexity

Retry recommended.
""",
    "api_error": """
**API Error**

The API returned an error. Recovery options:
1. Wait 10 seconds and retry
2. Check API status page
3. Try a different model

Retry with backoff recommended.
""",
    "context_overflow": """
**Context Window Overflow**

The request exceeded the context limit. Recovery options:
1. Use /compact to reduce context
2. Break the task into smaller steps
3. Focus on specific files rather than entire codebase

Context reduction required before retry.
""",
    "auth_error": """
**Authentication Error**

Authentication failed. Recovery options:
1. Run `stravinsky-auth login gemini` or `stravinsky-auth login openai`
2. Check if tokens have expired
3. Verify API credentials

Re-authentication required.
""",
}


def ensure_state_dir():
    """Ensure the state directory exists."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def detect_error_type(text: str) -> Optional[str]:
    """
    Detect the type of error from response text.
    Returns the error type or None if no error detected.
    """
    text_lower = text.lower()

    for error_type, patterns in ERROR_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return error_type

    return None


def log_recovery_event(
    error_type: str, tool_name: str, response_snippet: str, session_id: Optional[str] = None
):
    """Log a recovery event to the JSONL file."""
    ensure_state_dir()

    event = {
        "timestamp": datetime.now().isoformat(),
        "error_type": error_type,
        "tool_name": tool_name,
        "response_snippet": response_snippet[:500],  # Truncate
        "session_id": session_id,
    }

    try:
        with open(RECOVERY_LOG, "a") as f:
            f.write(json.dumps(event) + "\n")
    except Exception:
        pass  # Don't fail on logging errors


def get_recent_failures(minutes: int = 5) -> int:
    """Count recent failures within the specified time window."""
    if not RECOVERY_LOG.exists():
        return 0

    cutoff = datetime.now().timestamp() - (minutes * 60)
    count = 0

    try:
        with open(RECOVERY_LOG, "r") as f:
            for line in f:
                try:
                    event = json.loads(line)
                    event_time = datetime.fromisoformat(event["timestamp"]).timestamp()
                    if event_time > cutoff:
                        count += 1
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue
    except Exception:
        pass

    return count


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    tool_name = hook_input.get("tool_name", "")
    tool_response = hook_input.get("tool_response", "")
    session_id = hook_input.get("session_id")

    # Convert response to string if needed
    if isinstance(tool_response, dict):
        response_text = json.dumps(tool_response)
    else:
        response_text = str(tool_response)

    # Detect error type
    error_type = detect_error_type(response_text)

    if error_type:
        # Log the event
        log_recovery_event(
            error_type=error_type,
            tool_name=tool_name,
            response_snippet=response_text[:500],
            session_id=session_id,
        )

        # Check for repeated failures
        recent_count = get_recent_failures(minutes=5)

        # Output recovery suggestion
        suggestion = RECOVERY_SUGGESTIONS.get(error_type, "")

        output = {
            "error_detected": True,
            "error_type": error_type,
            "recent_failures": recent_count,
            "suggestion": suggestion.strip(),
        }

        # If many recent failures, add escalation notice
        if recent_count >= 3:
            output["escalation"] = (
                f"⚠️ {recent_count} failures in last 5 minutes. "
                "Consider pausing and investigating the root cause."
            )

        # Print as JSON for downstream processing
        print(json.dumps(output))

    return 0


if __name__ == "__main__":
    sys.exit(main())
