import pytest
import time
from mcp_bridge.utils.cache import IOCache

def test_cache_set_get():
    cache = IOCache(ttl=5)
    cache.set("test_key", "test_value")
    assert cache.get("test_key") == "test_value"

def test_cache_expiration():
    # Use 0.1s TTL for fast testing
    cache = IOCache(ttl=0.1)
    cache.set("expire_key", "value")
    assert cache.get("expire_key") == "value"
    
    time.sleep(0.2)
    assert cache.get("expire_key") is None

def test_cache_invalidation():
    cache = IOCache(ttl=10)
    cache.set("/path/to/file", "content")
    assert cache.get("/path/to/file") == "content"
    
    cache.invalidate("/path/to/file")
    assert cache.get("/path/to/file") is None

def test_cache_singleton():
    cache1 = IOCache.get_instance()
    cache2 = IOCache.get_instance()
    assert cache1 is cache2
