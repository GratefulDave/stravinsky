from mcp.types import Prompt, Tool


def get_tool_definitions() -> list[Tool]:
    """Return all Tool definitions for the Stravinsky MCP server."""
    return [
        Tool(
            name="stravinsky_version",
            description="Returns the current version of the Stravinsky MCP bridge and diagnostic info.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
                    meta={"defer_loading": True},
        ),
        Tool(
            name="system_restart",
            description="Force-restarts the Stravinsky MCP server by exiting the process. The host (Claude Code) will automatically respawn it, picking up any updated code/packages.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
            meta={"defer_loading": True},
        ),
        Tool(
            name="tool_search",
            description="Search for tools by name, description, or category. Returns matching tools with their descriptions and parameters. Use this to discover available tools before using them.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query to match against tool names, descriptions, and categories",
                    },
                    "category": {
                        "type": "string",
                        "description": "Optional category filter (e.g., 'semantic', 'lsp', 'agent', 'git')",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        ),
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
                        "description": "Gemini model to use (default: gemini-3-flash)",
                        "default": "gemini-3-flash",
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
                    "agent_context": {
                        "type": "object",
                        "description": "Optional agent metadata for logging (agent_type, task_id, description)",
                        "properties": {
                            "agent_type": {
                                "type": "string",
                                "description": "Type of agent (explore, delphi, frontend, etc.)",
                            },
                            "task_id": {
                                "type": "string",
                                "description": "Background task ID if running as agent",
                            },
                            "description": {
                                "type": "string",
                                "description": "Short description of what the agent is doing",
                            },
                        },
                    },
                },
                "required": ["prompt"],
            },
                    meta={"defer_loading": True},
        ),
        Tool(
            name="invoke_gemini_agentic",
            description=(
                "Invoke Gemini with function calling for agentic tasks. "
                "Implements a multi-turn agentic loop: sends prompt with tool definitions, "
                "executes tool calls, and iterates until final response or max_turns reached. "
                "Supports both API key (GEMINI_API_KEY) and OAuth authentication."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The task prompt for the agentic loop",
                    },
                    "model": {
                        "type": "string",
                        "description": "Gemini model to use (default: gemini-3-flash)",
                        "default": "gemini-3-flash",
                    },
                    "max_turns": {
                        "type": "integer",
                        "description": "Maximum number of tool-use turns (default: 10)",
                        "default": 10,
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Request timeout in seconds (default: 120)",
                        "default": 120,
                    },
                    "agent_context": {
                        "type": "object",
                        "description": "Optional agent metadata for logging (agent_type, task_id, description)",
                        "properties": {
                            "agent_type": {
                                "type": "string",
                                "description": "Type of agent (explore, delphi, frontend, etc.)",
                            },
                            "task_id": {
                                "type": "string",
                                "description": "Background task ID if running as agent",
                            },
                            "description": {
                                "type": "string",
                                "description": "Short description of what the agent is doing",
                            },
                        },
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
                        "description": "OpenAI model to use (default: gpt-5.2-codex)",
                        "default": "gpt-5.2-codex",
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
                    "reasoning_effort": {
                        "type": "string",
                        "description": "Reasoning effort for reasoning models (o1, o3): low, medium, high",
                        "enum": ["low", "medium", "high"],
                        "default": "medium",
                    },
                    "agent_context": {
                        "type": "object",
                        "description": "Optional agent metadata for logging (agent_type, task_id, description)",
                        "properties": {
                            "agent_type": {
                                "type": "string",
                                "description": "Type of agent (explore, delphi, frontend, etc.)",
                            },
                            "task_id": {
                                "type": "string",
                                "description": "Background task ID if running as agent",
                            },
                            "description": {
                                "type": "string",
                                "description": "Short description of what the agent is doing",
                            },
                        },
                    },
                },
                "required": ["prompt"],
            },
                    meta={"defer_loading": True},
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
                    meta={"defer_loading": True},
        ),
        Tool(
            name="get_system_health",
            description="Comprehensive check of system dependencies (rg, fd, sg, etc.) and authentication status.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
            meta={"defer_loading": True},
        ),
        Tool(
            name="lsp_diagnostics",
            description="Get diagnostics (errors, warnings) for a file using language tools (tsc, ruff).",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to file to analyze"},
                    "severity": {
                        "type": "string",
                        "description": "Filter: error, warning, all",
                        "default": "all",
                    },
                },
                "required": ["file_path"],
            },
            meta={"defer_loading": True},
        ),
        Tool(
            name="ast_grep_search",
            description="Search codebase using ast-grep for structural AST patterns.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "ast-grep pattern"},
                    "directory": {
                        "type": "string",
                        "description": "Directory to search",
                        "default": ".",
                    },
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
                    "directory": {
                        "type": "string",
                        "description": "Directory to search",
                        "default": ".",
                    },
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
                    "directory": {
                        "type": "string",
                        "description": "Base directory",
                        "default": ".",
                    },
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
                    meta={"defer_loading": True},
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
                    meta={"defer_loading": True},
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
                    meta={"defer_loading": True},
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
                    meta={"defer_loading": True},
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
                    meta={"defer_loading": True},
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
                    "prompt": {
                        "type": "string",
                        "description": "The prompt for the background agent",
                    },
                    "model": {
                        "type": "string",
                        "description": "Model to use (gemini-3-flash or gpt-4o)",
                        "default": "gemini-3-flash",
                    },
                },
                "required": ["prompt"],
            },
                    meta={"defer_loading": True},
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
                    meta={"defer_loading": True},
        ),
        Tool(
            name="task_list",
            description="List all active and recent background tasks.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
            meta={"defer_loading": True},
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
                    "prompt": {
                        "type": "string",
                        "description": "The task for the agent to perform",
                    },
                    "agent_type": {
                        "type": "string",
                        "description": "Agent type: explore, dewey, frontend (gemini-3-pro), delphi (gpt-5.2-medium), document_writer, multimodal",
                        "default": "explore",
                    },
                    "description": {
                        "type": "string",
                        "description": "Short description for status display",
                    },
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
                    "blocking": {
                        "type": "boolean",
                        "description": "If true, wait for agent completion and return result directly. Recommended for delphi consultations.",
                        "default": False,
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
                    "new_prompt": {
                        "type": "string",
                        "description": "Optional refined prompt for the retry",
                    },
                    "new_timeout": {
                        "type": "integer",
                        "description": "Optional new timeout in seconds",
                    },
                },
                "required": ["task_id"],
            },
                    meta={"defer_loading": True},
        ),
        Tool(
            name="agent_output",
            description="Get output from a background agent. Use block=true to wait for completion.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "The agent task ID"},
                    "block": {
                        "type": "boolean",
                        "description": "Wait for completion",
                        "default": False,
                    },
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
                    meta={"defer_loading": True},
        ),
        Tool(
            name="agent_list",
            description="List all background agent tasks with their status. By default shows all agents; use show_all=false to see only running/pending.",
            inputSchema={
                "type": "object",
                "properties": {
                    "show_all": {
                        "type": "boolean",
                        "description": "If false, only show running/pending agents. If true (default), show all.",
                        "default": True,
                    },
                },
            },
                    meta={"defer_loading": True},
        ),
        Tool(
            name="agent_cleanup",
            description="Clean up old completed/failed/cancelled agents to reduce clutter in agent_list. Removes agents older than max_age_minutes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "max_age_minutes": {
                        "type": "integer",
                        "description": "Remove agents older than this many minutes (default: 30)",
                        "default": 30,
                    },
                    "statuses": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of statuses to remove (default: ['completed', 'failed', 'cancelled'])",
                    },
                },
            },
                    meta={"defer_loading": True},
        ),
        Tool(
            name="agent_progress",
            description="Get real-time progress from a running background agent. Shows recent output lines to monitor what the agent is doing.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "The agent task ID"},
                    "lines": {
                        "type": "integer",
                        "description": "Number of recent lines to show",
                        "default": 20,
                    },
                },
                "required": ["task_id"],
            },
                    meta={"defer_loading": True},
        ),
        Tool(
            name="lsp_hover",
            description="Get type info, documentation, and signature at a position in a file.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Absolute path to the file"},
                    "line": {"type": "integer", "description": "Line number (1-indexed)"},
                    "character": {
                        "type": "integer",
                        "description": "Character position (0-indexed)",
                    },
                },
                "required": ["file_path", "line", "character"],
            },
                    meta={"defer_loading": True},
        ),
        Tool(
            name="lsp_goto_definition",
            description="Find where a symbol is defined. Jump to symbol definition.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Absolute path to the file"},
                    "line": {"type": "integer", "description": "Line number (1-indexed)"},
                    "character": {
                        "type": "integer",
                        "description": "Character position (0-indexed)",
                    },
                },
                "required": ["file_path", "line", "character"],
            },
                    meta={"defer_loading": True},
        ),
        Tool(
            name="lsp_find_references",
            description="Find all references to a symbol across the workspace.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Absolute path to the file"},
                    "line": {"type": "integer", "description": "Line number (1-indexed)"},
                    "character": {
                        "type": "integer",
                        "description": "Character position (0-indexed)",
                    },
                    "include_declaration": {
                        "type": "boolean",
                        "description": "Include the declaration itself",
                        "default": True,
                    },
                },
                "required": ["file_path", "line", "character"],
            },
                    meta={"defer_loading": True},
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
                    meta={"defer_loading": True},
        ),
        Tool(
            name="lsp_workspace_symbols",
            description="Search for symbols by name across the entire workspace.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Symbol name to search for (fuzzy match)",
                    },
                    "directory": {
                        "type": "string",
                        "description": "Workspace directory",
                        "default": ".",
                    },
                },
                "required": ["query"],
            },
                    meta={"defer_loading": True},
        ),
        Tool(
            name="lsp_prepare_rename",
            description="Check if a symbol at position can be renamed. Use before lsp_rename.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Absolute path to the file"},
                    "line": {"type": "integer", "description": "Line number (1-indexed)"},
                    "character": {
                        "type": "integer",
                        "description": "Character position (0-indexed)",
                    },
                },
                "required": ["file_path", "line", "character"],
            },
                    meta={"defer_loading": True},
        ),
        Tool(
            name="lsp_rename",
            description="Rename a symbol across the workspace. Use lsp_prepare_rename first to validate.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Absolute path to the file"},
                    "line": {"type": "integer", "description": "Line number (1-indexed)"},
                    "character": {
                        "type": "integer",
                        "description": "Character position (0-indexed)",
                    },
                    "new_name": {"type": "string", "description": "New name for the symbol"},
                    "dry_run": {
                        "type": "boolean",
                        "description": "Preview changes without applying",
                        "default": True,
                    },
                },
                "required": ["file_path", "line", "character", "new_name"],
            },
                    meta={"defer_loading": True},
        ),
        Tool(
            name="lsp_code_actions",
            description="Get available quick fixes and refactorings at a position.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Absolute path to the file"},
                    "line": {"type": "integer", "description": "Line number (1-indexed)"},
                    "character": {
                        "type": "integer",
                        "description": "Character position (0-indexed)",
                    },
                },
                "required": ["file_path", "line", "character"],
            },
                    meta={"defer_loading": True},
        ),
        Tool(
            name="lsp_code_action_resolve",
            description="Apply a specific code action/fix to a file (e.g., fix F401 unused import).",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Absolute path to the file"},
                    "action_code": {
                        "type": "string",
                        "description": "Code action ID to apply (e.g., 'F401', 'E501' for Python)",
                    },
                    "line": {
                        "type": "integer",
                        "description": "Optional line number filter (1-indexed)",
                    },
                },
                "required": ["file_path", "action_code"],
            },
                    meta={"defer_loading": True},
        ),
        Tool(
            name="lsp_extract_refactor",
            description="Extract code to a function or variable (Python via jedi).",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Absolute path to the file"},
                    "start_line": {"type": "integer", "description": "Start line (1-indexed)"},
                    "start_char": {"type": "integer", "description": "Start character (0-indexed)"},
                    "end_line": {"type": "integer", "description": "End line (1-indexed)"},
                    "end_char": {"type": "integer", "description": "End character (0-indexed)"},
                    "new_name": {
                        "type": "string",
                        "description": "Name for extracted function/variable",
                    },
                    "kind": {
                        "type": "string",
                        "description": "'function' or 'variable' (default: function)",
                    },
                },
                "required": [
                    "file_path",
                    "start_line",
                    "start_char",
                    "end_line",
                    "end_char",
                    "new_name",
                ],
            },
                    meta={"defer_loading": True},
        ),
        Tool(
            name="lsp_servers",
            description="List available LSP servers and their installation status.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
            meta={"defer_loading": True},
        ),
        Tool(
            name="ast_grep_replace",
            description="Replace code patterns using ast-grep's AST-aware replacement. More reliable than text-based replace for refactoring.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "ast-grep pattern to search (e.g., 'console.log($A)')",
                    },
                    "replacement": {
                        "type": "string",
                        "description": "Replacement pattern (e.g., 'logger.debug($A)')",
                    },
                    "directory": {
                        "type": "string",
                        "description": "Directory to search in",
                        "default": ".",
                    },
                    "language": {
                        "type": "string",
                        "description": "Filter by language (typescript, python, etc.)",
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "Preview changes without applying",
                        "default": True,
                    },
                },
                "required": ["pattern", "replacement"],
            },
                    meta={"defer_loading": True},
        ),
        # --- SEMANTIC SEARCH ---
        Tool(
            name="semantic_search",
            description=(
                "Search codebase using natural language queries. Uses vector embeddings to find "
                "semantically related code even without exact pattern matches. "
                "Supports filtering by language and node type. "
                "Example: 'find authentication logic' or 'error handling patterns'."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query (e.g., 'find authentication logic')",
                    },
                    "project_path": {
                        "type": "string",
                        "description": "Path to the project root",
                        "default": ".",
                    },
                    "n_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 10,
                    },
                    "language": {
                        "type": "string",
                        "description": "Filter by language (e.g., 'py', 'ts', 'js')",
                    },
                    "node_type": {
                        "type": "string",
                        "description": "Filter by node type (e.g., 'function', 'class', 'method')",
                    },
                    "provider": {
                        "type": "string",
                        "description": "Embedding provider: ollama/mxbai (local/free), gemini (cloud/OAuth), openai (cloud/OAuth), huggingface (cloud)",
                        "enum": ["ollama", "mxbai", "gemini", "openai", "huggingface"],
                        "default": "ollama",
                    },
                },
                "required": ["query"],
            },
                    meta={"defer_loading": True},
        ),
        Tool(
            name="hybrid_search",
            description=(
                "Hybrid search combining semantic similarity with structural AST matching. "
                "Use when you need both natural language understanding AND structural patterns. "
                "Example: query='find authentication logic' + pattern='def $FUNC($$$):'"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query",
                    },
                    "pattern": {
                        "type": "string",
                        "description": "ast-grep pattern for structural matching (optional)",
                    },
                    "project_path": {
                        "type": "string",
                        "description": "Path to the project root",
                        "default": ".",
                    },
                    "n_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 10,
                    },
                    "language": {
                        "type": "string",
                        "description": "Filter by language (e.g., 'py', 'ts', 'js')",
                    },
                    "node_type": {
                        "type": "string",
                        "description": "Filter by node type (e.g., 'function', 'class', 'method')",
                    },
                    "decorator": {
                        "type": "string",
                        "description": "Filter by decorator (e.g., '@property', '@staticmethod')",
                    },
                    "is_async": {
                        "type": "boolean",
                        "description": "Filter by async status (True = async only, False = sync only)",
                    },
                    "base_class": {
                        "type": "string",
                        "description": "Filter by base class (e.g., 'BaseClass')",
                    },
                    "provider": {
                        "type": "string",
                        "description": "Embedding provider: ollama/mxbai (local/free), gemini (cloud/OAuth), openai (cloud/OAuth), huggingface (cloud)",
                        "enum": ["ollama", "mxbai", "gemini", "openai", "huggingface"],
                        "default": "ollama",
                    },
                },
                "required": ["query"],
            },
                    meta={"defer_loading": True},
        ),
        Tool(
            name="find_code",
            description=(
                "Smart code search with automatic routing to optimal search strategy. "
                "Automatically detects whether query is AST pattern (e.g., 'class $X'), "
                "natural language (e.g., 'auth logic'), or complex query (e.g., 'JWT AND middleware'). "
                "Routes to ast_grep, semantic_search, hybrid_search, or grep based on pattern detection. "
                "**PREFERRED TOOL**: Use this instead of calling individual search tools directly."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (AST pattern, natural language, or text)",
                    },
                    "search_type": {
                        "type": "string",
                        "description": "Search strategy: 'auto' (default), 'ast', 'semantic', 'hybrid', 'grep', 'exact'",
                        "enum": ["auto", "ast", "semantic", "hybrid", "grep", "exact"],
                        "default": "auto",
                    },
                    "project_path": {
                        "type": "string",
                        "description": "Path to the project root",
                        "default": ".",
                    },
                    "language": {
                        "type": "string",
                        "description": "Filter by language (e.g., 'py', 'ts', 'js')",
                    },
                    "n_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 10,
                    },
                    "provider": {
                        "type": "string",
                        "description": "Embedding provider for semantic search: ollama (default), gemini, openai",
                        "default": "ollama",
                    },
                },
                "required": ["query"],
            },
                    meta={"defer_loading": True},
        ),
        Tool(
            name="semantic_index",
            description=(
                "Index a codebase for semantic search. Creates vector embeddings for all code files. "
                "Run this before using semantic_search on a new project."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": {
                        "type": "string",
                        "description": "Path to the project root",
                        "default": ".",
                    },
                    "force": {
                        "type": "boolean",
                        "description": "If true, reindex everything. Otherwise, only new/changed files.",
                        "default": False,
                    },
                    "provider": {
                        "type": "string",
                        "description": "Embedding provider: ollama/mxbai (local/free), gemini (cloud/OAuth), openai (cloud/OAuth), huggingface (cloud)",
                        "enum": ["ollama", "mxbai", "gemini", "openai", "huggingface"],
                        "default": "ollama",
                    },
                },
            },
                    meta={"defer_loading": True},
        ),
        Tool(
            name="semantic_stats",
            description="Get statistics about the semantic search index for a project.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": {
                        "type": "string",
                        "description": "Path to the project root",
                        "default": ".",
                    },
                    "provider": {
                        "type": "string",
                        "description": "Embedding provider: ollama/mxbai (local/free), gemini (cloud/OAuth), openai (cloud/OAuth), huggingface (cloud)",
                        "enum": ["ollama", "mxbai", "gemini", "openai", "huggingface"],
                        "default": "ollama",
                    },
                },
            },
                    meta={"defer_loading": True},
        ),
        Tool(
            name="start_file_watcher",
            description=(
                "Start automatic background reindexing when code files change. "
                "Watches for .py file changes and triggers semantic_index automatically. "
                "Run semantic_index() first before starting the watcher."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": {
                        "type": "string",
                        "description": "Path to the project root",
                        "default": ".",
                    },
                    "provider": {
                        "type": "string",
                        "description": "Embedding provider: ollama/mxbai (local/free), gemini (cloud/OAuth), openai (cloud/OAuth), huggingface (cloud)",
                        "enum": ["ollama", "mxbai", "gemini", "openai", "huggingface"],
                        "default": "ollama",
                    },
                    "debounce_seconds": {
                        "type": "number",
                        "description": "Wait time after file changes before reindexing (default: 2.0)",
                        "default": 2.0,
                    },
                },
            },
                    meta={"defer_loading": True},
        ),
        Tool(
            name="stop_file_watcher",
            description="Stop the file watcher for a project.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": {
                        "type": "string",
                        "description": "Path to the project root",
                        "default": ".",
                    },
                },
            },
                    meta={"defer_loading": True},
        ),
        Tool(
            name="cancel_indexing",
            description=(
                "Cancel an ongoing semantic indexing operation. "
                "Cancellation happens gracefully between batches - the current batch will complete before stopping."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": {
                        "type": "string",
                        "description": "Path to the project root",
                        "default": ".",
                    },
                    "provider": {
                        "type": "string",
                        "description": "Embedding provider (must match the one used for indexing)",
                        "enum": ["ollama", "mxbai", "gemini", "openai", "huggingface"],
                        "default": "ollama",
                    },
                },
            },
                    meta={"defer_loading": True},
        ),
        Tool(
            name="delete_index",
            description=(
                "Delete semantic search index(es). Can delete for specific project+provider, "
                "all providers for a project, or all indexes globally."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": {
                        "type": "string",
                        "description": "Path to the project root (ignored if delete_all=true)",
                        "default": ".",
                    },
                    "provider": {
                        "type": "string",
                        "description": "Specific provider to delete (if not specified, deletes all providers for project)",
                        "enum": ["ollama", "mxbai", "gemini", "openai", "huggingface"],
                    },
                    "delete_all": {
                        "type": "boolean",
                        "description": "If true, delete ALL indexes for ALL projects (ignores project_path and provider)",
                        "default": False,
                    },
                },
            },
                    meta={"defer_loading": True},
        ),
        Tool(
            name="list_file_watchers",
            description="List all active file watchers across all projects.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
            meta={"defer_loading": True},
        ),
        Tool(
            name="multi_query_search",
            description=(
                "Search with LLM-expanded query variations for better recall. "
                "Rephrases query into multiple semantic variations (e.g., 'database connection' -> "
                "['SQLAlchemy engine setup', 'postgres connection', 'db session factory']) "
                "and aggregates results using reciprocal rank fusion."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query",
                    },
                    "project_path": {
                        "type": "string",
                        "description": "Path to the project root",
                        "default": ".",
                    },
                    "n_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 10,
                    },
                    "num_expansions": {
                        "type": "integer",
                        "description": "Number of query variations to generate",
                        "default": 3,
                    },
                    "language": {
                        "type": "string",
                        "description": "Filter by language (e.g., 'py', 'ts')",
                    },
                    "node_type": {
                        "type": "string",
                        "description": "Filter by node type (e.g., 'function', 'class')",
                    },
                    "provider": {
                        "type": "string",
                        "description": "Embedding provider: ollama/mxbai (local/free), gemini (cloud/OAuth), openai (cloud/OAuth), huggingface (cloud)",
                        "enum": ["ollama", "mxbai", "gemini", "openai", "huggingface"],
                        "default": "ollama",
                    },
                },
                "required": ["query"],
            },
                    meta={"defer_loading": True},
        ),
        Tool(
            name="decomposed_search",
            description=(
                "Search by decomposing complex queries into focused sub-questions. "
                "Breaks multi-part queries like 'Initialize the DB and create a user model' "
                "into separate searches ('database initialization', 'user model definition') "
                "and returns organized results for each part."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Complex search query (may contain multiple concepts)",
                    },
                    "project_path": {
                        "type": "string",
                        "description": "Path to the project root",
                        "default": ".",
                    },
                    "n_results": {
                        "type": "integer",
                        "description": "Maximum results per sub-query",
                        "default": 10,
                    },
                    "language": {
                        "type": "string",
                        "description": "Filter by language",
                    },
                    "node_type": {
                        "type": "string",
                        "description": "Filter by node type",
                    },
                    "provider": {
                        "type": "string",
                        "description": "Embedding provider: ollama/mxbai (local/free), gemini (cloud/OAuth), openai (cloud/OAuth), huggingface (cloud)",
                        "enum": ["ollama", "mxbai", "gemini", "openai", "huggingface"],
                        "default": "ollama",
                    },
                },
                "required": ["query"],
            },
                    meta={"defer_loading": True},
        ),
        Tool(
            name="enhanced_search",
            description=(
                "Unified enhanced search combining query expansion and decomposition. "
                "Automatically selects strategy based on query complexity: "
                "simple queries use multi-query expansion, complex queries use decomposition. "
                "Use mode='auto' (default), 'expand', 'decompose', or 'both'."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (simple or complex)",
                    },
                    "project_path": {
                        "type": "string",
                        "description": "Path to the project root",
                        "default": ".",
                    },
                    "n_results": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 10,
                    },
                    "mode": {
                        "type": "string",
                        "description": "Search mode: 'auto' (default), 'expand', 'decompose', or 'both'",
                        "enum": ["auto", "expand", "decompose", "both"],
                        "default": "auto",
                    },
                    "language": {
                        "type": "string",
                        "description": "Filter by language",
                    },
                    "node_type": {
                        "type": "string",
                        "description": "Filter by node type",
                    },
                    "provider": {
                        "type": "string",
                        "description": "Embedding provider: ollama/mxbai (local/free), gemini (cloud/OAuth), openai (cloud/OAuth), huggingface (cloud)",
                        "enum": ["ollama", "mxbai", "gemini", "openai", "huggingface"],
                        "default": "ollama",
                    },
                },
                "required": ["query"],
            },
                    meta={"defer_loading": True},
        ),
        Tool(
            name="get_cost_report",
            description="Get a cost report for the current or specified session, breaking down token usage and cost by agent.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Optional session ID to filter by",
                    },
                },
            },
            meta={"defer_loading": True},
        ),
    ]


def get_prompt_definitions() -> list[Prompt]:
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
