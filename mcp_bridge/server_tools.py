from mcp.types import Tool, Prompt
from typing import List

def get_tool_definitions() -> List[Tool]:
    """Return all Tool definitions for the Stravinsky MCP server."""
    return [
        Tool(
            name="invoke_gemini",
            description=(
                "Invoke a Gemini model with the given prompt. "
                "Requires OAuth authentication with Google. "
                "Use this for tasks requiring Gemini's capabilities like "
                "frontend UI generation, documentation writing, or multimodal analysis."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The prompt to send to Gemini",
                    },
                    "model": {
                        "type": "string",
                        "description": "Gemini model to use (default: gemini-2.0-flash-exp)",
                        "default": "gemini-2.0-flash-exp",
                    },
                    "temperature": {
                        "type": "number",
                        "description": "Sampling temperature (0.0-2.0)",
                        "default": 0.7,
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum tokens in response",
                        "default": 8192,
                    },
                    "thinking_budget": {
                        "type": "integer",
                        "description": "Tokens reserved for internal reasoning (if model supports it)",
                        "default": 0,
                    },
                },
                "required": ["prompt"],
            },
        ),
        Tool(
            name="invoke_openai",
            description=(
                "Invoke an OpenAI model with the given prompt. "
                "Requires OAuth authentication with OpenAI. "
                "Use this for tasks requiring GPT capabilities like "
                "strategic advice, code review, or complex reasoning."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The prompt to send to OpenAI",
                    },
                    "model": {
                        "type": "string",
                        "description": "OpenAI model to use (default: gpt-4o)",
                        "default": "gpt-4o",
                    },
                    "temperature": {
                        "type": "number",
                        "description": "Sampling temperature (0.0-2.0)",
                        "default": 0.7,
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum tokens in response",
                        "default": 4096,
                    },
                    "thinking_budget": {
                        "type": "integer",
                        "description": "Tokens reserved for internal reasoning (e.g. o1 / o3)",
                        "default": 0,
                    },
                },
                "required": ["prompt"],
            },
        ),
        Tool(
            name="get_project_context",
            description="Summarize project environment including Git status, local rules (.claude/rules/), and pending todos.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": {"type": "string", "description": "Path to the project root"},
                },
            },
        ),
        Tool(
            name="get_system_health",
            description="Comprehensive check of system dependencies (rg, fd, sg, etc.) and authentication status.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="lsp_diagnostics",
            description="Get diagnostics (errors, warnings) for a file using language tools (tsc, ruff).",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to file to analyze"},
                    "severity": {"type": "string", "description": "Filter: error, warning, all", "default": "all"},
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="ast_grep_search",
            description="Search codebase using ast-grep for structural AST patterns.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "ast-grep pattern"},
                    "directory": {"type": "string", "description": "Directory to search", "default": "."},
                    "language": {"type": "string", "description": "Filter by language"},
                },
                "required": ["pattern"],
            },
        ),
        Tool(
            name="grep_search",
            description="Fast text search using ripgrep.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Search pattern (regex)"},
                    "directory": {"type": "string", "description": "Directory to search", "default": "."},
                    "file_pattern": {"type": "string", "description": "Glob filter (e.g. *.py)"},
                },
                "required": ["pattern"],
            },
        ),
        Tool(
            name="glob_files",
            description="Find files matching a glob pattern.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Glob pattern (e.g. **/*.py)"},
                    "directory": {"type": "string", "description": "Base directory", "default": "."},
                },
                "required": ["pattern"],
            },
        ),
        Tool(
            name="session_list",
            description="List Claude Code sessions with optional filtering.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": {"type": "string", "description": "Filter by project path"},
                    "limit": {"type": "integer", "description": "Max sessions", "default": 20},
                },
            },
        ),
        Tool(
            name="session_read",
            description="Read messages from a Claude Code session.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "Session ID"},
                    "limit": {"type": "integer", "description": "Max messages"},
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="session_search",
            description="Search across Claude Code session messages.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "session_id": {"type": "string", "description": "Search in specific session"},
                    "limit": {"type": "integer", "description": "Max results", "default": 20},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="skill_list",
            description="List available Claude Code skills/commands from .claude/commands/.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": {"type": "string", "description": "Project directory"},
                },
            },
        ),
        Tool(
            name="skill_get",
            description="Get the content of a specific skill/command.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Skill name"},
                    "project_path": {"type": "string", "description": "Project directory"},
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="task_spawn",
            description=(
                "Spawn a background task to execute a prompt asynchronously. "
                "Returns a Task ID. Best for deep research or parallel processing."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "The prompt for the background agent"},
                    "model": {
                        "type": "string", 
                        "description": "Model to use (gemini-3-flash or gpt-4o)",
                        "default": "gemini-3-flash"
                    },
                },
                "required": ["prompt"],
            },
        ),
        Tool(
            name="task_status",
            description="Check the status and retrieve results of a background task.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "The ID of the task to check"},
                },
                "required": ["task_id"],
            },
        ),
        Tool(
            name="task_list",
            description="List all active and recent background tasks.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="agent_spawn",
            description=(
                "PREFERRED TOOL for parallel work. Spawn multiple agents simultaneously for independent tasks. "
                "ALWAYS use this when you have 2+ independent research, implementation, or verification tasks. "
                "Call agent_spawn multiple times in ONE response to run tasks concurrently. "
                "Each agent runs independently with full Gemini capabilities."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "The task for the agent to perform"},
                    "agent_type": {
                        "type": "string",
                        "description": "Agent type: explore (codebase search), dewey (docs research), frontend (UI), delphi (architecture)",
                        "default": "explore",
                    },
                    "description": {"type": "string", "description": "Short description for status display"},
                    "model": {
                        "type": "string",
                        "description": "Model: gemini-3-flash (default) or claude",
                        "default": "gemini-3-flash",
                    },
                    "thinking_budget": {
                        "type": "integer",
                        "description": "Tokens reserved for internal reasoning (if model supports it)",
                        "default": 0,
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Maximum execution time in seconds",
                        "default": 300,
                    },
                },
                "required": ["prompt"],
            },
        ),
        Tool(
            name="agent_retry",
            description="Retry a failed or timed-out background agent. Can optionally refine the prompt.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "The ID of the task to retry"},
                    "new_prompt": {"type": "string", "description": "Optional refined prompt for the retry"},
                    "new_timeout": {"type": "integer", "description": "Optional new timeout in seconds"},
                },
                "required": ["task_id"],
            },
        ),
        Tool(
            name="agent_output",
            description="Get output from a background agent. Use block=true to wait for completion.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "The agent task ID"},
                    "block": {"type": "boolean", "description": "Wait for completion", "default": False},
                },
                "required": ["task_id"],
            },
        ),
        Tool(
            name="agent_cancel",
            description="Cancel a running background agent.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "The agent task ID to cancel"},
                },
                "required": ["task_id"],
            },
        ),
        Tool(
            name="agent_list",
            description="List all background agent tasks with their status.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="agent_progress",
            description="Get real-time progress from a running background agent. Shows recent output lines to monitor what the agent is doing.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "The agent task ID"},
                    "lines": {"type": "integer", "description": "Number of recent lines to show", "default": 20},
                },
                "required": ["task_id"],
            },
        ),
        Tool(
            name="lsp_hover",
            description="Get type info, documentation, and signature at a position in a file.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Absolute path to the file"},
                    "line": {"type": "integer", "description": "Line number (1-indexed)"},
                    "character": {"type": "integer", "description": "Character position (0-indexed)"},
                },
                "required": ["file_path", "line", "character"],
            },
        ),
        Tool(
            name="lsp_goto_definition",
            description="Find where a symbol is defined. Jump to symbol definition.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Absolute path to the file"},
                    "line": {"type": "integer", "description": "Line number (1-indexed)"},
                    "character": {"type": "integer", "description": "Character position (0-indexed)"},
                },
                "required": ["file_path", "line", "character"],
            },
        ),
        Tool(
            name="lsp_find_references",
            description="Find all references to a symbol across the workspace.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Absolute path to the file"},
                    "line": {"type": "integer", "description": "Line number (1-indexed)"},
                    "character": {"type": "integer", "description": "Character position (0-indexed)"},
                    "include_declaration": {"type": "boolean", "description": "Include the declaration itself", "default": True},
                },
                "required": ["file_path", "line", "character"],
            },
        ),
        Tool(
            name="lsp_document_symbols",
            description="Get hierarchical outline of all symbols (functions, classes, methods) in a file.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Absolute path to the file"},
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="lsp_workspace_symbols",
            description="Search for symbols by name across the entire workspace.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Symbol name to search for (fuzzy match)"},
                    "directory": {"type": "string", "description": "Workspace directory", "default": "."},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="lsp_prepare_rename",
            description="Check if a symbol at position can be renamed. Use before lsp_rename.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Absolute path to the file"},
                    "line": {"type": "integer", "description": "Line number (1-indexed)"},
                    "character": {"type": "integer", "description": "Character position (0-indexed)"},
                },
                "required": ["file_path", "line", "character"],
            },
        ),
        Tool(
            name="lsp_rename",
            description="Rename a symbol across the workspace. Use lsp_prepare_rename first to validate.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Absolute path to the file"},
                    "line": {"type": "integer", "description": "Line number (1-indexed)"},
                    "character": {"type": "integer", "description": "Character position (0-indexed)"},
                    "new_name": {"type": "string", "description": "New name for the symbol"},
                    "dry_run": {"type": "boolean", "description": "Preview changes without applying", "default": True},
                },
                "required": ["file_path", "line", "character", "new_name"],
            },
        ),
        Tool(
            name="lsp_code_actions",
            description="Get available quick fixes and refactorings at a position.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Absolute path to the file"},
                    "line": {"type": "integer", "description": "Line number (1-indexed)"},
                    "character": {"type": "integer", "description": "Character position (0-indexed)"},
                },
                "required": ["file_path", "line", "character"],
            },
        ),
        Tool(
            name="lsp_servers",
            description="List available LSP servers and their installation status.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="ast_grep_replace",
            description="Replace code patterns using ast-grep's AST-aware replacement. More reliable than text-based replace for refactoring.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "ast-grep pattern to search (e.g., 'console.log($A)')"},
                    "replacement": {"type": "string", "description": "Replacement pattern (e.g., 'logger.debug($A)')"},
                    "directory": {"type": "string", "description": "Directory to search in", "default": "."},
                    "language": {"type": "string", "description": "Filter by language (typescript, python, etc.)"},
                    "dry_run": {"type": "boolean", "description": "Preview changes without applying", "default": True},
                },
                "required": ["pattern", "replacement"],
            },
        ),
    ]

