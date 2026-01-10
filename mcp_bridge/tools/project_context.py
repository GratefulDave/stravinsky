"""
Project Context and System Health Tools.

Provides the agent with environmental awareness (Git, Rules, Todos)
and ensures all required dependencies are installed and authenticated.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from ..auth.token_store import TokenStore


async def get_project_context(project_path: str | None = None) -> str:
    """
    Summarize project environment: Git status, local rules, and pending todos.
    
    Args:
        project_path: Path to the project root
        
    Returns:
        Formatted summary of the project context.
    """
    root = Path(project_path) if project_path else Path.cwd()
    context = []

    # 1. Git Information
    context.append("### 🌿 Git Context")
    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], 
            stderr=subprocess.DEVNULL, text=True
        ).strip()
        status = subprocess.check_output(
            ["git", "status", "--short"], 
            stderr=subprocess.DEVNULL, text=True
        ).strip()
        
        context.append(f"**Branch**: `{branch}`")
        if status:
            files_changed = len(status.split("\n"))
            context.append(f"**Status**: {files_changed} files modified (staged/unstaged)")
        else:
            context.append("**Status**: Clean")
    except Exception:
        context.append("**Status**: Not a git repository")

    # 2. Local Rules (.claude/rules/)
    rules_dir = root / ".claude" / "rules"
    if rules_dir.exists():
        context.append("\n### 📜 Local Project Rules")
        rule_files = list(rules_dir.glob("*.md"))
        if rule_files:
            for rf in rule_files:
                try:
                    content = rf.read_text().strip()
                    context.append(f"#### {rf.name}\n{content}")
                except Exception:
                    continue
        else:
            context.append("_No specific rules found in .claude/rules/_")

    # 3. Pending Todos
    context.append("\n### 📝 Pending Todos (Top 20)")
    try:
        # Search for [ ] in code files, excluding common noise directories
        todo_cmd = [
            "rg", "--line-number", "--no-heading", "--column",
            "--glob", "!.git/*", "--glob", "!node_modules/*",
            "--glob", "!.venv/*",
            r"\[ \]", str(root)
        ]
        todo_output = subprocess.check_output(
            todo_cmd, stderr=subprocess.DEVNULL, text=True
        ).strip()
        
        if todo_output:
            lines = todo_output.split("\n")[:20]
            for line in lines:
                context.append(f"- {line}")
            if len(todo_output.split("\n")) > 20:
                context.append("_(... and more)_")
        else:
            context.append("_No pending [ ] markers found._")
    except Exception:
        context.append("_Ripgrep not found or error searching for todos._")

    return "\n".join(context)


async def get_system_health() -> str:
    """
    Comprehensive check of system dependencies and authentication status.
    
    Returns:
        Checklist of system health.
    """
    health = ["## 🏥 Stravinsky System Health Report\n"]
    
    # 1. CLI Dependencies
    health.append("### 🛠️ CLI Dependencies")
    dependencies = {
        "rg": "ripgrep",
        "fd": "fd-find",
        "sg": "ast-grep",
        "gh": "GitHub CLI",
        "ruff": "Python Linter",
        "tsc": "TypeScript Compiler",
        "git": "Git"
    }
    
    for cmd, name in dependencies.items():
        path = shutil.which(cmd)
        status = "✅" if path else "❌"
        health.append(f"- {status} **{name}** (`{cmd}`): {'Installed' if path else 'MISSING'}")

    # 2. Authentication Status
    health.append("\n### 🔑 Provider Authentication")
    token_store = TokenStore()
    providers = ["gemini", "openai"]
    
    for p in providers:
        has_token = token_store.has_valid_token(p)
        status = "✅" if has_token else "❌"
        health.append(f"- {status} **{p.capitalize()}**: {'Authenticated' if has_token else 'NOT LOGGED IN'}")

    # 3. Environment
    health.append("\n### 🐍 Environment")
    health.append(f"- **Python**: `{sys.version.split()[0]}`")
    health.append(f"- **Virtualenv**: `{os.environ.get('VIRTUAL_ENV', 'None')}`")
    
    health.append("\n---")
    health.append("**Resolution Guide**:")
    health.append("- For missing CLI tools: Use `brew install` or `npm install -g` as appropriate.")
    health.append("- For Auth: Run `python -m mcp_bridge.auth.cli login [provider]`.")
    
    return "\n".join(health)
