"""
Stravinsky MCP Bridge Server - Zero-Import-Weight Architecture

Optimized for extremely fast startup and protocol compliance:
- Lazy-loads all tool implementations and dependencies.
- Minimal top-level imports.
- Robust crash logging to stderr and /tmp.
"""

import sys
import os
import asyncio
import logging
import time
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

from . import __version__

# --- CRITICAL: PROTOCOL HYGIENE ---

# Configure logging to stderr explicitly to avoid protocol corruption
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Pre-async crash logger
def install_emergency_logger():
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.critical("FATAL PRE-STARTUP ERROR", exc_info=(exc_type, exc_value, exc_traceback))
        try:
            with open("/tmp/stravinsky_crash.log", "a") as f:
                import traceback
                f.write(f"\n--- CRASH AT {time.ctime()} ---\n")
                traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
        except:
            pass
            
    sys.excepthook = handle_exception

install_emergency_logger()

# --- SERVER INITIALIZATION ---

server = Server("stravinsky", version=__version__)

# Lazy-loaded systems
_token_store = None
_hook_manager = None

def get_token_store():
    global _token_store
    if _token_store is None:
        from .auth.token_store import TokenStore
        _token_store = TokenStore()
    return _token_store

def get_hook_manager_lazy():
    global _hook_manager
    if _hook_manager is None:
        from .hooks.manager import get_hook_manager
        _hook_manager = get_hook_manager()
    return _hook_manager

