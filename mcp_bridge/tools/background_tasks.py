"""
Background Task Manager for Stravinsky.

Provides mechanisms to spawn, monitor, and manage async sub-agents.
Tasks are persisted to .stravinsky/tasks.json.
"""

import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class BackgroundTask:
    id: str
    prompt: str
    model: str
    status: str  # pending, running, completed, failed
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    result: str | None = None
    error: str | None = None
    pid: int | None = None


class BackgroundManager:
    def __init__(self, base_dir: str | None = None):
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            # Default to .stravinsky in the current working directory
            self.base_dir = Path.cwd() / ".stravinsky"
        
        self.tasks_dir = self.base_dir / "tasks"
        self.state_file = self.base_dir / "tasks.json"
        
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.state_file.exists():
            self._save_tasks({})

    def _load_tasks(self) -> dict[str, Any]:
        try:
            with open(self.state_file) as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _save_tasks(self, tasks: dict[str, Any]):
        with open(self.state_file, "w") as f:
            json.dump(tasks, f, indent=2)

    def create_task(self, prompt: str, model: str) -> str:
        import uuid as uuid_module  # Local import for MCP context
        task_id = str(uuid_module.uuid4())[:8]
        task = BackgroundTask(
            id=task_id,
            prompt=prompt,
            model=model,
            status="pending",
            created_at=datetime.isoformat(datetime.now()),
        )
        
        tasks = self._load_tasks()
        tasks[task_id] = asdict(task)
        self._save_tasks(tasks)
        return task_id

    def update_task(self, task_id: str, **kwargs):
        tasks = self._load_tasks()
        if task_id in tasks:
            tasks[task_id].update(kwargs)
            self._save_tasks(tasks)

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        tasks = self._load_tasks()
        return tasks.get(task_id)

    def list_tasks(self) -> list[dict[str, Any]]:
        tasks = self._load_tasks()
        return list(tasks.values())

    def spawn(self, task_id: str):
        """
        Spawns a background process to execute the task.
        In this implementation, it uses another instance of the MCP bridge
        or a dedicated tool invoker script.
        """
        task = self.get_task(task_id)
        if not task:
            return

        # We'll use a wrapper script that handles the model invocation and updates the status
        # mcp_bridge/tools/task_runner.py (we will create this)
        
        log_file = self.tasks_dir / f"{task_id}.log"
        
        # Start the background process
        cmd = [
            sys.executable,
            "-m", "mcp_bridge.tools.task_runner",
            "--task-id", task_id,
            "--base-dir", str(self.base_dir)
        ]
        
        try:
            # Using Popen to run in background
            process = subprocess.Popen(
                cmd,
                stdout=open(log_file, "w"),
                stderr=subprocess.STDOUT,
                start_new_session=True # Run in its own session so it doesn't die with the server
            )
            
            self.update_task(task_id, status="running", pid=process.pid, started_at=datetime.isoformat(datetime.now()))
        except Exception as e:
            self.update_task(task_id, status="failed", error=str(e))


# Tool interface functions

async def task_spawn(prompt: str, model: str = "gemini-3-flash") -> str:
    """Spawns a new background task."""
    manager = BackgroundManager()
    task_id = manager.create_task(prompt, model)
    manager.spawn(task_id)
    return f"Task spawned with ID: {task_id}. Use task_status('{task_id}') to check progress."


async def task_status(task_id: str) -> str:
    """Checks the status of a background task."""
    manager = BackgroundManager()
    task = manager.get_task(task_id)
    if not task:
        return f"Task {task_id} not found."
    
    status = task["status"]
    if status == "completed":
        return f"Task {task_id} COMPLETED:\n\n{task.get('result')}"
    elif status == "failed":
        return f"Task {task_id} FAILED:\n\n{task.get('error')}"
    else:
        return f"Task {task_id} is currently {status} (PID: {task.get('pid')})."


async def task_list() -> str:
    """Lists all background tasks."""
    manager = BackgroundManager()
    tasks = manager.list_tasks()
    if not tasks:
        return "No background tasks found."
    
    lines = ["Background Tasks:"]
    for t in tasks:
        lines.append(f"- [{t['id']}] {t['status']}: {t['prompt'][:50]}...")
    
    return "\n".join(lines)
