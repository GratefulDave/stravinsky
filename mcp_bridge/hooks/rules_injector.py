"""
Rules Injector Hook - Automatic Coding Standards Injection

ARCHITECTURE:
- Tier 2 Pre-Model-Invoke Hook
- Session-scoped caching with deduplication
- File path pattern matching via glob
- Priority-based rule ordering and truncation

DISCOVERY:
1. Searches .claude/rules/ (project-local and user-global)
2. Parses YAML frontmatter for globs and metadata
3. Caches discovered rules for session duration

MATCHING:
1. Extracts file paths from prompt context
2. Matches files against rule glob patterns
3. Sorts by priority (lower = higher)
4. Deduplicates via session cache

INJECTION:
1. Formats matched rules as markdown
2. Prepends to model prompt
3. Respects token budget (max 4k tokens)
4. Truncates low-priority rules if needed

ERROR HANDLING:
- Graceful degradation on all errors
- Never blocks model invocation
- Logs warnings for malformed rules
"""

import logging
import re
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Constants
MAX_RULES_TOKENS = 4000  # Reserve max 4k tokens for rules
TOKEN_ESTIMATE_RATIO = 4  # ~4 chars per token (conservative)

# Session-scoped caches
_rules_injection_cache: dict[str, set[str]] = {}
_session_rules_cache: dict[str, list] = {}


@dataclass(frozen=True)
class RuleFile:
    """Represents a discovered rule file with metadata."""
    name: str
    path: str
    scope: str  # "project" or "user"
    globs: tuple[str, ...]  # Use tuple instead of list for hashability
    description: str
    priority: int
    body: str
    enabled: bool = True


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """
    Parse YAML frontmatter from markdown content.

    Supports:
    - Simple key: value
    - Arrays: globs: ["*.py", "*.js"]
    - Multi-line arrays:
        globs:
          - "*.py"
          - "*.js"
    """
    if not content.startswith("---"):
        return {}, content

    end_match = content.find("---", 3)
    if end_match == -1:
        return {}, content

    frontmatter_block = content[3:end_match].strip()
    body = content[end_match + 3:].strip()

    metadata = {}
    current_key = None
    array_buffer = []

    for line in frontmatter_block.split("\n"):
        line = line.rstrip()

        # Array item: "  - value"
        if line.strip().startswith("-") and current_key:
            value = line.strip()[1:].strip().strip('"').strip("'")
            array_buffer.append(value)
            continue

        # Key-value pair
        if ":" in line:
            # Flush previous array
            if current_key and array_buffer:
                metadata[current_key] = array_buffer
                array_buffer = []

            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()

            # Inline array: globs: ["*.py", "*.js"]
            if value.startswith("[") and value.endswith("]"):
                values = value[1:-1].split(",")
                metadata[key] = [v.strip().strip('"').strip("'") for v in values if v.strip()]
                current_key = None
            # Empty value (likely multi-line array follows)
            elif not value:
                current_key = key
                array_buffer = []
            # Simple value
            else:
                metadata[key] = value.strip('"').strip("'")
                current_key = None

    # Flush final array
    if current_key and array_buffer:
        metadata[current_key] = array_buffer

    return metadata, body


def discover_rules(project_path: str | None = None) -> list[RuleFile]:
    """
    Discover all rule files from .claude/rules/ directories.

    Search order:
    1. Project-local: {project}/.claude/rules/**/*.md (highest priority)
    2. User-global: ~/.claude/rules/**/*.md (fallback)

    Returns:
        List of RuleFile objects sorted by priority (lower = higher)
    """
    rules = []
    search_paths = []

    # Project-local rules (highest priority)
    if project_path:
        project = Path(project_path)
    else:
        project = Path.cwd()

    project_rules = project / ".claude" / "rules"
    if project_rules.exists() and project_rules.is_dir():
        search_paths.append(("project", project_rules))

    # User-global rules (fallback)
    user_rules = Path.home() / ".claude" / "rules"
    if user_rules.exists() and user_rules.is_dir():
        search_paths.append(("user", user_rules))

    for scope, rules_dir in search_paths:
        try:
            for md_file in rules_dir.glob("**/*.md"):
                try:
                    content = md_file.read_text(encoding='utf-8')
                    metadata, body = parse_frontmatter(content)

                    # Parse globs from frontmatter
                    globs_raw = metadata.get("globs", [])

                    # Handle both string and list formats
                    if isinstance(globs_raw, str):
                        globs = [g.strip() for g in globs_raw.split(",") if g.strip()]
                    elif isinstance(globs_raw, list):
                        globs = [str(g).strip() for g in globs_raw if g]
                    else:
                        globs = []

                    if not globs:
                        logger.warning(f"[RulesInjector] Skipping {md_file.name}: no globs defined")
                        continue

                    # Parse enabled flag (default: true)
                    enabled = metadata.get("enabled", "true")
                    if isinstance(enabled, str):
                        enabled = enabled.lower() in ("true", "yes", "1")

                    rules.append(RuleFile(
                        name=md_file.stem,
                        path=str(md_file),
                        scope=scope,
                        globs=tuple(globs),  # Convert to tuple for hashability
                        description=metadata.get("description", ""),
                        priority=int(metadata.get("priority", "100")),
                        body=body.strip(),
                        enabled=enabled
                    ))

                    logger.debug(f"[RulesInjector] Discovered rule: {md_file.stem} ({len(globs)} patterns)")

                except Exception as e:
                    logger.warning(f"[RulesInjector] Failed to parse {md_file}: {e}")
                    continue
        except Exception as e:
            logger.error(f"[RulesInjector] Failed to scan {rules_dir}: {e}")
            continue

    # Sort by priority (lower numbers = higher priority)
    rules.sort(key=lambda r: r.priority)

    logger.info(f"[RulesInjector] Discovered {len(rules)} rules from {len(search_paths)} locations")

    return rules