# --- MCP INTERFACE ---

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools (metadata only)."""
    from .server_tools import get_tool_definitions
    return get_tool_definitions()

@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls with deep lazy loading of implementations."""
    logger.info(f"Tool call: {name}")
    hook_manager = get_hook_manager_lazy()
    token_store = get_token_store()

    try:
        # Pre-tool call hooks orchestration
        arguments = await hook_manager.execute_pre_tool_call(name, arguments)
        
        result_content = None

        # --- MODEL DISPATCH ---
        if name == "invoke_gemini":
            from .tools.model_invoke import invoke_gemini
            result_content = await invoke_gemini(
                token_store=token_store,
                prompt=arguments["prompt"],
                model=arguments.get("model", "gemini-2.0-flash-exp"),
                temperature=arguments.get("temperature", 0.7),
                max_tokens=arguments.get("max_tokens", 8192),
                thinking_budget=arguments.get("thinking_budget", 0),
            )

        elif name == "invoke_openai":
            from .tools.model_invoke import invoke_openai
            result_content = await invoke_openai(
                token_store=token_store,
                prompt=arguments["prompt"],
                model=arguments.get("model", "gpt-4o"),
                temperature=arguments.get("temperature", 0.7),
                max_tokens=arguments.get("max_tokens", 4096),
                thinking_budget=arguments.get("thinking_budget", 0),
            )

        # --- CONTEXT DISPATCH ---
        elif name == "get_project_context":
            from .tools.project_context import get_project_context
            result_content = await get_project_context(project_path=arguments.get("project_path"))

        elif name == "get_system_health":
            from .tools.project_context import get_system_health
            result_content = await get_system_health()

        # --- SEARCH DISPATCH ---
        elif name == "grep_search":
            from .tools.code_search import grep_search
            result_content = await grep_search(
                pattern=arguments["pattern"],
                directory=arguments.get("directory", "."),
                file_pattern=arguments.get("file_pattern", ""),
            )

        elif name == "ast_grep_search":
            from .tools.code_search import ast_grep_search
            result_content = await ast_grep_search(
                pattern=arguments["pattern"],
                directory=arguments.get("directory", "."),
                language=arguments.get("language", ""),
            )

        elif name == "ast_grep_replace":
            from .tools.code_search import ast_grep_replace
            result_content = await ast_grep_replace(
                pattern=arguments["pattern"],
                replacement=arguments["replacement"],
                directory=arguments.get("directory", "."),
                language=arguments.get("language", ""),
                dry_run=arguments.get("dry_run", True),
            )

        elif name == "glob_files":
            from .tools.code_search import glob_files
            result_content = await glob_files(
                pattern=arguments["pattern"],
                directory=arguments.get("directory", "."),
            )

        # --- SESSION DISPATCH ---
        elif name == "session_list":
            from .tools.session_manager import list_sessions
            result_content = list_sessions(
                project_path=arguments.get("project_path"),
                limit=arguments.get("limit", 20),
            )

        elif name == "session_read":
            from .tools.session_manager import read_session
            result_content = read_session(
                session_id=arguments["session_id"],
                limit=arguments.get("limit"),
            )

        elif name == "session_search":
            from .tools.session_manager import search_sessions
            result_content = search_sessions(
                query=arguments["query"],
                session_id=arguments.get("session_id"),
                limit=arguments.get("limit", 20),
            )

        # --- SKILL DISPATCH ---
        elif name == "skill_list":
            from .tools.skill_loader import list_skills
            result_content = list_skills(project_path=arguments.get("project_path"))

        elif name == "skill_get":
            from .tools.skill_loader import get_skill
            result_content = get_skill(
                name=arguments["name"],
                project_path=arguments.get("project_path"),
            )
        
        elif name == "stravinsky_version":
            from . import __version__
            import sys
            import os
            result_content = [
                TextContent(
                    type="text",
                    text=f"Stravinsky Bridge v{__version__}\n"
                         f"Python: {sys.version.split()[0]}\n"
                         f"Platform: {sys.platform}\n"
                         f"CWD: {os.getcwd()}\n"
                         f"CLI: {os.environ.get('CLAUDE_CLI', '/opt/homebrew/bin/claude')}"
                )
            ]

        elif name == "system_restart":
            # Schedule a restart. We can't exit immediately or MCP will error on the reply.
            # We'll use a small delay.
            async def restart_soon():
                await asyncio.sleep(1)
                os._exit(0) # Immediate exit
            
            asyncio.create_task(restart_soon())
            result_content = [
                TextContent(
                    type="text",
                    text="🚀 Restarting Stravinsky Bridge... This process will exit and Claude Code will automatically respawn it. Please wait a few seconds before calling tools again."
                )
            ]

        # --- AGENT DISPATCH ---
        elif name == "agent_spawn":
            from .tools.agent_manager import agent_spawn
            result_content = await agent_spawn(**arguments)

        elif name == "agent_output":
            from .tools.agent_manager import agent_output
            result_content = await agent_output(
                task_id=arguments["task_id"],
                block=arguments.get("block", False),
            )

        elif name == "agent_cancel":
            from .tools.agent_manager import agent_cancel
            result_content = await agent_cancel(task_id=arguments["task_id"])

        elif name == "agent_list":
            from .tools.agent_manager import agent_list
            result_content = await agent_list()

        elif name == "agent_progress":
            from .tools.agent_manager import agent_progress
            result_content = await agent_progress(
                task_id=arguments["task_id"],
                lines=arguments.get("lines", 20),
            )

        elif name == "agent_retry":
            from .tools.agent_manager import agent_retry
            result_content = await agent_retry(
                task_id=arguments["task_id"],
                new_prompt=arguments.get("new_prompt"),
                new_timeout=arguments.get("new_timeout"),
            )

        # --- BACKGROUND TASK DISPATCH ---
        elif name == "task_spawn":
            from .tools.background_tasks import task_spawn
            result_content = await task_spawn(
                prompt=arguments["prompt"],
                model=arguments.get("model", "gemini-3-flash"),
            )

        elif name == "task_status":
            from .tools.background_tasks import task_status
            result_content = await task_status(task_id=arguments["task_id"])

        elif name == "task_list":
            from .tools.background_tasks import task_list
            result_content = await task_list()

        # --- LSP DISPATCH ---
        elif name == "lsp_hover":
            from .tools.lsp import lsp_hover
            result_content = await lsp_hover(
                file_path=arguments["file_path"],
                line=arguments["line"],
                character=arguments["character"],
            )

        elif name == "lsp_goto_definition":
            from .tools.lsp import lsp_goto_definition
            result_content = await lsp_goto_definition(
                file_path=arguments["file_path"],
                line=arguments["line"],
                character=arguments["character"],
            )

        elif name == "lsp_find_references":
            from .tools.lsp import lsp_find_references
            result_content = await lsp_find_references(
                file_path=arguments["file_path"],
                line=arguments["line"],
                character=arguments["character"],
                include_declaration=arguments.get("include_declaration", True),
            )

        elif name == "lsp_document_symbols":
            from .tools.lsp import lsp_document_symbols
            result_content = await lsp_document_symbols(file_path=arguments["file_path"])

        elif name == "lsp_workspace_symbols":
            from .tools.lsp import lsp_workspace_symbols
            result_content = await lsp_workspace_symbols(query=arguments["query"])

        elif name == "lsp_prepare_rename":
            from .tools.lsp import lsp_prepare_rename
            result_content = await lsp_prepare_rename(
                file_path=arguments["file_path"],
                line=arguments["line"],
                character=arguments["character"],
            )

        elif name == "lsp_rename":
            from .tools.lsp import lsp_rename
            result_content = await lsp_rename(
                file_path=arguments["file_path"],
                line=arguments["line"],
                character=arguments["character"],
                new_name=arguments["new_name"],
            )

        elif name == "lsp_code_actions":
            from .tools.lsp import lsp_code_actions
            result_content = await lsp_code_actions(
                file_path=arguments["file_path"],
                line=arguments["line"],
                character=arguments["character"],
            )

        elif name == "lsp_servers":
            from .tools.lsp import lsp_servers
            result_content = await lsp_servers()

        else:
            result_content = f"Unknown tool: {name}"

        # Post-tool call hooks orchestration
        if result_content is not None:
             if isinstance(result_content, list) and len(result_content) > 0 and hasattr(result_content[0], "text"):
                 processed_text = await hook_manager.execute_post_tool_call(name, arguments, result_content[0].text)
                 result_content[0].text = processed_text
             elif isinstance(result_content, str):
                 result_content = await hook_manager.execute_post_tool_call(name, arguments, result_content)
        
        # Format final return as List[TextContent]
        if isinstance(result_content, list):
            return result_content
        return [TextContent(type="text", text=str(result_content))]

    except Exception as e:
        logger.error(f"Error calling tool {name}: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]

@server.list_prompts()
async def list_prompts() -> list[Prompt]:
    """List available prompts (metadata only)."""
    from .server_tools import get_prompt_definitions
    return get_prompt_definitions()

@server.get_prompt()
async def get_prompt(name: str, arguments: dict[str, str] | None) -> GetPromptResult:
    """Get a specific prompt content (lazy loaded)."""
    from .prompts import stravinsky, delphi, dewey, explore, frontend, document_writer, multimodal
    
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
    """Server execution entry point."""
    # Initialize hooks at runtime, not import time
    try:
        from .hooks import initialize_hooks
        initialize_hooks()
    except Exception as e:
        logger.error(f"Failed to initialize hooks: {e}")

    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )
    except Exception as e:
        logger.critical("Server process crashed in async_main", exc_info=True)
        sys.exit(1)

