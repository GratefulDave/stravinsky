"""
Background Token Refresh Scheduler

Proactively refreshes OAuth tokens before they expire:
- Gemini: Refreshes when 30 minutes remaining (tokens expire in ~1 hour)
- OpenAI: Refreshes when 12 hours remaining (tokens expire in ~24 hours)
"""

import asyncio
import logging
import time
from typing import TYPE_CHECKING

from .oauth import refresh_access_token as gemini_refresh
from .openai_oauth import refresh_access_token as openai_refresh

if TYPE_CHECKING:
    from .token_store import TokenStore

logger = logging.getLogger(__name__)

# Refresh configuration per provider
REFRESH_CONFIG = {
    "gemini": {
        "interval": 3600,     # Token expires in ~1 hour
        "buffer": 1800,       # Refresh with 30 min remaining
    },
    "openai": {
        "interval": 86400,    # Token expires in ~24 hours
        "buffer": 43200,      # Refresh with 12 hours remaining
    },
}


async def background_token_refresh(token_store: "TokenStore") -> None:
    """
    Background task that proactively refreshes tokens before expiry.

    Runs in an infinite loop, checking every 5 minutes if any tokens
    need refreshing. This prevents tokens from expiring during long
    sessions.

    Args:
        token_store: The token store to manage.
    """
    logger.info("Starting background token refresh scheduler")

    while True:
        for provider, config in REFRESH_CONFIG.items():
            await _refresh_if_needed(token_store, provider, config["buffer"])

        # Check every 5 minutes
        await asyncio.sleep(300)


async def _refresh_if_needed(
    token_store: "TokenStore",
    provider: str,
    buffer_seconds: int,
) -> None:
    """
    Refresh a provider's token if it's close to expiring.

    Args:
        token_store: Token store instance
        provider: Provider name (gemini, openai)
        buffer_seconds: Refresh when this many seconds remain
    """
    try:
        # Check if token needs refresh
        if not token_store.needs_refresh(provider, buffer_seconds=buffer_seconds):
            return

        token = token_store.get_token(provider)
        if not token or not token.get("refresh_token"):
            return  # No token or no refresh token

        # Get the appropriate refresh function
        refresh_fn = gemini_refresh if provider == "gemini" else openai_refresh

        # Perform refresh
        result = refresh_fn(token["refresh_token"])

        # Update stored token
        token_store.update_access_token(
            provider,
            result.access_token,
            result.expires_in,
        )

        logger.info(
            f"Proactively refreshed {provider} token "
            f"(expires in {result.expires_in}s)"
        )

    except Exception as e:
        logger.warning(f"Failed to refresh {provider} token: {e}")


def get_token_status(token_store: "TokenStore") -> dict[str, dict]:
    """
    Get status of all provider tokens.

    Returns:
        Dict mapping provider to status info.
    """
    status = {}

    for provider in REFRESH_CONFIG:
        token = token_store.get_token(provider)

        if not token:
            status[provider] = {"status": "not_authenticated"}
            continue

        expires_at = token.get("expires_at", 0)
        if expires_at <= 0:
            status[provider] = {"status": "authenticated", "expires": "unknown"}
        else:
            remaining = expires_at - time.time()
            if remaining <= 0:
                status[provider] = {"status": "expired"}
            else:
                status[provider] = {
                    "status": "valid",
                    "expires_in_seconds": int(remaining),
                    "expires_in_minutes": int(remaining / 60),
                }

    return status
