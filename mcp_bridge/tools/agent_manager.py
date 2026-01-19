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
import asyncio
import sys
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional, List, Dict
import subprocess
from .mux_client import get_mux, MuxClient
try:
    from . import semantic_search
except ImportError:
    # Fallback or lazy import
    semantic_search = None

logger = logging.getLogger(__name__)


# Output formatting modes
class OutputMode(Enum):
    """Control verbosity of agent spawn output."""

    CLEAN = "clean"  # Concise single-line output
    VERBOSE = "verbose"  # Full details with colors
    SILENT = "silent"  # No output to stdout (logs only)


# Model routing configuration
AGENT_MODEL_ROUTING = {
    "explore": None,
    "dewey": None,
    "document_writer": None,
    "multimodal": None,
    "frontend": None,
    "delphi": None,
    "research-lead": None,
    "implementation-lead": "sonnet",
    "momus": None,
    "comment_checker": None,
    "debugger": "sonnet",
    "code-reviewer": None,
    "planner": "opus",
    "_default": "sonnet",
}

AGENT_COST_TIERS = {
    "explore": "CHEAP",
    "dewey": "CHEAP",
    "document_writer": "CHEAP",
    "multimodal": "CHEAP",
    "research-lead": "CHEAP",
    "implementation-lead": "MEDIUM",
    "momus": "CHEAP",
    "comment_checker": "CHEAP",
    "debugger": "MEDIUM",
    "code-reviewer": "CHEAP",
    "frontend": "MEDIUM",
    "delphi": "EXPENSIVE",
    "planner": "EXPENSIVE",
    "_default": "EXPENSIVE",
}

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

COST_TIER_EMOJI = {
    "CHEAP": "🟢",
    "MEDIUM": "🔵",
    "EXPENSIVE": "🟣",
}

MODEL_FAMILY_EMOJI = {
    "gemini-3-flash": "🟢",
    "gemini-3-pro-high": "🔵",
    "haiku": "🟢",
    "sonnet-4.5": "🟠",
    "opus-4.5": "🟣",
    "gpt-5.2": "🟣",
}


