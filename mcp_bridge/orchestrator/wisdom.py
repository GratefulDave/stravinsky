import os
from pathlib import Path

class WisdomLoader:
    def __init__(self, wisdom_path: str = ".stravinsky/wisdom.md"):
        self.wisdom_path = wisdom_path
        
    def load_wisdom(self) -> str:
        """Loads project wisdom/learnings."""
        if os.path.exists(self.wisdom_path):
            try:
                with open(self.wisdom_path, "r") as f:
                    return f.read()
            except Exception:
                return ""
        return ""

class CritiqueGenerator:
    def generate_critique_prompt(self, plan_content: str) -> str:
        """Generates a prompt for self-critique."""
        return f"""
You are currently in the CRITIQUE phase.
Review the following plan and identify potential weaknesses.

PLAN:
{plan_content}

INSTRUCTIONS:
1. List 3 ways this plan could fail (edge cases, race conditions, missing context).
2. Check if it violates any items in the 'Wisdom' file (if provided).
3. Propose specific improvements.

Respond with your critique.
"""
