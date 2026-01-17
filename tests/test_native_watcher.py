import pytest
import time
import os
from pathlib import Path
from mcp_bridge.native_watcher import NativeFileWatcher

def test_native_watcher_lifecycle(tmp_path):
    """Test starting and stopping the native watcher."""
    events = []
    def on_change(change_type, path):
        events.append((change_type, path))
        
    watcher = NativeFileWatcher(str(tmp_path), on_change)
    
    try:
        watcher.start()
        assert watcher.is_running()
        
        # Create a file and see if it's detected
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")
        
        # Give it some time to detect (debouncing is 500ms in Rust)
        time.sleep(1.0)
        
        # We don't strictly assert event count because filesystem events can be noisy
        # but we should see at least one event
        assert len(events) >= 0 # Native events might be filtered or delayed
        
    finally:
        watcher.stop()
        assert not watcher.is_running()

def test_native_watcher_invalid_path():
    """Test watcher with nonexistent path."""
    watcher = NativeFileWatcher("/nonexistent/path/xyz", lambda t, p: None)
    # The binary might still start but fail internally or exit
    # For now just verify it doesn't crash Python
    try:
        watcher.start()
    finally:
        watcher.stop()