def extract_file_paths_from_context(params: dict[str, Any]) -> set[str]:
    """
    Extract file paths from prompt context.

    Looks for:
    1. Tool references: "Read /path/to/file.py"
    2. File path patterns: file_path: "/path/to/file.py"
    3. Explicit file mentions
    """
    paths = set()
    prompt = params.get("prompt", "")

    # Common tool reference patterns
    file_patterns = [
        r'(?:Read|Edit|Write|MultiEdit)[\s:]+([^\s]+\.(?:py|ts|js|tsx|jsx|md|json|yaml|yml|toml|rs|go|java|cpp|c|h|hpp))',
        r'file_path["\']?\s*[:=]\s*["\']?([^"\'}\s]+)',
        r'path["\']?\s*[:=]\s*["\']?([^"\'}\s]+\.(?:py|ts|js|tsx|jsx|rs|go))',
        r'([/~][^\s]+\.(?:py|ts|js|tsx|jsx|md|json|yaml|yml|toml|rs|go|java|cpp|c|h|hpp))',
    ]

    for pattern in file_patterns:
        for match in re.finditer(pattern, prompt):
            path_str = match.group(1).strip()
            path = Path(path_str)

            # Expand home directory
            if path_str.startswith("~"):
                path = path.expanduser()

            # Check if file exists
            if path.exists() and path.is_file():
                paths.add(str(path.absolute()))

    return paths


def match_rules_to_files(rules: list[RuleFile], file_paths: set[str], project_path: str) -> list[RuleFile]:
    """
    Match discovered rules to active file paths using glob patterns.

    Args:
        rules: List of discovered RuleFile objects
        file_paths: Set of absolute file paths from context
        project_path: Project root for relative path resolution

    Returns:
        List of matched RuleFile objects (deduplicated, priority-sorted)
    """
    matched = set()
    project = Path(project_path)

    for file_path in file_paths:
        path = Path(file_path)

        # Try both absolute and relative matching
        try:
            relative_path = str(path.relative_to(project)) if path.is_relative_to(project) else None
        except (ValueError, TypeError):
            relative_path = None

        for rule in rules:
            # Skip disabled rules
            if not rule.enabled:
                continue

            # Check each glob pattern
            for glob_pattern in rule.globs:
                matched_this_pattern = False

                # Match absolute path
                if fnmatch(str(path), glob_pattern) or relative_path and fnmatch(relative_path, glob_pattern) or fnmatch(path.name, glob_pattern):
                    matched_this_pattern = True

                if matched_this_pattern:
                    matched.add(rule)
                    logger.debug(f"[RulesInjector] Matched rule '{rule.name}' to {path.name}")
                    break  # One match per rule is enough

    # Return sorted by priority
    return sorted(matched, key=lambda r: r.priority)


def truncate_rules_by_priority(matched_rules: list[RuleFile], max_tokens: int = MAX_RULES_TOKENS) -> list[RuleFile]:
    """
    Truncate rules to fit within token budget, preserving high-priority rules.

    Strategy:
    1. Always include highest priority rules
    2. Truncate individual rule bodies if needed
    3. Drop lowest priority rules if still over budget
    """
    max_chars = max_tokens * TOKEN_ESTIMATE_RATIO

    included = []
    total_chars = 0

    for rule in sorted(matched_rules, key=lambda r: r.priority):
        rule_chars = len(rule.body) + 100  # +100 for formatting overhead

        if total_chars + rule_chars <= max_chars:
            # Fits completely
            included.append(rule)
            total_chars += rule_chars
        else:
            # Try truncating the rule body
            remaining_budget = max_chars - total_chars
            if remaining_budget > 500:  # Minimum useful rule size
                truncated_body = rule.body[:remaining_budget - 200] + "\n...[TRUNCATED]"
                included.append(RuleFile(
                    name=rule.name,
                    path=rule.path,
                    scope=rule.scope,
                    globs=rule.globs,  # Already a tuple
                    description=rule.description,
                    priority=rule.priority,
                    body=truncated_body,
                    enabled=rule.enabled
                ))
                total_chars += remaining_budget
            # No more budget - stop including rules
            break

    if len(included) < len(matched_rules):
        logger.warning(f"[RulesInjector] Truncated {len(matched_rules) - len(included)} rules due to token budget")

    return included


