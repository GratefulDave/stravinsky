"""CLI tools for Stravinsky."""

from .install_hooks import main as install_hooks_main
from .session_report import main as session_report_main

__all__ = ["session_report_main", "install_hooks_main"]
