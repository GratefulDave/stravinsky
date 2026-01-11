#!/usr/bin/env python3
"""
PostToolUse hook for user-friendly tool messaging.

Outputs concise messages about which agent/tool was used and what it did.
Format examples:
- ast-grep('Searching for authentication patterns')
- delphi:openai/gpt-5.2-medium('Analyzing architecture trade-offs')
- explore:gemini-3-flash('Finding all API endpoints')
"""

import json
import os
import sys

# Add utils directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "utils"))
from colors import get_agent_color, colorize, Color, supports_color
from console_format import format_tool_use, format_agent_spawn, MessageType

# Agent model mappings
AGENT_MODELS = {
    "explore": "gemini-3-flash",
    "dewey": "gemini-3-flash",
    "code-reviewer": "sonnet",
    "debugger": "sonnet",
    "frontend": "gemini-3-pro-high",
    "delphi": "gpt-5.2-medium",
}

# MCP Server emoji mappings
SERVER_EMOJIS = {
    "github": "🟡",
    "ast-grep": "🟤",
    "grep-app": "🟣",
    "MCP_DOCKER": "🔵",
    "stravinsky": "🔧",
}

# Tool display names (legacy mapping for simple tools)
TOOL_NAMES = {
    "mcp__stravinsky__ast_grep_search": "ast-grep",
    "mcp__stravinsky__grep_search": "grep",
    "mcp__stravinsky__glob_files": "glob",
    "mcp__stravinsky__lsp_diagnostics": "lsp-diagnostics",
    "mcp__stravinsky__lsp_hover": "lsp-hover",
    "mcp__stravinsky__lsp_goto_definition": "lsp-goto-def",
    "mcp__stravinsky__lsp_find_references": "lsp-find-refs",
    "mcp__stravinsky__lsp_document_symbols": "lsp-symbols",
    "mcp__stravinsky__lsp_workspace_symbols": "lsp-workspace-symbols",
    "mcp__stravinsky__invoke_gemini": "gemini",
    "mcp__stravinsky__invoke_openai": "openai",
    "mcp__grep-app__searchCode": "grep.app",
    "mcp__grep-app__github_file": "github-file",
}


def parse_mcp_tool_name(tool_name: str) -> tuple[str, str, str]:
    """
    Parse MCP tool name into (server, tool_type, emoji).

    Examples:
        mcp__github__get_file_contents -> ("github", "get_file_contents", "🟡")
        mcp__stravinsky__grep_search -> ("stravinsky", "grep", "🔧")
        mcp__ast-grep__find_code -> ("ast-grep", "find_code", "🟤")
    """
    if not tool_name.startswith("mcp__"):
        return ("unknown", tool_name, "🔧")

    # Remove mcp__ prefix and split by __
    parts = tool_name[5:].split("__", 1)
    if len(parts) != 2:
        return ("unknown", tool_name, "🔧")

    server = parts[0]
    tool_type = parts[1]

    # Get emoji for server
    emoji = SERVER_EMOJIS.get(server, "🔧")

    # Get simplified tool name if available
    simple_name = TOOL_NAMES.get(tool_name, tool_type)

    return (server, simple_name, emoji)


