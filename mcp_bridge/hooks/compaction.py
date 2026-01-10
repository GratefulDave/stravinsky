"""
Preemptive context compaction hook.
Monitors context size and injects optimization reminders.
"""

from typing import Any

THRESHOLD_CHARS = 100000 # Roughly 25k-30k tokens for typical LLM text

COMPACTION_REMINDER = """
> **[SYSTEM ALERT - CONTEXT WINDOW NEAR LIMIT]**
> The current conversation history is reaching its limits. Performance may degrade.
> Please **STOP** and perform a **Session Compaction**:
> 1. Summarize all work completed so far in a `TASK_STATE.md` (if not already done).
> 2. List all pending todos.
> 3. Clear unnecessary tool outputs from your reasoning.
> 4. Keep your next responses concise and focused only on the current sub-task.
"""

async def context_compaction_hook(params: dict[str, Any]) -> dict[str, Any] | None:
    """
    Checks prompt length and injects a compaction reminder if it's too large.
    """
    prompt = params.get("prompt", "")
    
    if len(prompt) > THRESHOLD_CHARS:
        # Check if we haven't already injected the reminder recently
        if "CONTEXT WINDOW NEAR LIMIT" not in prompt:
            params["prompt"] = COMPACTION_REMINDER + prompt
            return params
            
    return None
