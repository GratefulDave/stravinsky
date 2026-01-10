"""
Thinking budget optimizer hook.
Analyzes prompt complexity and adjusts thinking_budget for models that support it.
"""

from typing import Any

REASONING_KEYWORDS = [
    "architect", "design", "refactor", "debug", "complex", "optimize", 
    "summarize", "analyze", "explain", "why", "review", "strangler"
]

async def budget_optimizer_hook(params: dict[str, Any]) -> dict[str, Any] | None:
    """
    Adjusts the thinking_budget based on presence of reasoning-heavy keywords.
    """
    model = params.get("model", "")
    # Only applies to models that typically support reasoning budgets (Gemini 2.0 Thinking, GPT-o1, etc.)
    if not any(m in model for m in ["thinking", "flash-thinking", "o1", "o3"]):
        return None
        
    prompt = params.get("prompt", "").lower()
    
    # Simple heuristic
    is_complex = any(keyword in prompt for keyword in REASONING_KEYWORDS)
    
    current_budget = params.get("thinking_budget", 0)
    
    if is_complex and current_budget < 4000:
        # Increase budget for complex tasks
        params["thinking_budget"] = 16000
        return params
    elif not is_complex and current_budget > 2000:
        # Lower budget for simple tasks to save time/cost
        params["thinking_budget"] = 2000
        return params
        
    return None
