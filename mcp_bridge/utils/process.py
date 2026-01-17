import asyncio
import os
from dataclasses import dataclass
from typing import Optional, List, Union

@dataclass
class ProcessResult:
    returncode: int
    stdout: str
    stderr: str

async def async_execute(
    cmd: Union[str, List[str]], 
    cwd: Optional[str] = None, 
    timeout: Optional[float] = None
) -> ProcessResult:
    """
    Execute a subprocess asynchronously.
    
    Args:
        cmd: Command string or list of arguments.
        cwd: Working directory.
        timeout: Maximum execution time in seconds.
        
    Returns:
        ProcessResult containing exit code, stdout, and stderr.
        
    Raises:
        asyncio.TimeoutError: If the process exceeds the timeout.
    """
    if isinstance(cmd, str):
        # Use shell wrapper for string commands
        process = await asyncio.create_subprocess_exec(
            "bash", "-c", cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd
        )
    else:
        # Use direct execution for list of arguments
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd
        )
    
    try:
        if timeout:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout=timeout)
        else:
            stdout_bytes, stderr_bytes = await process.communicate()
            
    except asyncio.TimeoutError:
        try:
            # Kill process group if started with bash
            if isinstance(cmd, str):
                process.kill()
            else:
                process.kill()
        except ProcessLookupError:
            pass # Already gone
        # Wait for it to actually die to avoid zombies
        await process.wait()
        raise
        
    return ProcessResult(
        returncode=process.returncode if process.returncode is not None else 0,
        stdout=stdout_bytes.decode('utf-8', errors='replace'),
        stderr=stderr_bytes.decode('utf-8', errors='replace')
    )