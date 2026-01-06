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

# Agent model mappings
AGENT_MODELS = {
    "explore": "gemini-3-flash",
    "dewey": "gemini-3-flash",
    "code-reviewer": "sonnet",
    "debugger": "sonnet",
    "frontend": "gemini-3-pro-high",
    "delphi": "gpt-5.2-medium",
}

# Tool display names
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


def extract_description(tool_name: str, params: dict) -> str:
    """Extract a concise description of what the tool did."""

    # AST-grep
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
        first_line = prompt.split('\n')[0][:50] if prompt else "Processing"
        return first_line

    # OpenAI invocation
    if "invoke_openai" in tool_name:
        prompt = params.get("prompt", "")
        first_line = prompt.split('\n')[0][:50] if prompt else "Strategic analysis"
        return first_line

    # GitHub file fetch
    if "github_file" in tool_name:
        path = params.get("path", "")
        repo = params.get("repo", "")
        return f"Fetching {path} from {repo}"

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

        # Get tool display name
        display_name = TOOL_NAMES.get(tool_name, tool_name)

        # Special handling for Task delegations
        if tool_name == "Task":
            subagent_type = params.get("subagent_type", "unknown")
            description = params.get("description", "")
            model = AGENT_MODELS.get(subagent_type, "unknown")

            # Show full agent delegation message
            print(f"🎯 {subagent_type}:{model}('{description}')", file=sys.stderr)
        else:
            # Regular tool usage
            description = extract_description(tool_name, params)
            print(f"🔧 {display_name}('{description}')", file=sys.stderr)

        sys.exit(0)

    except Exception as e:
        # On error, fail silently (don't disrupt workflow)
        print(f"Tool messaging hook error: {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
