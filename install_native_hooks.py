import json
import os
from pathlib import Path

def install():
    project_root = Path.cwd()
    settings_path = project_root / ".claude" / "settings.json"
    
    # Create .claude directory if missing
    settings_path.parent.mkdir(exist_ok=True)

    # Initial settings
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text())
        except Exception:
            settings = {}
    else:
        settings = {}

    if "hooks" not in settings:
        settings["hooks"] = {}

    hooks = settings["hooks"]

    # Hook 1: UserPromptSubmit (Context)
    hooks["UserPromptSubmit"] = [
        {
            "type": "command",
            "command": f"python3 {project_root}/mcp_bridge/native_hooks/context.py"
        }
    ]

    # Hook 2: PostToolUse (Recovery & Truncation)
    # We chain them or use a dispatcher. Chaining is easier in the JSON.
    hooks["PostToolUse"] = [
        {
            "type": "command",
            "command": f"python3 {project_root}/mcp_bridge/native_hooks/truncator.py"
        },
        {
            "type": "command",
            "command": f"python3 {project_root}/mcp_bridge/native_hooks/edit_recovery.py",
            "matcher": ["Edit", "MultiEdit"]
        }
    ]

    # Save
    settings_path.write_text(json.dumps(settings, indent=2))
    print(f"✅ Stravinsky native hooks installed to {settings_path}")

if __name__ == "__main__":
    install()
