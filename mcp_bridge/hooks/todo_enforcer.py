"""
Todo Continuation Enforcer Hook.

Prevents early stopping when pending todos exist.
Injects a system reminder forcing the agent to complete all todos.
Includes evidence extraction and verification to prevent vague completion claims.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

TODO_CONTINUATION_REMINDER = """
[SYSTEM REMINDER - TODO CONTINUATION & VERIFICATION]

You have pending todos that are NOT yet completed. You MUST continue working.

**Pending Todos:**
{pending_todos}

**CRITICAL RULES:**
1. You CANNOT mark a todo completed without CONCRETE EVIDENCE
2. Evidence = file paths with line numbers (e.g., src/auth.ts:45-67) or tool output
3. Vague claims like "I created the file" will be REJECTED
4. Each completed todo MUST include: `✅ [Todo] - Evidence: path/to/file.py:123`
5. If you cannot provide evidence, the todo is NOT complete - keep working
6. Use Read tool to verify file contents before claiming completion

**Example GOOD completion:**
✅ Create auth validation → Evidence: src/auth.ts:45-67 (validateJWT function implemented)

**Example BAD completion (will be REJECTED):**
✅ Create auth validation → I created the validation logic

{verification_failures}

CONTINUE WORKING NOW with evidence-backed completions.
"""


async def todo_continuation_hook(params: dict[str, Any]) -> dict[str, Any] | None:
    """
    Pre-model invoke hook that checks for pending todos.

    If pending todos exist, injects a reminder into the prompt
    forcing the agent to continue working.

    Also extracts evidence from agent output and verifies claims.
    """
    prompt = params.get("prompt", "")

    # Extract pending todos
    pending_todos = _extract_pending_todos(prompt)

    # Extract verification failures from previous output (if any)
    verification_failures = ""
    skip_verification = params.get("skip_verification", False)

    if not skip_verification:
        # Check if there's recent output to verify
        # This would come from previous agent turns
        previous_output = params.get("previous_output", "")
        if previous_output:
            verification_failures = _verify_agent_claims(previous_output)

    if pending_todos:
        logger.info(
            f"[TodoEnforcer] Found {len(pending_todos)} pending todos, injecting continuation reminder"
        )

        todos_formatted = "\n".join(f"- [ ] {todo}" for todo in pending_todos)

        # Format verification failures if any
        failures_text = ""
        if verification_failures:
            failures_text = f"\n\n⚠️ VERIFICATION FAILURES FROM PREVIOUS TURN:\n{verification_failures}\n"

        reminder = TODO_CONTINUATION_REMINDER.format(
            pending_todos=todos_formatted,
            verification_failures=failures_text
        )

        modified_prompt = prompt + "\n\n" + reminder
        params["prompt"] = modified_prompt

        return params

    return None


def _extract_pending_todos(prompt: str) -> list:
    """
    Extract pending todos from the prompt/context.
    Looks for common todo patterns.
    """
    pending = []
    lines = prompt.split("\n")

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- [ ]") or stripped.startswith("* [ ]"):
            todo_text = stripped[5:].strip()
            if todo_text:
                pending.append(todo_text)
        elif '"status": "pending"' in stripped or '"status": "in_progress"' in stripped:
            pass

    return pending


def _extract_evidence(output: str) -> dict[str, list[str]]:
    """
    Extract evidence references (file paths, URLs) from agent output.

    Returns:
        Dict with keys: 'files', 'urls', 'commands'
    """
    evidence = {
        "files": [],
        "urls": [],
        "commands": []
    }

    # File path pattern: src/auth.ts:45 or /path/to/file.py or path/file.js:10-20
    # Matches common file extensions and optional line numbers
    file_pattern = r'(?:^|[\s\(\[])([\w/\._-]+\.(?:py|ts|js|tsx|jsx|go|rs|java|c|cpp|h|hpp|md|json|yaml|yml|toml|sh|rb|php|swift|kt))(?::(\d+)(?:-(\d+))?)?'

    for match in re.finditer(file_pattern, output, re.MULTILINE):
        file_path = match.group(1)
        line_start = match.group(2)
        line_end = match.group(3)

        # Build reference string
        if line_start:
            if line_end:
                ref = f"{file_path}:{line_start}-{line_end}"
            else:
                ref = f"{file_path}:{line_start}"
        else:
            ref = file_path

        evidence["files"].append(ref)

    # URL pattern
    url_pattern = r'https?://[^\s\)\]>]+'
    evidence["urls"] = re.findall(url_pattern, output)

    # Command/tool usage pattern (e.g., "Used Read tool", "Ran grep")
    command_pattern = r'(?:Used|Ran|Called|Executed)\s+(\w+(?:\s+\w+)?)\s+(?:tool|command)'
    evidence["commands"] = re.findall(command_pattern, output, re.IGNORECASE)

    return evidence


def _verify_file_claim(claim: str, file_references: list[str]) -> dict[str, Any]:
    """
    Verify a completion claim has file evidence.

    This is a synchronous check - actual file existence verification
    would require async Read tool access (not available in hooks).

    Returns:
        Dict with 'verified' (bool) and 'reason' (str)
    """
    # Check if claim has any file references
    if not file_references:
        return {
            "verified": False,
            "reason": "No file paths provided as evidence"
        }

    # Check for vague language that indicates lack of actual work
    vague_patterns = [
        r'\bI\s+(?:created|made|wrote|added|implemented)\b',  # "I created..."
        r'\b(?:should|will|would)\s+(?:create|add|implement)\b',  # Future tense
        r'\b(?:basically|essentially|just|simply)\b',  # Minimizing language
    ]

    claim_lower = claim.lower()
    vague_count = sum(1 for pattern in vague_patterns if re.search(pattern, claim_lower))

    if vague_count >= 2:
        return {
            "verified": False,
            "reason": f"Claim uses vague language without concrete evidence. Files mentioned: {', '.join(file_references[:3])}"
        }

    # If we have file references and no vague language, consider it verified
    # (Actual file content verification would happen in a post-hook with Read access)
    return {
        "verified": True,
        "reason": f"Evidence provided: {', '.join(file_references[:3])}"
    }


def _verify_agent_claims(output: str) -> str:
    """
    Verify agent claims against actual evidence.

    Extracts completion claims and checks for concrete evidence.

    Returns:
        Formatted string of verification failures (empty if all verified)
    """
    # Extract evidence from output
    evidence = _extract_evidence(output)

    # Look for completion claims (✅, "completed", "done", etc.)
    completion_patterns = [
        r'✅\s+(.+?)(?:\n|$)',  # Checkmark pattern
        r'(?:Completed|Finished|Done):\s*(.+?)(?:\n|$)',  # Explicit completion
        r'"status":\s*"completed".*?"content":\s*"(.+?)"',  # JSON todo format
    ]

    claims = []
    for pattern in completion_patterns:
        matches = re.finditer(pattern, output, re.IGNORECASE | re.DOTALL)
        for match in matches:
            claim_text = match.group(1).strip()
            if claim_text:
                claims.append(claim_text)

    if not claims:
        # No completion claims found, nothing to verify
        return ""

    # Verify each claim
    failures = []
    for claim in claims:
        verification = _verify_file_claim(claim, evidence["files"])
        if not verification["verified"]:
            failures.append(f"- {claim[:100]}... → {verification['reason']}")

    if failures:
        return "\n".join([
            "The following completion claims lack concrete evidence:",
            *failures,
            "",
            "REQUIRED: Provide file paths with line numbers (e.g., src/auth.ts:45-67)",
            "Use the Read tool to verify files exist before claiming completion."
        ])

    return ""
