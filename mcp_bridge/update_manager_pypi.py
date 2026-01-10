"""
PyPI Update Manager for Stravinsky MCP server.

Checks PyPI for new versions with throttling to prevent excessive API calls.
Logs all checks to ~/.stravinsky/update.log for debugging and monitoring.
Non-blocking background update checks on server startup.
"""

import logging
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Get the logger for this module
logger = logging.getLogger(__name__)

# Import version from main module
from mcp_bridge import __version__


def _get_stravinsky_home() -> Path | None:
    """Get or create ~/.stravinsky directory."""
    home_dir = Path.home() / ".stravinsky"
    try:
        home_dir.mkdir(parents=True, exist_ok=True)
        return home_dir
    except Exception as e:
        logger.warning(f"Failed to create ~/.stravinsky directory: {e}")
        return None


def _get_last_check_time() -> datetime | None:
    """
    Read the last update check time from ~/.stravinsky/update.log.

    Returns:
        datetime of last check, or None if file doesn't exist or is invalid
    """
    try:
        home_dir = _get_stravinsky_home()
        if not home_dir:
            return None

        update_log = home_dir / "update.log"
        if not update_log.exists():
            return None

        # Read the last line (most recent check)
        with open(update_log) as f:
            lines = f.readlines()
            if not lines:
                return None

            last_line = lines[-1].strip()
            if not last_line:
                return None

            # Parse format: YYYY-MM-DD HH:MM:SS | VERSION_CHECK | ...
            parts = last_line.split(" | ")
            if len(parts) < 1:
                return None

            timestamp_str = parts[0]
            last_check = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            return last_check

    except Exception as e:
        logger.debug(f"Failed to read last check time: {e}")
        return None


def _should_check(last_check_time: datetime | None) -> bool:
    """
    Determine if enough time has passed since the last check.

    Args:
        last_check_time: datetime of last check, or None

    Returns:
        True if 24+ hours have passed or no prior check exists
    """
    if last_check_time is None:
        return True

    now = datetime.now()
    time_since_last_check = now - last_check_time

    # Check if 24+ hours have passed
    return time_since_last_check >= timedelta(hours=24)


def _get_pypi_version() -> str | None:
    """
    Fetch the latest version of stravinsky from PyPI.

    Uses: pip index versions stravinsky

    Returns:
        Version string (e.g., "0.3.10"), or None if unable to fetch
    """
    try:
        # Run: pip index versions stravinsky
        result = subprocess.run(
            [sys.executable, "-m", "pip", "index", "versions", "stravinsky"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            logger.debug(f"pip index versions failed: {result.stderr}")
            return None

        # Parse output: first line is "Available versions: X.Y.Z, A.B.C, ..."
        output = result.stdout.strip()
        if not output:
            logger.debug("pip index versions returned empty output")
            return None

        # Extract available versions line
        lines = output.split("\n")
        for line in lines:
            if line.startswith("Available versions:"):
                # Format: "Available versions: 0.3.10, 0.3.9, 0.3.8, ..."
                versions_part = line.replace("Available versions:", "").strip()
                versions = [v.strip() for v in versions_part.split(",")]

                if versions:
                    latest = versions[0]
                    logger.debug(f"Latest version on PyPI: {latest}")
                    return latest

        logger.debug(f"Could not parse pip output: {output}")
        return None

    except subprocess.TimeoutExpired:
        logger.warning("pip index versions timed out after 10 seconds")
        return None
    except Exception as e:
        logger.debug(f"Failed to fetch PyPI version: {e}")
        return None


def _compare_versions(current: str, latest: str) -> bool:
    """
    Compare semantic versions.

    Args:
        current: Current version string (e.g., "0.3.9")
        latest: Latest version string (e.g., "0.3.10")

    Returns:
        True if latest > current, False otherwise
    """
    try:
        # Parse versions as tuples of integers
        current_parts = [int(x) for x in current.split(".")]
        latest_parts = [int(x) for x in latest.split(".")]

        # Pad shorter version with zeros
        max_len = max(len(current_parts), len(latest_parts))
        current_parts += [0] * (max_len - len(current_parts))
        latest_parts += [0] * (max_len - len(latest_parts))

        # Tuple comparison works element-by-element
        return tuple(latest_parts) > tuple(current_parts)

    except Exception as e:
        logger.debug(f"Failed to compare versions '{current}' and '{latest}': {e}")
        return False


def _log_check(current: str, latest: str | None, status: str) -> None:
    """
    Log the update check to ~/.stravinsky/update.log.

    Format: YYYY-MM-DD HH:MM:SS | VERSION_CHECK | current=X.Y.Z pypi=A.B.C | <status>

    Args:
        current: Current version
        latest: Latest version from PyPI (or None)
        status: Check status ("new_available", "up_to_date", "error", etc.)
    """
    try:
        home_dir = _get_stravinsky_home()
        if not home_dir:
            return

        update_log = home_dir / "update.log"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if latest:
            log_entry = f"{timestamp} | VERSION_CHECK | current={current} pypi={latest} | {status}"
        else:
            log_entry = f"{timestamp} | VERSION_CHECK | current={current} pypi=unknown | {status}"

        with open(update_log, "a") as f:
            f.write(log_entry + "\n")

        logger.debug(f"Logged update check: {status}")

    except Exception as e:
        logger.warning(f"Failed to log update check: {e}")


async def check_for_updates(skip_updates: bool = False) -> dict:
    """
    Check PyPI for new versions of stravinsky.

    Implements 24-hour throttling to prevent excessive API calls.
    All failures are handled gracefully without raising exceptions.
    Non-blocking - safe to run via asyncio.create_task().

    Args:
        skip_updates: If True, skip the check entirely

    Returns:
        dict with keys:
            - status: "checked" | "skipped" | "error"
            - current: current version (e.g., "0.3.9")
            - latest: latest version (e.g., "0.3.10") or None
            - update_available: bool
            - message: str (optional, for errors)
    """
    try:
        # Get current version
        current_version = __version__

        # Return early if updates are skipped
        if skip_updates:
            logger.debug("Update check skipped (skip_updates=True)")
            return {
                "status": "skipped",
                "current": current_version,
                "latest": None,
                "update_available": False,
            }

        # Check if enough time has passed since last check
        last_check_time = _get_last_check_time()
        if not _should_check(last_check_time):
            logger.debug("Update check throttled (24-hour limit)")
            return {
                "status": "skipped",
                "current": current_version,
                "latest": None,
                "update_available": False,
            }

        # Fetch latest version from PyPI
        latest_version = _get_pypi_version()

        if latest_version is None:
            logger.warning("Failed to fetch latest version from PyPI")
            _log_check(current_version, None, "error")
            return {
                "status": "error",
                "current": current_version,
                "latest": None,
                "update_available": False,
                "message": "Failed to fetch version from PyPI",
            }

        # Compare versions
        update_available = _compare_versions(current_version, latest_version)

        # Determine status
        if update_available:
            status = "new_available"
            logger.info(
                f"Update available: {current_version} -> {latest_version}. "
                f"Install with: pip install --upgrade stravinsky"
            )
        else:
            status = "up_to_date"
            logger.debug(f"Stravinsky is up to date ({current_version})")

        # Log the check
        _log_check(current_version, latest_version, status)

        return {
            "status": "checked",
            "current": current_version,
            "latest": latest_version,
            "update_available": update_available,
        }

    except Exception as e:
        logger.error(f"Unexpected error during update check: {e}", exc_info=True)
        return {
            "status": "error",
            "current": __version__,
            "latest": None,
            "update_available": False,
            "message": f"Update check failed: {str(e)}",
        }
