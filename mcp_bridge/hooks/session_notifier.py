"""
Session Notification Hook.

Provides OS-level desktop notifications when sessions are idle.
"""

import logging
import platform
import subprocess
from typing import Any

logger = logging.getLogger(__name__)

# Track which sessions have been notified (avoid duplicates)
_notified_sessions: set[str] = set()


def get_notification_command(title: str, message: str, sound: bool = True) -> list | None:
    """
    Get platform-specific notification command.

    Returns command as list of args, or None if platform not supported.
    """
    system = platform.system()

    if system == "Darwin":  # macOS
        # Use osascript for macOS notifications
        script = f'display notification "{message}" with title "{title}"'
        if sound:
            script += ' sound name "Glass"'
        return ["osascript", "-e", script]

    elif system == "Linux":
        # Use notify-send for Linux
        cmd = ["notify-send", title, message]
        if sound:
            cmd.extend(["--urgency=normal"])
        return cmd

    elif system == "Windows":
        # Use PowerShell for Windows notifications
        ps_script = f"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.UI.Notifications.ToastNotification, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null

$template = @"
<toast>
    <visual>
        <binding template="ToastGeneric">
            <text>{title}</text>
            <text>{message}</text>
        </binding>
    </visual>
</toast>
"@

$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml($template)
$toast = New-Object Windows.UI.Notifications.ToastNotification $xml
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Stravinsky").Show($toast)
"""
        return ["powershell", "-Command", ps_script]

    return None


async def session_notifier_hook(
    session_id: str,
    has_pending_todos: bool,
    idle_seconds: float,
    params: dict[str, Any]
) -> None:
    """
    Session idle hook that sends desktop notification.

    Called when session becomes idle with pending work.
    """
    # Skip if already notified for this session
    if session_id in _notified_sessions:
        return

    # Skip if no pending work
    if not has_pending_todos:
        return

    # Skip if idle time is too short (< 5 seconds)
    if idle_seconds < 5.0:
        return

    # Prepare notification
    title = "Stravinsky Session Idle"
    message = f"Session has pending todos and has been idle for {int(idle_seconds)}s"

    # Get platform-specific command
    cmd = get_notification_command(title, message, sound=True)

    if not cmd:
        logger.warning(f"[SessionNotifier] Desktop notifications not supported on {platform.system()}")
        return

    try:
        # Send notification (non-blocking)
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )

        # Mark as notified
        _notified_sessions.add(session_id)
        logger.info(f"[SessionNotifier] Sent desktop notification for session {session_id}")

    except FileNotFoundError:
        logger.warning(f"[SessionNotifier] Notification command not found: {cmd[0]}")
    except Exception as e:
        logger.error(f"[SessionNotifier] Failed to send notification: {e}")


def clear_notification_state(session_id: str) -> None:
    """
    Clear notification state for a session (called when session resumes activity).
    """
    _notified_sessions.discard(session_id)
