import asyncio
import json
import logging
import os
import socket
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

SOCKET_PATH = "/tmp/stravinsky.sock"

@dataclass
class LogMessage:
    agent_id: str
    type: str  # stdout, stderr, event, lifecycle
    content: str
    timestamp: str

class MuxClient:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self._socket: socket.socket | None = None
        self._connected = False

    def connect(self):
        try:
            if not os.path.exists(SOCKET_PATH):
                return
            
            self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self._socket.connect(SOCKET_PATH)
            self._socket.setblocking(False)
            self._connected = True
        except Exception as e:
            logger.debug(f"Failed to connect to mux: {e}")
            self._connected = False

    def log(self, content: str, stream: str = "stdout"):
        if not self._connected:
            self.connect()
        
        if not self._connected or not self._socket:
            return

        msg = LogMessage(
            agent_id=self.agent_id,
            type=stream,
            content=content,
            timestamp=datetime.now().isoformat()
        )
        
        try:
            data = json.dumps(asdict(msg)) + "\n"
            self._socket.sendall(data.encode('utf-8'))
        except (BrokenPipeError, OSError):
            self._connected = False
            self._socket.close()
            self._socket = None

    def close(self):
        if self._socket:
            self._socket.close()
            self._connected = False

# Global instance for the main process
_global_mux: MuxClient | None = None

def get_mux(agent_id: str = "main") -> MuxClient:
    global _global_mux
    if _global_mux is None:
        _global_mux = MuxClient(agent_id)
    return _global_mux
