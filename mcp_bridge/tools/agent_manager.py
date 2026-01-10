"""
Agent Manager for Stravinsky.

Spawns background agents using Claude Code CLI with full tool access.
This replaces the simple model-only invocation with true agentic execution.
"""

import asyncio
import json
import os
import shutil
import subprocess
import signal
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import threading
import logging

logger = logging.getLogger(__name__)

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
    "implementation-lead": None,  # Hierarchical orchestrator using haiku
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
    "implementation-lead": "CHEAP",  # Uses haiku
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
    "implementation-lead": "haiku",
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


@dataclass
class AgentTask:
    """Represents a background agent task with full tool access."""

    id: str
    prompt: str
    agent_type: str  # explore, dewey, frontend, delphi, etc.
    description: str
    status: str  # pending, running, completed, failed, cancelled
    created_at: str
    parent_session_id: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None
    pid: Optional[int] = None
    timeout: int = 300  # Default 5 minutes
    progress: Optional[Dict[str, Any]] = None  # tool calls, last update


@dataclass
class AgentProgress:
    """Progress tracking for a running agent."""

    tool_calls: int = 0
    last_tool: Optional[str] = None
    last_message: Optional[str] = None
    last_update: Optional[str] = None


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

    def __init__(self, base_dir: Optional[str] = None):
        # Initialize lock FIRST - used by _save_tasks and _load_tasks
        self._lock = threading.RLock()

        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            self.base_dir = Path.cwd() / ".stravinsky"

        self.agents_dir = self.base_dir / "agents"
        self.state_file = self.base_dir / "agents.json"

        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.agents_dir.mkdir(parents=True, exist_ok=True)

        if not self.state_file.exists():
            self._save_tasks({})

        # In-memory tracking for running processes
        self._processes: Dict[str, subprocess.Popen] = {}
        self._notification_queue: Dict[str, List[Dict[str, Any]]] = {}

    def _load_tasks(self) -> Dict[str, Any]:
        """Load tasks from persistent storage."""
        with self._lock:
            try:
                if not self.state_file.exists():
                    return {}
                with open(self.state_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return {}

    def _save_tasks(self, tasks: Dict[str, Any]):
        """Save tasks to persistent storage."""
        with self._lock:
            with open(self.state_file, "w") as f:
                json.dump(tasks, f, indent=2)

    def _update_task(self, task_id: str, **kwargs):
        """Update a task's fields."""
        with self._lock:
            tasks = self._load_tasks()
            if task_id in tasks:
                tasks[task_id].update(kwargs)
                self._save_tasks(tasks)

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a task by ID."""
        tasks = self._load_tasks()
        return tasks.get(task_id)

    def list_tasks(self, parent_session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all tasks, optionally filtered by parent session."""
        tasks = self._load_tasks()
        task_list = list(tasks.values())

        if parent_session_id:
            task_list = [t for t in task_list if t.get("parent_session_id") == parent_session_id]

        return task_list

    def spawn(
        self,
        token_store: Any,
        prompt: str,
        agent_type: str = "explore",
        description: str = "",
        parent_session_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
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
        system_prompt: Optional[str] = None,
        model: str = "gemini-3-flash",
        thinking_budget: int = 0,
        timeout: int = 300,
    ):
        """Execute agent using Claude CLI with full tool access.

        Uses `claude -p` to spawn a background agent with complete tool access,
        just like oh-my-opencode's Sisyphus implementation.
        """

        def run_agent():
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
                        self._update_task(
                            task_id,
                            status="failed",
                            error=error_msg,
                            completed_at=datetime.now().isoformat(),
                        )
                        logger.error(f"[AgentManager] Agent {task_id} failed: {error_msg}")

                except subprocess.TimeoutExpired:
                    process.kill()
                    self._update_task(
                        task_id,
                        status="failed",
                        error=f"Agent timed out after {timeout}s",
                        completed_at=datetime.now().isoformat(),
                    )
                    logger.warning(f"[AgentManager] Agent {task_id} timed out")

            except FileNotFoundError:
                error_msg = f"Claude CLI not found at {self.CLAUDE_CLI}. Install with: npm install -g @anthropic-ai/claude-code"
                log_file.write_text(error_msg)
                self._update_task(
                    task_id,
                    status="failed",
                    error=error_msg,
                    completed_at=datetime.now().isoformat(),
                )
                logger.error(f"[AgentManager] {error_msg}")

            except Exception as e:
                error_msg = str(e)
                log_file.write_text(error_msg)
                self._update_task(
                    task_id,
                    status="failed",
                    error=error_msg,
                    completed_at=datetime.now().isoformat(),
                )
                logger.exception(f"[AgentManager] Agent {task_id} exception")

            finally:
                self._processes.pop(task_id, None)
                self._notify_completion(task_id)

        # Run in background thread
        thread = threading.Thread(target=run_agent, daemon=True)
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

    def get_pending_notifications(self, session_id: str) -> List[Dict[str, Any]]:
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

    def stop_all(self, clear_history: bool = False) -> int:
        """
        Stop all running agents and optionally clear task history.

        Args:
            clear_history: If True, also remove completed/failed tasks from history

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

        # Optionally clear history
        if clear_history:
            cleared = len(tasks)
            self._save_tasks({})
            self._processes.clear()
            logger.info(f"[AgentManager] Cleared all {cleared} agent tasks")
            return cleared

        return stopped_count

    def get_output(self, task_id: str, block: bool = False, timeout: float = 30.0) -> str:
        """
        Get output from an agent task.

        Args:
            task_id: The task ID
            block: If True, wait for completion
            timeout: Max seconds to wait if blocking

        Returns:
            Formatted task output/status
        """
        task = self.get_task(task_id)
        if not task:
            return f"Task {task_id} not found."

        if block and task["status"] == "running":
            # Poll for completion
            start = datetime.now()
            while (datetime.now() - start).total_seconds() < timeout:
                task = self.get_task(task_id)
                if not task or task["status"] != "running":
                    break
                time.sleep(0.5)

        # Refresh task state after potential blocking wait
        if not task:
            return f"Task {task_id} not found."

        status = task["status"]
        description = task.get("description", "")
        agent_type = task.get("agent_type", "unknown")

        # Get cost-tier emoji for visual differentiation
        cost_emoji = get_agent_emoji(agent_type)
        display_model = AGENT_DISPLAY_MODELS.get(agent_type, AGENT_DISPLAY_MODELS["_default"])

        if status == "completed":
            result = task.get("result", "(no output)")
            return f"""{cost_emoji} {Colors.BRIGHT_GREEN}✅ Agent Task Completed{Colors.RESET}

**Task ID**: {Colors.BRIGHT_BLACK}{task_id}{Colors.RESET}
**Agent**: {Colors.CYAN}{agent_type}{Colors.RESET}:{Colors.YELLOW}{display_model}{Colors.RESET}('{Colors.BOLD}{description}{Colors.RESET}')

**Result**:
{result}"""

        elif status == "failed":
            error = task.get("error", "(no error details)")
            return f"""{cost_emoji} {Colors.BRIGHT_RED}❌ Agent Task Failed{Colors.RESET}

**Task ID**: {Colors.BRIGHT_BLACK}{task_id}{Colors.RESET}
**Agent**: {Colors.CYAN}{agent_type}{Colors.RESET}:{Colors.YELLOW}{display_model}{Colors.RESET}('{Colors.BOLD}{description}{Colors.RESET}')

**Error**:
{error}"""

        elif status == "cancelled":
            return f"""{cost_emoji} {Colors.BRIGHT_YELLOW}⚠️ Agent Task Cancelled{Colors.RESET}

**Task ID**: {Colors.BRIGHT_BLACK}{task_id}{Colors.RESET}
**Agent**: {Colors.CYAN}{agent_type}{Colors.RESET}:{Colors.YELLOW}{display_model}{Colors.RESET}('{Colors.BOLD}{description}{Colors.RESET}')"""

        else:  # pending or running
            pid = task.get("pid", "N/A")
            started = task.get("started_at", "N/A")
            return f"""{cost_emoji} {Colors.BRIGHT_YELLOW}⏳ Agent Task Running{Colors.RESET}

**Task ID**: {Colors.BRIGHT_BLACK}{task_id}{Colors.RESET}
**Agent**: {Colors.CYAN}{agent_type}{Colors.RESET}:{Colors.YELLOW}{display_model}{Colors.RESET}('{Colors.BOLD}{description}{Colors.RESET}')
**PID**: {Colors.DIM}{pid}{Colors.RESET}
**Started**: {Colors.DIM}{started}{Colors.RESET}

Use `agent_output` with block=true to wait for completion."""

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
_manager: Optional[AgentManager] = None
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
    model: str = "gemini-3-flash",
    thinking_budget: int = 0,
    timeout: int = 300,
    blocking: bool = False,
) -> str:
    """
    Spawn a background agent.

    Args:
        prompt: The task for the agent to perform
        agent_type: Type of agent (explore, dewey, frontend, delphi)
        description: Short description shown in status
        model: Model to use (gemini-3-flash, gemini-2.0-flash, claude)
        thinking_budget: Reserved reasoning tokens
        timeout: Execution timeout in seconds
        blocking: If True, wait for completion and return result directly (use for delphi)

    Returns:
        Task ID and instructions, or full result if blocking=True
    """
    manager = get_manager()

    # Map agent types to system prompts
    # ALL agents use invoke_gemini or invoke_openai - NOT Claude directly
    # explore/dewey/document_writer/multimodal/frontend → gemini-3-flash
    # delphi → openai gpt-5.2
    system_prompts = {
        "explore": """You are a codebase exploration specialist. Find files, patterns, and answer 'where is X?' questions.

MODEL ROUTING (MANDATORY):
You MUST use invoke_gemini_agentic with model="gemini-3-flash" for ALL analysis and reasoning.
The agentic mode gives you autonomous tool access: read_file, list_directory, grep_search, write_file.

WORKFLOW:
1. Call invoke_gemini_agentic(prompt="<task description>", model="gemini-3-flash", max_turns=5, agent_context={"agent_type": "explore"})
2. The agentic model will autonomously explore the codebase using available tools
3. Return the Gemini response with findings

RECOMMENDED: max_turns=5 for thorough exploration""",
        "dewey": """You are a documentation and research specialist. Find implementation examples and official docs.

MODEL ROUTING (MANDATORY):
You MUST use invoke_gemini_agentic with model="gemini-3-flash" for ALL analysis, summarization, and reasoning.
The agentic mode gives you autonomous tool access: read_file, list_directory, grep_search, write_file.

WORKFLOW:
1. Call invoke_gemini_agentic(prompt="<task description>", model="gemini-3-flash", max_turns=5, agent_context={"agent_type": "dewey"})
2. The agentic model will autonomously research and gather information using available tools
3. Return the Gemini response with findings

RECOMMENDED: max_turns=5 for comprehensive research""",
        "frontend": """You are a Senior Frontend Architect & UI Designer.

MODEL ROUTING (MANDATORY):
You MUST use invoke_gemini_agentic with model="gemini-3-pro-high" for ALL code generation and design work.
The agentic mode gives you autonomous tool access: read_file, list_directory, grep_search, write_file.

DESIGN PHILOSOPHY:
- Anti-Generic: Reject standard layouts. Bespoke, asymmetric, distinctive.
- Library Discipline: Use existing UI libraries (Shadcn, Radix, MUI) if detected.
- Stack: React/Vue/Svelte, Tailwind/Custom CSS, semantic HTML5.

WORKFLOW:
1. Call invoke_gemini_agentic(prompt="Generate frontend code for: <task>", model="gemini-3-pro-high", max_turns=3, agent_context={"agent_type": "frontend"})
2. The agentic model will autonomously analyze the codebase and generate code using available tools
3. Return the generated code

RECOMMENDED: max_turns=3 for focused code generation""",
        "delphi": """You are a strategic technical advisor for architecture and hard debugging.

MODEL ROUTING (MANDATORY):
You MUST use invoke_openai with model="gpt-5.2" for ALL strategic advice and analysis.

WORKFLOW:
1. Gather context about the problem
2. Call invoke_openai(prompt="<problem description>", model="gpt-5.2", agent_context={"agent_type": "delphi"})
3. Return the GPT response""",
        "document_writer": """You are a Technical Documentation Specialist.

MODEL ROUTING (MANDATORY):
You MUST use invoke_gemini_agentic with model="gemini-3-flash" for ALL documentation generation.
The agentic mode gives you autonomous tool access: read_file, list_directory, grep_search, write_file.

DOCUMENT TYPES: README, API docs, ADRs, user guides, inline docs.

WORKFLOW:
1. Call invoke_gemini_agentic(prompt="Write documentation for: <topic>", model="gemini-3-flash", max_turns=3, agent_context={"agent_type": "document_writer"})
2. The agentic model will autonomously gather context and generate documentation using available tools
3. Return the documentation

RECOMMENDED: max_turns=3 for focused documentation generation""",
        "multimodal": """You interpret media files (PDFs, images, diagrams, screenshots).

MODEL ROUTING (MANDATORY):
You MUST use invoke_gemini_agentic with model="gemini-3-flash" for ALL visual analysis.
The agentic mode gives you autonomous tool access: read_file, list_directory, grep_search, write_file.

WORKFLOW:
1. Call invoke_gemini_agentic(prompt="Analyze this file: <path>. Extract: <goal>", model="gemini-3-flash", max_turns=3, agent_context={"agent_type": "multimodal"})
2. The agentic model will autonomously access and analyze the file using available tools
3. Return extracted information only

RECOMMENDED: max_turns=3 for focused visual analysis""",
        "planner": """You are a pre-implementation planning specialist. You analyze requests and produce structured implementation plans BEFORE any code changes begin.

PURPOSE:
- Analyze requests and produce actionable implementation plans
- Identify dependencies and parallelization opportunities
- Enable efficient parallel execution by the orchestrator
- Prevent wasted effort through upfront planning

METHODOLOGY:
1. EXPLORE FIRST: Spawn explore agents IN PARALLEL to understand the codebase
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
    }

    system_prompt = system_prompts.get(agent_type, None)

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

    # If blocking mode (recommended for delphi), wait for completion
    if blocking:
        result = manager.get_output(task_id, block=True, timeout=timeout)
        blocking_msg = colorize_agent_spawn_message(
            cost_emoji, agent_type, display_model, short_desc, task_id
        )
        return f"{blocking_msg} {Colors.BOLD}[BLOCKING]{Colors.RESET}\n\n{result}"

    # Enhanced format with ANSI colors: cost_emoji agent:model('description') status_emoji
    # 🟢 explore:gemini-3-flash('Find auth...') ⏳
    # With colors: agent type in cyan, model in yellow, description bold
    return colorize_agent_spawn_message(
        cost_emoji, agent_type, display_model, short_desc, task_id
    )


async def agent_output(task_id: str, block: bool = False) -> str:
    """
    Get output from a background agent task.

    Args:
        task_id: The task ID from agent_spawn
        block: If True, wait for the task to complete (up to 30s)

    Returns:
        Task status and output
    """
    manager = get_manager()
    return manager.get_output(task_id, block=block)


async def agent_retry(
    task_id: str,
    new_prompt: Optional[str] = None,
    new_timeout: Optional[int] = None,
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


async def agent_list() -> str:
    """
    List all background agent tasks.

    Returns:
        Formatted list of tasks
    """
    manager = get_manager()
    tasks = manager.list_tasks()

    if not tasks:
        return "No background agent tasks found."

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
