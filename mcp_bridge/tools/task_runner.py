"""
Task Runner for Stravinsky background sub-agents.

This script is executed as a background process to handle agent tasks,
capture output, and update status in tasks.json.
"""

import argparse
import json
import logging
import os
import sys
import asyncio
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("task_runner")

async def run_task(task_id: str, base_dir: str):
    base_path = Path(base_dir)
    tasks_file = base_path / "tasks.json"
    agents_dir = base_path / "agents"
    
    # Load task details
    try:
        with open(tasks_file, "r") as f:
            tasks = json.load(f)
        task = tasks.get(task_id)
    except Exception as e:
        logger.error(f"Failed to load tasks: {e}")
        return

    if not task:
        logger.error(f"Task {task_id} not found")
        return

    prompt = task.get("prompt")
    model = task.get("model", "gemini-2.0-flash")
    
    output_file = agents_dir / f"{task_id}.out"
    agents_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Import model invocation
        from mcp_bridge.tools.model_invoke import invoke_gemini
        
        logger.info(f"Executing task {task_id} with model {model}...")
        
        # Execute the model call
        result = await invoke_gemini(prompt=prompt, model=model)
        
        # Save result
        with open(output_file, "w") as f:
            f.write(result)
            
        # Update status
        with open(tasks_file, "r") as f:
            tasks = json.load(f)
        
        if task_id in tasks:
            tasks[task_id].update({
                "status": "completed",
                "result": result,
                "completed_at": datetime.now().isoformat()
            })
            with open(tasks_file, "w") as f:
                json.dump(tasks, f, indent=2)
                
        logger.info(f"Task {task_id} completed successfully")
        
    except Exception as e:
        logger.exception(f"Task {task_id} failed: {e}")
        
        # Update status with error
        try:
            with open(tasks_file, "r") as f:
                tasks = json.load(f)
            if task_id in tasks:
                tasks[task_id].update({
                    "status": "failed",
                    "error": str(e),
                    "completed_at": datetime.now().isoformat()
                })
                with open(tasks_file, "w") as f:
                    json.dump(tasks, f, indent=2)
        except:
            pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--base-dir", required=True)
    args = parser.parse_args()
    
    asyncio.run(run_task(args.task_id, args.base_dir))
