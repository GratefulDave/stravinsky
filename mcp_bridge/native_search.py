"""
Native Search Wrapper - Optional Rust integration for performance.
"""

import os
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Attempt to import the native module
try:
    import stravinsky_native
    HAS_NATIVE = True
except ImportError:
    HAS_NATIVE = False
    logger.debug("stravinsky_native module not found. Falling back to CLI tools.")

_executor: Optional[ThreadPoolExecutor] = None

def get_executor() -> ThreadPoolExecutor:
    """Get the singleton thread pool executor."""
    global _executor
    if _executor is None:
        # Limit worker threads to avoid overwhelming the system
        _executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="native_ffi")
    return _executor

async def native_glob_files(pattern: str, directory: str = ".") -> Optional[List[str]]:
    """
    Find files matching a glob pattern using Rust implementation.
    """
    if not HAS_NATIVE:
        return None
    
    try:
        # Convert to absolute path for Rust
        abs_dir = os.path.abspath(directory)
        loop = asyncio.get_running_loop()
        
        # Offload blocking FFI call to thread pool
        return await loop.run_in_executor(
            get_executor(), 
            stravinsky_native.glob_files, 
            abs_dir, 
            pattern
        )
    except Exception as e:
        logger.error(f"Native glob_files failed: {e}")
        return None

async def native_grep_search(pattern: str, directory: str = ".", case_sensitive: bool = False) -> Optional[List[Dict[str, Any]]]:
    """
    Fast text search using Rust implementation.
    """
    if not HAS_NATIVE:
        return None
    
    try:
        abs_dir = os.path.abspath(directory)
        loop = asyncio.get_running_loop()
        
        return await loop.run_in_executor(
            get_executor(),
            stravinsky_native.grep_search,
            pattern,
            abs_dir,
            case_sensitive
        )
    except Exception as e:
        logger.error(f"Native grep_search failed: {e}")
        return None

async def native_chunk_code(content: str, language: str) -> Optional[List[Dict[str, Any]]]:
    """
    AST-aware code chunking using Rust/tree-sitter.
    """
    if not HAS_NATIVE:
        return None
    
    try:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            get_executor(),
            stravinsky_native.chunk_code,
            content,
            language
        )
    except Exception as e:
        logger.error(f"Native chunk_code failed: {e}")
        return None