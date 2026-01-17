import time
import os
import threading
from typing import Any, Dict, Optional, Tuple

class IOCache:
    """
    Lightweight, thread-safe in-memory cache for I/O operations.
    Supports TTL-based expiration and manual invalidation.
    """
    _instance = None
    _lock = threading.Lock()

    def __init__(self, ttl: float = 5.0):
        self.ttl = ttl
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._cache_lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        """Get the singleton instance of IOCache."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """
        Store a value in the cache.
        
        Args:
            key: Cache key (e.g., file path or command).
            value: Data to cache.
            ttl: Optional override for the default TTL.
        """
        expiry = time.time() + (ttl if ttl is not None else self.ttl)
        with self._cache_lock:
            self._cache[key] = (value, expiry)

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a value from the cache if it hasn't expired.
        
        Returns:
            The cached value, or None if missing or expired.
        """
        with self._cache_lock:
            if key not in self._cache:
                return None
            
            value, expiry = self._cache[key]
            if time.time() > expiry:
                del self._cache[key]
                return None
            
            return value

    def invalidate(self, key: str) -> None:
        """Remove a specific key from the cache."""
        with self._cache_lock:
            if key in self._cache:
                del self._cache[key]

    def invalidate_path(self, path: str) -> None:
        """
        Invalidate all cache entries related to a specific file path.
        Matches keys for read_file, list_dir, etc.
        """
        # Use realpath to resolve symlinks (crucial for macOS /var -> /private/var)
        abs_path = os.path.realpath(path)
        with self._cache_lock:
            keys_to_del = [
                k for k in self._cache.keys() 
                if abs_path in k
            ]
            for k in keys_to_del:
                del self._cache[k]

    def clear(self) -> None:
        """Clear all cached entries."""
        with self._cache_lock:
            self._cache.clear()