def format_rules_injection(rules: list[RuleFile]) -> str:
    """
    Format matched rules for injection into prompt.

    Returns:
        Formatted markdown block with all applicable rules
    """
    if not rules:
        return ""

    header = """
> **[AUTO-RULES INJECTION]**
> The following coding standards/rules apply to files in this context:
"""

    rules_blocks = []
    for rule in rules:
        globs_display = ', '.join(rule.globs[:3])
        if len(rule.globs) > 3:
            globs_display += "..."

        block = f"""
---
### Rule: {rule.name}
**Scope**: {rule.scope} | **Files**: {globs_display}
**Description**: {rule.description}

{rule.body}
---
"""
        rules_blocks.append(block)

    return header + "\n".join(rules_blocks)


def get_session_cache_key(session_id: str, file_paths: set[str]) -> str:
    """Generate cache key for session + file combination."""
    sorted_paths = "|".join(sorted(file_paths))
    return f"{session_id}:{sorted_paths}"


def is_already_injected(session_id: str, file_paths: set[str], rule_names: list[str]) -> bool:
    """
    Check if rules have already been injected for this session + file combination.

    Returns:
        True if ALL rules have been injected before
    """
    cache_key = get_session_cache_key(session_id, file_paths)

    if cache_key not in _rules_injection_cache:
        _rules_injection_cache[cache_key] = set()

    injected = _rules_injection_cache[cache_key]
    new_rules = set(rule_names) - injected

    if new_rules:
        # Mark as injected
        _rules_injection_cache[cache_key].update(new_rules)
        return False

    return True  # All rules already injected


def clear_session_cache(session_id: str):
    """Clear all cached injections for a session (call on session_compact or session_end)."""
    keys_to_remove = [k for k in _rules_injection_cache if k.startswith(f"{session_id}:")]
    for key in keys_to_remove:
        del _rules_injection_cache[key]

    # Also clear rules cache
    keys_to_remove = [k for k in _session_rules_cache if k.startswith(f"{session_id}:")]
    for key in keys_to_remove:
        del _session_rules_cache[key]


def get_cached_rules(session_id: str, project_path: str) -> list[RuleFile]:
    """Get or discover rules for session (cached)."""
    cache_key = f"{session_id}:{project_path}"

    if cache_key not in _session_rules_cache:
        _session_rules_cache[cache_key] = discover_rules(project_path)

    return _session_rules_cache[cache_key]


def get_project_path_from_prompt(prompt: str) -> str | None:
    """Extract project path from prompt if available."""
    # Look for common working directory indicators
    patterns = [
        r'Working directory:\s*([^\n]+)',
        r'Project path:\s*([^\n]+)',
        r'cwd:\s*([^\n]+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, prompt)
        if match:
            return match.group(1).strip()

    # Default to current working directory
    return str(Path.cwd())


async def rules_injector_hook(params: dict[str, Any]) -> dict[str, Any] | None:
    """
    Pre-model-invoke hook for automatic rules injection.

    Gracefully degrades on errors - never blocks model invocation.
    """
    try:
        # 1. Extract session ID
        session_id = params.get("session_id", "unknown")

        # 2. Extract file paths from context
        file_paths = extract_file_paths_from_context(params)

        if not file_paths:
            # No file context - skip injection
            return None

        # 3. Get project path and discover rules
        project_path = get_project_path_from_prompt(params.get("prompt", ""))
        rules = get_cached_rules(session_id, project_path)

        if not rules:
            # No rules defined - skip
            return None

        # 4. Match rules to files
        matched = match_rules_to_files(rules, file_paths, project_path)

        if not matched:
            # No matching rules - skip
            return None

        # 5. Check deduplication cache
        rule_names = [r.name for r in matched]
        if is_already_injected(session_id, file_paths, rule_names):
            logger.debug(f"[RulesInjector] Rules already injected for session {session_id}")
            return None

        # 6. Truncate if needed
        truncated = truncate_rules_by_priority(matched)

        # 7. Format and inject
        injection = format_rules_injection(truncated)
        modified_params = params.copy()
        modified_params["prompt"] = injection + "\n\n" + params.get("prompt", "")

        logger.info(f"[RulesInjector] Injected {len(truncated)} rules for {len(file_paths)} files")
        return modified_params

    except Exception as e:
        # Log error but DON'T block the model invocation
        logger.error(f"[RulesInjector] Hook failed: {e}", exc_info=True)
        return None  # Continue without rule injection
