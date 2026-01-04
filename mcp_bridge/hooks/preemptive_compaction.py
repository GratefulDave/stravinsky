"""
Preemptive Context Compaction Hook.

Proactively compresses context BEFORE hitting limits by:
- Tracking estimated token usage
- Triggering compaction at 70% capacity (not waiting for errors)
- Using DCP -> Truncate -> Summarize pipeline
- Registered as pre_model_invoke hook
"""

import logging
import re
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Token estimation constants
CHARS_PER_TOKEN = 4  # Rough estimate for English text
MAX_CONTEXT_TOKENS = 200000  # Claude's context window
PREEMPTIVE_THRESHOLD = 0.70  # Trigger at 70% capacity
WARNING_THRESHOLD = 0.85  # Critical warning at 85%

# Calculate character thresholds
PREEMPTIVE_CHAR_THRESHOLD = int(MAX_CONTEXT_TOKENS * CHARS_PER_TOKEN * PREEMPTIVE_THRESHOLD)
WARNING_CHAR_THRESHOLD = int(MAX_CONTEXT_TOKENS * CHARS_PER_TOKEN * WARNING_THRESHOLD)


def estimate_tokens(text: str) -> int:
    """Estimate token count from character count."""
    return len(text) // CHARS_PER_TOKEN


def calculate_usage_percentage(text: str) -> float:
    """Calculate context window usage as a percentage."""
    estimated_tokens = estimate_tokens(text)
    return (estimated_tokens / MAX_CONTEXT_TOKENS) * 100


def apply_dcp_truncation(text: str, target_reduction: float = 0.3) -> str:
    """
    Apply DCP (Deferred Context Pruning) truncation strategy.

    Prioritizes keeping:
    1. System instructions (first ~10%)
    2. Recent context (last ~30%)
    3. Key structural elements in middle

    Args:
        text: The full context text
        target_reduction: How much to reduce (0.3 = reduce by 30%)

    Returns:
        Truncated text with summary markers
    """
    lines = text.split('\n')
    total_lines = len(lines)

    if total_lines < 100:
        # Small context, don't truncate
        return text

    # Calculate segment boundaries
    system_end = int(total_lines * 0.10)  # Keep first 10%
    recent_start = int(total_lines * 0.70)  # Keep last 30%

    # Extract segments
    system_segment = lines[:system_end]
    recent_segment = lines[recent_start:]
    middle_segment = lines[system_end:recent_start]

    # For middle segment, keep key structural elements
    kept_middle = []
    for line in middle_segment:
        # Keep lines with structural importance
        if any([
            line.strip().startswith('##'),  # Headers
            line.strip().startswith('def '),  # Function definitions
            line.strip().startswith('class '),  # Class definitions
            line.strip().startswith('- '),  # Bullet points
            'error' in line.lower(),  # Errors
            'warning' in line.lower(),  # Warnings
            'todo' in line.lower(),  # TODOs
        ]):
            kept_middle.append(line)

    # Limit middle to avoid bloat
    max_middle = int(total_lines * (1 - target_reduction) * 0.3)
    kept_middle = kept_middle[:max_middle]

    # Compose truncated context
    truncation_marker = f"\n[...{len(middle_segment) - len(kept_middle)} lines truncated for context optimization...]\n"

    result_lines = system_segment + [truncation_marker] + kept_middle + [truncation_marker] + recent_segment
    return '\n'.join(result_lines)


PREEMPTIVE_COMPACTION_NOTICE = """
> **[PREEMPTIVE CONTEXT OPTIMIZATION]**
> Context usage at {usage:.1f}% - proactively optimizing to maintain performance.
> The context has been structured for efficiency:
> - System instructions preserved
> - Recent interactions kept in full
> - Historical middle sections summarized
> - Key structural elements retained
"""

CRITICAL_WARNING = """
> **[CRITICAL - CONTEXT WINDOW AT {usage:.1f}%]**
> Immediate action recommended:
> 1. Complete current task and document results in TASK_STATE.md
> 2. Start a new session for fresh context
> 3. Reference TASK_STATE.md in new session for continuity
"""


async def preemptive_compaction_hook(params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Pre-model invoke hook that proactively compresses context before hitting limits.

    Uses a multi-tier strategy:
    - Below 70%: No action
    - 70-85%: Apply DCP truncation with notice
    - Above 85%: Apply aggressive truncation with critical warning
    """
    prompt = params.get("prompt", "")
    prompt_length = len(prompt)

    # Skip if already optimized recently
    if "[PREEMPTIVE CONTEXT OPTIMIZATION]" in prompt or "[CRITICAL - CONTEXT WINDOW" in prompt:
        return None

    usage = calculate_usage_percentage(prompt)

    if prompt_length >= WARNING_CHAR_THRESHOLD:
        # Critical level - aggressive truncation
        logger.warning(f"[PreemptiveCompaction] Critical context usage: {usage:.1f}%")

        truncated = apply_dcp_truncation(prompt, target_reduction=0.4)
        notice = CRITICAL_WARNING.format(usage=usage)
        params["prompt"] = notice + truncated

        logger.info(f"[PreemptiveCompaction] Applied aggressive truncation: {len(prompt)} -> {len(truncated)} chars")
        return params

    elif prompt_length >= PREEMPTIVE_CHAR_THRESHOLD:
        # Preemptive level - moderate truncation
        logger.info(f"[PreemptiveCompaction] Preemptive compaction at {usage:.1f}%")

        truncated = apply_dcp_truncation(prompt, target_reduction=0.3)
        notice = PREEMPTIVE_COMPACTION_NOTICE.format(usage=usage)
        params["prompt"] = notice + truncated

        logger.info(f"[PreemptiveCompaction] Applied moderate truncation: {len(prompt)} -> {len(truncated)} chars")
        return params

    # Below threshold, no action needed
    return None