def get_prompt_definitions() -> List[Prompt]:
    """Return all Prompt definitions for the Stravinsky MCP server."""
    return [
        Prompt(
            name="stravinsky",
            description=(
                "Stravinsky - Powerful AI orchestrator. "
                "Plans obsessively with todos, assesses search complexity before "
                "exploration, delegates strategically to specialized agents."
            ),
            arguments=[],
        ),
        Prompt(
            name="delphi",
            description=(
                "Delphi - Strategic advisor using GPT for debugging, "
                "architecture review, and complex problem solving."
            ),
            arguments=[],
        ),
        Prompt(
            name="dewey",
            description=(
                "Dewey - Documentation and GitHub research specialist. "
                "Finds implementation examples, official docs, and code patterns."
            ),
            arguments=[],
        ),
        Prompt(
            name="explore",
            description=(
                "Explore - Fast codebase search specialist. "
                "Answers 'Where is X?', finds files and code patterns."
            ),
            arguments=[],
        ),
        Prompt(
            name="frontend",
            description=(
                "Frontend UI/UX Engineer - Designer-turned-developer for stunning visuals. "
                "Excels at styling, layout, animation, typography."
            ),
            arguments=[],
        ),
        Prompt(
            name="document_writer",
            description=(
                "Document Writer - Technical documentation specialist. "
                "README files, API docs, architecture docs, user guides."
            ),
            arguments=[],
        ),
        Prompt(
            name="multimodal",
            description=(
                "Multimodal Looker - Visual content analysis. "
                "PDFs, images, diagrams - extracts and interprets visual data."
            ),
            arguments=[],
        ),
    ]
