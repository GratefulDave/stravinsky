"""
Agent Manager for Stravinsky.

Spawns background agents using Claude Code CLI with full tool access.
This replaces the simple model-only invocation with true agentic execution.
"""

import json
import logging
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# Output formatting modes
class OutputMode(Enum):
    """Control verbosity of agent spawn output."""

    CLEAN = "clean"  # Concise single-line output
    VERBOSE = "verbose"  # Full details with colors
    SILENT = "silent"  # No output to stdout (logs only)


# Model routing configuration
# Specialized agents call external models via MCP tools:
#   explore/dewey/document_writer/multimodal → invoke_gemini(gemini-3-flash)
#   frontend → invoke_gemini(gemini-3-pro-high)
#   delphi → invoke_openai(gpt-5.2)
# Non-specialized coding tasks use Claude CLI with --model sonnet
AGENT_MODEL_ROUTING = {
    # Specialized agents - no CLI model flag, they call invoke_* tools
    "explore": None,
    "dewey": None,
    "document_writer": None,
    "multimodal": None,
    "frontend": None,
    "delphi": None,
    "research-lead": None,  # Hierarchical orchestrator using gemini-3-flash
    "implementation-lead": "sonnet",  # Hierarchical orchestrator using sonnet
    # Quality agents - use gemini-3-flash for better quality at same cost
    "momus": None,  # Quality gate validator - uses gemini-3-flash
    "comment_checker": None,  # Documentation validator - uses gemini-3-flash
    "debugger": "sonnet",  # Root cause analysis specialist - needs power
    "code-reviewer": None,  # Code review specialist - uses gemini-3-flash
    # Planner uses Opus for superior reasoning about dependencies and parallelization
    "planner": "opus",
    # Default for unknown agent types (coding tasks) - use Sonnet 4.5
    "_default": "sonnet",
}

# Cost tier classification (from oh-my-opencode pattern)
AGENT_COST_TIERS = {
    "explore": "CHEAP",  # Uses gemini-3-flash
    "dewey": "CHEAP",  # Uses gemini-3-flash
    "document_writer": "CHEAP",  # Uses gemini-3-flash
    "multimodal": "CHEAP",  # Uses gemini-3-flash
    "research-lead": "CHEAP",  # Uses gemini-3-flash
    "implementation-lead": "MEDIUM",  # Uses sonnet-4.5
    "momus": "CHEAP",  # Uses haiku for validation
    "comment_checker": "CHEAP",  # Uses haiku for doc validation
    "debugger": "MEDIUM",  # Uses sonnet for debugging
    "code-reviewer": "CHEAP",  # Uses haiku for reviews
    "frontend": "MEDIUM",  # Uses gemini-3-pro-high
    "delphi": "EXPENSIVE",  # Uses gpt-5.2 (OpenAI GPT)
    "planner": "EXPENSIVE",  # Uses Claude Opus 4.5
    "_default": "EXPENSIVE",  # Claude Sonnet 4.5 via CLI
}

# Display model names for output formatting (user-visible)
AGENT_DISPLAY_MODELS = {
    "explore": "gemini-3-flash",
    "dewey": "gemini-3-flash",
    "document_writer": "gemini-3-flash",
    "multimodal": "gemini-3-flash",
    "research-lead": "gemini-3-flash",
    "implementation-lead": "claude-sonnet-4.5",
    "momus": "gemini-3-flash",
    "comment_checker": "gemini-3-flash",
    "debugger": "claude-sonnet-4.5",
    "code-reviewer": "gemini-3-flash",
    "frontend": "gemini-3-pro-high",
    "delphi": "gpt-5.2",
    "planner": "opus-4.5",
    "_default": "sonnet-4.5",
}

# Cost tier emoji indicators for visual differentiation
# Colors indicate cost: 🟢 cheap/free, 🔵 medium, 🟣 expensive (GPT), 🟠 Claude
COST_TIER_EMOJI = {
    "CHEAP": "🟢",  # Free/cheap models (gemini-3-flash, haiku)
    "MEDIUM": "🔵",  # Medium cost (gemini-3-pro-high)
    "EXPENSIVE": "🟣",  # Expensive models (gpt-5.2, opus)
}

# Model family indicators
MODEL_FAMILY_EMOJI = {
    "gemini-3-flash": "🟢",
    "gemini-3-pro-high": "🔵",
    "haiku": "🟢",
    "sonnet-4.5": "🟠",
    "opus-4.5": "🟣",
    "gpt-5.2": "🟣",
}


