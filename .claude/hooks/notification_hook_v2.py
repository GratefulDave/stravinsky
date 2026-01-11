#!/usr/bin/env python3
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "utils"))

try:
    from colors import get_agent_color, Color
    from console_format import format_agent_spawn
except ImportError:

    def get_agent_color(agent_type):
        return ("", "⚪")

    def format_agent_spawn(agent_type, model, description, color_code, emoji):
        lines = [f"{emoji} {agent_type.upper()} → {model}", f"   Task: {description}", ""]
        return "\n".join(lines)


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


def extract_agent_info(message):
    message_lower = message.lower()
    agent_type = None
    description = ""

    for agent in AGENT_DISPLAY_MODELS.keys():
        if agent == "_default":
            continue
        if agent in message_lower:
            agent_type = agent
            idx = message_lower.find(agent)
            description = message[idx + len(agent) :].strip()[:80]
            break

    if not agent_type:
        return None

    description = description.strip(":-() ")
    if not description:
        description = "task delegated"

    model = AGENT_DISPLAY_MODELS.get(agent_type, AGENT_DISPLAY_MODELS["_default"])
    color_code, emoji = get_agent_color(agent_type)

    return {
        "agent_type": agent_type,
        "model": model,
        "description": description,
        "color_code": color_code,
        "emoji": emoji,
    }


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    message = hook_input.get("message", "")
    agent_keywords = ["agent", "spawn", "delegat", "task"]
    if not any(kw in message.lower() for kw in agent_keywords):
        return 0

    agent_info = extract_agent_info(message)
    if not agent_info:
        return 0

    formatted = format_agent_spawn(
        agent_info["agent_type"],
        agent_info["model"],
        agent_info["description"],
        agent_info["color_code"],
        agent_info["emoji"],
    )
    print(formatted, file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
