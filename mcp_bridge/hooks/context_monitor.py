"""
Context Window Monitor Hook.

Monitors context window usage and provides headroom reminders.
At 70% usage, reminds the agent there's still capacity.
At 85%, suggests compaction before hitting hard limits.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

HEADROOM_REMINDER = """
[CONTEXT AWARENESS]
Current context usage: ~{usage:.0%}
You have approximately {remaining:.0%} headroom remaining.
Continue working - no compaction needed yet.
"""

COMPACTION_WARNING = """
[CONTEXT WARNING - PREEMPTIVE COMPACTION RECOMMENDED]
Current context usage: ~{usage:.0%}
Approaching context limit. Consider:
1. Completing current task quickly
2. Using `background_cancel(all=true)` to clean up agents
3. Summarizing findings before context overflow
"""

CONTEXT_THRESHOLD_REMINDER = 0.70
CONTEXT_THRESHOLD_WARNING = 0.85
ESTIMATED_MAX_TOKENS = 200000


async def context_monitor_hook(params: dict[str, Any]) -> dict[str, Any] | None:
    """
    Pre-model invoke hook that monitors context window usage.
    """
    prompt = params.get("prompt", "")
    estimated_tokens = len(prompt) / 4

    usage_ratio = estimated_tokens / ESTIMATED_MAX_TOKENS

    if usage_ratio >= CONTEXT_THRESHOLD_WARNING:
        remaining = 1.0 - usage_ratio
        logger.warning(f"[ContextMonitor] High context usage: {usage_ratio:.0%}")
        warning = COMPACTION_WARNING.format(usage=usage_ratio, remaining=remaining)
        params["prompt"] = prompt + "\n\n" + warning
        return params

    elif usage_ratio >= CONTEXT_THRESHOLD_REMINDER:
        remaining = 1.0 - usage_ratio
        logger.info(f"[ContextMonitor] Context usage: {usage_ratio:.0%}, reminding of headroom")
        reminder = HEADROOM_REMINDER.format(usage=usage_ratio, remaining=remaining)
        params["prompt"] = prompt + "\n\n" + reminder
        return params

    return None
