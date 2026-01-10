"""
Auto Slash Command Hook.

Detects and auto-processes slash commands in user input:
- Parses `/command` patterns in user input
- Looks up matching skill via skill_loader
- Injects skill content into prompt
- Registered as pre_model_invoke hook
"""

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Pattern to match slash commands at the beginning of a line or after whitespace
SLASH_COMMAND_PATTERN = re.compile(r'(?:^|(?<=\s))\/([a-zA-Z][a-zA-Z0-9_-]*)\b', re.MULTILINE)


def extract_slash_commands(text: str) -> list[str]:
    """
    Extract all slash command names from text.

    Args:
        text: Input text to scan for slash commands

    Returns:
        List of command names (without the slash)
    """
    matches = SLASH_COMMAND_PATTERN.findall(text)
    # Deduplicate while preserving order
    seen = set()
    unique = []
    for match in matches:
        if match.lower() not in seen:
            seen.add(match.lower())
            unique.append(match)
    return unique


def load_skill_content(command_name: str, project_path: str | None = None) -> tuple[str, str] | None:
    """
    Load skill content by command name.

    Args:
        command_name: The command name to look up
        project_path: Optional project path for local skills

    Returns:
        Tuple of (skill_name, skill_content) or None if not found
    """
    from ..tools.skill_loader import discover_skills, parse_frontmatter

    skills = discover_skills(project_path)

    # Find matching skill (case-insensitive)
    skill = next(
        (s for s in skills if s["name"].lower() == command_name.lower()),
        None
    )

    if not skill:
        return None

    try:
        content = Path(skill["path"]).read_text()
        metadata, body = parse_frontmatter(content)

        # Build the skill injection block
        skill_block = f"""
---
## Skill: /{skill['name']}
**Source**: {skill['path']}
"""
        if metadata.get("description"):
            skill_block += f"**Description**: {metadata['description']}\n"

        if metadata.get("allowed-tools"):
            skill_block += f"**Allowed Tools**: {metadata['allowed-tools']}\n"

        skill_block += f"""
### Instructions:
{body}
---
"""
        return skill["name"], skill_block

    except Exception as e:
        logger.error(f"[AutoSlashCommand] Error loading skill '{command_name}': {e}")
        return None


def get_project_path_from_prompt(prompt: str) -> str | None:
    """
    Try to extract project path from prompt context.
    Looks for common patterns that indicate the working directory.
    """
    # Look for CWD markers
    cwd_patterns = [
        r'CWD:\s*([^\n]+)',
        r'Working directory:\s*([^\n]+)',
        r'project_path["\']?\s*[:=]\s*["\']?([^"\'}\n]+)',
    ]

    for pattern in cwd_patterns:
        match = re.search(pattern, prompt)
        if match:
            path = match.group(1).strip()
            if Path(path).exists():
                return path

    return None


SKILL_INJECTION_HEADER = """
> **[AUTO-SKILL INJECTION]**
> The following skill(s) have been automatically loaded based on slash commands detected in your input:
"""

SKILL_NOT_FOUND_WARNING = """
> **[SKILL NOT FOUND]**
> The slash command `/{command}` was detected but no matching skill was found.
> Available skills can be listed with the `skill_list` tool.
"""


async def auto_slash_command_hook(params: dict[str, Any]) -> dict[str, Any] | None:
    """
    Pre-model invoke hook that detects slash commands and injects skill content.

    Scans the prompt for /command patterns and loads corresponding skill files
    from .claude/commands/ directories.
    """
    prompt = params.get("prompt", "")

    # Skip if already processed
    if "[AUTO-SKILL INJECTION]" in prompt:
        return None

    # Extract slash commands
    commands = extract_slash_commands(prompt)

    if not commands:
        return None

    logger.info(f"[AutoSlashCommand] Detected slash commands: {commands}")

    # Try to get project path from prompt context
    project_path = get_project_path_from_prompt(prompt)

    # Load skills for each command
    injections = []
    warnings = []
    loaded_skills = []

    for command in commands:
        result = load_skill_content(command, project_path)
        if result:
            skill_name, skill_content = result
            injections.append(skill_content)
            loaded_skills.append(skill_name)
            logger.info(f"[AutoSlashCommand] Loaded skill: {skill_name}")
        else:
            warnings.append(SKILL_NOT_FOUND_WARNING.format(command=command))
            logger.warning(f"[AutoSlashCommand] Skill not found: {command}")

    if not injections and not warnings:
        return None

    # Build the injection block
    injection_block = ""

    if injections:
        injection_block = SKILL_INJECTION_HEADER
        injection_block += f"> Skills loaded: {', '.join(loaded_skills)}\n"
        injection_block += "\n".join(injections)

    if warnings:
        injection_block += "\n".join(warnings)

    # Prepend the injection to the prompt
    params["prompt"] = injection_block + "\n\n" + prompt

    return params