class Colors:
    """ANSI color codes for colorized terminal output."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
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

AGENT_TOOLS = {
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
    "momus": ["Read", "Grep", "Glob", "Bash", "lsp_diagnostics", "ast_grep_search"],
    "comment_checker": ["Read", "Grep", "Glob", "Bash", "ast_grep_search", "lsp_document_symbols"],
    # Specialized agents
    "document_writer": ["Read", "Write", "Grep", "Glob", "Bash", "invoke_gemini"],
    "multimodal": ["Read", "invoke_gemini"],
    "planner": ["Read", "Grep", "Glob", "Bash"],
}


def validate_agent_tools(agent_type: str, required_tools: list[str]) -> None:
    if agent_type not in AGENT_TOOLS:
        raise ValueError(
            f"Unknown agent_type '{agent_type}'. Valid types: {list(AGENT_TOOLS.keys())}"
        )

    allowed_tools = AGENT_TOOLS[agent_type]
    if "all" in allowed_tools:
        return

    missing_tools = [tool for tool in required_tools if tool not in allowed_tools]
    if missing_tools:
        raise ValueError(
            f"Agent type '{agent_type}' does not have access to required tools: {missing_tools}\n"
            f"Allowed tools for {agent_type}: {allowed_tools}"
        )


def validate_agent_hierarchy(spawning_agent: str, target_agent: str) -> None:
    if spawning_agent in ORCHESTRATOR_AGENTS:
        return

    if spawning_agent in WORKER_AGENTS and target_agent in ORCHESTRATOR_AGENTS:
        raise ValueError(
            f"Worker agent '{spawning_agent}' cannot spawn orchestrator agent '{target_agent}'."
        )

    if spawning_agent in WORKER_AGENTS and target_agent in WORKER_AGENTS:
        raise ValueError(
            f"Worker agent '{spawning_agent}' cannot spawn another worker agent '{target_agent}'."
        )


def colorize_agent_spawn_message(
    cost_emoji: str,
    agent_type: str,
    display_model: str,
    description: str,
    task_id: str,
) -> str:
    short_desc = (description or "")[:50].strip()
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
    if mode == OutputMode.SILENT:
        return ""

    cost_emoji = get_agent_emoji(agent_type)
    if mode == OutputMode.CLEAN:
        return (
            f"{Colors.GREEN}✓{Colors.RESET} "
            f"{Colors.CYAN}{agent_type}{Colors.RESET}:"
            f"{Colors.YELLOW}{display_model}{Colors.RESET} "
            f"→ {Colors.CYAN}{task_id}{Colors.RESET}"
        )
    return ""


@dataclass
class AgentTask:
    id: str
    prompt: str
    agent_type: str
    description: str
    status: str
    created_at: str
    parent_session_id: str | None = None
    terminal_session_id: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    result: str | None = None
    error: str | None = None
    pid: int | None = None
    timeout: int = 300
    progress: dict[str, Any] | None = None


class AgentManager:
    CLAUDE_CLI = shutil.which("claude") or "/opt/homebrew/bin/claude"

    def __init__(self, base_dir: str | None = None):
        self._lock = threading.RLock()
        import uuid as uuid_module

        self.session_id = os.environ.get(
            "CLAUDE_CODE_SESSION_ID", f"pid_{os.getpid()}_{uuid_module.uuid4().hex[:8]}"
        )
        
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            self.base_dir = Path.cwd() / ".stravinsky"

        self.agents_dir = self.base_dir / "agents"
        self.state_file = self.base_dir / f"agents_{self.session_id}.json"

        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.agents_dir.mkdir(parents=True, exist_ok=True)

        if not self.state_file.exists():
            self._save_tasks({})

        self._processes: dict[str, Any] = {} 
        self._notification_queue: dict[str, list[dict[str, Any]]] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._progress_monitors: dict[str, asyncio.Task] = {}
        self._stop_monitors = asyncio.Event()
        
        # Orchestrator Integration
        self.orchestrator = None # Type: Optional[OrchestratorState]

        try:
            self._sync_cleanup(max_age_minutes=30)
        except Exception:
            pass
            
        self._ensure_sidecar_running()

    def _ensure_sidecar_running(self):
        """Start the Go sidecar if not running."""
        # Simple check: is socket present?
        if os.path.exists("/tmp/stravinsky.sock"):
            return

        mux_path = Path.cwd() / "dist" / "stravinsky-mux"
        if mux_path.exists():
            try:
                subprocess.Popen(
                    [str(mux_path)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
                logger.info("Started stravinsky-mux sidecar")
                # Wait briefly for socket
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"Failed to start sidecar: {e}")

    def _sync_cleanup(self, max_age_minutes: int = 30):
        tasks = self._load_tasks()
        now = datetime.now()
        removed_ids = []
        for task_id, task in list(tasks.items()):
            if task.get("status") in ["completed", "failed", "cancelled"]:
                completed_at = task.get("completed_at")
                if completed_at:
                    try:
                        completed_time = datetime.fromisoformat(completed_at)
                        if (now - completed_time).total_seconds() / 60 > max_age_minutes:
                            removed_ids.append(task_id)
                            del tasks[task_id]
                    except: continue
        if removed_ids:
            self._save_tasks(tasks)

    def _load_tasks(self) -> dict[str, Any]:
        with self._lock:
            try:
                if not self.state_file.exists():
                    return {}
                with open(self.state_file) as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return {}

    def _save_tasks(self, tasks: dict[str, Any]):
        with self._lock, open(self.state_file, "w") as f:
            json.dump(tasks, f, indent=2)

    def _update_task(self, task_id: str, **kwargs):
        with self._lock:
            tasks = self._load_tasks()
            if task_id in tasks:
                tasks[task_id].update(kwargs)
                self._save_tasks(tasks)

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        tasks = self._load_tasks()
        return tasks.get(task_id)

    def list_tasks(
        self,
        parent_session_id: str | None = None,
        show_all: bool = True,
        current_session_only: bool = True,
    ) -> list[dict[str, Any]]:
        tasks = self._load_tasks()
        task_list = list(tasks.values())
        if current_session_only:
            task_list = [t for t in task_list if t.get("terminal_session_id") == self.session_id]
        if parent_session_id:
            task_list = [t for t in task_list if t.get("parent_session_id") == parent_session_id]
        if not show_all:
            task_list = [t for t in task_list if t.get("status") in ["running", "pending"]]
        return task_list

    async def spawn_async(
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
        semantic_first: bool = False,
    ) -> str:
        # Orchestrator Logic
        if self.orchestrator:
            logger.info(f"Spawning agent {agent_type} in phase {self.orchestrator.current_phase}")
            # Example: If in PLAN phase, inject wisdom automatically
            from ..orchestrator.enums import OrchestrationPhase
            if self.orchestrator.current_phase == OrchestrationPhase.PLAN:
                from ..orchestrator.wisdom import WisdomLoader
                wisdom = WisdomLoader().load_wisdom()
                if wisdom:
                    prompt = f"## PROJECT WISDOM\n{wisdom}\n\n---\n\n{prompt}"

        # Semantic First Context Injection
        if semantic_first and semantic_search:
            try:
                # Run search in thread to avoid blocking loop
                results = await asyncio.to_thread(
                    semantic_search.search, 
                    query=prompt, 
                    n_results=5, 
                    project_path=str(self.base_dir.parent)
                )
                if results and "No results" not in results and "Error" not in results:
                    prompt = (
                        f"## 🧠 SEMANTIC CONTEXT (AUTO-INJECTED)\n"
                        f"The following code snippets were found in the vector index based on your task:\n\n"
                        f"{results}\n\n"
                        f"---\n\n"
                        f"## 📋 YOUR TASK\n"
                        f"{prompt}"
                    )
            except Exception as e:
                logger.error(f"Semantic context injection failed: {e}")

        import uuid as uuid_module
        task_id = f"agent_{uuid_module.uuid4().hex[:8]}"

        task = AgentTask(
            id=task_id,
            prompt=prompt,
            agent_type=agent_type,
            description=description or prompt[:50],
            status="pending",
            created_at=datetime.now().isoformat(),
            parent_session_id=parent_session_id,
            terminal_session_id=self.session_id,
            timeout=timeout,
        )

        with self._lock:
            tasks = self._load_tasks()
            tasks[task_id] = asdict(task)
            self._save_tasks(tasks)

        task_obj = asyncio.create_task(
            self._execute_agent_async(
                task_id, token_store, prompt, agent_type, system_prompt, model, thinking_budget, timeout
            )
        )
        self._tasks[task_id] = task_obj

        return task_id

    def spawn(self, *args, **kwargs) -> str:
        try:
            loop = asyncio.get_running_loop()
            task_id_ref = [None]
            async def wrap():
                task_id_ref[0] = await self.spawn_async(*args, **kwargs)
            
            thread = threading.Thread(target=lambda: asyncio.run(wrap()))
            thread.start()
            thread.join()
            return task_id_ref[0]
        except RuntimeError:
            return asyncio.run(self.spawn_async(*args, **kwargs))

    async def _execute_agent_async(
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
        self.agents_dir.mkdir(parents=True, exist_ok=True)
        log_file = self.agents_dir / f"{task_id}.log"
        output_file = self.agents_dir / f"{task_id}.out"

        self._update_task(task_id, status="running", started_at=datetime.now().isoformat())

        try:
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n---\n\n{prompt}"

            cmd = [
                self.CLAUDE_CLI,
                "-p",
                full_prompt,
                "--output-format",
                "text",
                "--dangerously-skip-permissions",
            ]

            cli_model = AGENT_MODEL_ROUTING.get(agent_type, AGENT_MODEL_ROUTING.get("_default", "sonnet"))
            if cli_model:
                cmd.extend(["--model", cli_model])

            if thinking_budget and thinking_budget > 0:
                cmd.extend(["--thinking-budget", str(thinking_budget)])

            if system_prompt:
                system_file = self.agents_dir / f"{task_id}.system"
                system_file.write_text(system_prompt)
                cmd.extend(["--system-prompt", str(system_file)])

            logger.info(f"[AgentManager] Spawning {task_id}: {' '.join(cmd[:3])}...")

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(Path.cwd()),
                env={**os.environ, "CLAUDE_CODE_ENTRYPOINT": "stravinsky-agent"},
                start_new_session=True,
            )

            self._processes[task_id] = process
            self._update_task(task_id, pid=process.pid)
            
            # Streaming read loop for Mux
            stdout_buffer = []
            stderr_buffer = []
            mux = MuxClient(task_id)
            mux.connect()
            
            async def read_stream(stream, buffer, stream_name):
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    decoded = line.decode('utf-8', errors='replace')
                    buffer.append(decoded)
                    mux.log(decoded.strip(), stream_name)
            
            try:
                await asyncio.wait_for(
                    asyncio.gather(
                        read_stream(process.stdout, stdout_buffer, "stdout"),
                        read_stream(process.stderr, stderr_buffer, "stderr"),
                        process.wait()
                    ),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                except: pass
                # Clean up streams
                await process.wait()
                error_msg = f"Timed out after {timeout}s"
                output_file.write_text(f"❌ TIMEOUT: {error_msg}")
                self._update_task(task_id, status="failed", error=error_msg, completed_at=datetime.now().isoformat())
                return

            stdout = "".join(stdout_buffer)
            stderr = "".join(stderr_buffer)
            
            if stderr:
                log_file.write_text(stderr)

            if process.returncode == 0:
                output_file.write_text(stdout)
                self._update_task(
                    task_id,
                    status="completed",
                    result=stdout.strip(),
                    completed_at=datetime.now().isoformat(),
                )
            else:
                error_msg = f"Exit code {process.returncode}\n{stderr}"
                output_file.write_text(f"❌ ERROR: {error_msg}")
                self._update_task(
                    task_id,
                    status="failed",
                    error=error_msg,
                    completed_at=datetime.now().isoformat(),
                )

        except asyncio.CancelledError:
            
            

            
            try:
                if task_id in self._processes:
                    proc = self._processes[task_id]
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    await proc.wait()
            except: pass
            raise
        except Exception as e:
            error_msg = str(e)
            output_file.write_text(f"❌ EXCEPTION: {error_msg}")
            self._update_task(task_id, status="failed", error=error_msg, completed_at=datetime.now().isoformat())
        finally:
            self._processes.pop(task_id, None)
            self._tasks.pop(task_id, None)
            self._notify_completion(task_id)

    def _notify_completion(self, task_id: str):
        task = self.get_task(task_id)
        if task and task.get("parent_session_id"):
            parent_id = task["parent_session_id"]
            if parent_id not in self._notification_queue:
                self._notification_queue[parent_id] = []
            self._notification_queue[parent_id].append(task)

    async def _monitor_progress_async(self, task_id: str, interval: int = 10):
        task = self.get_task(task_id)
        if not task: return
        start_time = datetime.fromisoformat(task.get("started_at") or datetime.now().isoformat())

        while not self._stop_monitors.is_set():
            task = self.get_task(task_id)
            if not task or task["status"] not in ["running", "pending"]:
                # Final status reporting...
                break
            
            elapsed = int((datetime.now() - start_time).total_seconds())
            sys.stderr.write(f"{Colors.YELLOW}⏳{Colors.RESET} {Colors.CYAN}{task_id}{Colors.RESET} running ({elapsed}s)...\n")
            sys.stderr.flush()
            
            try:
                await asyncio.wait_for(self._stop_monitors.wait(), timeout=interval)
                break
            except asyncio.TimeoutError:
                continue

    def cancel(self, task_id: str) -> bool:
        task = self.get_task(task_id)
        if not task or task["status"] not in ["pending", "running"]:
            return False

        process = self._processes.get(task_id)
        if process:
            try:
                if hasattr(process, 'pid'):
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            except: pass
            
        async_task = self._tasks.get(task_id)
        if async_task:
            async_task.cancel()
            
        self._update_task(task_id, status="cancelled", completed_at=datetime.now().isoformat())
        return True

    async def stop_all_async(self, clear_history: bool = False) -> int:
        tasks = self._load_tasks()
        stopped_count = 0
        for task_id, task in list(tasks.items()):
            status = task.get("status")
            if status in ["pending", "running"]:
                if self.cancel(task_id):
                    stopped_count += 1
        
        self._stop_monitors.set()
        
        if self._tasks:
            await asyncio.gather(*self._tasks.values(), return_exceptions=True)
        if self._progress_monitors:
            await asyncio.gather(*self._progress_monitors.values(), return_exceptions=True)
            
        if clear_history:
            cleared = len(tasks)
            self._save_tasks({})
            self._processes.clear()
            self._tasks.clear()
            self._progress_monitors.clear()
            return cleared
        return stopped_count

    def stop_all(self, clear_history: bool = False) -> int:
        try:
            return asyncio.run(self.stop_all_async(clear_history))
        except RuntimeError:
            # Loop already running, use a thread
            res = [0]
            def wrap(): res[0] = asyncio.run(self.stop_all_async(clear_history))
            t = threading.Thread(target=wrap)
            t.start()
            t.join()
            return res[0]

    def cleanup(self, max_age_minutes: int = 30, statuses: list[str] | None = None) -> dict:
        if statuses is None: statuses = ["completed", "failed", "cancelled"]
        tasks = self._load_tasks()
        now = datetime.now()
        removed_ids = []
        for task_id, task in list(tasks.items()):
            if task.get("status") in statuses:
                completed_at = task.get("completed_at")
                if completed_at:
                    try:
                        completed_time = datetime.fromisoformat(completed_at)
                        if (now - completed_time).total_seconds() / 60 > max_age_minutes:
                            removed_ids.append(task_id)
                            del tasks[task_id]
                            for ext in [".log", ".out", ".system"]:
                                (self.agents_dir / f"{task_id}{ext}").unlink(missing_ok=True)
                    except: continue
        if removed_ids: self._save_tasks(tasks)
        return {"removed": len(removed_ids), "task_ids": removed_ids, "summary": f"Removed {len(removed_ids)} agents"}

    async def get_output(self, task_id: str, block: bool = False, timeout: float = 30.0, auto_cleanup: bool = False) -> str:
        task = self.get_task(task_id)
        if not task: return f"Task {task_id} not found."

        if block and task["status"] in ["pending", "running"]:
            start = time.time()
            while (time.time() - start) < timeout:
                task = self.get_task(task_id)
                if not task or task["status"] not in ["pending", "running"]: break
                await asyncio.sleep(0.5)

        task = self.get_task(task_id)
        status = task["status"]
        agent_type = task.get("agent_type", "unknown")
        cost_emoji = get_agent_emoji(agent_type)
        display_model = AGENT_DISPLAY_MODELS.get(agent_type, AGENT_DISPLAY_MODELS["_default"])

        if status == "completed":
            res = task.get("result", "")
            return f"{cost_emoji} {Colors.BRIGHT_GREEN}✅ Completed{Colors.RESET}\n\n**ID**: {task_id}\n**Result**:\n{res}"
        elif status == "failed":
            err = task.get("error", "")
            return f"{cost_emoji} {Colors.BRIGHT_RED}❌ Failed{Colors.RESET}\n\n**ID**: {task_id}\n**Error**:\n{err}"
        else:
            return f"{cost_emoji} {Colors.BRIGHT_YELLOW}⏳ Running{Colors.RESET}\n\n**ID**: {task_id}\nStatus: {status}"

    def get_progress(self, task_id: str, lines: int = 20) -> str:
        task = self.get_task(task_id)
        if not task: return f"Task {task_id} not found."
        output_file = self.agents_dir / f"{task_id}.out"
        output_content = ""
        if output_file.exists():
            try:
                text = output_file.read_text()
                output_content = "\n".join(text.strip().split("\n")[-lines:])
            except: pass
        return f"**Agent Progress**\nID: {task_id}\nStatus: {task['status']}\n\nOutput:\n```\n{output_content}\n```"


_manager: AgentManager | None = None
_manager_lock = threading.Lock()

def get_manager() -> AgentManager:
    global _manager
    if _manager is None:
        with _manager_lock:
            if _manager is None:
                _manager = AgentManager()
    return _manager


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
    semantic_first: bool = False,
) -> str:
    manager = get_manager()
    if spawning_agent in ORCHESTRATOR_AGENTS:
        if not delegation_reason or not expected_outcome or not required_tools:
            raise ValueError("Orchestrators must provide delegation metadata")
    if required_tools: validate_agent_tools(agent_type, required_tools)
    if spawning_agent: validate_agent_hierarchy(spawning_agent, agent_type)
    system_prompt = f"You are a {agent_type} specialist." 
    from ..auth.token_store import TokenStore
    token_store = TokenStore()
    task_id = await manager.spawn_async(
        token_store=token_store,
        prompt=prompt,
        agent_type=agent_type,
        description=description,
        system_prompt=system_prompt,
        timeout=timeout,
        semantic_first=semantic_first,
    )
    if not blocking:
        monitor_task = asyncio.create_task(manager._monitor_progress_async(task_id))
        manager._progress_monitors[task_id] = monitor_task
    if blocking:
        return await manager.get_output(task_id, block=True, timeout=timeout)
    display_model = AGENT_DISPLAY_MODELS.get(agent_type, AGENT_DISPLAY_MODELS["_default"])
    return format_spawn_output(agent_type, display_model, task_id)


async def agent_output(task_id: str, block: bool = False, auto_cleanup: bool = False) -> str:
    manager = get_manager()
    return await manager.get_output(task_id, block=block, auto_cleanup=auto_cleanup)

async def agent_retry(task_id: str, new_prompt: str = None, new_timeout: int = None) -> str:
    manager = get_manager()
    task = manager.get_task(task_id)
    if not task: return f"❌ Task {task_id} not found."
    return await agent_spawn(prompt=new_prompt or task["prompt"], agent_type=task["agent_type"], timeout=new_timeout or task["timeout"])

async def agent_cancel(task_id: str) -> str:
    manager = get_manager()
    if not manager.get_task(task_id): return f"❌ Task {task_id} not found."
    if manager.cancel(task_id): return f"✅ Cancelled {task_id}."
    return f"❌ Could not cancel {task_id}."

async def agent_cleanup(max_age_minutes: int = 30, statuses: list[str] = None) -> str:
    manager = get_manager()
    res = manager.cleanup(max_age_minutes, statuses)
    return res["summary"]

async def agent_list(show_all: bool = False, all_sessions: bool = False) -> str:
    manager = get_manager()
    tasks = manager.list_tasks(show_all=show_all, current_session_only=not all_sessions)
    if not tasks: return "No tasks found."
    return "\n".join([f"• {t['id']} ({t['status']}) - {t['agent_type']}" for t in tasks])

async def agent_progress(task_id: str, lines: int = 20) -> str:
    manager = get_manager()
    return manager.get_progress(task_id, lines)