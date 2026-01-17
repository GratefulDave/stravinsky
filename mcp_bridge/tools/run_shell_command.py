import os
from mcp_bridge.utils.cache import IOCache
from mcp_bridge.utils.process import async_execute

async def run_shell_command(command: str, description: str, dir_path: str = ".") -> str:
    """
    Execute a shell command and invalidate cache if it looks like a write.
    """
    # USER-VISIBLE NOTIFICATION
    import sys
    print(f"🐚 BASH: {command} ({description})", file=sys.stderr)

    try:
        # Run command asynchronously
        result = await async_execute(command, cwd=dir_path, timeout=300)
        
        # Check if it looks like a write command (simplistic heuristic)
        write_keywords = ["git commit", "git push", "rm ", "mv ", "cp ", "touch ", "> ", ">> ", "sed ", "chmod "]
        is_write = any(kw in command for kw in write_keywords)
        
        if is_write:
            # Broad invalidation for write commands
            cache = IOCache.get_instance()
            # If we're in a specific dir, invalidate that dir
            cache.invalidate_path(os.path.abspath(dir_path))
            
        # Format output
        output = []
        output.append(f"Command: {command}")
        output.append(f"Directory: {dir_path}")
        output.append(f"Stdout: {result.stdout}")
        output.append(f"Stderr: {result.stderr}")
        output.append(f"Exit Code: {result.returncode}")
        
        return "\n".join(output)

    except Exception as e:
        return f"Error executing command: {str(e)}"