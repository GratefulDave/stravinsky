"""
Native Search Wrapper - Optional Rust integration for performance.
"""

import os
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Attempt to import the native module
try:
    import stravinsky_native
    HAS_NATIVE = True
except ImportError:
    HAS_NATIVE = False
    logger.debug("stravinsky_native module not found. Falling back to CLI tools.")

def native_glob_files(pattern: str, directory: str = ".") -> Optional[List[str]]:
    """
    Find files matching a glob pattern using Rust implementation.
    """
    if not HAS_NATIVE:
        return None
    
    try:
        # Convert to absolute path for Rust
        abs_dir = os.path.abspath(directory)
        return stravinsky_native.glob_files(abs_dir, pattern)
    except Exception as e:
        logger.error(f"Native glob_files failed: {e}")
        return None

def native_grep_search(pattern: str, directory: str = ".", case_sensitive: bool = False) -> Optional[List[Dict[str, Any]]]:
    """
    Fast text search using Rust implementation.
    """
    if not HAS_NATIVE:
        return None
    
    try:
        abs_dir = os.path.abspath(directory)
        return stravinsky_native.grep_search(pattern, abs_dir, case_sensitive)
    except Exception as e:
        logger.error(f"Native grep_search failed: {e}")
        return None

def native_chunk_code(content: str, language: str) -> Optional[List[Dict[str, Any]]]:
    """
    AST-aware code chunking using Rust/tree-sitter.
    """
    if not HAS_NATIVE:
        return None
    
    try:
        return stravinsky_native.chunk_code(content, language)
    except Exception as e:
        logger.error(f"Native chunk_code failed: {e}")
        return None
