#!/usr/bin/env python3
"""
Session Report CLI

A rich CLI tool for viewing Claude Code sessions with tool/agent/model summaries.
Optionally uses Gemini for session summarization.
"""

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

console = Console()


def get_sessions_directory() -> Path:
    """Get the Claude sessions directory."""
    return Path.home() / ".claude" / "projects"


def get_sessions(limit: int = 10, search_id: str | None = None) -> list[dict]:
    """Get recent sessions sorted by modification time.

    If search_id is provided, searches ALL sessions (ignores limit).
    """
    sessions_dir = get_sessions_directory()
    if not sessions_dir.exists():
        return []

    sessions = []
    for project_dir in sessions_dir.iterdir():
        if not project_dir.is_dir():
            continue

        for session_file in project_dir.glob("*.jsonl"):
            try:
                stat = session_file.stat()
                mtime = datetime.fromtimestamp(stat.st_mtime)
                sessions.append({
                    "id": session_file.stem,
                    "path": str(session_file),
                    "project": project_dir.name,
                    "modified": mtime,
                    "size": stat.st_size,
                })
            except Exception:
                continue

    sessions.sort(key=lambda s: s["modified"], reverse=True)

    # If searching by ID, don't limit
    if search_id:
        return sessions

    return sessions[:limit]


def read_session_messages(session_path: str) -> list[dict]:
    """Read all messages from a session file."""
    messages = []
    try:
        with open(session_path) as f:
            for line in f:
                if line.strip():
                    try:
                        msg = json.loads(line)
                        messages.append(msg)
                    except json.JSONDecodeError:
                        continue
    except Exception:
        pass
    return messages


def extract_tool_usage(messages: list[dict]) -> dict[str, Any]:
    """Extract tool, agent, and model usage from session messages.

    Claude Code session format:
    - Top-level: {type: "user"|"assistant", message: {role, content, model?}}
    - content can be string or list of {type: "text"|"tool_use"|"tool_result", ...}
    - tool_use has: {type: "tool_use", name: "ToolName", input: {...}}

    Captures:
    1. Subagents spawned (Task tool with subagent_type, MCP agent_spawn)
    2. External models invoked (invoke_gemini, invoke_openai with model param)
    3. All tools used (native and MCP)
    4. LSP tools specifically
    """
    # Native Claude tools (Read, Write, Edit, Bash, etc.)
    native_tools = Counter()
    # MCP tools by server (stravinsky, github, grep-app, etc.)
    mcp_tools_by_server: dict[str, Counter] = {}
    # Subagents from Task tool
    subagents = Counter()
    # MCP agents from agent_spawn
    mcp_agents = Counter()
    # Claude model used for responses
    claude_models = Counter()
    # External models invoked (gemini, openai)
    external_models = Counter()
    # LSP tools specifically
    lsp_tools = Counter()

    for msg in messages:
        msg_type = msg.get("type", "")
        inner_msg = msg.get("message", {})

        # Skip non-message types (snapshots, etc.)
        if msg_type not in ("user", "assistant"):
            continue

        # Extract Claude model from assistant messages
        model = inner_msg.get("model", "")
        if model and msg_type == "assistant":
            claude_models[model] += 1

        content = inner_msg.get("content", "")

        # Handle content as list (tool_use, text blocks, etc.)
        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue

                block_type = block.get("type", "")

                # Tool use blocks
                if block_type == "tool_use":
                    tool_name = block.get("name", "unknown")
                    tool_input = block.get("input", {})

                    # MCP tools (format: mcp__server__tool)
                    if tool_name.startswith("mcp__"):
                        parts = tool_name.split("__")
                        if len(parts) >= 3:
                            server = parts[1]
                            tool = parts[2]

                            # Track by server
                            if server not in mcp_tools_by_server:
                                mcp_tools_by_server[server] = Counter()
                            mcp_tools_by_server[server][tool] += 1

                            # Stravinsky-specific: agent_spawn
                            if server == "stravinsky" and tool == "agent_spawn":
                                agent_type = tool_input.get("agent_type", "explore")
                                model_used = tool_input.get("model", "gemini-3-flash")
                                mcp_agents[f"{agent_type} ({model_used})"] += 1

                            # Stravinsky-specific: invoke_gemini
                            if server == "stravinsky" and tool == "invoke_gemini":
                                model_used = tool_input.get("model", "gemini-3-flash")
                                external_models[f"gemini:{model_used}"] += 1

                            # Stravinsky-specific: invoke_openai
                            if server == "stravinsky" and tool == "invoke_openai":
                                model_used = tool_input.get("model", "gpt-5.2-codex")
                                external_models[f"openai:{model_used}"] += 1

                            # LSP tools
                            if server == "stravinsky" and tool.startswith("lsp_"):
                                lsp_tools[tool] += 1

                    # Native Task tool (spawns subagents)
                    elif tool_name == "Task":
                        subagent = tool_input.get("subagent_type", "")
                        if subagent:
                            subagents[subagent] += 1

                    # Other native tools
                    else:
                        native_tools[tool_name] += 1

    # Build categorized MCP tools dict
    mcp_tools_flat = {}
    for server, tools in mcp_tools_by_server.items():
        for tool, count in tools.items():
            mcp_tools_flat[f"{server}:{tool}"] = count

    return {
        "native_tools": dict(native_tools),
        "mcp_tools": mcp_tools_flat,
        "mcp_tools_by_server": {s: dict(t) for s, t in mcp_tools_by_server.items()},
        "subagents": dict(subagents),
        "mcp_agents": dict(mcp_agents),
        "claude_models": dict(claude_models),
        "external_models": dict(external_models),
        "lsp_tools": dict(lsp_tools),
    }


