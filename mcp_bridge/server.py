"""
Stravinsky MCP Bridge Server - Zero-Import-Weight Architecture

Optimized for extremely fast startup and protocol compliance:
- Lazy-loads all tool implementations and dependencies.
- Minimal top-level imports.
- Robust crash logging to stderr and /tmp.
"""

import asyncio
import logging
import os
import sys
import time
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    GetPromptResult,
    Prompt,
    PromptMessage,
    TextContent,
    Tool,
)

from . import __version__

# --- CRITICAL: PROTOCOL HYGIENE ---

# Configure logging to stderr explicitly to avoid protocol corruption
logging.basicConfig(
    level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s", stream=sys.stderr
)
logger = logging.getLogger(__name__)

# --- LOAD .env FILES (GEMINI_API_KEY, etc.) ---
# Load from ~/.stravinsky/.env (dedicated config location)
try:
    from pathlib import Path

    from dotenv import load_dotenv

    # Load from ~/.env (user-global, lowest priority)
    home_env = Path.home() / ".env"
    if home_env.exists():
        load_dotenv(home_env, override=False)

    # Load from ~/.stravinsky/.env (stravinsky config, takes precedence)
    stravinsky_env = Path.home() / ".stravinsky" / ".env"
    if stravinsky_env.exists():
        load_dotenv(stravinsky_env, override=True)
        logger.info(f"[Config] Loaded environment from {stravinsky_env}")
