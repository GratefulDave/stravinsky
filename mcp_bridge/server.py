"""
Claude Superagent MCP Bridge Server

Main entry point for the MCP server that provides tools for:
- OAuth-authenticated Gemini model invocation
- OAuth-authenticated OpenAI model invocation
- LSP tool proxies
- Session management

Run with: python -m mcp_bridge.server
"""

import asyncio
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    Resource,
    Prompt,
    PromptMessage,
    GetPromptResult,
)

from .auth.token_store import TokenStore
from .tools import (
    invoke_gemini, 
    invoke_openai,
    lsp_diagnostics, 
    ast_grep_search, 
    ast_grep_replace, 
    grep_search, 
    glob_files,
    list_sessions, 
    read_session, 
    search_sessions, 
    get_session_info,
    list_skills, 
    get_skill, 
    create_skill,
    agent_spawn, 
    agent_output, 
    agent_cancel, 
    agent_list, 
    agent_progress, 
    agent_retry,
    task_spawn,
    task_status,
    task_list
)
from .tools.project_context import get_project_context, get_system_health
from .tools.lsp import (
    lsp_hover,
    lsp_goto_definition,
    lsp_find_references,
    lsp_document_symbols,
    lsp_workspace_symbols,
    lsp_prepare_rename,
    lsp_rename,
    lsp_code_actions,
    lsp_servers,
)
from .prompts import stravinsky, delphi, dewey, explore, frontend, document_writer, multimodal
from .hooks.manager import get_hook_manager
from . import hooks  # Triggers hook registration in __init__.py

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the MCP server
server = Server("stravinsky")

