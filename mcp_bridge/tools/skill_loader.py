"""
Skill Loader - Claude Code Slash Command Discovery

Discovers and lists available skills (slash commands) from:
1. Project-local .claude/commands/
2. User-global ~/.claude/commands/

Skills are markdown files with frontmatter defining the command behavior.
"""

import re
from pathlib import Path
from typing import Any


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """
    Parse YAML frontmatter from markdown content.

    Returns:
        Tuple of (metadata dict, body content)
    """
    if not content.startswith("---"):
        return {}, content

    # Find the closing ---
    end_match = content.find("---", 3)
    if end_match == -1:
        return {}, content

    frontmatter = content[3:end_match].strip()
    body = content[end_match + 3 :].strip()

    # Simple YAML parsing for key: value pairs
    metadata = {}
    for line in frontmatter.split("\n"):
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            metadata[key] = value

    return metadata, body


def discover_skills(project_path: str | None = None) -> list[dict[str, Any]]:
    """
    Discover available skills/commands.

    Searches:
    1. Project-local: {project}/.claude/commands/
    2. User-global: ~/.claude/commands/

    Args:
        project_path: Project directory to search (defaults to cwd)

    Returns:
        List of skill definitions.
    """
    skills = []
    search_paths = []

    # Project-local commands
    project = Path(project_path) if project_path else Path.cwd()
    project_commands = project / ".claude" / "commands"
    if project_commands.exists():
        search_paths.append(("project", project_commands))

    # User-global commands
    user_commands = Path.home() / ".claude" / "commands"
    if user_commands.exists():
        search_paths.append(("user", user_commands))

    for scope, commands_dir in search_paths:
        for md_file in commands_dir.glob("**/*.md"):
            try:
                content = md_file.read_text()
                metadata, body = parse_frontmatter(content)

                skills.append(
                    {
                        "name": md_file.stem,
                        "scope": scope,
                        "path": str(md_file),
                        "description": metadata.get("description", ""),
                        "allowed_tools": metadata.get("allowed-tools", "").split(",")
                        if metadata.get("allowed-tools")
                        else [],
                        "body_preview": body[:200] + "..." if len(body) > 200 else body,
                    }
                )
            except Exception:
                continue

    return skills


def list_skills(project_path: str | None = None) -> str:
    """
    List all available skills for MCP tool.

    Args:
        project_path: Project directory to search

    Returns:
        Formatted skill listing.
    """
    skills = discover_skills(project_path)

    if not skills:
        return "No skills found. Create .claude/commands/*.md files to add skills."

    lines = [f"Found {len(skills)} skill(s):\n"]

    for skill in skills:
        scope_badge = "[project]" if skill["scope"] == "project" else "[user]"
        lines.append(f"  /{skill['name']} {scope_badge}")
        if skill["description"]:
            lines.append(f"    {skill['description']}")

    return "\n".join(lines)


def get_skill(name: str, project_path: str | None = None) -> str:
    """
    Get the content of a specific skill.

    Args:
        name: Skill name (filename without .md)
        project_path: Project directory to search

    Returns:
        Skill content or error message.
    """
    skills = discover_skills(project_path)

    skill = next((s for s in skills if s["name"] == name), None)
    if not skill:
        available = ", ".join(s["name"] for s in skills)
        return f"Skill '{name}' not found. Available: {available or 'none'}"

    try:
        content = Path(skill["path"]).read_text()
        metadata, body = parse_frontmatter(content)

        lines = [
            f"## Skill: {name}",
            f"**Scope**: {skill['scope']}",
            f"**Path**: {skill['path']}",
        ]

        if metadata.get("description"):
            lines.append(f"**Description**: {metadata['description']}")

        if metadata.get("allowed-tools"):
            lines.append(f"**Allowed Tools**: {metadata['allowed-tools']}")

        lines.extend(["", "---", "", body])

        return "\n".join(lines)

    except Exception as e:
        return f"Error reading skill: {e}"


def create_skill(
    name: str,
    description: str,
    content: str,
    scope: str = "project",
    project_path: str | None = None,
) -> str:
    """
    Create a new skill file.

    Args:
        name: Skill name (will be used as filename)
        description: Short description for frontmatter
        content: Skill body content
        scope: "project" or "user"
        project_path: Project directory for project-scope skills

    Returns:
        Success or error message.
    """
    # Sanitize name
    name = re.sub(r"[^a-zA-Z0-9_-]", "-", name.lower())

    if scope == "project":
        base_dir = Path(project_path) if project_path else Path.cwd()
        commands_dir = base_dir / ".claude" / "commands"
    else:
        commands_dir = Path.home() / ".claude" / "commands"

    # Ensure directory exists
    commands_dir.mkdir(parents=True, exist_ok=True)

    skill_path = commands_dir / f"{name}.md"

    if skill_path.exists():
        return f"Skill '{name}' already exists at {skill_path}"

    # Create skill content
    skill_content = f"""---
description: {description}
---

{content}
"""

    try:
        skill_path.write_text(skill_content)
        return f"Created skill '{name}' at {skill_path}"
    except Exception as e:
        return f"Error creating skill: {e}"
