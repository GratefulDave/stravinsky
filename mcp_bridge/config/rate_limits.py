"""
Rate Limiting Configuration for Stravinsky Agent Manager.

Provides per-model concurrency limits to prevent API overload.
Implements semaphore-based rate limiting with configurable limits
per model family.

Configuration file: ~/.stravinsky/config.json
{
  "rate_limits": {
    "claude-opus-4": 2,
    "claude-sonnet-4.5": 5,
    "gemini-3-flash": 10,
    "gemini-3-pro-high": 5,
    "gpt-5.2": 3
  }
}
"""

import json
import logging
import sys
import threading
import time
from collections import defaultdict, deque
from pathlib import Path

logger = logging.getLogger(__name__)

# Default rate limits per model (conservative defaults)
DEFAULT_RATE_LIMITS = {
    # Claude models via CLI
    "opus": 2,  # Expensive, limit parallel calls
    "sonnet": 5,  # Moderate cost
    "haiku": 10,  # Cheap, allow more
    # Gemini models via MCP
    "gemini-3-flash": 10,  # Free/cheap, allow many
    "gemini-3-pro-high": 5,  # Medium cost
    # OpenAI models via MCP
    "gpt-5.2": 3,  # Expensive
    # Default for unknown models
    "_default": 5,
}

# Config file location
CONFIG_FILE = Path.home() / ".stravinsky" / "config.json"


class RateLimiter:
    """
    Semaphore-based rate limiter for model concurrency.

    Thread-safe implementation that limits concurrent requests
    per model family to prevent API overload.
    """

    def __init__(self):
        self._semaphores: dict[str, threading.Semaphore] = {}
        self._lock = threading.Lock()
        self._limits = self._load_limits()
        self._active_counts: dict[str, int] = defaultdict(int)
        self._queue_counts: dict[str, int] = defaultdict(int)

    def _load_limits(self) -> dict[str, int]:
        """Load rate limits from config file or use defaults."""
        limits = DEFAULT_RATE_LIMITS.copy()

        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE) as f:
                    config = json.load(f)
                    if "rate_limits" in config:
                        limits.update(config["rate_limits"])
                        logger.info(f"[RateLimiter] Loaded custom limits from {CONFIG_FILE}")
            except (OSError, json.JSONDecodeError) as e:
                logger.warning(f"[RateLimiter] Failed to load config: {e}")

        return limits

    def _get_semaphore(self, model: str) -> threading.Semaphore:
        """Get or create a semaphore for a model."""
        with self._lock:
            if model not in self._semaphores:
                limit = self._limits.get(model, self._limits.get("_default", 5))
                self._semaphores[model] = threading.Semaphore(limit)
                logger.debug(f"[RateLimiter] Created semaphore for {model} with limit {limit}")
            return self._semaphores[model]

    def _normalize_model(self, model: str) -> str:
        """Normalize model name to match config keys."""
        model_lower = model.lower()

        # Match known patterns
        if "opus" in model_lower:
            return "opus"
        elif "sonnet" in model_lower:
            return "sonnet"
        elif "haiku" in model_lower:
            return "haiku"
        elif "gemini" in model_lower and "flash" in model_lower:
            return "gemini-3-flash"
        elif "gemini" in model_lower and ("pro" in model_lower or "high" in model_lower):
            return "gemini-3-pro-high"
        elif "gpt" in model_lower:
            return "gpt-5.2"

        return model_lower

    def acquire(self, model: str, timeout: float = 60.0) -> bool:
        """
        Acquire a slot for the given model.

        Args:
            model: Model name to acquire slot for
            timeout: Maximum time to wait in seconds

        Returns:
            True if slot acquired, False if timed out
        """
        normalized = self._normalize_model(model)
        semaphore = self._get_semaphore(normalized)

        with self._lock:
            self._queue_counts[normalized] += 1

        logger.debug(f"[RateLimiter] Acquiring slot for {normalized}")
        acquired = semaphore.acquire(blocking=True, timeout=timeout)

        with self._lock:
            self._queue_counts[normalized] -= 1
            if acquired:
                self._active_counts[normalized] += 1

        if acquired:
            logger.debug(f"[RateLimiter] Acquired slot for {normalized}")
        else:
            logger.warning(f"[RateLimiter] Timeout waiting for slot for {normalized}")

        return acquired

    def release(self, model: str):
        """Release a slot for the given model."""
        normalized = self._normalize_model(model)
        semaphore = self._get_semaphore(normalized)

        with self._lock:
            self._active_counts[normalized] = max(0, self._active_counts[normalized] - 1)

        semaphore.release()
        logger.debug(f"[RateLimiter] Released slot for {normalized}")

    def get_status(self) -> dict[str, dict[str, int]]:
        """Get current rate limiter status."""
        with self._lock:
            return {
                model: {
                    "limit": self._limits.get(model, self._limits.get("_default", 5)),
                    "active": self._active_counts[model],
                    "queued": self._queue_counts[model],
                }
                for model in set(list(self._active_counts.keys()) + list(self._queue_counts.keys()))
            }

    def update_limits(self, new_limits: dict[str, int]):
        """
        Update rate limits dynamically.

        Note: This only affects new semaphores. Existing ones
        will continue with their original limits until recreated.
        """
        with self._lock:
            self._limits.update(new_limits)
            logger.info(f"[RateLimiter] Updated limits: {new_limits}")


