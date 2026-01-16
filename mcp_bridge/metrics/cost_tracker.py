import json
import time
import os
from pathlib import Path
from dataclasses import dataclass, asdict
import threading
import logging

logger = logging.getLogger(__name__)

# Approximate costs per 1M tokens (Input/Output)
MODEL_COSTS = {
    "gemini-3-flash": (0.075, 0.30),
    "gemini-3-pro": (1.25, 5.00),
    "gpt-5.2-codex": (2.50, 10.00), # Estimated based on GPT-4o
    "gpt-4o": (2.50, 10.00),
    "claude-3-5-sonnet": (3.00, 15.00),
    "claude-3-5-haiku": (0.25, 1.25),
}

@dataclass
class CostRecord:
    timestamp: float
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    agent_type: str
    task_id: str
    session_id: str

class CostTracker:
    _instance = None
    _lock = threading.Lock()
    
    def __init__(self):
        self.file_path = Path.home() / ".stravinsky" / "usage.jsonl"
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        # Default to Flash pricing if unknown
        input_price, output_price = MODEL_COSTS.get(model, MODEL_COSTS["gemini-3-flash"])
        return (input_tokens / 1_000_000 * input_price) + (output_tokens / 1_000_000 * output_price)

    def track_usage(self, model: str, input_tokens: int, output_tokens: int, agent_type: str = "unknown", task_id: str = ""):
        cost = self.calculate_cost(model, input_tokens, output_tokens)
        session_id = os.environ.get("CLAUDE_SESSION_ID", "default")
        
        record = CostRecord(
            timestamp=time.time(),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            agent_type=agent_type,
            task_id=task_id,
            session_id=session_id
        )
        
        try:
            with open(self.file_path, "a") as f:
                f.write(json.dumps(asdict(record)) + "\n")
        except Exception as e:
            logger.error(f"Failed to write usage record: {e}")

    def get_session_summary(self, session_id: str = None) -> dict:
        if session_id is None:
            session_id = os.environ.get("CLAUDE_SESSION_ID", "default")
            
        total_cost = 0.0
        total_tokens = 0
        by_agent = {}
        
        if not self.file_path.exists():
            return {"total_cost": 0.0, "total_tokens": 0, "by_agent": {}}
            
        try:
            with open(self.file_path, "r") as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        if data.get("session_id") == session_id:
                            cost = data.get("cost", 0.0)
                            tokens = data.get("input_tokens", 0) + data.get("output_tokens", 0)
                            agent = data.get("agent_type", "unknown")
                            
                            total_cost += cost
                            total_tokens += tokens
                            
                            if agent not in by_agent:
                                by_agent[agent] = {"cost": 0.0, "tokens": 0}
                            by_agent[agent]["cost"] += cost
                            by_agent[agent]["tokens"] += tokens
                            
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error(f"Failed to read usage records: {e}")
            
        return {
            "total_cost": total_cost,
            "total_tokens": total_tokens,
            "by_agent": by_agent
        }

def get_cost_tracker():
    return CostTracker.get_instance()
