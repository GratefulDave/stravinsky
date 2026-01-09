#!/usr/bin/env python3
"""
PreToolUse hook: Comment Quality Enforcer (oh-my-opencode parity)

Fires BEFORE git commit/push operations to check for low-quality comments.
Challenges comments that just restate what the code does.

Exit codes:
- 0: Allow the operation to proceed
- 2: Block the operation (hard block)

Trigger: PreToolUse on Bash tool when command contains 'git commit' or 'git push'
"""

import json
import sys
import re
from pathlib import Path
from typing import List, Tuple, Optional

# Patterns that indicate low-quality comments
LOW_QUALITY_PATTERNS = [
    # Comments that just describe what code literally does
    r"#\s*(?:set|get|return|call|create|initialize|init)\s+\w+",
    # Comments that are just variable/function names repeated
    r"#\s*\w+\s*$",
    # Empty or trivial comments
    r"#\s*(?:TODO|FIXME|XXX|HACK)?\s*$",
    # Comments that state the obvious
    r"#\s*(?:loop|iterate|check|if|else|for|while)\s+(?:through|over|if|the)?\s*\w*\s*$",
    # Comments like "# increment i" or "# add 1 to x"
    r"#\s*(?:increment|decrement|add|subtract|multiply|divide)\s+\w+",
]

# Patterns for GOOD comments we should NOT flag
GOOD_COMMENT_PATTERNS = [
    # Docstrings and multi-line comments explaining WHY
    r'""".*"""',
    r"'''.*'''",
    # Comments explaining business logic or reasoning
    r"#\s*(?:because|since|note|important|warning|caution|reason|why|rationale)",
    # Comments with URLs or references
    r"#\s*(?:see|ref|https?://|link)",
    # Type hints or type comments
    r"#\s*type:",
    # Pragma or directive comments
    r"#\s*(?:noqa|type:|pragma|pylint|flake8)",
]


def is_low_quality_comment(comment: str) -> bool:
    """Check if a comment is low-quality (just restates code)."""
    comment_lower = comment.lower().strip()

    # Skip if it matches a good pattern
    for pattern in GOOD_COMMENT_PATTERNS:
        if re.search(pattern, comment_lower, re.IGNORECASE):
            return False

    # Check against low-quality patterns
    for pattern in LOW_QUALITY_PATTERNS:
        if re.search(pattern, comment_lower, re.IGNORECASE):
            return True

    # Very short comments (< 10 chars after #) are often low quality
    content = comment.replace("#", "").strip()
    if len(content) < 10 and not any(c in content for c in ["!", "?", ":", "TODO", "FIXME"]):
        return True

    return False


def extract_added_comments_from_diff(diff_text: str) -> List[Tuple[str, str]]:
    """
    Extract newly added comments from a git diff.
    Returns list of (filename, comment) tuples.
    """
    added_comments = []
    current_file = None

    for line in diff_text.split("\n"):
        # Track which file we're in
        if line.startswith("+++ b/"):
            current_file = line[6:]
        # Only look at added lines (starting with +, but not +++)
        elif line.startswith("+") and not line.startswith("+++"):
            content = line[1:]  # Remove the leading +
            # Check for Python comments
            if "#" in content and not content.strip().startswith("#!"):
                # Extract the comment part
                comment_match = re.search(r"#.*$", content)
                if comment_match:
                    comment = comment_match.group(0)
                    if current_file:
                        added_comments.append((current_file, comment))

    return added_comments


def check_staged_diff() -> Optional[str]:
    """
    Check the staged diff for low-quality comments.
    Returns a warning message if issues found, None otherwise.
    """
    import subprocess

    try:
        # Get the staged diff
        result = subprocess.run(
            ["git", "diff", "--cached", "--unified=0"], capture_output=True, text=True, timeout=10
        )

        if result.returncode != 0:
            return None  # Can't get diff, allow commit

        diff_text = result.stdout
        if not diff_text:
            return None  # No staged changes

        # Extract and check comments
        added_comments = extract_added_comments_from_diff(diff_text)
        low_quality = []

        for filename, comment in added_comments:
            if is_low_quality_comment(comment):
                low_quality.append((filename, comment))

        if low_quality:
            warning = "⚠️ **Comment Quality Check Failed**\n\n"
            warning += "The following comments appear to just restate the code:\n\n"
            for filename, comment in low_quality[:5]:  # Limit to 5 examples
                warning += f"- `{filename}`: `{comment[:50]}...`\n"
            warning += "\n**Good comments explain WHY, not WHAT.**\n"
            warning += "Consider removing or improving these comments.\n\n"
            warning += "To proceed anyway, use: `git commit --no-verify`"
            return warning

        return None

    except subprocess.TimeoutExpired:
        return None  # Timeout, allow commit
    except FileNotFoundError:
        return None  # Git not found, allow commit
    except Exception:
        return None  # Any other error, allow commit


def is_git_commit_command(command: str) -> bool:
    """Check if the command is a git commit or push."""
    command_lower = command.lower()
    return any(
        pattern in command_lower
        for pattern in [
            "git commit",
            "git push",
        ]
    )


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    # Only check Bash commands
    if tool_name != "Bash":
        return 0

    command = tool_input.get("command", "")

    # Only check git commit/push commands
    if not is_git_commit_command(command):
        return 0

    # Check for low-quality comments in staged diff
    warning = check_staged_diff()

    if warning:
        # Output warning to stderr (shown to user)
        print(warning, file=sys.stderr)
        # Return 0 to allow but warn, or 2 to block
        # We'll warn but allow - users can use --no-verify to skip
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
