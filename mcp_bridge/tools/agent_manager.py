"""
Agent Manager for Stravinsky.

Spawns background agents using Claude Code CLI with full tool access.
This replaces the simple model-only invocation with true agentic execution.
"""

import asyncio
import json
import os
import subprocess
import signal
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import threading
import logging

logger = logging.getLogger(__name__)


@dataclass
class AgentTask:
    """Represents a background agent task with full tool access."""
    id: str
    prompt: str
    agent_type: str  # explore, librarian, frontend, etc.
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
    
    CLAUDE_CLI = "/opt/homebrew/bin/claude"
    
    def __init__(self, base_dir: Optional[str] = None):
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
        self._notification_queue: Dict[str, List[AgentTask]] = {}
        self._lock = threading.RLock()
    
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
        task_id = f"agent_{uuid.uuid4().hex[:8]}"
        
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
        self._execute_agent(task_id, token_store, prompt, agent_type, system_prompt, model, thinking_budget, timeout)
        
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
        """Execute agent in background thread using direct API calls.
        
        NOTE: The Claude CLI (`claude -p`) hangs in non-interactive mode in v2.0.76,
        so we use direct API calls instead. This means agents don't have tool access,
        but they can still perform research/analysis tasks.
        """
        
        def run_agent():
            log_file = self.agents_dir / f"{task_id}.log"
            output_file = self.agents_dir / f"{task_id}.out"
            
            self._update_task(
                task_id,
                status="running",
                started_at=datetime.now().isoformat()
            )
            
            try:
                # Use direct API calls instead of hanging CLI
                # Import here to avoid circular imports
                from .model_invoke import invoke_gemini, invoke_openai
                
                # Prepare full prompt with system prompt if provided
                full_prompt = prompt
                if system_prompt:
                    full_prompt = f"{system_prompt}\n\n---\n\n{prompt}"
                
                logger.info(f"[AgentManager] Executing agent {task_id} via API ({model})")
                
                # Create event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    # Route to appropriate model
                    if model.startswith("gpt") or model.startswith("o1") or model.startswith("o3"):
                        result = loop.run_until_complete(
                            invoke_openai(
                                token_store=token_store,
                                prompt=full_prompt,
                                model=model,
                                thinking_budget=thinking_budget,
                            )
                        )
                    else:
                        # Default to Gemini
                        result = loop.run_until_complete(
                            invoke_gemini(
                                token_store=token_store,
                                prompt=full_prompt,
                                model=model,
                                thinking_budget=thinking_budget,
                            )
                        )
                finally:
                    loop.close()
                
                # Write output
                output_file.write_text(result)
                
                self._update_task(
                    task_id,
                    status="completed",
                    result=result,
                    completed_at=datetime.now().isoformat()
                )
                logger.info(f"[AgentManager] Agent {task_id} completed successfully")
                    
            except Exception as e:
                error_msg = str(e)
                log_file.write_text(error_msg)
                self._update_task(
                    task_id,
                    status="failed",
                    error=error_msg,
                    completed_at=datetime.now().isoformat()
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
        
        self._update_task(
            task_id,
            status="cancelled",
            completed_at=datetime.now().isoformat()
        )
        
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
                if task["status"] != "running":
                    break
                asyncio.sleep(0.5)
        
        status = task["status"]
        description = task.get("description", "")
        agent_type = task.get("agent_type", "unknown")
        
        if status == "completed":
            result = task.get("result", "(no output)")
            return f"""✅ Agent Task Completed

**Task ID**: {task_id}
**Agent**: {agent_type}
**Description**: {description}

**Result**:
{result}"""
        
        elif status == "failed":
            error = task.get("error", "(no error details)")
            return f"""❌ Agent Task Failed

**Task ID**: {task_id}
**Agent**: {agent_type}
**Description**: {description}

**Error**:
{error}"""
        
        elif status == "cancelled":
            return f"""⚠️ Agent Task Cancelled

**Task ID**: {task_id}
**Agent**: {agent_type}
**Description**: {description}"""
        
        else:  # pending or running
            pid = task.get("pid", "N/A")
            started = task.get("started_at", "N/A")
            return f"""⏳ Agent Task Running

**Task ID**: {task_id}
**Agent**: {agent_type}
**Description**: {description}
**PID**: {pid}
**Started**: {started}

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
                        completed_at=datetime.now().isoformat()
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
        
        result = f"""{status_emoji} **Agent Progress**

**Task ID**: {task_id}
**Agent**: {agent_type}
**Description**: {description}
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


def get_manager() -> AgentManager:
    """Get or create the global AgentManager instance."""
    global _manager
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
        
    Returns:
        Task ID and instructions
    """
    manager = get_manager()
    
    # Map agent types to system prompts
    system_prompts = {
        "explore": "You are a codebase exploration specialist. Find files, patterns, and answer 'where is X?' questions efficiently.",
        "dewey": "You are a documentation and research specialist. Find implementation examples, official docs, and provide evidence-based answers.",
        "frontend": """You are a Senior Frontend Architect & Avant-Garde UI Designer with 15+ years experience.

OPERATIONAL DIRECTIVES:
- Follow instructions. Execute immediately. No fluff.
- Output First: Prioritize code and visual solutions.

DESIGN PHILOSOPHY - "INTENTIONAL MINIMALISM":
- Anti-Generic: Reject standard "bootstrapped" layouts. If it looks like a template, it's wrong.
- Bespoke layouts, asymmetry, distinctive typography.
- Before placing any element, calculate its purpose. No purpose = delete it.

FRONTEND CODING STANDARDS:
- Library Discipline: If a UI library (Shadcn, Radix, MUI) is detected, YOU MUST USE IT.
- Do NOT build custom components if the library provides them.
- Stack: Modern (React/Vue/Svelte), Tailwind/Custom CSS, semantic HTML5.
- Focus on micro-interactions, perfect spacing, "invisible" UX.

RESPONSE FORMAT:
1. Rationale: (1 sentence on why elements were placed there)
2. The Code.

ULTRATHINK MODE (when user says "ULTRATHINK" or "think harder"):
1. Deep Reasoning Chain: Detailed breakdown of architectural and design decisions
2. Edge Case Analysis: What could go wrong and how we prevented it
3. The Code: Optimized, bespoke, production-ready, utilizing existing libraries""",
        "delphi": "You are a strategic advisor. Provide architecture guidance, debugging assistance, and code review.",
        "document_writer": """You are a Technical Documentation Specialist. Your expertise is creating clear, comprehensive documentation.

DOCUMENT TYPES YOU EXCEL AT:
- README files with proper structure
- API documentation with examples
- Architecture decision records (ADRs)
- User guides and tutorials
- Inline code documentation

DOCUMENTATION PRINCIPLES:
- Audience-first: Know who's reading and what they need
- Progressive disclosure: Overview → Details → Edge cases
- Examples over explanations: Show, don't just tell
- Keep it DRY: Reference rather than repeat
- Version awareness: Note when behavior differs across versions

RESPONSE FORMAT:
1. Document type and target audience identified
2. The documentation, properly formatted in markdown""",
        "multimodal": """You interpret media files that cannot be read as plain text.

Your job: examine the attached file and extract ONLY what was requested.

CAPABILITIES:
- PDFs: extract text, structure, tables, data from specific sections
- Images: describe layouts, UI elements, text, diagrams, charts
- Diagrams: explain relationships, flows, architecture depicted
- Screenshots: analyze UI/UX, identify components, extract text

HOW YOU WORK:
1. Receive a file path and a goal describing what to extract
2. Read and analyze the file deeply using Gemini's vision capabilities
3. Return ONLY the relevant extracted information
4. The main agent never processes the raw file - you save context tokens

RESPONSE RULES:
- Return extracted information directly, no preamble
- If info not found, state clearly what's missing
- Be thorough on the goal, concise on everything else""",
    }
    
    system_prompt = system_prompts.get(agent_type, None)
    
    # Override model based on agent type for optimal performance
    agent_model_overrides = {
        "frontend": "gemini-3-pro",  # Pro for UI/UX complexity
        "delphi": "gpt-5.2-medium",  # OpenAI for strategic reasoning
    }
    actual_model = agent_model_overrides.get(agent_type, model)
    
    # Get token store for authentication
    from ..auth.token_store import TokenStore
    token_store = TokenStore()
    
    task_id = manager.spawn(
        token_store=token_store,
        prompt=prompt,
        agent_type=agent_type,
        description=description or prompt[:50],
        system_prompt=system_prompt,
        model=actual_model,
        thinking_budget=thinking_budget,
        timeout=timeout,
    )
    
    return f"""🚀 Background agent spawned successfully.

**Task ID**: {task_id}
**Agent Type**: {agent_type}
**Model**: {model}
**Thinking Budget**: {thinking_budget if thinking_budget > 0 else "N/A"}
**Description**: {description or prompt[:50]}

The agent is now running. Use:
- `agent_progress(task_id="{task_id}")` to monitor real-time progress
- `agent_output(task_id="{task_id}")` to get final result
- `agent_cancel(task_id="{task_id}")` to stop the agent"""


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
        timeout=timeout
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
    
    lines = ["**Background Agent Tasks**", ""]
    
    for t in sorted(tasks, key=lambda x: x.get("created_at", ""), reverse=True):
        status_emoji = {
            "pending": "⏳",
            "running": "🔄",
            "completed": "✅",
            "failed": "❌",
            "cancelled": "⚠️",
        }.get(t["status"], "❓")
        
        desc = t.get("description", t.get("prompt", "")[:40])
        lines.append(f"- {status_emoji} [{t['id']}] {t['agent_type']}: {desc}")
    
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
