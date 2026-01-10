"""
Agent Usage Reminder Hook.

When direct search tools (grep, glob, find) are used,
suggests using background agents for more comprehensive results.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

AGENT_SUGGESTION = """
[AGENT SUGGESTION]
You used `{tool_name}` directly. For more comprehensive results, consider:

**Background Agents (parallel, more thorough):**
```
background_task(agent="explore", prompt="Search for {search_context}...")
background_task(agent="dewey", prompt="Find documentation for {search_context}...")
```

Background agents can search multiple patterns simultaneously and provide richer context.
Use direct tools for quick, targeted lookups. Use agents for exploratory research.
"""

SEARCH_TOOLS = {"grep", "glob", "rg", "find", "Grep", "Glob", "grep_search", "glob_files"}


async def agent_reminder_hook(
    tool_name: str, arguments: dict[str, Any], output: str
) -> str | None:
    """
    Post-tool call hook that suggests background agents after direct search tool usage.
    """
    if tool_name not in SEARCH_TOOLS:
        return None

    search_context = _extract_search_context(arguments)

    if not search_context:
        return None

    if len(output) < 100:
        logger.info(
            f"[AgentReminder] Direct search '{tool_name}' returned limited results, suggesting agents"
        )
        suggestion = AGENT_SUGGESTION.format(tool_name=tool_name, search_context=search_context)
        return output + "\n" + suggestion

    return None


def _extract_search_context(arguments: dict[str, Any]) -> str:
    """Extract search context from tool arguments."""
    for key in ("pattern", "query", "search", "name", "path"):
        if key in arguments:
            value = arguments[key]
            if isinstance(value, str) and len(value) < 100:
                return value
    return "related patterns"
