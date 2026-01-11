"""
Task Runner for Stravinsky background sub-agents.

This script is executed as a background process to handle agent tasks,
capture output, and update status in tasks.json.
"""

import argparse
import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("task_runner")


async def run_task(task_id: str, base_dir: str):
    base_path = Path(base_dir)
    tasks_file = base_path / "tasks.json"
    agents_dir = base_path / "agents"

    # Load task details
    try:
        with open(tasks_file) as f:
            tasks = json.load(f)
        task = tasks.get(task_id)
    except Exception as e:
        logger.error(f"Failed to load tasks: {e}")
        return

    if not task:
        logger.error(f"Task {task_id} not found")
        return

    prompt = task.get("prompt")
    model = task.get("model", "gemini-3-flash")

    output_file = agents_dir / f"{task_id}.out"
    agents_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Use Claude CLI for background tasks to ensure tool access
        # Discover CLI path
        claude_cli = os.environ.get("CLAUDE_CLI", "/opt/homebrew/bin/claude")

        cmd = [
            claude_cli,
            "-p",
        ]

        if model:
            cmd.extend(["--model", model])

        cmd.append(prompt)

        logger.info(f"Executing task {task_id} via CLI ({model})...")

        # Open output and log files
        with (
            open(output_file, "w") as out_f,
            open(base_path / "tasks" / f"{task_id}.log", "a") as log_f,
        ):
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=out_f, stderr=log_f, cwd=os.getcwd()
            )

            await process.wait()

        # Read result
        if output_file.exists():
            result = output_file.read_text()
        else:
            result = ""

        # Save result
        with open(output_file, "w") as f:
            f.write(result)

        # Update status
        with open(tasks_file) as f:
            tasks = json.load(f)

        if task_id in tasks:
            tasks[task_id].update(
                {
                    "status": "completed",
                    "result": result,
                    "completed_at": datetime.now().isoformat(),
                }
            )
            with open(tasks_file, "w") as f:
                json.dump(tasks, f, indent=2)

        logger.info(f"Task {task_id} completed successfully")

    except Exception as e:
        logger.exception(f"Task {task_id} failed: {e}")

        # Update status with error
        try:
            with open(tasks_file) as f:
                tasks = json.load(f)
            if task_id in tasks:
                tasks[task_id].update(
                    {
                        "status": "failed",
                        "error": str(e),
                        "completed_at": datetime.now().isoformat(),
                    }
                )
                with open(tasks_file, "w") as f:
                    json.dump(tasks, f, indent=2)
        except:
            pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Internal task runner for Stravinsky background agents. "
        "Executes agent tasks via Claude CLI and manages output/status.",
        prog="task_runner",
    )
    parser.add_argument(
        "--task-id",
        required=True,
        help="Unique identifier for the task to execute",
    )
    parser.add_argument(
        "--base-dir",
        required=True,
        help="Base directory containing tasks.json and agents/ output folder",
    )
    args = parser.parse_args()

    asyncio.run(run_task(args.task_id, args.base_dir))
