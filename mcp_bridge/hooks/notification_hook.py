#!/usr/bin/env python3
"""
Notification hook for agent spawn messages.

Fires on Notification events to output user-friendly messages about
which agent was spawned, what model it uses, and what task it's doing.

Format: spawned {agent_type}:{model}('{description}')
Example: spawned delphi:gpt-5.2-medium('Debug xyz code')
"""

import json
import os
import sys

# Agent display model mappings
AGENT_DISPLAY_MODELS = {
    "explore": "gemini-3-flash",
    "dewey": "gemini-3-flash",
    "document_writer": "gemini-3-flash",
    "multimodal": "gemini-3-flash",
    "frontend": "gemini-3-pro-high",
    "delphi": "gpt-5.2-medium",
    "planner": "opus-4.5",
    "code-reviewer": "sonnet-4.5",
    "debugger": "sonnet-4.5",
    "_default": "sonnet-4.5",
}


def extract_agent_info(message: str) -> dict[str, str] | None:
    """
    Extract agent spawn information from notification message.

    Looks for patterns like:
    - "Agent explore spawned for task..."
    - "Spawned delphi agent: description"
    - Task tool delegation messages
    """
    message_lower = message.lower()

    # Try to extract agent type from message
    agent_type = None
    description = ""

    for agent in AGENT_DISPLAY_MODELS:
        if agent == "_default":
            continue
        if agent in message_lower:
            agent_type = agent
            # Extract description after agent name
            idx = message_lower.find(agent)
            description = message[idx + len(agent) :].strip()[:60]
            break

    if not agent_type:
        return None

    # Clean up description
    description = description.strip(":-() ")
    if not description:
        description = "task delegated"

    display_model = AGENT_DISPLAY_MODELS.get(agent_type, AGENT_DISPLAY_MODELS["_default"])

    return {
        "agent_type": agent_type,
        "model": display_model,
        "description": description,
    }


def main():
    """Main hook entry point."""
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    # Get notification message
    message = hook_input.get("message", "")
    notification_type = hook_input.get("notification_type", "")

    # Only process agent-related notifications
    agent_keywords = ["agent", "spawn", "delegat", "task"]
    if not any(kw in message.lower() for kw in agent_keywords):
        return 0

    # Extract agent info
    agent_info = extract_agent_info(message)
    if not agent_info:
        return 0

    # Get repo name for context
    cwd = os.environ.get("CLAUDE_CWD", "")
    repo_name = os.path.basename(cwd) if cwd else ""

    # Format and output
    if repo_name:
        output = f"spawned [{repo_name}] {agent_info['agent_type']}:{agent_info['model']}('{agent_info['description']}')"
    else:
        output = f"spawned {agent_info['agent_type']}:{agent_info['model']}('{agent_info['description']}')"

    print(output, file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