# Token store for OAuth tokens
token_store = TokenStore()


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    tools = [
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
                        "default": 4096,
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
                        "description": "OpenAI model to use (default: gpt-5.2)",
                        "default": "gpt-5.2",
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
                        "description": "Tokens reserved for internal reasoning (e.g. gpt-5.2 / o1 / o3)",
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
                        "description": "Model to use (gemini-3-flash or gpt-5.2)",
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
        # New Agent Tools with Full Tool Access
        Tool(
            name="agent_spawn",
            description=(
                "Spawn a background agent. Uses Gemini by default for fast execution. "
                "Set model='claude' to use Claude Code CLI with full tool access."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "The task for the agent to perform"},
                    "agent_type": {
                        "type": "string",
                        "description": "Agent type: explore, dewey, frontend, delphi",
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
        # LSP Tools
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
    return tools


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool invocations."""
    logger.info(f"Tool called: {name} with args: {arguments}")
    hook_manager = get_hook_manager()

    try:
        # Pre-tool call hooks
        arguments = await hook_manager.execute_pre_tool_call(name, arguments)
        
        result_content = None

        if name == "invoke_gemini":
            result = await invoke_gemini(
                token_store=token_store,
                prompt=arguments["prompt"],
                model=arguments.get("model", "gemini-3-flash"),
                temperature=arguments.get("temperature", 0.7),
                max_tokens=arguments.get("max_tokens", 4096),
                thinking_budget=arguments.get("thinking_budget", 0),
            )
            result_content = result

        elif name == "invoke_openai":
            result = await invoke_openai(
                token_store=token_store,
                prompt=arguments["prompt"],
                model=arguments.get("model", "gpt-5.2"),
                temperature=arguments.get("temperature", 0.7),
                max_tokens=arguments.get("max_tokens", 4096),
                thinking_budget=arguments.get("thinking_budget", 0),
            )
            result_content = result

        elif name == "get_project_context":
            result = await get_project_context(
                project_path=arguments.get("project_path"),
            )
            result_content = result

        elif name == "get_system_health":
            result = await get_system_health()
            result_content = result

        elif name == "lsp_diagnostics":
            result = await lsp_diagnostics(
                file_path=arguments["file_path"],
                severity=arguments.get("severity", "all"),
            )
            result_content = result

        elif name == "ast_grep_search":
            result = await ast_grep_search(
                pattern=arguments["pattern"],
                directory=arguments.get("directory", "."),
                language=arguments.get("language", ""),
            )
            result_content = result

        elif name == "grep_search":
            result = await grep_search(
                pattern=arguments["pattern"],
                directory=arguments.get("directory", "."),
                file_pattern=arguments.get("file_pattern", ""),
            )
            result_content = result

        elif name == "glob_files":
            result = await glob_files(
                pattern=arguments["pattern"],
                directory=arguments.get("directory", "."),
            )
            result_content = result

        elif name == "session_list":
            result = list_sessions(
                project_path=arguments.get("project_path"),
                limit=arguments.get("limit", 20),
            )
            result_content = result

        elif name == "session_read":
            result = read_session(
                session_id=arguments["session_id"],
                limit=arguments.get("limit"),
            )
            result_content = result

        elif name == "session_search":
            result = search_sessions(
                query=arguments["query"],
                session_id=arguments.get("session_id"),
                limit=arguments.get("limit", 20),
            )
            result_content = result

        elif name == "skill_list":
            result = list_skills(
                project_path=arguments.get("project_path"),
            )
            result_content = result

        elif name == "skill_get":
            result = get_skill(
                name=arguments["name"],
                project_path=arguments.get("project_path"),
            )
            result_content = result

        elif name == "task_spawn":
            result = await task_spawn(
                prompt=arguments["prompt"],
                model=arguments.get("model", "gemini-3-flash"),
            )
            result_content = result

        elif name == "task_status":
            result = await task_status(
                task_id=arguments["task_id"],
            )
            result_content = result

        elif name == "agent_retry":
            result = await agent_retry(
                task_id=arguments["task_id"],
                new_prompt=arguments.get("new_prompt"),
                new_timeout=arguments.get("new_timeout"),
            )
            result_content = result

        elif name == "task_list":
            result = await task_list()
            result_content = result

        # Agent tools with full tool access
        elif name == "agent_spawn":
            result = await agent_spawn(
                prompt=arguments["prompt"],
                agent_type=arguments.get("agent_type", "explore"),
                description=arguments.get("description", ""),
                model=arguments.get("model", "gemini-3-flash"),
                thinking_budget=arguments.get("thinking_budget", 0),
                timeout=arguments.get("timeout", 300),
            )
            result_content = result

        elif name == "agent_output":
            result = await agent_output(
                task_id=arguments["task_id"],
                block=arguments.get("block", False),
            )
            result_content = result

        elif name == "agent_cancel":
            result = await agent_cancel(
                task_id=arguments["task_id"],
            )
            result_content = result

        elif name == "agent_list":
            result = await agent_list()
            result_content = result

        elif name == "agent_progress":
            result = await agent_progress(
                task_id=arguments["task_id"],
                lines=arguments.get("lines", 20),
            )
            result_content = result

        # LSP Tools
        elif name == "lsp_hover":
            result = await lsp_hover(
                file_path=arguments["file_path"],
                line=arguments["line"],
                character=arguments["character"],
            )
            result_content = result

        elif name == "lsp_goto_definition":
            result = await lsp_goto_definition(
                file_path=arguments["file_path"],
                line=arguments["line"],
                character=arguments["character"],
            )
            result_content = result

        elif name == "lsp_find_references":
            result = await lsp_find_references(
                file_path=arguments["file_path"],
                line=arguments["line"],
                character=arguments["character"],
                include_declaration=arguments.get("include_declaration", True),
            )
            result_content = result

        elif name == "lsp_document_symbols":
            result = await lsp_document_symbols(
                file_path=arguments["file_path"],
            )
            result_content = result

        elif name == "lsp_workspace_symbols":
            result = await lsp_workspace_symbols(
                query=arguments["query"],
            )
            result_content = result

        elif name == "lsp_prepare_rename":
            result = await lsp_prepare_rename(
                file_path=arguments["file_path"],
                line=arguments["line"],
                character=arguments["character"],
            )
            result_content = result

        elif name == "lsp_rename":
            result = await lsp_rename(
                file_path=arguments["file_path"],
                line=arguments["line"],
                character=arguments["character"],
                new_name=arguments["new_name"],
            )
            result_content = result

        elif name == "lsp_code_actions":
            result = await lsp_code_actions(
                file_path=arguments["file_path"],
                line=arguments["line"],
                character=arguments["character"],
            )
            result_content = result

        elif name == "lsp_servers":
            result = await lsp_servers()
            result_content = result

        elif name == "ast_grep_replace":
            result = await ast_grep_replace(
                pattern=arguments["pattern"],
                replacement=arguments["replacement"],
                directory=arguments.get("directory", "."),
                language=arguments.get("language", ""),
                dry_run=arguments.get("dry_run", True),
            )
            result_content = result

        else:
            result_content = f"Unknown tool: {name}"

        # Post-tool call hooks orchestration
        if result_content is not None:
             # Ensure we extract the text for hook processing
             if isinstance(result_content, list) and len(result_content) > 0 and hasattr(result_content[0], "text"):
                 processed_text = await hook_manager.execute_post_tool_call(name, arguments, result_content[0].text)
                 result_content[0].text = processed_text
             elif isinstance(result_content, str):
                 result_content = await hook_manager.execute_post_tool_call(name, arguments, result_content)
        
        # Format the final return
        if isinstance(result_content, list):
            return result_content
        return [TextContent(type="text", text=str(result_content))]

    except Exception as e:
        logger.error(f"Error in tool {name}: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


@server.list_prompts()
async def list_prompts() -> list[Prompt]:
    """List available agent prompts."""
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


@server.get_prompt()
async def get_prompt(name: str, arguments: dict[str, str] | None) -> GetPromptResult:
    """Get a specific agent prompt."""
    prompts_map = {
        "stravinsky": ("Stravinsky orchestrator system prompt", stravinsky.get_stravinsky_prompt),
        "delphi": ("Delphi advisor system prompt", delphi.get_delphi_prompt),
        "dewey": ("Dewey research agent prompt", dewey.get_dewey_prompt),
        "explore": ("Explore codebase search prompt", explore.get_explore_prompt),
        "frontend": ("Frontend UI/UX Engineer prompt", frontend.get_frontend_prompt),
        "document_writer": ("Document Writer prompt", document_writer.get_document_writer_prompt),
        "multimodal": ("Multimodal Looker prompt", multimodal.get_multimodal_prompt),
    }
    
    if name not in prompts_map:
        raise ValueError(f"Unknown prompt: {name}")
    
    description, get_prompt_fn = prompts_map[name]
    prompt_text = get_prompt_fn()
    
    return GetPromptResult(
        description=description,
        messages=[
            PromptMessage(
                role="user",
                content=TextContent(type="text", text=prompt_text),
            )
        ],
    )


async def async_main():
    """Async entry point for the MCP server."""
    # Move hook initialization to startup instead of import time
    from .hooks import initialize_hooks
    initialize_hooks()
    
    logger.info("Starting Stravinsky MCP Bridge Server...")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main():
    """Synchronous main entry point for uvx/CLI."""
    import argparse
    from . import __version__ as pkg_version
    
    parser = argparse.ArgumentParser(description="Stravinsky MCP Bridge Server")
    parser.add_argument("--version", action="version", version=f"stravinsky {pkg_version}")
    
    # Check for known arguments, but ignore others to pass through to stdio_server
    args, unknown = parser.parse_known_args()
    
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