def format_size(size_bytes: int) -> str:
    """Format bytes to human readable size."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def display_session_list(sessions: list[dict]) -> None:
    """Display sessions in a rich table."""
    table = Table(title="Recent Claude Code Sessions", show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=3)
    table.add_column("Session ID", style="cyan", width=15)
    table.add_column("Modified", style="green", width=20)
    table.add_column("Size", justify="right", style="yellow", width=10)
    table.add_column("Project Hash", style="dim", width=12)

    for i, session in enumerate(sessions, 1):
        table.add_row(
            str(i),
            session["id"][:12] + "...",
            session["modified"].strftime("%Y-%m-%d %H:%M"),
            format_size(session["size"]),
            session["project"][:10] + "...",
        )

    console.print(table)


def extract_hooks(messages: list[dict]) -> dict[str, int]:
    """Extract hooks triggered from session messages.

    Hooks appear in:
    - system-reminder tags in user messages
    - tool_result content with hook output
    """
    hooks = Counter()

    for msg in messages:
        inner_msg = msg.get("message", {})
        content = inner_msg.get("content", "")

        # Check all content - could be string or list
        texts_to_check = []

        if isinstance(content, str):
            texts_to_check.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    # Text blocks
                    if block.get("type") == "text":
                        texts_to_check.append(block.get("text", ""))
                    # Tool result blocks (hooks often appear here)
                    elif block.get("type") == "tool_result":
                        result_content = block.get("content", "")
                        if isinstance(result_content, str):
                            texts_to_check.append(result_content)

        # Check all collected texts for hook patterns
        for text in texts_to_check:
            if "UserPromptSubmit hook" in text:
                hooks["UserPromptSubmit"] += 1
            if "PreToolUse hook" in text:
                hooks["PreToolUse"] += 1
            if "PostToolUse hook" in text:
                hooks["PostToolUse"] += 1
            if "<system-reminder>" in text:
                # Count system-reminder injections
                hooks["system-reminder"] += text.count("<system-reminder>")

    return dict(hooks)


def display_session_details(session: dict, usage: dict[str, Any], messages: list[dict]) -> None:
    """Display detailed session information with rich formatting."""
    # Session header
    header = Text()
    header.append("Session: ", style="bold")
    header.append(session["id"], style="cyan")
    console.print(Panel(header, title="Session Details", border_style="blue"))

    # Statistics
    stats_table = Table(show_header=False, box=None)
    stats_table.add_column("Key", style="bold")
    stats_table.add_column("Value")
    stats_table.add_row("Path", session["path"])
    stats_table.add_row("Modified", session["modified"].strftime("%Y-%m-%d %H:%M:%S"))
    stats_table.add_row("Size", format_size(session["size"]))
    stats_table.add_row("Messages", str(len(messages)))

    # Count roles (Claude Code format: type field at top level)
    user_msgs = sum(1 for m in messages if m.get("type") == "user")
    assistant_msgs = sum(1 for m in messages if m.get("type") == "assistant")
    stats_table.add_row("User Messages", str(user_msgs))
    stats_table.add_row("Assistant Messages", str(assistant_msgs))

    console.print(Panel(stats_table, title="Statistics", border_style="green"))

    # Claude Models (the model Claude Code uses)
    if usage.get("claude_models"):
        models_tree = Tree("[bold yellow]Claude Models")
        for model, count in sorted(usage["claude_models"].items(), key=lambda x: -x[1]):
            models_tree.add(f"{model}: [cyan]{count}[/cyan] responses")
        console.print(Panel(models_tree, title="Claude Model", border_style="yellow"))

    # External Models (gemini, openai invoked via MCP)
    if usage.get("external_models"):
        ext_tree = Tree("[bold green]External Models Invoked")
        for model, count in sorted(usage["external_models"].items(), key=lambda x: -x[1]):
            ext_tree.add(f"{model}: [cyan]{count}[/cyan] calls")
        console.print(Panel(ext_tree, title="External Models (Gemini/OpenAI)", border_style="green"))

    # Native tools
    if usage.get("native_tools"):
        tools_tree = Tree("[bold magenta]Native Tools")
        for tool, count in sorted(usage["native_tools"].items(), key=lambda x: -x[1]):
            tools_tree.add(f"{tool}: [yellow]{count}[/yellow] calls")
        console.print(Panel(tools_tree, title="Native Tool Usage", border_style="magenta"))

    # MCP tools by server
    if usage.get("mcp_tools_by_server"):
        for server, tools in sorted(usage["mcp_tools_by_server"].items()):
            server_tree = Tree(f"[bold cyan]{server}")
            for tool, count in sorted(tools.items(), key=lambda x: -x[1]):
                server_tree.add(f"{tool}: [yellow]{count}[/yellow] calls")
            console.print(Panel(server_tree, title=f"MCP: {server}", border_style="cyan"))

    # Subagents (Task tool)
    if usage.get("subagents"):
        subagents_tree = Tree("[bold blue]Subagents (Task tool)")
        for agent, count in sorted(usage["subagents"].items(), key=lambda x: -x[1]):
            subagents_tree.add(f"{agent}: [yellow]{count}[/yellow] spawned")
        console.print(Panel(subagents_tree, title="Subagent Usage", border_style="blue"))

    # MCP Agents (agent_spawn)
    if usage.get("mcp_agents"):
        agents_tree = Tree("[bold cyan]MCP Agents (agent_spawn)")
        for agent, count in sorted(usage["mcp_agents"].items(), key=lambda x: -x[1]):
            agents_tree.add(f"{agent}: [yellow]{count}[/yellow] spawned")
        console.print(Panel(agents_tree, title="MCP Agent Usage", border_style="cyan"))

    # LSP Tools
    if usage.get("lsp_tools"):
        lsp_tree = Tree("[bold red]LSP Tools")
        for tool, count in sorted(usage["lsp_tools"].items(), key=lambda x: -x[1]):
            lsp_tree.add(f"{tool}: [yellow]{count}[/yellow] calls")
        console.print(Panel(lsp_tree, title="LSP Usage", border_style="red"))

    # Hooks
    hooks = extract_hooks(messages)
    if hooks:
        hooks_tree = Tree("[bold white]Hooks Triggered")
        for hook, count in sorted(hooks.items(), key=lambda x: -x[1]):
            hooks_tree.add(f"{hook}: [yellow]{count}[/yellow] times")
        console.print(Panel(hooks_tree, title="Hooks", border_style="white"))


def summarize_with_gemini(session: dict, messages: list[dict], usage: dict[str, Any]) -> str | None:
    """Use Gemini to summarize the session."""
    try:
        from mcp_bridge.tools.model_invoke import invoke_gemini
    except ImportError:
        console.print("[red]Error: Could not import invoke_gemini[/red]")
        return None

    # Build context for Gemini
    user_msgs = sum(1 for m in messages if m.get("type") == "user")
    assistant_msgs = sum(1 for m in messages if m.get("type") == "assistant")

    context_parts = [
        "# Claude Code Session Analysis Request\n\n",
        f"**Session ID:** {session['id']}\n",
        f"**Modified:** {session['modified']}\n",
        f"**Total Messages:** {len(messages)} ({user_msgs} user, {assistant_msgs} assistant)\n\n",
        "## Tool/Agent/Model Usage Summary\n\n",
        f"**Tools Used:** {json.dumps(usage['tools'], indent=2)}\n\n",
        f"**MCP Tools:** {json.dumps(usage['mcp_tools'], indent=2)}\n\n",
        f"**Subagents (Task):** {usage.get('subagents', {})}\n\n",
        f"**MCP Agents:** {usage['agents']}\n\n",
        f"**Models:** {usage['models']}\n\n",
        "## Session Transcript\n\n",
    ]

    # Add messages (Gemini has 1M context window)
    # Parse Claude Code session format
    for i, msg in enumerate(messages):
        msg_type = msg.get("type", "")
        if msg_type not in ("user", "assistant"):
            continue

        inner_msg = msg.get("message", {})
        role = inner_msg.get("role", msg_type)
        content = inner_msg.get("content", "")

        # Extract text from content blocks
        if isinstance(content, list):
            text_parts = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif block.get("type") == "tool_use":
                        tool_name = block.get("name", "unknown")
                        text_parts.append(f"[TOOL: {tool_name}]")
                    elif block.get("type") == "thinking":
                        text_parts.append("[THINKING]")
            content = " ".join(text_parts)

        # Truncate very long messages
        if len(content) > 2000:
            content = content[:2000] + "... [truncated]"

        context_parts.append(f"**[{i+1}] {role}:** {content}\n\n")

    context = "".join(context_parts)

    prompt = f"""Analyze this Claude Code session and provide a concise summary:

