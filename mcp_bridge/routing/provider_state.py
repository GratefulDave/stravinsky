"""
Provider State Tracking for Multi-Provider Routing.

Tracks the availability and health of each provider (Claude, OpenAI, Gemini)
to enable intelligent fallback when providers are rate-limited or unavailable.
"""

from __future__ import annotations

import logging
import sys
import threading
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ProviderState:
    """Tracks the state of a single provider."""

    name: str
    is_available: bool = True
    cooldown_until: float | None = None
    error_count: int = 0
    last_success: float | None = None
    last_error: str | None = None
    total_requests: int = 0
    total_failures: int = 0

    def mark_rate_limited(self, duration: int = 300, reason: str = "429 rate limit") -> None:
        """
        Mark provider as rate-limited with cooldown.

        Args:
            duration: Cooldown duration in seconds (default 5 minutes)
            reason: Reason for rate limiting (for logging)
        """
        self.cooldown_until = time.time() + duration
        self.is_available = False
        self.error_count += 1
        self.total_failures += 1
        self.last_error = reason

        logger.warning(
            f"[ProviderState] {self.name} rate-limited: {reason}. "
            f"Cooldown until {time.strftime('%H:%M:%S', time.localtime(self.cooldown_until))}"
        )

        # User-visible notification
        print(
            f"⚠️ {self.name.upper()}: Rate-limited ({reason}). Cooldown for {duration}s.",
            file=sys.stderr,
        )

    def mark_success(self) -> None:
        """Mark a successful request to this provider."""
        self.last_success = time.time()
        self.error_count = 0  # Reset consecutive error count
        self.total_requests += 1

        # If we were in cooldown but succeeded, clear it
        if self.cooldown_until is not None:
            logger.info(f"[ProviderState] {self.name} recovered from cooldown")
            self.cooldown_until = None
            self.is_available = True

    def mark_error(self, error: str) -> None:
        """Mark a non-rate-limit error."""
        self.error_count += 1
        self.total_failures += 1
        self.last_error = error
        logger.warning(f"[ProviderState] {self.name} error ({self.error_count}): {error}")

    def check_availability(self) -> bool:
        """
        Check if provider is available (cooldown expired?).

        Returns:
            True if provider is available, False if in cooldown
        """
        if self.cooldown_until is None:
            return True

        if time.time() > self.cooldown_until:
            # Cooldown expired - reset
            logger.info(f"[ProviderState] {self.name} cooldown expired. Marking available.")
            self.cooldown_until = None
            self.is_available = True
            return True

        # Still in cooldown
        remaining = self.cooldown_until - time.time()
        logger.debug(f"[ProviderState] {self.name} still in cooldown ({remaining:.0f}s remaining)")
        return False

    def get_cooldown_remaining(self) -> float | None:
        """Get remaining cooldown time in seconds, or None if not in cooldown."""
        if self.cooldown_until is None:
            return None
        remaining = self.cooldown_until - time.time()
        return max(0, remaining)

    def reset(self) -> None:
        """Reset provider state (clear cooldown and errors)."""
        self.is_available = True
        self.cooldown_until = None
        self.error_count = 0
        self.last_error = None
        logger.info(f"[ProviderState] {self.name} state reset")


class ProviderStateTracker:
    """
    Tracks availability of all providers with thread-safe access.

    Provides fallback chain logic when primary providers are unavailable.
    """

    # Default fallback chains for each provider
    DEFAULT_FALLBACK_CHAINS: dict[str, list[str]] = {
        "claude": ["openai", "gemini"],
        "openai": ["gemini", "claude"],
        "gemini": ["openai", "claude"],
    }

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.providers: dict[str, ProviderState] = {
            "claude": ProviderState("claude"),
            "openai": ProviderState("openai"),
            "gemini": ProviderState("gemini"),
        }
        self._fallback_chains = self.DEFAULT_FALLBACK_CHAINS.copy()

    def get_provider(self, name: str) -> ProviderState:
        """Get the state for a specific provider."""
        with self._lock:
            if name not in self.providers:
                # Create new provider state if not exists
                self.providers[name] = ProviderState(name)
            return self.providers[name]

    def mark_rate_limited(
        self, provider: str, duration: int = 300, reason: str = "429 rate limit"
    ) -> None:
        """Mark a provider as rate-limited."""
        with self._lock:
            self.get_provider(provider).mark_rate_limited(duration, reason)

    def mark_success(self, provider: str) -> None:
        """Mark a successful request to a provider."""
        with self._lock:
            self.get_provider(provider).mark_success()

    def mark_error(self, provider: str, error: str) -> None:
        """Mark an error for a provider."""
        with self._lock:
            self.get_provider(provider).mark_error(error)

    def is_available(self, provider: str) -> bool:
        """Check if a provider is available."""
        with self._lock:
            return self.get_provider(provider).check_availability()

    def get_fallback_provider(self, preferred: str) -> str:
        """
        Get best available provider, falling back as needed.

        Args:
            preferred: The preferred provider to use

        Returns:
            The best available provider (preferred if available, otherwise fallback)
        """
        with self._lock:
            # Check preferred first
            if self.get_provider(preferred).check_availability():
                return preferred

            # Try fallback chain
            fallback_chain = self._fallback_chains.get(preferred, [])
            for fallback in fallback_chain:
                if self.get_provider(fallback).check_availability():
                    logger.info(
                        f"[ProviderStateTracker] Falling back from {preferred} to {fallback}"
                    )
                    # Notify user
                    print(
                        f"⚠️ {preferred.title()} unavailable → Routing to {fallback.title()}",
                        file=sys.stderr,
                    )
                    return fallback

            # All providers unavailable, return preferred anyway (will likely fail)
            logger.warning(
                f"[ProviderStateTracker] All providers unavailable. Using {preferred} anyway."
            )
            return preferred

    def get_status(self) -> dict[str, dict[str, Any]]:
        """Get status of all providers for dashboard/CLI."""
        with self._lock:
            status = {}
            for name, state in self.providers.items():
                state.check_availability()  # Update availability
                cooldown_remaining = state.get_cooldown_remaining()
                status[name] = {
                    "available": state.is_available,
                    "cooldown_remaining": cooldown_remaining,
                    "error_count": state.error_count,
                    "last_success": state.last_success,
                    "last_error": state.last_error,
                    "total_requests": state.total_requests,
                    "total_failures": state.total_failures,
                }
            return status

    def reset_all(self) -> None:
        """Reset all provider states."""
        with self._lock:
            for state in self.providers.values():
                state.reset()
            logger.info("[ProviderStateTracker] All provider states reset")

    def reset_provider(self, provider: str) -> None:
        """Reset a specific provider's state."""
        with self._lock:
            if provider in self.providers:
                self.providers[provider].reset()

    def set_fallback_chain(self, provider: str, chain: list[str]) -> None:
        """Set custom fallback chain for a provider."""
        with self._lock:
            self._fallback_chains[provider] = chain


# Global singleton instance
_provider_tracker: ProviderStateTracker | None = None
_tracker_lock = threading.Lock()


def get_provider_tracker() -> ProviderStateTracker:
    """Get or create the global ProviderStateTracker instance."""
    global _provider_tracker
    if _provider_tracker is None:
        with _tracker_lock:
            if _provider_tracker is None:
                _provider_tracker = ProviderStateTracker()
                logger.info("[ProviderStateTracker] Created global instance")
    return _provider_tracker


def reset_provider_tracker() -> None:
    """Reset the global provider tracker (mainly for testing)."""
    global _provider_tracker
    with _tracker_lock:
        if _provider_tracker is not None:
            _provider_tracker.reset_all()
