"""
Task Validator Hook (empty-task-response-detector equivalent).

Detects and warns about empty or failed Task tool execution results.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

EMPTY_PATTERNS = [
    r"^\s*$",  # Completely empty
    r"^null$",  # Null response
    r"^None$",  # Python None
    r"^undefined$",  # JavaScript undefined
    r"^{}$",  # Empty JSON object
    r"^\[\]$",  # Empty array
]

TASK_FAILURE_WARNING = """
[TASK EXECUTION WARNING]
The background task completed but returned empty or invalid output.

Possible causes:
- Agent terminated prematurely
- Tool execution failed silently
- Output was not captured properly
- Task encountered an unhandled exception

Recommended actions:
1. Check task logs for errors
2. Verify agent has proper tool access
3. Re-run task with explicit error handling
4. Use agent_progress(task_id) to monitor execution
"""


async def task_validator_hook(
    tool_name: str, tool_input: dict[str, Any], tool_response: str
) -> str:
    """
    Post-tool-call hook that validates Task tool responses.

    Detects empty/failed responses and injects diagnostic warning.
    """
    # Only validate Task tool responses
    if tool_name not in ["Task", "agent_spawn"]:
        return tool_response

    # Skip if response is non-empty and meaningful
    if tool_response and len(tool_response.strip()) > 50:
        return tool_response

    # Check for empty patterns
    response_stripped = tool_response.strip()
    for pattern in EMPTY_PATTERNS:
        if re.match(pattern, response_stripped, re.IGNORECASE):
            logger.warning(
                f"[TaskValidator] Empty/invalid response detected for {tool_name}"
            )
            # Inject warning but preserve original response
            return tool_response + "\n" + TASK_FAILURE_WARNING

    # Check for suspiciously short responses (< 10 chars)
    if len(response_stripped) < 10:
        logger.warning(
            f"[TaskValidator] Suspiciously short response ({len(response_stripped)} chars)"
        )
        return tool_response + "\n" + TASK_FAILURE_WARNING

    return tool_response