def main():
    """Synchronous entry point with CLI arg handling."""
    import argparse
    import sys
    from .tools.agent_manager import get_manager
    from .auth.token_store import TokenStore
    
    parser = argparse.ArgumentParser(description="Stravinsky MCP Bridge Server")
    parser.add_argument("--version", action="version", version=f"stravinsky {__version__}")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # list command
    subparsers.add_parser("list", help="List background agent tasks")
    
    # status command
    subparsers.add_parser("status", help="Show system health and auth status")
    
    # start command (explicit server start)
    subparsers.add_parser("start", help="Start the MCP server (STDIO)")
    
    # stop command (stop all agents)
    stop_parser = subparsers.add_parser("stop", help="Stop all running agents")
    stop_parser.add_argument("--clear", action="store_true", help="Also clear agent history")
    
    # auth command (authentication)
    auth_parser = subparsers.add_parser("auth", help="Authentication commands")
    auth_subparsers = auth_parser.add_subparsers(dest="auth_command", help="Auth subcommands")
    login_parser = auth_subparsers.add_parser("login", help="Login to a provider")
    login_parser.add_argument("provider", choices=["gemini", "openai"], help="Provider to authenticate with")
    
    # Check for CLI flags
    args, unknown = parser.parse_known_args()
    
    if args.command == "list":
        # Run agent_list logic
        manager = get_manager()
        tasks = manager.list_tasks()
        if not tasks:
            print("No background agent tasks found.")
            return 0
        
        print("\nStravinsky Background Agents:")
        print("-" * 100)
        print(f"{'STATUS':10} | {'ID':15} | {'TYPE':10} | {'STARTED':20} | DESCRIPTION")
        print("-" * 100)
        for t in sorted(tasks, key=lambda x: x.get("created_at", ""), reverse=True):
            status = t["status"]
            task_id = t["id"]
            agent = t["agent_type"]
            created = t.get("created_at", "")[:19].replace("T", " ")  # Format datetime
            desc = t.get("description", t.get("prompt", "")[:40])[:40]
            print(f"{status.upper():10} | {task_id:15} | {agent:10} | {created:20} | {desc}")
            
            # Show error for failed agents
            if status == "failed" and t.get("error"):
                error_msg = t["error"][:100].replace("\n", " ")
                print(f"           └─ ERROR: {error_msg}")
        print("-" * 100)
        return 0
        
    elif args.command == "status":
        from .auth.cli import cmd_status
        return cmd_status(TokenStore())
        
    elif args.command == "start":
        asyncio.run(async_main())
        return 0
        
    elif args.command == "stop":
        manager = get_manager()
        count = manager.stop_all(clear_history=getattr(args, 'clear', False))
        if getattr(args, 'clear', False):
            print(f"Cleared {count} agent task(s) from history.")
        else:
            print(f"Stopped {count} running agent(s).")
        return 0
        
    elif args.command == "auth":
        if getattr(args, 'auth_command', None) == "login":
            from .auth.cli import cmd_login
            return cmd_login(args.provider)
        else:
            auth_parser.print_help()
            return 0
        
    else:
        # Default behavior: start server (fallback for MCP runners and unknown args)
        # This ensures that flags like --transport stdio don't cause an exit
        if unknown:
            logger.info(f"Starting MCP server with unknown arguments: {unknown}")
        asyncio.run(async_main())
        return 0

if __name__ == "__main__":
    main()