def extract_description(tool_name: str, params: dict) -> str:
    """Extract a concise description of what the tool did."""

    # GitHub tools
    if "github" in tool_name.lower():
        if "get_file_contents" in tool_name:
            path = params.get("path", "")
            repo = params.get("repo", "")
            owner = params.get("owner", "")
            return f"Fetching {path} from {owner}/{repo}"
        elif "create_or_update_file" in tool_name:
            path = params.get("path", "")
            return f"Updating {path}"
        elif "search_repositories" in tool_name:
            query = params.get("query", "")
            return f"Searching repos for '{query[:40]}'"
        elif "search_code" in tool_name:
            q = params.get("q", "")
            return f"Searching code for '{q[:40]}'"
        elif "create_pull_request" in tool_name:
            title = params.get("title", "")
            return f"Creating PR: {title[:40]}"
        elif "get_pull_request" in tool_name or "list_pull_requests" in tool_name:
            return "Fetching PR details"
        return "GitHub operation"

    # MCP_DOCKER tools
    if "MCP_DOCKER" in tool_name:
        if "web_search_exa" in tool_name:
            query = params.get("query", "")
            return f"Web search: '{query[:40]}'"
        elif "create_entities" in tool_name:
            entities = params.get("entities", [])
            count = len(entities)
            return f"Creating {count} knowledge graph entities"
        elif "search_nodes" in tool_name:
            query = params.get("query", "")
            return f"Searching knowledge graph for '{query[:40]}'"
        return "Knowledge graph operation"

    # ast-grep tools
    if "ast-grep" in tool_name or "ast_grep" in tool_name:
        if "find_code" in tool_name or "search" in tool_name:
            pattern = params.get("pattern", "")
            return f"AST search for '{pattern[:40]}'"
        elif "test_match" in tool_name:
            return "Testing AST pattern"
        elif "dump_syntax" in tool_name:
            return "Dumping syntax tree"
        return "AST operation"

    # grep-app tools
    if "grep-app" in tool_name or "grep_app" in tool_name:
        if "searchCode" in tool_name:
            query = params.get("query", "")
            return f"Searching GitHub for '{query[:40]}'"
        elif "github_file" in tool_name:
            path = params.get("path", "")
            repo = params.get("repo", "")
            return f"Fetching {path} from {repo}"
        return "grep.app search"

    # AST-grep (stravinsky)
    if "ast_grep" in tool_name:
        pattern = params.get("pattern", "")
        directory = params.get("directory", ".")
        return f"Searching AST in {directory} for '{pattern[:40]}...'"

    # Grep/search
    if "grep_search" in tool_name or "searchCode" in tool_name:
        pattern = params.get("pattern", params.get("query", ""))
        return f"Searching for '{pattern[:40]}...'"

    # Glob
    if "glob_files" in tool_name:
        pattern = params.get("pattern", "")
        return f"Finding files matching '{pattern}'"

    # LSP diagnostics
    if "lsp_diagnostics" in tool_name:
        file_path = params.get("file_path", "")
        filename = os.path.basename(file_path) if file_path else "file"
        return f"Checking {filename} for errors"

    # LSP hover
    if "lsp_hover" in tool_name:
        file_path = params.get("file_path", "")
        line = params.get("line", "")
        filename = os.path.basename(file_path) if file_path else "file"
        return f"Type info for {filename}:{line}"

    # LSP goto definition
    if "lsp_goto" in tool_name:
        file_path = params.get("file_path", "")
        filename = os.path.basename(file_path) if file_path else "symbol"
        return f"Finding definition in {filename}"

    # LSP find references
    if "lsp_find_references" in tool_name:
        file_path = params.get("file_path", "")
        filename = os.path.basename(file_path) if file_path else "symbol"
        return f"Finding all references to symbol in {filename}"

    # LSP symbols
    if "lsp_symbols" in tool_name or "lsp_document_symbols" in tool_name:
        file_path = params.get("file_path", "")
        filename = os.path.basename(file_path) if file_path else "file"
        return f"Getting symbols from {filename}"

    if "lsp_workspace_symbols" in tool_name:
        query = params.get("query", "")
        return f"Searching workspace for symbol '{query}'"

    # Gemini invocation
    if "invoke_gemini" in tool_name:
        prompt = params.get("prompt", "")
        # Extract first meaningful line
        first_line = prompt.split("\n")[0][:50] if prompt else "Processing"
        return first_line

    # OpenAI invocation
    if "invoke_openai" in tool_name:
        prompt = params.get("prompt", "")
        first_line = prompt.split("\n")[0][:50] if prompt else "Strategic analysis"
        return first_line

    # GitHub file fetch
    if "github_file" in tool_name:
        path = params.get("path", "")
        repo = params.get("repo", "")
        return f"Fetching {path} from {repo}"

    # Agent spawn (MCP tool)
    if "agent_spawn" in tool_name:
        agent_type = params.get("agent_type", "unknown")
        description = params.get("description", "")
        model = AGENT_MODELS.get(agent_type, "gemini-3-flash")
        return f"{agent_type}({model})"

    # Task delegation
    if tool_name == "Task":
        subagent_type = params.get("subagent_type", "unknown")
        description = params.get("description", "")
        model = AGENT_MODELS.get(subagent_type, "unknown")
        return f"{subagent_type}:{model}('{description}')"

    return "Processing"


def main():
    try:
        # Read hook input from stdin
        hook_input = json.loads(sys.stdin.read())

        tool_name = hook_input.get("toolName", hook_input.get("tool_name", ""))
        params = hook_input.get("params", hook_input.get("tool_input", {}))

        # Only output messages for MCP tools and Task delegations
        if not (tool_name.startswith("mcp__") or tool_name == "Task"):
            sys.exit(0)

        # Special handling for Task delegations
        if tool_name == "Task":
            subagent_type = params.get("subagent_type", "unknown")
            description = params.get("description", "")
            model = AGENT_MODELS.get(subagent_type, "unknown")

            # Use rich formatting for agent spawns
            message = format_agent_spawn(
                agent_type=subagent_type, model=model, description=description
            )
            print(message, file=sys.stderr)
        else:
            # Parse MCP tool name to get server, tool_type, and emoji
            server, tool_type, emoji = parse_mcp_tool_name(tool_name)

            # Get description of what the tool did
            description = extract_description(tool_name, params)

            # Use rich formatting for tool usage
            message = format_tool_use(
                tool_name=tool_type, server=server, description=description, emoji=emoji
            )
            print(message, file=sys.stderr)

        sys.exit(0)

    except Exception as e:
        # On error, fail silently (don't disrupt workflow)
        print(f"Tool messaging hook error: {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
