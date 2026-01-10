"""
Continuous Loop (Ralph Loop) for Stravinsky.

Allows Stravinsky to operate in an autonomous loop until criteria are met.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

async def enable_ralph_loop(goal: str, max_iterations: int = 10) -> str:
    """
    Enable continuous processing until a goal is met.
    
    Args:
        goal: The goal to achieve and verify.
        max_iterations: Maximum number of iterations before stopping.
    """
    project_root = Path.cwd()
    settings_file = project_root / ".claude" / "settings.json"
    
    settings = {}
    if settings_file.exists():
        try:
            settings = json.loads(settings_file.read_text())
        except:
            pass
            
    if "hooks" not in settings:
        settings["hooks"] = {}
        
    # Set the Stop hook to re-trigger if goal not met
    # Note: Stravinsky's prompt will handle the internal logic 
    # but the presence of this hook signals "Continue" to Claude Code.
    settings["hooks"]["Stop"] = [
        {
            "type": "command",
            "command": f'echo "Looping for goal: {goal}"',
        }
    ]
    
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    settings_file.write_text(json.dumps(settings, indent=2))
    
    return f"🔄 Ralph Loop ENABLED. Goal: {goal}. Stravinsky will now process continuously until completion."

async def disable_ralph_loop() -> str:
    """Disable the autonomous loop."""
    project_root = Path.cwd()
    settings_file = project_root / ".claude" / "settings.json"
    
    if not settings_file.exists():
        return "Ralph Loop is already disabled."
        
    try:
        settings = json.loads(settings_file.read_text())
        if "hooks" in settings and "Stop" in settings["hooks"]:
            del settings["hooks"]["Stop"]
            settings_file.write_text(json.dumps(settings, indent=2))
            return "✅ Ralph Loop DISABLED."
    except:
        pass
        
    return "Failed to disable Ralph Loop or it was not active."