except ImportError:
    pass  # python-dotenv not installed, skip


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
                model=arguments.get("model", "gemini-3-flash"),
                temperature=arguments.get("temperature", 0.7),
                max_tokens=arguments.get("max_tokens", 8192),
                thinking_budget=arguments.get("thinking_budget", 0),
            )

        elif name == "invoke_gemini_agentic":
            from .tools.model_invoke import invoke_gemini_agentic

            result_content = await invoke_gemini_agentic(
                token_store=token_store,
                prompt=arguments["prompt"],
                model=arguments.get("model", "gemini-3-flash"),
                max_turns=arguments.get("max_turns", 10),
                timeout=arguments.get("timeout", 120),
            )

        elif name == "invoke_openai":
            from .tools.model_invoke import invoke_openai

            result_content = await invoke_openai(
                token_store=token_store,
                prompt=arguments["prompt"],
                model=arguments.get("model", "gpt-5.2-codex"),
                temperature=arguments.get("temperature", 0.7),
                max_tokens=arguments.get("max_tokens", 4096),
                thinking_budget=arguments.get("thinking_budget", 0),
                reasoning_effort=arguments.get("reasoning_effort", "medium"),
            )

        # --- CONTEXT DISPATCH ---
        elif name == "get_project_context":
            from .tools.project_context import get_project_context

            result_content = await get_project_context(project_path=arguments.get("project_path"))

        elif name == "get_system_health":
            from .tools.project_context import get_system_health

            result_content = await get_system_health()

        elif name == "semantic_health":
            from .tools.semantic_search import semantic_health

            result_content = await semantic_health(
                project_path=arguments.get("project_path", "."),
                provider=arguments.get("provider", "ollama"),
            )

        elif name == "lsp_health":
            from .tools.lsp.tools import lsp_health

            result_content = await lsp_health()

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

        elif name == "tool_search":
            from .tools.tool_search import search_tools
            from .server_tools import get_tool_definitions

            # Get all registered tool definitions to search through
            all_tools = get_tool_definitions()

            result_content = search_tools(
                query=arguments["query"],
                tools=all_tools,
                top_k=arguments.get("top_k", 5),
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
            # sys and os already imported at module level
            result_content = [
                TextContent(
                    type="text",
                    text=f"Stravinsky Bridge v{__version__}\n"
                    f"Python: {sys.version.split()[0]}\n"
                    f"Platform: {sys.platform}\n"
                    f"CWD: {os.getcwd()}\n"
                    f"CLI: {os.environ.get('CLAUDE_CLI', '/opt/homebrew/bin/claude')}",
                )
            ]

        elif name == "system_restart":
            # Schedule a restart. We can't exit immediately or MCP will error on the reply.
            # We'll use a small delay.
            async def restart_soon():
                await asyncio.sleep(1)
                os._exit(0)  # Immediate exit

            asyncio.create_task(restart_soon())
            result_content = [
                TextContent(
                    type="text",
                    text="🚀 Restarting Stravinsky Bridge... This process will exit and Claude Code will automatically respawn it. Please wait a few seconds before calling tools again.",
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

            result_content = await agent_list(show_all=arguments.get("show_all", True))

        elif name == "agent_cleanup":
            from .tools.agent_manager import agent_cleanup

            result_content = await agent_cleanup(
                max_age_minutes=arguments.get("max_age_minutes", 30),
                statuses=arguments.get("statuses"),
            )

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

        elif name == "lsp_code_action_resolve":
            from .tools.lsp import lsp_code_action_resolve

            result_content = await lsp_code_action_resolve(
                file_path=arguments["file_path"],
                action_code=arguments["action_code"],
                line=arguments.get("line"),
            )

        elif name == "lsp_extract_refactor":
            from .tools.lsp import lsp_extract_refactor

            result_content = await lsp_extract_refactor(
                file_path=arguments["file_path"],
                start_line=arguments["start_line"],
                start_char=arguments["start_char"],
                end_line=arguments["end_line"],
                end_char=arguments["end_char"],
                new_name=arguments["new_name"],
                kind=arguments.get("kind", "function"),
            )

        elif name == "lsp_servers":
            from .tools.lsp import lsp_servers

            result_content = await lsp_servers()

        elif name == "lsp_diagnostics":
            from .tools.code_search import lsp_diagnostics

            result_content = await lsp_diagnostics(
                file_path=arguments["file_path"],
                severity=arguments.get("severity", "all"),
            )

        elif name == "semantic_search":
            from .tools.semantic_search import semantic_search

            result_content = await semantic_search(
                query=arguments["query"],
                project_path=arguments.get("project_path", "."),
                n_results=arguments.get("n_results", 10),
                language=arguments.get("language"),
                node_type=arguments.get("node_type"),
                provider=arguments.get("provider", "ollama"),
            )

        elif name == "hybrid_search":
            from .tools.semantic_search import hybrid_search

            result_content = await hybrid_search(
                query=arguments["query"],
                pattern=arguments.get("pattern"),
                project_path=arguments.get("project_path", "."),
                n_results=arguments.get("n_results", 10),
                language=arguments.get("language"),
                provider=arguments.get("provider", "ollama"),
            )

        elif name == "find_code":
            from .tools.find_code import find_code

            result_content = await find_code(
                query=arguments["query"],
                search_type=arguments.get("search_type", "auto"),
                project_path=arguments.get("project_path", "."),
                language=arguments.get("language"),
                n_results=arguments.get("n_results", 10),
                provider=arguments.get("provider", "ollama"),
            )

        elif name == "multi_query_search":
            from .tools.search_enhancements import multi_query_search

            result_content = await multi_query_search(
                query=arguments["query"],
                project_path=arguments.get("project_path", "."),
                n_results=arguments.get("n_results", 10),
                num_expansions=arguments.get("num_expansions", 3),
                language=arguments.get("language"),
                node_type=arguments.get("node_type"),
                provider=arguments.get("provider", "ollama"),
            )

        elif name == "decomposed_search":
            from .tools.search_enhancements import decomposed_search

            result_content = await decomposed_search(
                query=arguments["query"],
                project_path=arguments.get("project_path", "."),
                n_results=arguments.get("n_results", 10),
                language=arguments.get("language"),
                node_type=arguments.get("node_type"),
                provider=arguments.get("provider", "ollama"),
            )

        elif name == "enhanced_search":
            from .tools.search_enhancements import enhanced_search

            result_content = await enhanced_search(
                query=arguments["query"],
                project_path=arguments.get("project_path", "."),
                n_results=arguments.get("n_results", 10),
                mode=arguments.get("mode", "auto"),
                language=arguments.get("language"),
                node_type=arguments.get("node_type"),
                provider=arguments.get("provider", "ollama"),
            )

        elif name == "get_cost_report":
            from .tools.dashboard import get_cost_report

            result_content = await get_cost_report(
                session_id=arguments.get("session_id"),
            )

        elif name == "semantic_index":
            from .tools.semantic_search import index_codebase

            result_content = await index_codebase(
                project_path=arguments.get("project_path", "."),
                force=arguments.get("force", False),
                provider=arguments.get("provider", "ollama"),
            )

        elif name == "semantic_stats":
            from .tools.semantic_search import semantic_stats

            result_content = await semantic_stats(
                project_path=arguments.get("project_path", "."),
                provider=arguments.get("provider", "ollama"),
            )

        elif name == "start_file_watcher":
            import json

            from .tools.semantic_search import start_file_watcher

            try:
                watcher = await start_file_watcher(
                    project_path=arguments.get("project_path", "."),
                    provider=arguments.get("provider", "ollama"),
                    debounce_seconds=arguments.get("debounce_seconds", 2.0),
                )

                result_content = json.dumps(
                    {
                        "status": "started",
                        "project_path": str(watcher.project_path),
                        "debounce_seconds": watcher.debounce_seconds,
                        "provider": watcher.store.provider_name,
                        "is_running": watcher.is_running(),
                    },
                    indent=2,
                )
            except ValueError as e:
                # No index exists
                result_content = json.dumps(
                    {"error": str(e), "hint": "Run semantic_index() before starting file watcher"},
                    indent=2,
                )
                print(f"⚠️  start_file_watcher ValueError: {e}", file=sys.stderr)
            except Exception as e:
                # Unexpected error
                import traceback

                result_content = json.dumps(
                    {
                        "error": f"{type(e).__name__}: {str(e)}",
                        "hint": "Check MCP server logs for details",
                    },
                    indent=2,
                )
                print(f"❌ start_file_watcher error: {e}", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)

        elif name == "stop_file_watcher":
            import json

            from .tools.semantic_search import stop_file_watcher

            stopped = stop_file_watcher(
                project_path=arguments.get("project_path", "."),
            )

            result_content = json.dumps(
                {"stopped": stopped, "project_path": arguments.get("project_path", ".")}, indent=2
            )

        elif name == "cancel_indexing":
            from .tools.semantic_search import cancel_indexing

            result_content = cancel_indexing(
                project_path=arguments.get("project_path", "."),
                provider=arguments.get("provider", "ollama"),
            )

        elif name == "delete_index":
            from .tools.semantic_search import delete_index

            result_content = delete_index(
                project_path=arguments.get("project_path", "."),
                provider=arguments.get("provider"),  # None if not specified
                delete_all=arguments.get("delete_all", False),
            )

        elif name == "list_file_watchers":
            import json

            from .tools.semantic_search import list_file_watchers

            result_content = json.dumps(list_file_watchers(), indent=2)

        elif name == "multi_query_search":
            from .tools.semantic_search import multi_query_search

            result_content = await multi_query_search(
                query=arguments["query"],
                project_path=arguments.get("project_path", "."),
                n_results=arguments.get("n_results", 10),
                num_expansions=arguments.get("num_expansions", 3),
                language=arguments.get("language"),
                node_type=arguments.get("node_type"),
                provider=arguments.get("provider", "ollama"),
            )

        elif name == "decomposed_search":
            from .tools.semantic_search import decomposed_search

            result_content = await decomposed_search(
                query=arguments["query"],
                project_path=arguments.get("project_path", "."),
                n_results=arguments.get("n_results", 10),
                language=arguments.get("language"),
                node_type=arguments.get("node_type"),
                provider=arguments.get("provider", "ollama"),
            )

        elif name == "enhanced_search":
            from .tools.semantic_search import enhanced_search

            result_content = await enhanced_search(
                query=arguments["query"],
                project_path=arguments.get("project_path", "."),
                n_results=arguments.get("n_results", 10),
                mode=arguments.get("mode", "auto"),
                language=arguments.get("language"),
                node_type=arguments.get("node_type"),
                provider=arguments.get("provider", "ollama"),
            )

        else:
            result_content = f"Unknown tool: {name}"

        # Post-tool call hooks orchestration
        if result_content is not None:
            if (
                isinstance(result_content, list)
                and len(result_content) > 0
                and hasattr(result_content[0], "text")
            ):
                processed_text = await hook_manager.execute_post_tool_call(
                    name, arguments, result_content[0].text
                )
                # Only update if processed_text is non-empty to avoid empty text blocks
                # (API error: cache_control cannot be set for empty text blocks)
                if processed_text:
                    result_content[0].text = processed_text
            elif isinstance(result_content, str):
                result_content = await hook_manager.execute_post_tool_call(
                    name, arguments, result_content
                )

        # Format final return as List[TextContent]
        if isinstance(result_content, list):
            return result_content
        return [TextContent(type="text", text=str(result_content))]

    except Exception as e:
        import traceback

        tb = traceback.format_exc()
        logger.error(f"Error calling tool {name}: {e}\n{tb}")
        return [TextContent(type="text", text=f"Error: {str(e)}\n\nTraceback:\n{tb}")]


@server.list_prompts()
async def list_prompts() -> list[Prompt]:
    """List available prompts (metadata only)."""
    from .server_tools import get_prompt_definitions

    return get_prompt_definitions()


@server.get_prompt()
async def get_prompt(name: str, arguments: dict[str, str] | None) -> GetPromptResult:
    """Get a specific prompt content (lazy loaded)."""
    from .prompts import delphi, dewey, document_writer, explore, frontend, multimodal, stravinsky

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


def sync_user_assets():
    """
    Copy package assets to user scope (~/.claude/) on every MCP load.

    This ensures all repos get the latest commands, hooks, rules, and agents
    from the installed Stravinsky package.

    Handles both:
    - Development: .claude/ relative to project root
    - Installed package: stravinsky_claude_assets/ in site-packages
    """
    from pathlib import Path
    import shutil

    # Try multiple locations for package assets
    package_dir = Path(__file__).parent.parent  # stravinsky/

    # Location 1: Development - .claude/ at project root
    dev_claude = package_dir / ".claude"

    # Location 2: Installed package - stravinsky_claude_assets in site-packages
    # When installed via pip/uvx, hatch includes .claude as stravinsky_claude_assets
    installed_claude = package_dir / "stravinsky_claude_assets"

    # Also check relative to mcp_bridge (alternate install layout)
    mcp_bridge_dir = Path(__file__).parent
    installed_claude_alt = mcp_bridge_dir.parent / "stravinsky_claude_assets"

    # Find the first existing assets directory
    package_claude = None
    for candidate in [dev_claude, installed_claude, installed_claude_alt]:
        if candidate.exists():
            package_claude = candidate
            break

    # User scope directory
    user_claude = Path.home() / ".claude"

    if package_claude is None:
        # Try importlib.resources as last resort (Python 3.9+)
        try:
            import importlib.resources as resources

            # Check if stravinsky_claude_assets is a package
            with resources.files("stravinsky_claude_assets") as assets_path:
                if assets_path.is_dir():
                    package_claude = Path(assets_path)
        except (ImportError, ModuleNotFoundError, TypeError):
            pass

    if package_claude is None:
        logger.debug(f"Package assets not found (checked: {dev_claude}, {installed_claude})")
        return

    # Directories to sync
    dirs_to_sync = ["commands", "hooks", "rules", "agents"]

    for dir_name in dirs_to_sync:
        src_dir = package_claude / dir_name
        dst_dir = user_claude / dir_name

        if not src_dir.exists():
            continue

        # Create destination if it doesn't exist
        dst_dir.mkdir(parents=True, exist_ok=True)

        # Copy all files recursively (overwrite if source is newer)
        for src_file in src_dir.rglob("*"):
            if src_file.is_file():
                # Compute relative path
                rel_path = src_file.relative_to(src_dir)
                dst_file = dst_dir / rel_path

                # Create parent directories
                dst_file.parent.mkdir(parents=True, exist_ok=True)

                # Copy if source is newer or dest doesn't exist
                should_copy = not dst_file.exists()
                if dst_file.exists():
                    src_mtime = src_file.stat().st_mtime
                    dst_mtime = dst_file.stat().st_mtime
                    should_copy = src_mtime > dst_mtime

                if should_copy:
                    shutil.copy2(src_file, dst_file)
                    logger.debug(f"Synced {dir_name}/{rel_path} to user scope")

    logger.info("Synced package assets to user scope (~/.claude/)")


async def async_main():
    """Server execution entry point."""
    # Sync package assets to user scope on every MCP load
    try:
        sync_user_assets()
    except Exception as e:
        logger.warning(f"Failed to sync user assets: {e}")

    # Initialize hooks at runtime, not import time
    try:
        from .hooks import initialize_hooks

        initialize_hooks()
    except Exception as e:
        logger.error(f"Failed to initialize hooks: {e}")

    # Clean up stale ChromaDB locks on startup
    try:
        from .tools.semantic_search import cleanup_stale_chromadb_locks

        removed_count = cleanup_stale_chromadb_locks()
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} stale ChromaDB lock(s)")
    except Exception as e:
        logger.warning(f"Failed to cleanup ChromaDB locks: {e}")

    # Start background token refresh scheduler
    try:
        from .auth.token_refresh import background_token_refresh

        asyncio.create_task(background_token_refresh(get_token_store()))
        logger.info("Background token refresh scheduler started")
    except Exception as e:
        logger.warning(f"Failed to start token refresh scheduler: {e}")

    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )
    except Exception:
        logger.critical("Server process crashed in async_main", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Initiating shutdown sequence...")
        from .tools.lsp.manager import get_lsp_manager

        lsp_manager = get_lsp_manager()
        await lsp_manager.shutdown()


def main():
    """Synchronous entry point with CLI arg handling."""
    import argparse

    from .auth.token_store import TokenStore
    from .tools.agent_manager import get_manager

    parser = argparse.ArgumentParser(
        description="Stravinsky MCP Bridge - Multi-model AI orchestration for Claude Code. "
        "Spawns background agents with full tool access via Claude CLI.",
        prog="stravinsky",
        epilog="Examples:\n"
        "  stravinsky              # Start MCP server (default)\n"
        "  stravinsky list         # Show all background agents\n"
        "  stravinsky status       # Check auth status\n"
        "  stravinsky stop --clear # Stop agents and clear history\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"stravinsky {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands", metavar="COMMAND")

    # list command
    subparsers.add_parser(
        "list",
        help="List all background agent tasks",
        description="Shows status, ID, type, and description of all spawned agents.",
    )

    # status command
    subparsers.add_parser(
        "status",
        help="Show authentication status for all providers",
        description="Displays OAuth authentication status and token expiration for Gemini and OpenAI.",
    )

    # start command (explicit server start)
    subparsers.add_parser(
        "start",
        help="Explicitly start the MCP server (STDIO transport)",
        description="Starts the MCP server for communication with Claude Code. Usually started automatically.",
    )

    # stop command (stop all agents)
    stop_parser = subparsers.add_parser(
        "stop",
        help="Stop all running background agents",
        description="Terminates all active agent processes. Use --clear to also remove history.",
    )
    stop_parser.add_argument(
        "--clear",
        action="store_true",
        help="Also clear agent history from .stravinsky/agents.json",
    )

    # auth command (authentication)
    auth_parser = subparsers.add_parser(
        "auth",
        help="Authentication commands (login/logout/refresh/status)",
        description="Manage OAuth authentication for Gemini and OpenAI providers.",
    )
    auth_subparsers = auth_parser.add_subparsers(
        dest="auth_command", help="Auth subcommands", metavar="SUBCOMMAND"
    )

    # auth login
    login_parser = auth_subparsers.add_parser(
        "login",
        help="Login to a provider via browser OAuth",
        description="Opens browser for OAuth authentication with the specified provider.",
    )
    login_parser.add_argument(
        "provider",
        choices=["gemini", "openai"],
        metavar="PROVIDER",
        help="Provider to authenticate with: gemini (Google) or openai (ChatGPT Plus/Pro)",
    )

    # auth logout
    logout_parser = auth_subparsers.add_parser(
        "logout",
        help="Remove stored OAuth credentials",
        description="Deletes stored access and refresh tokens for the specified provider.",
    )
    logout_parser.add_argument(
        "provider",
        choices=["gemini", "openai"],
        metavar="PROVIDER",
        help="Provider to logout from: gemini or openai",
    )

    # auth status
    auth_subparsers.add_parser(
        "status",
        help="Show authentication status for all providers",
        description="Displays authentication status and token expiration for Gemini and OpenAI.",
    )

    # auth refresh
    refresh_parser = auth_subparsers.add_parser(
        "refresh",
        help="Manually refresh access token",
        description="Force-refresh the access token using the stored refresh token.",
    )
    refresh_parser.add_argument(
        "provider",
        choices=["gemini", "openai"],
        metavar="PROVIDER",
        help="Provider to refresh token for: gemini or openai",
    )

    # auth init
    auth_subparsers.add_parser(
        "init",
        help="Bootstrap current repository for Stravinsky",
        description="Creates .stravinsky/ directory structure and copies default configuration files.",
    )

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
        count = manager.stop_all(clear_history=getattr(args, "clear", False))
        if getattr(args, "clear", False):
            print(f"Cleared {count} agent task(s) from history.")
        else:
            print(f"Stopped {count} running agent(s).")
        return 0

    elif args.command == "auth":
        auth_cmd = getattr(args, "auth_command", None)
        token_store = get_token_store()

        if auth_cmd == "login":
            from .auth.cli import cmd_login

            return cmd_login(args.provider, token_store)

        elif auth_cmd == "logout":
            from .auth.cli import cmd_logout

            return cmd_logout(args.provider, token_store)

        elif auth_cmd == "status":
            from .auth.cli import cmd_status

            return cmd_status(token_store)

        elif auth_cmd == "refresh":
            from .auth.cli import cmd_refresh

            return cmd_refresh(args.provider, token_store)

        elif auth_cmd == "init":
            from .tools.init import bootstrap_repo

            print(bootstrap_repo())
            return 0

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
    sys.exit(main())
