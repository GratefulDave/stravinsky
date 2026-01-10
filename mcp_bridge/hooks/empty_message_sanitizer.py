"""
Empty Message Sanitizer Hook.

Cleans up empty/malformed messages:
- Detects empty content in messages
- Replaces with placeholder or removes
- Prevents API errors from empty content
- Registered as pre_model_invoke hook
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Patterns that indicate effectively empty content
EMPTY_PATTERNS = [
    r'^\s*$',  # Whitespace only
    r'^[\n\r]+$',  # Newlines only
    r'^[\t ]+$',  # Tabs/spaces only
    r'^\s*null\s*$',  # Null string
    r'^\s*undefined\s*$',  # Undefined string
    r'^\s*None\s*$',  # Python None as string
]

# Patterns for malformed JSON-like content
MALFORMED_PATTERNS = [
    r'^\s*\{\s*\}\s*$',  # Empty JSON object
    r'^\s*\[\s*\]\s*$',  # Empty JSON array
    r'^\s*""\s*$',  # Empty quoted string
    r"^\s*''\s*$",  # Empty single-quoted string
]

# Characters that might corrupt the prompt
DANGEROUS_PATTERNS = [
    r'\x00',  # Null byte
    r'[\x01-\x08]',  # Control characters
    r'[\x0b\x0c]',  # Vertical tab, form feed
    r'[\x0e-\x1f]',  # More control characters
    r'\x7f',  # DEL character
]

PLACEHOLDER_MESSAGE = "[Content sanitized - empty or malformed input detected]"

SANITIZATION_NOTICE = """
> **[MESSAGE SANITIZATION]**
> {count} empty or malformed message segment(s) were detected and sanitized.
> This prevents API errors and ensures proper message processing.
"""


def is_empty_or_malformed(content: str) -> bool:
    """
    Check if content is empty or malformed.

    Args:
        content: The content string to check

    Returns:
        True if content is empty or malformed
    """
    if content is None:
        return True

    if not isinstance(content, str):
        # Try to convert to string
        try:
            content = str(content)
        except:
            return True

    # Check empty patterns
    for pattern in EMPTY_PATTERNS:
        if re.match(pattern, content, re.IGNORECASE):
            return True

    # Check malformed patterns
    for pattern in MALFORMED_PATTERNS:
        if re.match(pattern, content, re.IGNORECASE):
            return True

    return False


def contains_dangerous_characters(content: str) -> bool:
    """
    Check if content contains potentially dangerous control characters.

    Args:
        content: The content string to check

    Returns:
        True if dangerous characters are found
    """
    if not isinstance(content, str):
        return False

    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, content):
            return True

    return False


def sanitize_content(content: str) -> str:
    """
    Sanitize content by removing dangerous characters.

    Args:
        content: The content to sanitize

    Returns:
        Sanitized content
    """
    if not isinstance(content, str):
        try:
            content = str(content)
        except:
            return PLACEHOLDER_MESSAGE

    # Remove dangerous characters
    sanitized = content
    for pattern in DANGEROUS_PATTERNS:
        sanitized = re.sub(pattern, '', sanitized)

    # If result is empty after sanitization, use placeholder
    if is_empty_or_malformed(sanitized):
        return PLACEHOLDER_MESSAGE

    return sanitized


def sanitize_message_blocks(prompt: str) -> tuple[str, int]:
    """
    Scan prompt for message blocks and sanitize empty ones.

    This handles common message formats in prompts:
    - user: content
    - assistant: content
    - system: content
    - <role>content</role>

    Args:
        prompt: The full prompt text

    Returns:
        Tuple of (sanitized prompt, count of sanitized blocks)
    """
    sanitized_count = 0

    # Pattern for role-prefixed messages (user:, assistant:, system:)
    role_pattern = re.compile(
        r'((?:user|assistant|system|human|ai):\s*)([\n\r]+|$)',
        re.IGNORECASE | re.MULTILINE
    )

    def replace_empty_role(match):
        nonlocal sanitized_count
        sanitized_count += 1
        role = match.group(1)
        return f"{role}{PLACEHOLDER_MESSAGE}\n"

    prompt = role_pattern.sub(replace_empty_role, prompt)

    # Pattern for XML-style message tags
    xml_pattern = re.compile(
        r'(<(?:user|assistant|system|human|ai)>)\s*(</\1>)',
        re.IGNORECASE
    )

    def replace_empty_xml(match):
        nonlocal sanitized_count
        sanitized_count += 1
        open_tag = match.group(1)
        close_tag = match.group(2)
        return f"{open_tag}{PLACEHOLDER_MESSAGE}{close_tag}"

    prompt = xml_pattern.sub(replace_empty_xml, prompt)

    return prompt, sanitized_count


async def empty_message_sanitizer_hook(params: dict[str, Any]) -> dict[str, Any] | None:
    """
    Pre-model invoke hook that sanitizes empty and malformed message content.

    Scans the prompt for:
    - Empty message blocks
    - Malformed content patterns
    - Dangerous control characters

    And sanitizes them to prevent API errors.
    """
    prompt = params.get("prompt", "")

    # Skip if already sanitized
    if "[MESSAGE SANITIZATION]" in prompt:
        return None

    # Skip if prompt is valid and not empty
    if not prompt or not isinstance(prompt, str):
        logger.warning("[EmptyMessageSanitizer] Empty or invalid prompt detected")
        params["prompt"] = PLACEHOLDER_MESSAGE
        return params

    modifications_made = False
    sanitized_count = 0

    # Check for dangerous characters in the entire prompt
    if contains_dangerous_characters(prompt):
        prompt = sanitize_content(prompt)
        modifications_made = True
        sanitized_count += 1
        logger.info("[EmptyMessageSanitizer] Removed dangerous control characters")

    # Sanitize empty message blocks
    prompt, block_count = sanitize_message_blocks(prompt)
    if block_count > 0:
        sanitized_count += block_count
        modifications_made = True
        logger.info(f"[EmptyMessageSanitizer] Sanitized {block_count} empty message blocks")

    # Check if the entire prompt is effectively empty
    if is_empty_or_malformed(prompt):
        prompt = PLACEHOLDER_MESSAGE
        sanitized_count += 1
        modifications_made = True
        logger.warning("[EmptyMessageSanitizer] Entire prompt was empty/malformed")

    if not modifications_made:
        return None

    # Add sanitization notice if modifications were made
    notice = SANITIZATION_NOTICE.format(count=sanitized_count)
    params["prompt"] = notice + prompt

    logger.info(f"[EmptyMessageSanitizer] Applied {sanitized_count} sanitization(s)")

    return params
