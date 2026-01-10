"""
Directory context injector hook.
Automatically finds and injects local AGENTS.md or README.md content based on the current context.
"""

from pathlib import Path
from typing import Any


async def directory_context_hook(params: dict[str, Any]) -> dict[str, Any] | None:
    """
    Search for AGENTS.md or README.md in the current working directory and inject them.
    """
    cwd = Path.cwd()
    
    # Check for AGENTS.md or README.md
    target_files = ["AGENTS.md", "README.md"]
    found_file = None
    for filename in target_files:
        if (cwd / filename).exists():
            found_file = cwd / filename
            break
            
    if not found_file:
        return None
        
    try:
        content = found_file.read_text()
        # Injects as a special system reminder
        injection = f"\n\n### Local Directory Context ({found_file.name}):\n{content}\n"
        
        # Modify the prompt if it exists in params
        if "prompt" in params:
            # Add to the beginning of the prompt as a context block
            params["prompt"] = injection + params["prompt"]
            return params
    except Exception:
        pass
        
    return None