{context}

Please provide:
1. **Session Purpose**: What was the user trying to accomplish?
2. **Key Actions**: Main tools, agents, and operations used
3. **Outcome**: Was the task successful? Any notable issues?
4. **Recommendations**: Any suggestions for improvement?

Keep the summary concise but informative."""

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task(description="Analyzing session with Gemini...", total=None)
        try:
            # Run synchronously
            import asyncio
            result = asyncio.run(invoke_gemini(
                prompt=prompt,
                model="gemini-3-flash",
                max_tokens=2048,
            ))
            return result
        except Exception as e:
            console.print(f"[red]Gemini error: {e}[/red]")
            return None


def main():
    parser = argparse.ArgumentParser(
        description="Analyze Claude Code sessions with rich formatting",
        prog="stravinsky-sessions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  stravinsky-sessions                    # List 10 recent sessions
  stravinsky-sessions --limit 20         # List 20 recent sessions
  stravinsky-sessions --select 1         # Show details for session #1
  stravinsky-sessions --select 1 --summarize  # Summarize with Gemini
  stravinsky-sessions --id abc123        # Show session by ID prefix
""",
    )

    parser.add_argument(
        "--limit", "-n",
        type=int,
        default=10,
        help="Number of sessions to list (default: 10)",
    )
    parser.add_argument(
        "--select", "-s",
        type=int,
        help="Select session by number from list (1-indexed)",
    )
    parser.add_argument(
        "--id",
        type=str,
        help="Select session by ID or ID prefix",
    )
    parser.add_argument(
        "--summarize",
        action="store_true",
        help="Use Gemini to summarize the session",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON instead of rich formatting",
    )

    args = parser.parse_args()

    # Get sessions (search all if --id is specified)
    sessions = get_sessions(limit=args.limit, search_id=args.id)

    if not sessions:
        console.print("[yellow]No sessions found[/yellow]")
        return 1

    # Select session by number or ID
    selected_session = None

    if args.select:
        # For --select, re-get with limit
        display_sessions = get_sessions(limit=args.limit)
        if 1 <= args.select <= len(display_sessions):
            selected_session = display_sessions[args.select - 1]
        else:
            console.print(f"[red]Invalid selection: {args.select}. Must be 1-{len(display_sessions)}[/red]")
            return 1
    elif args.id:
        for s in sessions:
            if s["id"].startswith(args.id):
                selected_session = s
                break
        if not selected_session:
            console.print(f"[red]Session not found: {args.id}[/red]")
            return 1

    if selected_session:
        # Read and analyze session
        messages = read_session_messages(selected_session["path"])
        usage = extract_tool_usage(messages)

        if args.json:
            user_msgs = sum(1 for m in messages if m.get("type") == "user")
            assistant_msgs = sum(1 for m in messages if m.get("type") == "assistant")
            hooks = extract_hooks(messages)
            output = {
                "session": {
                    "id": selected_session["id"],
                    "path": selected_session["path"],
                    "modified": selected_session["modified"].isoformat(),
                    "size": selected_session["size"],
                    "message_count": len(messages),
                    "user_messages": user_msgs,
                    "assistant_messages": assistant_msgs,
                },
                "claude_models": usage.get("claude_models", {}),
                "external_models": usage.get("external_models", {}),
                "native_tools": usage.get("native_tools", {}),
                "mcp_tools_by_server": usage.get("mcp_tools_by_server", {}),
                "subagents": usage.get("subagents", {}),
                "mcp_agents": usage.get("mcp_agents", {}),
                "lsp_tools": usage.get("lsp_tools", {}),
                "hooks": hooks,
            }
            print(json.dumps(output, indent=2))
        else:
            display_session_details(selected_session, usage, messages)

        if args.summarize:
            console.print()
            summary = summarize_with_gemini(selected_session, messages, usage)
            if summary:
                console.print(Panel(summary, title="Gemini Summary", border_style="green"))
    else:
        # List sessions
        if args.json:
            output = [
                {
                    "id": s["id"],
                    "modified": s["modified"].isoformat(),
                    "size": s["size"],
                }
                for s in sessions
            ]
            print(json.dumps(output, indent=2))
        else:
            display_session_list(sessions)
            console.print("\n[dim]Use --select N or --id PREFIX to view session details[/dim]")

    return 0


if __name__ == "__main__":
    sys.exit(main())