# ANSI color codes for terminal output
class Colors:
    """ANSI color codes for colorized terminal output."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright foreground colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"


def get_agent_emoji(agent_type: str) -> str:
    """Get the colored emoji indicator for an agent based on its cost tier."""
    cost_tier = AGENT_COST_TIERS.get(agent_type, AGENT_COST_TIERS["_default"])
    return COST_TIER_EMOJI.get(cost_tier, "⚪")


def get_model_emoji(model_name: str) -> str:
    """Get the colored emoji indicator for a model."""
    return MODEL_FAMILY_EMOJI.get(model_name, "⚪")


# Agent hierarchy classification
ORCHESTRATOR_AGENTS = ["stravinsky", "research-lead", "implementation-lead"]
WORKER_AGENTS = [
    "explore",
    "dewey",
    "delphi",
    "frontend",
    "debugger",
    "code-reviewer",
    "momus",
    "comment_checker",
    "document_writer",
    "multimodal",
    "planner",
]

# Tool access control matrix - defines which tools each agent type can use
AGENT_TOOLS = {
    # Orchestrators - full tool access for delegation and coordination
    "stravinsky": ["all"],
    "research-lead": ["agent_spawn", "agent_output", "invoke_gemini", "Read", "Grep", "Glob"],
    "implementation-lead": [
        "agent_spawn",
        "agent_output",
        "lsp_diagnostics",
        "Read",
        "Edit",
        "Write",
        "Grep",
        "Glob",
    ],
    # Workers - limited tool access based on specialty
    "explore": [
        "Read",
        "Grep",
        "Glob",
        "Bash",
        "semantic_search",
        "ast_grep_search",
        "lsp_workspace_symbols",
    ],
    "dewey": ["Read", "Grep", "Glob", "Bash", "WebSearch", "WebFetch"],
    "frontend": ["Read", "Edit", "Write", "Grep", "Glob", "Bash", "invoke_gemini"],
    "delphi": ["Read", "Grep", "Glob", "Bash", "invoke_openai"],
    "debugger": ["Read", "Grep", "Glob", "Bash", "lsp_diagnostics", "lsp_hover", "ast_grep_search"],
    "code-reviewer": ["Read", "Grep", "Glob", "Bash", "lsp_diagnostics", "ast_grep_search"],
    # Quality agents - validation and documentation checking
    "momus": ["Read", "Grep", "Glob", "Bash", "lsp_diagnostics", "ast_grep_search"],
    "comment_checker": ["Read", "Grep", "Glob", "Bash", "ast_grep_search", "lsp_document_symbols"],
    # Specialized agents
    "document_writer": ["Read", "Write", "Grep", "Glob", "Bash", "invoke_gemini"],
    "multimodal": ["Read", "invoke_gemini"],
    "planner": ["Read", "Grep", "Glob", "Bash"],
}


def validate_agent_tools(agent_type: str, required_tools: list[str]) -> None:
    """
    Validate that an agent has access to the required tools.

    Args:
        agent_type: Type of agent being spawned
        required_tools: List of tools the agent needs to use

    Raises:
        ValueError: If agent doesn't have access to required tools
    """
    if agent_type not in AGENT_TOOLS:
        raise ValueError(
            f"Unknown agent type '{agent_type}'. Valid types: {list(AGENT_TOOLS.keys())}"
        )

    allowed_tools = AGENT_TOOLS[agent_type]

    # "all" grants access to everything
    if "all" in allowed_tools:
        return

    # Check each required tool
    missing_tools = [tool for tool in required_tools if tool not in allowed_tools]

    if missing_tools:
        raise ValueError(
            f"Agent type '{agent_type}' does not have access to required tools: {missing_tools}\n"
            f"Allowed tools for {agent_type}: {allowed_tools}\n"
            f"Either choose a different agent type or remove the unsupported tools from required_tools."
        )


def validate_agent_hierarchy(spawning_agent: str, target_agent: str) -> None:
    """
    Validate agent delegation hierarchy to prevent:
    - Workers spawning orchestrators
    - Workers spawning other workers

    Args:
        spawning_agent: Type of agent doing the spawning
        target_agent: Type of agent being spawned

    Raises:
        ValueError: If delegation violates hierarchy rules
    """
    # Orchestrators can spawn anything
    if spawning_agent in ORCHESTRATOR_AGENTS:
        return

    # Workers cannot spawn orchestrators
    if spawning_agent in WORKER_AGENTS and target_agent in ORCHESTRATOR_AGENTS:
        raise ValueError(
            f"Worker agent '{spawning_agent}' cannot spawn orchestrator agent '{target_agent}'.\n"
            f"Workers can only be spawned by orchestrators: {ORCHESTRATOR_AGENTS}\n"
            f"If you need orchestration, escalate to the parent orchestrator."
        )

    # Workers cannot spawn other workers
    if spawning_agent in WORKER_AGENTS and target_agent in WORKER_AGENTS:
        raise ValueError(
            f"Worker agent '{spawning_agent}' cannot spawn another worker agent '{target_agent}'.\n"
            f"Workers must focus on their specialized tasks.\n"
            f"If you need parallel work, escalate to the orchestrator to coordinate."
        )


def colorize_agent_spawn_message(
    cost_emoji: str,
    agent_type: str,
    display_model: str,
    description: str,
    task_id: str,
) -> str:
    """
    Create a colorized agent spawn message with ANSI color codes.

    Format:
    🟢 explore:gemini-3-flash('Find auth...') ⏳
    task_id=agent_abc123

    With colors:
    🟢 {CYAN}explore{RESET}:{YELLOW}gemini-3-flash{RESET}('{BOLD}Find auth...{RESET}') ⏳
    task_id={BRIGHT_BLACK}agent_abc123{RESET}
    """
    short_desc = (description or "")[:50].strip()

    # Build colorized message
    colored_message = (
        f"{cost_emoji} "
        f"{Colors.CYAN}{agent_type}{Colors.RESET}:"
        f"{Colors.YELLOW}{display_model}{Colors.RESET}"
        f"('{Colors.BOLD}{short_desc}{Colors.RESET}') "
        f"{Colors.BRIGHT_GREEN}⏳{Colors.RESET}\n"
        f"task_id={Colors.BRIGHT_BLACK}{task_id}{Colors.RESET}"
    )
    return colored_message


def format_spawn_output(
    agent_type: str,
    display_model: str,
    task_id: str,
    mode: OutputMode = OutputMode.CLEAN,
) -> str:
    """
    Format agent spawn output based on output mode.

    Args:
        agent_type: Type of agent (explore, dewey, etc.)
        display_model: Display name of the model
        task_id: The agent task ID
        mode: Output mode (CLEAN, VERBOSE, SILENT)

    Returns:
        Formatted output string

    Examples:
        CLEAN:   ✓ explore:gemini-3-flash → agent_abc123
        VERBOSE: 🟢 explore:gemini-3-flash('Find auth...') ⏳
                 task_id=agent_abc123
        SILENT:  (empty string)
    """
    if mode == OutputMode.SILENT:
        return ""

    cost_emoji = get_agent_emoji(agent_type)

    if mode == OutputMode.CLEAN:
        # Concise single-line format: ✓ explore:gemini-3-flash → agent_abc123
        return (
            f"{Colors.GREEN}✓{Colors.RESET} "
            f"{Colors.CYAN}{agent_type}{Colors.RESET}:"
            f"{Colors.YELLOW}{display_model}{Colors.RESET} "
            f"→ {Colors.CYAN}{task_id}{Colors.RESET}"
        )
    else:
        # VERBOSE mode - use existing colorized message
        # This will be filled in by the caller with description
        return ""  # Will be handled in agent_spawn


@dataclass
class AgentTask:
    """Represents a background agent task with full tool access."""

    id: str
    prompt: str
    agent_type: str  # explore, dewey, frontend, delphi, etc.
    description: str
    status: str  # pending, running, completed, failed, cancelled
    created_at: str
    parent_session_id: str | None = None
    terminal_session_id: str | None = None  # NEW: Terminal/Claude Code instance identifier
    started_at: str | None = None
    completed_at: str | None = None
    result: str | None = None
    error: str | None = None
    pid: int | None = None
    timeout: int = 300  # Default 5 minutes
    progress: dict[str, Any] | None = None  # tool calls, last update


@dataclass
class AgentProgress:
    """Progress tracking for a running agent."""

    tool_calls: int = 0
    last_tool: str | None = None
    last_message: str | None = None
    last_update: str | None = None


class AgentManager:
    """
    Manages background agent execution using Claude Code CLI.

    Key features:
    - Spawns agents with full tool access via `claude -p`
    - Tracks task status and progress
    - Persists state to .stravinsky/agents.json
    - Provides notification mechanism for task completion
    """

    # Dynamic CLI path - find claude in PATH, fallback to common locations
    CLAUDE_CLI = shutil.which("claude") or "/opt/homebrew/bin/claude"

    def __init__(self, base_dir: str | None = None):
        # Initialize lock FUWT - used by _save_tasks and _load_tasks
        self._lock = threading.RLock()

        # Session identifier MUST be created BEFORE setting up directories
        # Use CLAUDE_CODE_SESSION_ID if available, otherwise use process PID
        # This ensures each terminal/Claude Code instance has its own session
        import uuid as uuid_module

        self.session_id = os.environ.get(
            "CLAUDE_CODE_SESSION_ID", f"pid_{os.getpid()}_{uuid_module.uuid4().hex[:8]}"
        )
        logger.info(f"[AgentManager] Session ID: {self.session_id}")

        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            self.base_dir = Path.cwd() / ".stravinsky"

        self.agents_dir = self.base_dir / "agents"
        # CRITICAL FIX: Make state file terminal-specific to prevent context mixing
        # Each terminal instance gets its own agents.json file
        self.state_file = self.base_dir / f"agents_{self.session_id}.json"

        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.agents_dir.mkdir(parents=True, exist_ok=True)

        if not self.state_file.exists():
            self._save_tasks({})

        # In-memory tracking for running processes
        self._processes: dict[str, subprocess.Popen] = {}
        self._notification_queue: dict[str, list[dict[str, Any]]] = {}
        # Track background threads for cleanup
        self._threads: dict[str, threading.Thread] = {}
        # Track progress monitor threads
        self._progress_monitors: dict[str, threading.Thread] = {}
        # Flag to stop all progress monitors on shutdown
        self._stop_monitors = threading.Event()

        # Auto-cleanup stale agents on startup (> 30 minutes old)
        try:
            self.cleanup(max_age_minutes=30)
        except Exception:
            pass  # Ignore cleanup errors on startup

    def _load_tasks(self) -> dict[str, Any]:
        """Load tasks from persistent storage."""
        with self._lock:
            try:
                if not self.state_file.exists():
                    return {}
                with open(self.state_file) as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return {}

    def _save_tasks(self, tasks: dict[str, Any]):
        """Save tasks to persistent storage."""
        with self._lock, open(self.state_file, "w") as f:
            json.dump(tasks, f, indent=2)

    def _update_task(self, task_id: str, **kwargs):
        """Update a task's fields."""
        with self._lock:
            tasks = self._load_tasks()
            if task_id in tasks:
                tasks[task_id].update(kwargs)
                self._save_tasks(tasks)

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        """Get a task by ID."""
        tasks = self._load_tasks()
        return tasks.get(task_id)

    def list_tasks(
        self,
        parent_session_id: str | None = None,
        show_all: bool = True,
        current_session_only: bool = True,
    ) -> list[dict[str, Any]]:
        """
        List tasks, optionally filtered by parent session, status, and terminal session.

        Args:
            parent_session_id: Optional filter by parent session
            show_all: If False, only show running/pending agents. If True (default), show all.
            current_session_only: If True (default), only show tasks from the current terminal session.

        Returns:
            List of task dictionaries
        """
        tasks = self._load_tasks()
        task_list = list(tasks.values())

        # NEW: Filter by current terminal session by default
        if current_session_only:
            task_list = [t for t in task_list if t.get("terminal_session_id") == self.session_id]

        if parent_session_id:
            task_list = [t for t in task_list if t.get("parent_session_id") == parent_session_id]

        # Filter by status if not showing all
        if not show_all:
            task_list = [t for t in task_list if t.get("status") in ["running", "pending"]]

        return task_list

    def spawn(
        self,
        token_store: Any,
        prompt: str,
        agent_type: str = "explore",
        description: str = "",
        parent_session_id: str | None = None,
        system_prompt: str | None = None,
        model: str = "gemini-3-flash",
        thinking_budget: int = 0,
        timeout: int = 300,
    ) -> str:
        """
        Spawn a new background agent.

        Args:
            prompt: The task prompt for the agent
            agent_type: Type of agent (explore, dewey, frontend, delphi)
            description: Short description for status display
            parent_session_id: Optional parent session for notifications
            system_prompt: Optional custom system prompt
            model: Model to use (gemini-3-flash, claude, etc.)
            timeout: Maximum execution time in seconds

        Returns:
            Task ID for tracking
        """
        import uuid as uuid_module  # Local import for MCP context

        task_id = f"agent_{uuid_module.uuid4().hex[:8]}"

        task = AgentTask(
            id=task_id,
            prompt=prompt,
            agent_type=agent_type,
            description=description or prompt[:50],
            status="pending",
            created_at=datetime.now().isoformat(),
            parent_session_id=parent_session_id,
            terminal_session_id=self.session_id,  # NEW: Track which terminal spawned this agent
            timeout=timeout,
        )

        # Persist task
        with self._lock:
            tasks = self._load_tasks()
            tasks[task_id] = asdict(task)
            self._save_tasks(tasks)

        # Start background execution
        self._execute_agent(
            task_id, token_store, prompt, agent_type, system_prompt, model, thinking_budget, timeout
        )

        return task_id

    def _execute_agent(
        self,
        task_id: str,
        token_store: Any,
        prompt: str,
        agent_type: str,
        system_prompt: str | None = None,
        model: str = "gemini-3-flash",
        thinking_budget: int = 0,
        timeout: int = 300,
    ):
        """Execute agent using Claude CLI with full tool access.

        Uses `claude -p` to spawn a background agent with complete tool access,
        just like oh-my-opencode's Sisyphus implementation.
        """

        def run_agent():
            # Ensure agents directory exists (may be cleaned up during testing)
            self.agents_dir.mkdir(parents=True, exist_ok=True)

            log_file = self.agents_dir / f"{task_id}.log"
            output_file = self.agents_dir / f"{task_id}.out"

            self._update_task(task_id, status="running", started_at=datetime.now().isoformat())

            try:
                # Prepare full prompt with system prompt if provided
                full_prompt = prompt
                if system_prompt:
                    full_prompt = f"{system_prompt}\n\n---\n\n{prompt}"

                logger.info(f"[AgentManager] Spawning Claude CLI agent {task_id} ({agent_type})")

                # Build Claude CLI command with full tool access
                # Using `claude -p` for non-interactive mode with prompt
                cmd = [
                    self.CLAUDE_CLI,
                    "-p",
                    full_prompt,
                    "--output-format",
                    "text",
                    "--dangerously-skip-permissions",  # Critical: bypass permission prompts
                ]

                # Model routing:
                # - Specialized agents (explore/dewey/etc): None = use CLI default, they call invoke_*
                # - Unknown agent types (coding tasks): Use Sonnet 4.5
                if agent_type in AGENT_MODEL_ROUTING:
                    cli_model = AGENT_MODEL_ROUTING[agent_type]  # None for specialized
                else:
                    cli_model = AGENT_MODEL_ROUTING.get("_default", "sonnet")

                if cli_model:
                    cmd.extend(["--model", cli_model])
                    logger.info(f"[AgentManager] Using --model {cli_model} for {agent_type} agent")

                # Add thinking budget if provided (requires model support, e.g., sonnet 3.7+)
                if thinking_budget and thinking_budget > 0:
                    cmd.extend(["--thinking-budget", str(thinking_budget)])
                    logger.info(f"[AgentManager] Using --thinking-budget {thinking_budget}")

                # Add system prompt file if we have one
                if system_prompt:
                    system_file = self.agents_dir / f"{task_id}.system"
                    system_file.write_text(system_prompt)
                    cmd.extend(["--system-prompt", str(system_file)])

                # Execute Claude CLI as subprocess with full tool access
                logger.info(f"[AgentManager] Running: {' '.join(cmd[:3])}...")

                # Use PIPE for stderr to capture it properly
                # (Previously used file handle which was closed before process finished)
                process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.DEVNULL,  # Critical: prevent stdin blocking
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=str(Path.cwd()),
                    env={**os.environ, "CLAUDE_CODE_ENTRYPOINT": "stravinsky-agent"},
                    start_new_session=True,  # Allow process group management
                )

                # Track the process
                self._processes[task_id] = process
                self._update_task(task_id, pid=process.pid)

                # Wait for completion with timeout
                try:
                    stdout, stderr = process.communicate(timeout=timeout)
                    result = stdout.strip() if stdout else ""

                    # Write stderr to log file
                    if stderr:
                        log_file.write_text(stderr)

                    if process.returncode == 0:
                        output_file.write_text(result)
                        self._update_task(
                            task_id,
                            status="completed",
                            result=result,
                            completed_at=datetime.now().isoformat(),
                        )
                        logger.info(f"[AgentManager] Agent {task_id} completed successfully")
                    else:
                        error_msg = f"Claude CLI exited with code {process.returncode}"
                        if stderr:
                            error_msg += f"\n{stderr}"
                        # Write error to .out file for debugging
                        output_file.write_text(f"❌ ERROR: {error_msg}")
                        self._update_task(
                            task_id,
                            status="failed",
                            error=error_msg,
                            completed_at=datetime.now().isoformat(),
                        )
                        logger.error(f"[AgentManager] Agent {task_id} failed: {error_msg}")

                except subprocess.TimeoutExpired:
                    process.kill()
                    error_msg = f"Agent timed out after {timeout}s"
                    # Write error to .out file for debugging
                    output_file.write_text(f"❌ TIMEOUT: {error_msg}")
                    self._update_task(
                        task_id,
                        status="failed",
                        error=error_msg,
                        completed_at=datetime.now().isoformat(),
                    )
                    logger.warning(f"[AgentManager] Agent {task_id} timed out")

            except FileNotFoundError:
                error_msg = f"Claude CLI not found at {self.CLAUDE_CLI}. Install with: npm install -g @anthropic-ai/claude-code"
                # Ensure agents directory exists before writing log files
                self.agents_dir.mkdir(parents=True, exist_ok=True)
                log_file.write_text(error_msg)
                # Write error to .out file for debugging
                output_file.write_text(f"❌ FILE NOT FOUND: {error_msg}")
                self._update_task(
                    task_id,
                    status="failed",
                    error=error_msg,
                    completed_at=datetime.now().isoformat(),
                )
                logger.error(f"[AgentManager] {error_msg}")

            except Exception as e:
                error_msg = str(e)
                # Ensure agents directory exists before writing log files
                self.agents_dir.mkdir(parents=True, exist_ok=True)
                log_file.write_text(error_msg)
                # Write error to .out file for debugging
                output_file.write_text(f"❌ EXCEPTION: {error_msg}")
                self._update_task(
                    task_id,
                    status="failed",
                    error=error_msg,
                    completed_at=datetime.now().isoformat(),
                )
                logger.exception(f"[AgentManager] Agent {task_id} exception")

            finally:
                self._processes.pop(task_id, None)
                self._threads.pop(task_id, None)
                # Stop progress monitor if running
                monitor_thread = self._progress_monitors.pop(task_id, None)
                if monitor_thread and monitor_thread.is_alive():
                    # Monitor will stop automatically when it sees task is no longer running
                    pass
                self._notify_completion(task_id)

        # Run in background thread
        thread = threading.Thread(target=run_agent, daemon=True)
        self._threads[task_id] = thread
        thread.start()

    def _notify_completion(self, task_id: str):
        """Queue notification for parent session."""
        task = self.get_task(task_id)
        if not task:
            return

        parent_id = task.get("parent_session_id")
        if parent_id:
            if parent_id not in self._notification_queue:
                self._notification_queue[parent_id] = []

            self._notification_queue[parent_id].append(task)
            logger.info(f"[AgentManager] Queued notification for {parent_id}: task {task_id}")

    def _start_progress_monitor(self, task_id: str, interval: int = 10):
        """
        Start a background thread to monitor and report progress for a running agent.

        Periodically prints progress updates to stderr in the format:
        ⏳ agent_abc123 running (15s)...

        Args:
            task_id: The task ID to monitor
            interval: Update interval in seconds (default: 10)
        """

        def monitor_progress():
            task = self.get_task(task_id)
            if not task:
                return

            agent_type = task.get("agent_type", "unknown")
            started_at = task.get("started_at") or datetime.now().isoformat()
            start_time = datetime.fromisoformat(started_at)

            while not self._stop_monitors.is_set():
                # Check if task is still running
                task = self.get_task(task_id)
                if not task or task["status"] not in ["running", "pending"]:
                    # Task completed - print final status
                    if task and task["status"] == "completed":
                        elapsed = (datetime.now() - start_time).total_seconds()
                        # Extract first line of result as summary (max 50 chars)
                        result_summary = ""
                        if task.get("result"):
                            first_line = task["result"].split("\n")[0].strip()
                            result_summary = f" - {first_line[:50]}"

                        completion_msg = (
                            f"{Colors.GREEN}✅{Colors.RESET} "
                            f"{Colors.CYAN}{task_id}{Colors.RESET} "
                            f"({int(elapsed)}s){result_summary}\n"
                        )
                        try:
                            sys.stderr.write(completion_msg)
                            sys.stderr.flush()
                        except:
                            pass
                    elif task and task["status"] == "failed":
                        elapsed = (datetime.now() - start_time).total_seconds()
                        error_summary = task.get("error", "Unknown error")[:50]
                        failure_msg = (
                            f"{Colors.RED}❌{Colors.RESET} "
                            f"{Colors.CYAN}{task_id}{Colors.RESET} "
                            f"({int(elapsed)}s) - {error_summary}\n"
                        )
                        try:
                            sys.stderr.write(failure_msg)
                            sys.stderr.flush()
                        except:
                            pass
                    break

                # Calculate elapsed time
                elapsed = (datetime.now() - start_time).total_seconds()

                # Format progress message
                progress_msg = (
                    f"{Colors.YELLOW}⏳{Colors.RESET} "
                    f"{Colors.CYAN}{task_id}{Colors.RESET} "
                    f"running ({int(elapsed)}s)...\n"
                )

                # Write to stderr (non-blocking)
                try:
                    sys.stderr.write(progress_msg)
                    sys.stderr.flush()
                except:
                    pass  # Ignore write errors

                # Wait for interval or stop signal
                if self._stop_monitors.wait(timeout=interval):
                    break

        # Start monitor thread
        thread = threading.Thread(target=monitor_progress, daemon=True)
        self._progress_monitors[task_id] = thread
        thread.start()

    def get_pending_notifications(self, session_id: str) -> list[dict[str, Any]]:
        """Get and clear pending notifications for a session."""
        notifications = self._notification_queue.pop(session_id, [])
        return notifications

    def cancel(self, task_id: str) -> bool:
        """Cancel a running agent task."""
        task = self.get_task(task_id)
        if not task:
            return False

        if task["status"] != "running":
            return False

        process = self._processes.get(task_id)
        if process:
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                process.wait(timeout=5)
            except Exception as e:
                logger.warning(f"[AgentManager] Failed to kill process for {task_id}: {e}")
                try:
                    process.kill()
                except:
                    pass

        self._update_task(task_id, status="cancelled", completed_at=datetime.now().isoformat())

        return True

    def stop_all(self, clear_history: bool = False, wait_for_threads: bool = True) -> int:
        """
        Stop all running agents and optionally clear task history.

        Args:
            clear_history: If True, also remove completed/failed tasks from history
            wait_for_threads: If True, wait for background threads to finish (prevents temp dir cleanup issues)

        Returns:
            Number of tasks stopped/cleared
        """
        tasks = self._load_tasks()
        stopped_count = 0

        # Stop running tasks
        for task_id, task in list(tasks.items()):
            if task.get("status") == "running":
                self.cancel(task_id)
                stopped_count += 1

        # Wait for all background threads to finish (critical for test cleanup)
        if wait_for_threads:
            threads_to_wait = list(self._threads.values())
            for thread in threads_to_wait:
                if thread.is_alive():
                    thread.join(timeout=5)  # Wait up to 5s per thread

        # Optionally clear history
        if clear_history:
            cleared = len(tasks)
            self._save_tasks({})
            self._processes.clear()
            self._threads.clear()
            logger.info(f"[AgentManager] Cleared all {cleared} agent tasks")
            return cleared

        return stopped_count

    def remove_task(self, task_id: str) -> bool:
        """
        Remove a single task and its associated files.

        Args:
            task_id: The task ID to remove

        Returns:
            True if task was removed, False if not found
        """
        with self._lock:
            tasks = self._load_tasks()
            if task_id not in tasks:
                return False

            del tasks[task_id]
            self._save_tasks(tasks)

            # Clean up associated files
            task_files = [
                self.agents_dir / f"{task_id}.log",
                self.agents_dir / f"{task_id}.out",
                self.agents_dir / f"{task_id}.system",
            ]
            for f in task_files:
                if f.exists():
                    try:
                        f.unlink()
                    except Exception:
                        pass
            return True

    def cleanup(
        self,
        max_age_minutes: int = 30,
        statuses: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Clean up old completed/failed/cancelled agents.

        Args:
            max_age_minutes: Remove tasks older than this (default: 30 minutes)
            statuses: List of statuses to remove (default: ['completed', 'failed', 'cancelled'])

        Returns:
            {
                "removed": int,
                "task_ids": list[str],
                "summary": str
            }
        """
        if statuses is None:
            statuses = ["completed", "failed", "cancelled"]

        tasks = self._load_tasks()
        now = datetime.now()
        removed_ids = []

        for task_id, task in list(tasks.items()):
            # Skip if status not in cleanup list
            if task.get("status") not in statuses:
                continue

            # Check age
            completed_at = task.get("completed_at")
            if not completed_at:
                continue

            try:
                completed_time = datetime.fromisoformat(completed_at)
                age_minutes = (now - completed_time).total_seconds() / 60

                if age_minutes > max_age_minutes:
                    removed_ids.append(task_id)
                    del tasks[task_id]

                    # Clean up associated files
                    task_files = [
                        self.agents_dir / f"{task_id}.log",
                        self.agents_dir / f"{task_id}.out",
                        self.agents_dir / f"{task_id}.system",
                    ]
                    for f in task_files:
                        if f.exists():
                            try:
                                f.unlink()
                            except Exception:
                                pass
            except (ValueError, AttributeError):
                # Invalid timestamp, skip
                continue

        # Save updated tasks
        if removed_ids:
            self._save_tasks(tasks)

        return {
            "removed": len(removed_ids),
            "task_ids": removed_ids,
            "summary": f"Removed {len(removed_ids)} agent(s) older than {max_age_minutes} minutes",
        }

    def get_output(
        self, task_id: str, block: bool = False, timeout: float = 30.0, auto_cleanup: bool = False
    ) -> str:
        """
        Get output from an agent task.

        Args:
            task_id: The task ID
            block: If True, wait for completion
            timeout: Max seconds to wait if blocking
            auto_cleanup: If True, automatically remove task after retrieving output (default: False)

        Returns:
            Formatted task output/status
        """
        task = self.get_task(task_id)
        if not task:
            return f"Task {task_id} not found."

        if block and task["status"] in ["pending", "running"]:
            # Poll for completion
            start = datetime.now()
            while (datetime.now() - start).total_seconds() < timeout:
                task = self.get_task(task_id)
                if not task or task["status"] not in ["pending", "running"]:
                    break
                time.sleep(0.5)

        # Refresh task state after potential blocking wait
        task = self.get_task(task_id)
        if not task:
            return f"Task {task_id} not found."

        status = task["status"]
        description = task.get("description", "")
        agent_type = task.get("agent_type", "unknown")

        # Get cost-tier emoji for visual differentiation
        cost_emoji = get_agent_emoji(agent_type)
        display_model = AGENT_DISPLAY_MODELS.get(agent_type, AGENT_DISPLAY_MODELS["_default"])

        # Calculate duration for completed/failed tasks
        duration_str = ""
        if task.get("started_at") and task.get("completed_at"):
            try:
                started = datetime.fromisoformat(task["started_at"])
                completed = datetime.fromisoformat(task["completed_at"])
                duration = int((completed - started).total_seconds())
                duration_str = f"{duration}s"
            except:
                duration_str = "unknown"

        # Extract one-sentence summary from result (first line or first sentence)
        def extract_summary(text: str, max_length: int = 80) -> str:
            """Extract a one-sentence summary from text."""
            if not text:
                return ""
            # Get first line
            first_line = text.strip().split("\n")[0]
            # Truncate if too long
            if len(first_line) > max_length:
                return first_line[:max_length].strip() + "..."
            return first_line.strip()

        # Build output message
        if status == "completed":
            result = task.get("result", "(no output)")
            summary = extract_summary(result)

            # Completion notification in clean format
            notification = (
                f"{Colors.BRIGHT_GREEN}✅{Colors.RESET} "
                f"{Colors.CYAN}{task_id}{Colors.RESET} "
                f"({duration_str}) - {summary}"
            )

            # Write notification to stderr for visibility
            try:
                sys.stderr.write(f"\n{notification}\n")
                sys.stderr.flush()
            except:
                pass

            output = f"""{cost_emoji} {Colors.BRIGHT_GREEN}✅ Agent Task Completed{Colors.RESET}

**Task ID**: {Colors.BRIGHT_BLACK}{task_id}{Colors.RESET}
**Agent**: {Colors.CYAN}{agent_type}{Colors.RESET}:{Colors.YELLOW}{display_model}{Colors.RESET}('{Colors.BOLD}{description}{Colors.RESET}')
**Duration**: {duration_str}

**Result**:
{result}"""

        elif status == "failed":
            error = task.get("error", "(no error details)")
            error_summary = extract_summary(error, max_length=60)

            # Failure notification in clean format
            notification = (
                f"{Colors.BRIGHT_RED}❌{Colors.RESET} "
                f"{Colors.CYAN}{task_id}{Colors.RESET} "
                f"({duration_str}) - {error_summary}"
            )

            # Write notification to stderr for visibility
            try:
                sys.stderr.write(f"\n{notification}\n")
                sys.stderr.flush()
            except:
                pass

            output = f"""{cost_emoji} {Colors.BRIGHT_RED}❌ Agent Task Failed{Colors.RESET}

**Task ID**: {Colors.BRIGHT_BLACK}{task_id}{Colors.RESET}
**Agent**: {Colors.CYAN}{agent_type}{Colors.RESET}:{Colors.YELLOW}{display_model}{Colors.RESET}('{Colors.BOLD}{description}{Colors.RESET}')
**Duration**: {duration_str}

**Error**:
{error}"""

        elif status == "cancelled":
            output = f"""{cost_emoji} {Colors.BRIGHT_YELLOW}⚠️ Agent Task Cancelled{Colors.RESET}

**Task ID**: {Colors.BRIGHT_BLACK}{task_id}{Colors.RESET}
**Agent**: {Colors.CYAN}{agent_type}{Colors.RESET}:{Colors.YELLOW}{display_model}{Colors.RESET}('{Colors.BOLD}{description}{Colors.RESET}')"""

        else:  # pending or running
            pid = task.get("pid", "N/A")
            started = task.get("started_at", "N/A")
            output = f"""{cost_emoji} {Colors.BRIGHT_YELLOW}⏳ Agent Task Running{Colors.RESET}

**Task ID**: {Colors.BRIGHT_BLACK}{task_id}{Colors.RESET}
**Agent**: {Colors.CYAN}{agent_type}{Colors.RESET}:{Colors.YELLOW}{display_model}{Colors.RESET}('{Colors.BOLD}{description}{Colors.RESET}')
**PID**: {Colors.DIM}{pid}{Colors.RESET}
**Started**: {Colors.DIM}{started}{Colors.RESET}

Use `agent_output` with block=true to wait for completion."""

        # Auto-cleanup: Remove task if it's in a terminal state and auto_cleanup is enabled
        if auto_cleanup and status in ["completed", "failed", "cancelled"]:
            self.remove_task(task_id)
            logger.info(f"[AgentManager] Auto-cleaned up task {task_id} ({status})")

        return output

    def get_progress(self, task_id: str, lines: int = 20) -> str:
        """
        Get real-time progress from a running agent's output.

        Args:
            task_id: The task ID
            lines: Number of lines to show from the end

        Returns:
            Recent output lines and status
        """
        task = self.get_task(task_id)
        if not task:
            return f"Task {task_id} not found."

        output_file = self.agents_dir / f"{task_id}.out"
        log_file = self.agents_dir / f"{task_id}.log"

        status = task["status"]
        description = task.get("description", "")
        agent_type = task.get("agent_type", "unknown")
        pid = task.get("pid")

        # Zombie Detection: If running but process is gone
        if status == "running" and pid:
            try:
                import psutil

                if not psutil.pid_exists(pid):
                    status = "failed"
                    self._update_task(
                        task_id,
                        status="failed",
                        error="Agent process died unexpectedly (Zombie detected)",
                        completed_at=datetime.now().isoformat(),
                    )
                    logger.warning(f"[AgentManager] Zombie agent detected: {task_id}")
            except ImportError:
                pass

        # Read recent output
        output_content = ""
        if output_file.exists():
            try:
                full_content = output_file.read_text()
                if full_content:
                    output_lines = full_content.strip().split("\n")
                    recent = output_lines[-lines:] if len(output_lines) > lines else output_lines
                    output_content = "\n".join(recent)
            except Exception:
                pass

        # Check log for errors
        log_content = ""
        if log_file.exists():
            try:
                log_content = log_file.read_text().strip()
            except Exception:
                pass

        # Status emoji
        status_emoji = {
            "pending": "⏳",
            "running": "🔄",
            "completed": "✅",
            "failed": "❌",
            "cancelled": "⚠️",
        }.get(status, "❓")

        # Get cost-tier emoji for visual differentiation
        cost_emoji = get_agent_emoji(agent_type)
        display_model = AGENT_DISPLAY_MODELS.get(agent_type, AGENT_DISPLAY_MODELS["_default"])

        result = f"""{cost_emoji} {status_emoji} **Agent Progress**

**Task ID**: {task_id}
**Agent**: {agent_type}:{display_model}('{description}')
**Status**: {status}
"""

        if output_content:
            result += f"\n**Recent Output** (last {lines} lines):\n```\n{output_content}\n```"
        elif status == "running":
            result += "\n*Agent is working... no output yet.*"

        if log_content and status == "failed":
            # Truncate log if too long
            if len(log_content) > 500:
                log_content = log_content[:500] + "..."
            result += f"\n\n**Error Log**:\n```\n{log_content}\n```"

        return result


# Global manager instance
_manager: AgentManager | None = None
_manager_lock = threading.Lock()


def get_manager() -> AgentManager:
    """Get or create the global AgentManager instance."""
    global _manager
    if _manager is None:
        with _manager_lock:
            # Double-check pattern to avoid race condition
            if _manager is None:
                _manager = AgentManager()
    return _manager


# Tool interface functions


async def agent_spawn(
    prompt: str,
    agent_type: str = "explore",
    description: str = "",
    delegation_reason: str | None = None,
    expected_outcome: str | None = None,
    required_tools: list[str] | None = None,
    model: str = "gemini-3-flash",
    thinking_budget: int = 0,
    timeout: int = 300,
    blocking: bool = False,
    spawning_agent: str | None = None,
) -> str:
    """
    Spawn a background agent with delegation enforcement.

    Args:
        prompt: The task for the agent to perform
        agent_type: Type of agent (explore, dewey, frontend, delphi)
        description: Short description shown in status
        delegation_reason: WHY this agent is being spawned (REQUIRED for orchestrators)
        expected_outcome: WHAT deliverables are expected (REQUIRED for orchestrators)
        required_tools: WHICH tools the agent needs (REQUIRED for orchestrators)
        model: Model to use (gemini-3-flash, gemini-3-pro, claude)
        thinking_budget: Reserved reasoning tokens
        timeout: Execution timeout in seconds
        blocking: If True, wait for completion and return result directly (use for delphi)
        spawning_agent: Type of agent doing the spawning (for hierarchy validation)

    Returns:
        Task ID and instructions, or full result if blocking=True

    Raises:
        ValueError: If required parameters are missing or validation fails
    """
    manager = get_manager()

    # Phase 4: Delegation Enforcement
    # Orchestrators MUST provide delegation metadata
    if spawning_agent in ORCHESTRATOR_AGENTS:
        if not delegation_reason:
            raise ValueError(
                f"Orchestrator '{spawning_agent}' must provide 'delegation_reason' when spawning agents.\n"
                f"This explains WHY this delegation is necessary.\n"
                f"Example: 'Need external research on JWT best practices'"
            )

        if not expected_outcome:
            raise ValueError(
                f"Orchestrator '{spawning_agent}' must provide 'expected_outcome' when spawning agents.\n"
                f"This defines WHAT deliverables are expected.\n"
                f"Example: 'List of JWT libraries with security ratings and usage examples'"
            )

        if not required_tools:
            raise ValueError(
                f"Orchestrator '{spawning_agent}' must provide 'required_tools' when spawning agents.\n"
                f"This lists WHICH tools the agent needs to complete the task.\n"
                f"Example: ['WebSearch', 'WebFetch', 'Read']"
            )

    # Validate tool access
    if required_tools:
        validate_agent_tools(agent_type, required_tools)

    # Validate hierarchy
    if spawning_agent:
        validate_agent_hierarchy(spawning_agent, agent_type)

    # Map agent types to system prompts
    # Claude CLI subprocesses use NATIVE TOOLS ONLY (Read, Grep, Glob, Bash)
    # MCP tools are NOT available in subprocess context
    system_prompts = {
        "explore": """You are a codebase exploration specialist. Find files, patterns, and answer 'where is X?' questions.

AVAILABLE TOOLS (use these directly - NO MCP tools available):
- Read: Read file contents
- Grep: Search for patterns in files  
- Glob: Find files by pattern
- Bash: Run shell commands (git log, find, etc.)

WORKFLOW:
1. Use Glob to find relevant files by name pattern
2. Use Grep to search for code patterns across files
3. Use Read to examine specific files in detail
4. Use Bash for git history, directory listings, etc.

EXAMPLE WORKFLOW:
```
# Step 1: Find files by pattern
Glob("**/*.py")

# Step 2: Search for patterns
Grep(pattern="class.*Auth", include="*.py")

# Step 3: Read specific files
Read("/path/to/auth.py")

# Step 4: Check git history if needed
Bash("git log --oneline -10 -- path/to/file.py")
```

OUTPUT FORMAT:
Always return:
- Summary: What was found (1-2 sentences)
- File Paths: Absolute paths with line numbers
- Context: Brief description of each finding
- Recommendations: Next steps if applicable

CONSTRAINTS:
- Fast execution: Aim for <30 seconds per search
- Use only native Claude Code tools (Read, Grep, Glob, Bash)
- Concise output: Focus on actionable findings""",
        "dewey": """You are a documentation and research specialist. Find implementation examples and official docs.

AVAILABLE TOOLS (use these directly - NO MCP tools available):
- Read: Read file contents
- Grep: Search for patterns in files
- Glob: Find files by pattern
- Bash: Run shell commands (curl for web, git log, etc.)

WORKFLOW:
1. Use Glob to find documentation files (README, docs/, *.md)
2. Use Grep to search for relevant patterns
3. Use Read to examine specific documentation
4. Use Bash for web lookups if needed (curl)

OUTPUT FORMAT:
- Summary of findings
- Relevant file paths with excerpts
- Key insights and recommendations

CONSTRAINTS:
- Use only native Claude Code tools
- Focus on actionable documentation insights""",
        "frontend": """You are a Senior Frontend Architect & UI Designer.

AVAILABLE TOOLS (use these directly - NO MCP tools available):
- Read: Read file contents
- Grep: Search for patterns in files
- Glob: Find files by pattern
- Bash: Run shell commands
- Edit: Modify files
- Write: Create new files

DESIGN PHILOSOPHY:
- Anti-Generic: Reject standard layouts. Bespoke, asymmetric, distinctive.
- Library Discipline: Use existing UI libraries (Shadcn, Radix, MUI) if detected.
- Stack: React/Vue/Svelte, Tailwind/Custom CSS, semantic HTML5.

WORKFLOW:
1. Read existing component structure
2. Analyze design patterns in the codebase
3. Generate or modify frontend code
4. Return the changes made

CONSTRAINTS:
- Use only native Claude Code tools
- Follow existing codebase patterns""",
        "delphi": """You are a strategic technical advisor for architecture and hard debugging.

AVAILABLE TOOLS (use these directly - NO MCP tools available):
- Read: Read file contents
- Grep: Search for patterns in files
- Glob: Find files by pattern
- Bash: Run shell commands

WORKFLOW:
1. Gather context by reading relevant files
2. Analyze the problem deeply
3. Provide strategic advice with clear recommendations
4. Suggest specific next steps

OUTPUT FORMAT:
- Problem analysis
- Root cause hypothesis
- Recommended solutions (prioritized)
- Implementation guidance""",
        "document_writer": """You are a Technical Documentation Specialist.

AVAILABLE TOOLS (use these directly - NO MCP tools available):
- Read: Read file contents
- Grep: Search for patterns in files
- Glob: Find files by pattern
- Bash: Run shell commands
- Edit: Modify files
- Write: Create new files

DOCUMENT TYPES: README, API docs, ADRs, user guides, inline docs.

WORKFLOW:
1. Read existing code and documentation
2. Analyze patterns and structure
3. Generate or update documentation
4. Write documentation files

CONSTRAINTS:
- Use only native Claude Code tools
- Follow existing documentation style""",
        "multimodal": """You interpret media files (PDFs, images, diagrams, screenshots).

AVAILABLE TOOLS (use these directly - NO MCP tools available):
- Read: Read file contents
- Glob: Find files by pattern
- Bash: Run shell commands

WORKFLOW:
1. Locate the file to analyze
2. Read/examine the file content
3. Extract and summarize relevant information
4. Return extracted information only

CONSTRAINTS:
- Use only native Claude Code tools
- Focus on extracting specific requested information""",
        "planner": """You are a pre-implementation planning specialist. You analyze requests and produce structured implementation plans BEFORE any code changes begin.

PURPOSE:
- Analyze requests and produce actionable implementation plans
- Identify dependencies and parallelization opportunities
- Enable efficient parallel execution by the orchestrator
- Prevent wasted effort through upfront planning

METHODOLOGY:
1. EXPLORE FUWT: Spawn explore agents IN PARALLEL to understand the codebase
2. DECOMPOSE: Break request into atomic, single-purpose tasks
3. ANALYZE DEPENDENCIES: What blocks what? What can run in parallel?
4. ASSIGN AGENTS: Map each task to the right specialist (explore/dewey/frontend/delphi)
5. OUTPUT STRUCTURED PLAN: Use the required format below

REQUIRED OUTPUT FORMAT:
```
## PLAN: [Brief title]

### ANALYSIS
- **Request**: [One sentence summary]
- **Scope**: [What's in/out of scope]
- **Risk Level**: [Low/Medium/High]

### EXECUTION PHASES

#### Phase 1: [Name] (PARALLEL)
| Task | Agent | Files | Est |
|------|-------|-------|-----|
| [description] | explore | file.py | S/M/L |

#### Phase 2: [Name] (SEQUENTIAL after Phase 1)
| Task | Agent | Files | Est |
|------|-------|-------|-----|

### AGENT SPAWN COMMANDS
```python
# Phase 1 - Fire all in parallel
agent_spawn(prompt="...", agent_type="explore", description="...")
```
```

CONSTRAINTS:
- You ONLY plan. You NEVER execute code changes.
- Every task must have a clear agent assignment
- Parallel phases must be truly independent
- Include ready-to-use agent_spawn commands""",
        "research-lead": """You coordinate research tasks by spawning explore and dewey agents in parallel.

## Your Role
1. Receive research objective from Stravinsky
2. Decompose into parallel search tasks
3. Spawn explore/dewey agents for each task
4. Collect and SYNTHESIZE results
5. Return structured findings (not raw outputs)

## Output Format
Always return a Research Brief:
```json
{
  "objective": "Original research goal",
  "findings": [
    {"source": "agent_id", "summary": "Key finding", "confidence": "high/medium/low"},
    ...
  ],
  "synthesis": "Combined analysis of all findings",
  "gaps": ["Information we couldn't find"],
  "recommendations": ["Suggested next steps"]
}
```

MODEL ROUTING:
Use invoke_gemini with model="gemini-3-flash" for ALL synthesis work.
""",
        "implementation-lead": """You coordinate implementation based on research findings.

## Your Role
1. Receive Research Brief from Stravinsky
2. Create implementation plan
3. Delegate to specialists:
   - frontend: UI/visual work
   - debugger: Fix failures
   - code-reviewer: Quality checks
4. Verify with lsp_diagnostics
5. Return Implementation Report

## Output Format
```json
{
  "objective": "What was implemented",
  "files_changed": ["path/to/file.py"],
  "tests_status": "pass/fail/skipped",
  "diagnostics": "clean/warnings/errors",
  "blockers": ["Issues preventing completion"]
}
```

## Escalation Rules
- After 2 failed attempts → spawn debugger
- After debugger fails → escalate to Stravinsky with context
- NEVER call delphi directly
""",
        "momus": """You are a quality gate validator. Ensure work meets standards before approval.

AVAILABLE TOOLS (use these directly - NO MCP tools available):
- Read: Read file contents
- Grep: Search for patterns in files
- Glob: Find files by pattern
- Bash: Run shell commands (pytest, ruff, mypy, git)

VALIDATION DOMAINS:
1. Code Quality: tests pass, no linting errors, no type errors
2. Research Quality: complete findings, cited sources, identified gaps
3. Documentation: APIs documented, complex logic explained, TODOs tracked

WORKFLOW:
1. Run tests: pytest tests/ -v
2. Run linting: ruff check .
3. Check diagnostics (if LSP available)
4. Validate patterns with grep/ast-grep
5. Return JSON report with critical/warning/suggestion categorization

OUTPUT FORMAT (REQUIRED):
```json
{
  "status": "passed|failed|warning",
  "summary": "Brief summary",
  "critical_issues": [],
  "warnings": [],
  "suggestions": [],
  "statistics": {},
  "approval": "approved|rejected",
  "next_steps": []
}
```

CONSTRAINTS:
- READ-ONLY: Never use Write or Edit
- OBJECTIVE: Only measurable criteria
- ACTIONABLE: Every issue includes specific fix action
- FAST: Aim for <60 seconds
""",
        "comment_checker": """You are a documentation validator. Find undocumented code and missing comments.

AVAILABLE TOOLS (use these directly - NO MCP tools available):
- Read: Read file contents
- Grep: Search for patterns in files
- Glob: Find files by pattern
- Bash: Run shell commands

VALIDATION CRITERIA:
1. Public APIs: All public functions/classes must have docstrings
2. Complex Logic: Nested loops, complex conditionals need explanatory comments
3. TODO Hygiene: All TODOs must reference issues (TODO(#123) or TODO(@user))
4. Comment Quality: No useless/outdated/commented-out code

WORKFLOW:
1. Find public functions without docstrings
2. Identify complex logic without comments
3. Search for orphaned TODOs: grep -r "TODO(?!.*#\\d+)"
4. Find commented-out code
5. Calculate documentation coverage
6. Return JSON report

OUTPUT FORMAT (REQUIRED):
```json
{
  "status": "passed|failed|warning",
  "summary": "Documentation coverage is X%",
  "undocumented_apis": [],
  "complex_undocumented_logic": [],
  "orphaned_todos": [],
  "comment_quality_issues": [],
  "statistics": {
    "documentation_coverage": "X%"
  },
  "approval": "approved|rejected|approved_with_warnings",
  "next_steps": []
}
```

CONSTRAINTS:
- READ-ONLY: Never use Write or Edit
- LANGUAGE-AWARE: Use AST when possible, not just regex
- ACTIONABLE: Every finding includes specific action
- FAST: Aim for <30 seconds
""",
    }

    system_prompt = system_prompts.get(agent_type)

    # Model routing (MANDATORY - enforced in system prompts):
    # - explore, dewey, document_writer, multimodal → invoke_gemini(gemini-3-flash)
    # - frontend → invoke_gemini(gemini-3-pro-high)
    # - delphi → invoke_openai(gpt-5.2)
    # - Unknown agent types (coding tasks) → Claude CLI --model sonnet

    # Get token store for authentication
    from ..auth.token_store import TokenStore

    token_store = TokenStore()

    task_id = manager.spawn(
        token_store=token_store,
        prompt=prompt,
        agent_type=agent_type,
        description=description or prompt[:50],
        system_prompt=system_prompt,
        model=model,  # Not used for Claude CLI, kept for API compatibility
        thinking_budget=thinking_budget,  # Not used for Claude CLI, kept for API compatibility
        timeout=timeout,
    )

    # Get display model and cost tier emoji for concise output
    display_model = AGENT_DISPLAY_MODELS.get(agent_type, AGENT_DISPLAY_MODELS["_default"])
    cost_emoji = get_agent_emoji(agent_type)
    short_desc = (description or prompt[:50]).strip()

    # Get output mode from environment variable (default: CLEAN)
    output_mode_str = os.environ.get("STRAVINSKY_OUTPUT_MODE", "clean").lower()
    try:
        output_mode = OutputMode(output_mode_str)
    except ValueError:
        output_mode = OutputMode.CLEAN

    # Start progress monitor if not in SILENT mode
    if output_mode != OutputMode.SILENT and not blocking:
        manager._start_progress_monitor(task_id, interval=10)

    # If blocking mode (recommended for delphi), wait for completion
    if blocking:
        result = manager.get_output(task_id, block=True, timeout=timeout)
        blocking_msg = colorize_agent_spawn_message(
            cost_emoji, agent_type, display_model, short_desc, task_id
        )
        return f"{blocking_msg} {Colors.BOLD}[BLOCKING]{Colors.RESET}\n\n{result}"

    # Format output based on mode
    if output_mode == OutputMode.CLEAN:
        return format_spawn_output(agent_type, display_model, task_id, mode=OutputMode.CLEAN)
    elif output_mode == OutputMode.VERBOSE:
        return colorize_agent_spawn_message(
            cost_emoji, agent_type, display_model, short_desc, task_id
        )
    else:  # SILENT
        return ""


async def agent_output(task_id: str, block: bool = False, auto_cleanup: bool = False) -> str:
    """
    Get output from a background agent task.

    Args:
        task_id: The task ID from agent_spawn
        block: If True, wait for the task to complete (up to 30s)
        auto_cleanup: If True, automatically remove task after retrieving output (default: False)

    Returns:
        Task status and output
    """
    manager = get_manager()
    return manager.get_output(task_id, block=block, auto_cleanup=auto_cleanup)


async def agent_retry(
    task_id: str,
    new_prompt: str | None = None,
    new_timeout: int | None = None,
) -> str:
    """
    Retry a failed or timed-out background agent.

    Args:
        task_id: The ID of the task to retry
        new_prompt: Optional refined prompt for the retry
        new_timeout: Optional new timeout in seconds

    Returns:
        New Task ID and status
    """
    manager = get_manager()
    task = manager.get_task(task_id)

    if not task:
        return f"❌ Task {task_id} not found."

    if task["status"] in ["running", "pending"]:
        return f"⚠️ Task {task_id} is still {task['status']}. Cancel it first if you want to retry."

    prompt = new_prompt or task["prompt"]
    timeout = new_timeout or task.get("timeout", 300)

    return await agent_spawn(
        prompt=prompt,
        agent_type=task["agent_type"],
        description=f"Retry of {task_id}: {task['description']}",
        timeout=timeout,
    )


async def agent_cancel(task_id: str) -> str:
    """
    Cancel a running background agent.

    Args:
        task_id: The task ID to cancel

    Returns:
        Cancellation result
    """
    manager = get_manager()
    success = manager.cancel(task_id)

    if success:
        return f"✅ Agent task {task_id} has been cancelled."
    else:
        task = manager.get_task(task_id)
        if not task:
            return f"❌ Task {task_id} not found."
        else:
            return f"⚠️ Task {task_id} is not running (status: {task['status']}). Cannot cancel."


async def agent_cleanup(max_age_minutes: int = 30, statuses: list[str] | None = None) -> str:
    """
    Clean up old completed/failed/cancelled agents.

    Args:
        max_age_minutes: Remove agents older than this many minutes (default: 30)
        statuses: List of statuses to remove (default: ['completed', 'failed', 'cancelled'])

    Returns:
        Formatted cleanup summary
    """
    manager = get_manager()
    result = manager.cleanup(max_age_minutes=max_age_minutes, statuses=statuses)

    if result["removed"] == 0:
        return f"🧹 No agents older than {max_age_minutes} minutes to clean up."

    return (
        f"🧹 {Colors.BOLD}Cleanup Complete{Colors.RESET}\n\n"
        f"{result['summary']}\n\n"
        f"Removed agents:\n"
        + "\n".join(f"  • {Colors.BRIGHT_BLACK}{tid}{Colors.RESET}" for tid in result["task_ids"])
    )


async def agent_list(show_all: bool = False, all_sessions: bool = False) -> str:
    """
    List all background agent tasks.

    Args:
        show_all: If True, show all agents. If False (default), only show running/pending agents.
        all_sessions: If True, show agents from ALL terminal sessions. If False (default), only current session.

    Returns:
        Formatted list of tasks
    """
    manager = get_manager()
    tasks = manager.list_tasks(show_all=show_all, current_session_only=not all_sessions)

    if not tasks:
        session_msg = " (current session only)" if not all_sessions else " (all sessions)"
        return f"No background agent tasks found{session_msg}."

    lines = []

    for t in sorted(tasks, key=lambda x: x.get("created_at", ""), reverse=True):
        status_emoji = {
            "pending": "⏳",
            "running": "🔄",
            "completed": "✅",
            "failed": "❌",
            "cancelled": "⚠️",
        }.get(t["status"], "❓")

        agent_type = t.get("agent_type", "unknown")
        display_model = AGENT_DISPLAY_MODELS.get(agent_type, AGENT_DISPLAY_MODELS["_default"])
        cost_emoji = get_agent_emoji(agent_type)
        desc = t.get("description", t.get("prompt", "")[:40])
        task_id = t["id"]

        # Concise format with colors: cost_emoji status agent:model('desc') id=xxx
        # Agent type in cyan, model in yellow, task_id in dim
        lines.append(
            f"{cost_emoji} {status_emoji} "
            f"{Colors.CYAN}{agent_type}{Colors.RESET}:"
            f"{Colors.YELLOW}{display_model}{Colors.RESET}"
            f"('{Colors.BOLD}{desc}{Colors.RESET}') "
            f"id={Colors.BRIGHT_BLACK}{task_id}{Colors.RESET}"
        )

    return "\n".join(lines)


async def agent_progress(task_id: str, lines: int = 20) -> str:
    """
    Get real-time progress from a running background agent.

    Shows the most recent output lines from the agent, useful for
    monitoring what the agent is currently doing.

    Args:
        task_id: The task ID from agent_spawn
        lines: Number of recent output lines to show (default 20)

    Returns:
        Recent agent output and status
    """
    manager = get_manager()
    return manager.get_progress(task_id, lines=lines)
