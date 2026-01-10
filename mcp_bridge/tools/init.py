"""
Repository bootstrap logic for Stravinsky.
"""

import logging
from pathlib import Path

from .templates import CLAUDE_MD_TEMPLATE, SLASH_COMMANDS

logger = logging.getLogger(__name__)

def bootstrap_repo(project_path: str | Path | None = None) -> str:
    """
    Bootstrap a repository for Stravinsky MCP usage.
    
    Creates:
    - .claude/commands/ (with standard slash commands)
    - Appends/Creates CLAUDE.md
    """
    root = Path(project_path or Path.cwd())
    
    # 1. Setup Slash Commands
    commands_dir = root / ".claude" / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)
    
    commands_created = 0
    for filename, content in SLASH_COMMANDS.items():
        cmd_file = commands_dir / filename
        if not cmd_file.exists():
            cmd_file.write_text(content)
            commands_created += 1
            
    # 2. Setup CLAUDE.md
    claude_md = root / "CLAUDE.md"
    if not claude_md.exists():
        claude_md.write_text("# Project Notes\n\n" + CLAUDE_MD_TEMPLATE)
        claude_msg = "Created CLAUDE.md"
    else:
        content = claude_md.read_text()
        if "Stravinsky MCP" not in content:
            with open(claude_md, "a") as f:
                f.write("\n\n" + CLAUDE_MD_TEMPLATE)
            claude_msg = "Updated CLAUDE.md with Stravinsky instructions"
        else:
            claude_msg = "CLAUDE.md already configured"
            
    return (
        f"✅ Repository Initialized!\n"
        f"- {claude_msg}\n"
        f"- Installed {commands_created} new slash commands to .claude/commands/stra/"
    )
