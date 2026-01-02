"""
Hooks Configuration for Claude Code

Claude Code supports hooks via .claude/settings.json or .claude/hooks/ directory.
This module provides utilities for working with Claude Code's native hooks system.

Claude Code Hooks (native):
- PreToolUse: Run before tool execution
- PostToolUse: Run after tool execution  
- UserPromptSubmit: Run when user submits a prompt
- Stop: Run when assistant stops generating

These hooks are configured in .claude/settings.json under the "hooks" key.
"""

import json
from pathlib import Path
from typing import Any


def get_hooks_config(project_path: str | None = None) -> dict[str, Any]:
    """
    Load Claude Code hooks configuration from .claude/settings.json.
    
    Args:
        project_path: Project directory (defaults to cwd)
        
    Returns:
        Hooks configuration dict.
    """
    project = Path(project_path) if project_path else Path.cwd()
    settings_file = project / ".claude" / "settings.json"
    
    if not settings_file.exists():
        return {}
    
    try:
        settings = json.loads(settings_file.read_text())
        return settings.get("hooks", {})
    except Exception:
        return {}


def list_hook_scripts(project_path: str | None = None) -> list[dict[str, Any]]:
    """
    List hook scripts from .claude/hooks/ directory.
    
    Args:
        project_path: Project directory
        
    Returns:
        List of hook script info.
    """
    project = Path(project_path) if project_path else Path.cwd()
    hooks_dir = project / ".claude" / "hooks"
    
    if not hooks_dir.exists():
        return []
    
    scripts = []
    for script in hooks_dir.glob("*"):
        if script.is_file() and (script.suffix in (".sh", ".py", ".js", ".ts") or script.stat().st_mode & 0o111):
            scripts.append({
                "name": script.name,
                "path": str(script),
                "type": script.suffix or "executable",
            })
    
    return scripts


def configure_hook(
    hook_type: str,
    command: str,
    project_path: str | None = None,
) -> str:
    """
    Add a hook configuration to .claude/settings.json.
    
    Args:
        hook_type: Hook type (PreToolUse, PostToolUse, UserPromptSubmit, Stop)
        command: Command to run for the hook
        project_path: Project directory
        
    Returns:
        Success or error message.
    """
    valid_hooks = ["PreToolUse", "PostToolUse", "UserPromptSubmit", "Stop"]
    if hook_type not in valid_hooks:
        return f"Invalid hook type. Valid types: {', '.join(valid_hooks)}"
    
    project = Path(project_path) if project_path else Path.cwd()
    settings_file = project / ".claude" / "settings.json"
    
    # Load existing settings
    settings = {}
    if settings_file.exists():
        try:
            settings = json.loads(settings_file.read_text())
        except Exception:
            pass
    
    # Add hook
    if "hooks" not in settings:
        settings["hooks"] = {}
    
    if hook_type not in settings["hooks"]:
        settings["hooks"][hook_type] = []
    
    settings["hooks"][hook_type].append({
        "type": "command",
        "command": command,
    })
    
    # Ensure directory exists
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        settings_file.write_text(json.dumps(settings, indent=2))
        return f"Added {hook_type} hook: {command}"
    except Exception as e:
        return f"Error saving settings: {e}"


HOOK_DOCUMENTATION = """
# Claude Code Hooks

Claude Code supports the following hook types:

## PreToolUse
Runs before a tool is executed. Can modify or block the tool call.

Example in .claude/settings.json:
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "type": "command",
        "command": "python .claude/hooks/check_tool.py",
        "tool_names": ["Write", "Edit"]
      }
    ]
  }
}
```

## PostToolUse
Runs after a tool completes. Can add warnings or modify output.

## UserPromptSubmit
Runs when user submits a prompt. Can augment the prompt.

## Stop
Runs when the assistant stops generating. Can trigger follow-up actions.

## Hook Script Environment Variables

Hooks receive context via environment variables:
- CLAUDE_SESSION_ID: Current session ID
- CLAUDE_TOOL_NAME: Name of tool (for tool hooks)
- CLAUDE_TOOL_INPUT: JSON of tool input
- CLAUDE_CWD: Current working directory

## Hook Exit Codes
- 0: Continue normally
- 1: Block/deny the operation
- 2+: Error (logged but continues)
"""


def get_hook_documentation() -> str:
    """Get documentation for Claude Code hooks."""
    return HOOK_DOCUMENTATION
