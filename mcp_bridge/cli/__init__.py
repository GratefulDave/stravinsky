"""CLI tools for Stravinsky."""

from .session_report import main as session_report_main
from .install_hooks import main as install_hooks_main

__all__ = ["session_report_main", "install_hooks_main"]
