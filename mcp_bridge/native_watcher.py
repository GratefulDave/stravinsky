"""
Native Watcher Integration - Rust-based file watching.
"""

import asyncio
import json
import logging
import os
import subprocess
import threading
from pathlib import Path
from typing import Optional, Callable

logger = logging.getLogger(__name__)

class NativeFileWatcher:
    """
    Python wrapper for the Rust-based stravinsky_watcher binary.
    """
    def __init__(self, project_path: str, on_change: Callable[[str, str], None]):
        self.project_path = os.path.abspath(project_path)
        self.on_change = on_change
        self.process: Optional[subprocess.Popen] = None
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def _get_binary_path(self) -> Path:
        """Find the stravinsky_watcher binary."""
        # Try relative to this file
        root_dir = Path(__file__).parent.parent
        candidates = [
            root_dir / "rust_native" / "target" / "release" / "stravinsky_watcher",
            root_dir / "rust_native" / "target" / "debug" / "stravinsky_watcher",
        ]
        
        for c in candidates:
            if c.exists():
                return c
        
        raise FileNotFoundError("stravinsky_watcher binary not found. Build it with cargo first.")

    def start(self):
        """Start the native watcher process in a background thread."""
        if self.process:
            return

        binary_path = self._get_binary_path()
        logger.info(f"Starting native watcher: {binary_path} {self.project_path}")
        
        self.process = subprocess.Popen(
            [str(binary_path), self.project_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        self._thread = threading.Thread(target=self._read_stdout, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the native watcher process."""
        self._stop_event.set()
        
        if self.process:
            logger.info(f"Stopping native watcher process (PID: {self.process.pid})")
            # Try to terminate gracefully first
            self.process.terminate()
            try:
                self.process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                logger.warning(f"Native watcher (PID: {self.process.pid}) did not terminate, killing...")
                self.process.kill()
                try:
                    self.process.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    logger.error(f"Failed to kill native watcher (PID: {self.process.pid})")
            
            # Close streams
            if self.process.stdout:
                self.process.stdout.close()
            if self.process.stderr:
                self.process.stderr.close()
                
            self.process = None
            
        # Wait for reader thread to exit
        if self._thread and self._thread.is_alive():
            # Don't join with timeout in main thread if it might block,
            # but since we closed stdout, the reader loop should break.
            self._thread.join(timeout=1.0)
            if self._thread.is_alive():
                logger.warning("Native watcher reader thread did not exit cleanly")
            self._thread = None

    def _read_stdout(self):
        """Read JSON events from the watcher's stdout."""
        if not self.process or not self.process.stdout:
            return

        for line in self.process.stdout:
            if self._stop_event.is_set():
                break
            
            line = line.strip()
            if not line or not line.startswith("{"):
                continue

            try:
                event = json.loads(line)
                change_type = event.get("type", "unknown")
                path = event.get("path", "")
                self.on_change(change_type, path)
            except json.JSONDecodeError:
                logger.error(f"Failed to decode watcher event: {line}")

    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None
