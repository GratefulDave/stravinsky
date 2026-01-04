"""
PreCompact Hook - Context Preservation Before Compaction.

Triggers before session compaction to preserve critical context
that should survive summarization. Uses Gemini for intelligent
context extraction and preservation.

Based on oh-my-opencode's pre-compact hook pattern.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Flag to prevent recursive calls during Gemini invocation
_in_preservation = False

# Critical context patterns to preserve
PRESERVE_PATTERNS = [
    # Architecture decisions
    "ARCHITECTURE:",
    "DESIGN DECISION:",
    "## Architecture",

    # Important constraints
    "CONSTRAINT:",
    "REQUIREMENT:",
    "MUST NOT:",
    "NEVER:",

    # Session state
    "CURRENT TASK:",
    "BLOCKED BY:",
    "WAITING FOR:",

    # Critical errors
    "CRITICAL ERROR:",
    "SECURITY ISSUE:",
    "BREAKING CHANGE:",
]

# Memory anchors to inject into compaction
MEMORY_ANCHORS: List[str] = []


def register_memory_anchor(anchor: str, priority: str = "normal"):
    """
    Register a memory anchor to preserve during compaction.

    Args:
        anchor: The text to preserve
        priority: "critical" or "normal"
    """
    if priority == "critical":
        MEMORY_ANCHORS.insert(0, f"[CRITICAL] {anchor}")
    else:
        MEMORY_ANCHORS.append(anchor)

    # Limit to 10 anchors to prevent bloat
    while len(MEMORY_ANCHORS) > 10:
        MEMORY_ANCHORS.pop()


def clear_memory_anchors():
    """Clear all registered memory anchors."""
    MEMORY_ANCHORS.clear()


async def pre_compact_hook(params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Pre-model-invoke hook that runs before context compaction.

    Uses Gemini to intelligently extract and preserve critical context
    that should survive summarization.
    """
    global _in_preservation

    # Prevent recursive calls
    if _in_preservation:
        return None

    prompt = params.get("prompt", "")

    # Only activate for compaction-related prompts
    if not _is_compaction_prompt(prompt):
        return None

    # Collect pattern-matched context
    preserved_context = _extract_preserved_context(prompt)
    preserved_context.extend(MEMORY_ANCHORS)

    # Use Gemini for intelligent context extraction if prompt is long
    if len(prompt) > 50000:
        try:
            _in_preservation = True
            gemini_context = await _extract_context_with_gemini(prompt)
            if gemini_context:
                preserved_context.extend(gemini_context)
        except Exception as e:
            logger.warning(f"[PreCompactHook] Gemini extraction failed: {e}")
        finally:
            _in_preservation = False

    if not preserved_context:
        return None

    # Build preservation section
    preservation_section = _build_preservation_section(preserved_context)

    logger.info(f"[PreCompactHook] Preserving {len(preserved_context)} context items")

    # Inject into prompt
    modified_prompt = prompt + "\n\n" + preservation_section

    return {**params, "prompt": modified_prompt}


async def _extract_context_with_gemini(prompt: str) -> List[str]:
    """
    Use Gemini to intelligently extract critical context to preserve.

    Args:
        prompt: The full conversation/context to analyze

    Returns:
        List of critical context items to preserve
    """
    try:
        from ..tools.model_invoke import invoke_gemini_impl

        # Truncate prompt if too long for Gemini
        max_chars = 100000
        truncated = prompt[:max_chars] if len(prompt) > max_chars else prompt

        extraction_prompt = f"""Analyze this conversation and extract ONLY the most critical information that MUST be preserved during summarization.

Focus on:
1. Architecture decisions and their rationale
2. Critical constraints or requirements
3. Important error patterns or debugging insights
4. Key file paths and their purposes
5. Unfinished tasks or blocking issues

Return a bullet list of critical items (max 10). Be extremely concise.

CONVERSATION:
{truncated}

CRITICAL ITEMS TO PRESERVE:"""

        result = await invoke_gemini_impl(
            prompt=extraction_prompt,
            model="gemini-3-flash",
            max_tokens=2000,
            temperature=0.1,
        )

        if not result:
            return []

        # Parse bullet points from response
        lines = result.strip().split("\n")
        items = []
        for line in lines:
            line = line.strip()
            if line.startswith(("-", "*", "•")) or (len(line) > 1 and line[0].isdigit() and line[1] in ".):"):
                # Clean up the bullet
                item = line.lstrip("-*•0123456789.): ").strip()
                if item and len(item) > 10:
                    items.append(item)

        return items[:10]  # Max 10 items

    except Exception as e:
        logger.warning(f"[PreCompactHook] Gemini context extraction error: {e}")
        return []


def _is_compaction_prompt(prompt: str) -> bool:
    """Detect if this is a compaction/summarization prompt."""
    compaction_signals = [
        "summarize the conversation",
        "compact the context",
        "reduce context size",
        "context window",
        "summarization",
    ]

    prompt_lower = prompt.lower()
    return any(signal in prompt_lower for signal in compaction_signals)


def _extract_preserved_context(prompt: str) -> List[str]:
    """Extract context matching preservation patterns."""
    preserved = []
    lines = prompt.split("\n")

    for i, line in enumerate(lines):
        for pattern in PRESERVE_PATTERNS:
            if pattern in line:
                # Capture the line and next 2 lines for context
                context_lines = lines[i:i+3]
                preserved.append("\n".join(context_lines))
                break

    return preserved


def _build_preservation_section(context_items: List[str]) -> str:
    """Build the preservation section to inject."""
    section = """
## CRITICAL CONTEXT TO PRESERVE

The following information MUST be preserved in any summarization:

"""
    for i, item in enumerate(context_items, 1):
        section += f"{i}. {item}\n\n"

    section += """
When summarizing, ensure these items are included verbatim or with minimal paraphrasing.
"""
    return section