class RateLimitContext:
    """Context manager for rate-limited model access."""

    def __init__(self, limiter: RateLimiter, model: str, timeout: float = 60.0):
        self.limiter = limiter
        self.model = model
        self.timeout = timeout
        self.acquired = False

    def __enter__(self):
        self.acquired = self.limiter.acquire(self.model, self.timeout)
        if not self.acquired:
            raise TimeoutError(f"Rate limit timeout for model {self.model}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.acquired:
            self.limiter.release(self.model)
        return False


# Global rate limiter instance
_rate_limiter: RateLimiter | None = None
_rate_limiter_lock = threading.Lock()


def get_rate_limiter() -> RateLimiter:
    """Get or create the global RateLimiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        with _rate_limiter_lock:
            if _rate_limiter is None:
                _rate_limiter = RateLimiter()
    return _rate_limiter


def rate_limited(model: str, timeout: float = 60.0) -> RateLimitContext:
    """
    Get a rate-limited context for a model.

    Usage:
        with rate_limited("gemini-3-flash") as ctx:
            # Make API call
            pass
    """
    return RateLimitContext(get_rate_limiter(), model, timeout)


class TimeWindowRateLimiter:
    """
    Time-window rate limiter (30 requests/minute) with user-visible feedback.

    Implements sliding window algorithm for accurate rate limiting.
    Complements the existing semaphore-based concurrency limiter.
    """

    def __init__(self, calls: int = 30, period: int = 60):
        """
        Initialize time-window rate limiter.

        Args:
            calls: Maximum number of calls per period (default: 30)
            period: Time period in seconds (default: 60)
        """
        self.calls = calls
        self.period = period
        self._timestamps: deque = deque()
        self._lock = threading.Lock()

    def acquire_visible(self, provider: str, auth_mode: str) -> float:
        """
        Acquire slot with user-visible feedback.

        Args:
            provider: Provider name for logging (e.g., "GEMINI", "OPENAI")
            auth_mode: Authentication method (e.g., "OAuth", "API key")

        Returns:
            wait_time: Time to wait in seconds (0 if no wait needed)

        Note:
            This method prints status to stderr for user visibility.
        """
        with self._lock:
            now = time.time()

            # Clean old timestamps (sliding window)
            while self._timestamps and self._timestamps[0] < now - self.period:
                self._timestamps.popleft()

            current = len(self._timestamps)

            if current < self.calls:
                self._timestamps.append(now)
                # Show current count in stderr for visibility
                print(
                    f"🔮 {provider} ({auth_mode}): {current + 1}/{self.calls} this minute",
                    file=sys.stderr,
                )
                return 0.0

            # Rate limit hit - calculate wait time
            wait_time = self._timestamps[0] + self.period - now
            print(
                f"⏳ RATE LIMIT ({provider}): {self.calls}/min hit. Waiting {wait_time:.1f}s...",
                file=sys.stderr,
            )
            logger.warning(
                f"[RateLimit] {provider} hit {self.calls}/min limit. Waiting {wait_time:.1f}s ({auth_mode})"
            )

            return wait_time

    def get_stats(self) -> dict[str, int]:
        """Get current rate limiter statistics."""
        with self._lock:
            now = time.time()
            # Clean old timestamps
            while self._timestamps and self._timestamps[0] < now - self.period:
                self._timestamps.popleft()

            return {
                "current_count": len(self._timestamps),
                "limit": self.calls,
                "period_seconds": self.period,
            }


# Global time-window rate limiter for Gemini (30 req/min)
_gemini_time_limiter: TimeWindowRateLimiter | None = None
_gemini_time_limiter_lock = threading.Lock()


def get_gemini_time_limiter() -> TimeWindowRateLimiter:
    """Get or create the global Gemini time-window rate limiter."""
    global _gemini_time_limiter
    if _gemini_time_limiter is None:
        with _gemini_time_limiter_lock:
            if _gemini_time_limiter is None:
                _gemini_time_limiter = TimeWindowRateLimiter(calls=30, period=60)
                logger.info("[TimeWindowRateLimiter] Created Gemini rate limiter (30 req/min)")
    return _gemini_time_limiter
