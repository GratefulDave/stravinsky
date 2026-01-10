"""
Stravinsky Authentication CLI (stravinsky-auth)

OAuth authentication for Gemini (Google) and OpenAI (ChatGPT Plus/Pro).
No API keys required - uses browser-based OAuth flows.

Usage:
    stravinsky-auth login gemini    # Authenticate with Google (Gemini)
    stravinsky-auth login openai    # Authenticate with OpenAI (ChatGPT Plus/Pro)
    stravinsky-auth status          # Check authentication status
    stravinsky-auth logout gemini   # Remove stored credentials
    stravinsky-auth refresh gemini  # Manually refresh access token
    stravinsky-auth init            # Bootstrap current repository
"""

import argparse
import sys
import time

from ..tools.init import bootstrap_repo
from .oauth import perform_oauth_flow as gemini_oauth
from .oauth import refresh_access_token as gemini_refresh
from .openai_oauth import (
    perform_oauth_flow as openai_oauth,
)
from .openai_oauth import (
    refresh_access_token as openai_refresh,
)
from .token_store import TokenStore


def cmd_login(provider: str, token_store: TokenStore) -> int:
    """
    Perform OAuth login for a provider.

    For Gemini: Uses Google OAuth with Antigravity credentials
    For OpenAI: Uses OpenAI OAuth (ChatGPT Plus/Pro subscription)
    """
    if provider == "gemini":
        print("Starting Google OAuth for Gemini...")

        try:
            result = gemini_oauth()

            expires_at = int(time.time()) + result.tokens.expires_in

            token_store.set_token(
                provider="gemini",
                access_token=result.tokens.access_token,
                refresh_token=result.tokens.refresh_token,
                expires_at=expires_at,
            )

            print(f"\n✓ Successfully authenticated as: {result.user_info.email}")
            print(f"  Token expires in: {result.tokens.expires_in // 60} minutes")
            return 0

        except Exception as e:
            print(f"\n✗ OAuth failed: {e}", file=sys.stderr)
            return 1

    elif provider == "openai":
        print("Starting OpenAI OAuth for ChatGPT Plus/Pro...")
        print("Note: Requires ChatGPT Plus/Pro subscription and port 1455 available")

        try:
            result = openai_oauth()

            expires_at = int(time.time()) + result.expires_in

            token_store.set_token(
                provider="openai",
                access_token=result.access_token,
                refresh_token=result.refresh_token,
                expires_at=expires_at,
            )

            print("\n✓ Successfully authenticated with OpenAI")
            print(f"  Token expires in: {result.expires_in // 60} minutes")
            return 0

        except Exception as e:
            print(f"\n✗ OAuth failed: {e}", file=sys.stderr)
            print("\nTroubleshooting:")
            print("  - Ensure you have a ChatGPT Plus/Pro subscription")
            print("  - Stop Codex CLI if running: killall codex")
            print("  - Or use Codex CLI directly: codex login")
            return 1

    else:
        print(f"Unknown provider: {provider}", file=sys.stderr)
        print("Supported providers: gemini, openai")
        return 1


def cmd_logout(provider: str, token_store: TokenStore) -> int:
    """Remove stored tokens for a provider."""
    token_store.delete_token(provider)
    print(f"✓ Logged out from {provider}")
    return 0


def cmd_status(token_store: TokenStore) -> int:
    """Show authentication status for all providers."""
    print("Authentication Status:\n")

    for provider in ["gemini", "openai"]:
        has_token = token_store.has_valid_token(provider)
        status = "✓ Authenticated" if has_token else "✗ Not authenticated"
        print(f"  {provider.capitalize()}: {status}")

        if has_token:
            token = token_store.get_token(provider)
            if token and token.get("expires_at"):
                expires = token["expires_at"]
                remaining = expires - int(time.time())
                if remaining > 0:
                    hours = remaining // 3600
                    minutes = (remaining % 3600) // 60
                    print(f"    Expires in: {hours}h {minutes}m")
                else:
                    print("    Token expired")

    print()
    return 0


def cmd_refresh(provider: str, token_store: TokenStore) -> int:
    """Refresh access token for a provider."""
    token = token_store.get_token(provider)
    if not token or not token.get("refresh_token"):
        print(f"No refresh token found for {provider}")
        print(f"Please run: python -m mcp_bridge.auth.cli login {provider}")
        return 1

    try:
        print(f"Refreshing {provider} token...")

        if provider == "gemini":
            result = gemini_refresh(token["refresh_token"])
        elif provider == "openai":
            result = openai_refresh(token["refresh_token"])
        else:
            print(f"Refresh not supported for {provider}")
            return 1

        expires_at = int(time.time()) + result.expires_in

        token_store.set_token(
            provider=provider,
            access_token=result.access_token,
            refresh_token=result.refresh_token or token["refresh_token"],
            expires_at=expires_at,
        )

        print(f"✓ Token refreshed, expires in {result.expires_in // 60} minutes")
        return 0

    except Exception as e:
        print(f"✗ Refresh failed: {e}", file=sys.stderr)
        return 1


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Stravinsky OAuth authentication for Gemini and OpenAI. "
        "Authenticate via browser-based OAuth flows (no API keys).",
        prog="stravinsky-auth",
        epilog="Examples:\n"
        "  stravinsky-auth login gemini     # Login to Google (Gemini)\n"
        "  stravinsky-auth login openai     # Login to OpenAI (ChatGPT Plus/Pro)\n"
        "  stravinsky-auth status           # Check all provider status\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands", metavar="COMMAND")

    # login command
    login_parser = subparsers.add_parser(
        "login",
        help="Authenticate with a provider via browser OAuth",
        description="Opens browser for OAuth authentication. Tokens are stored securely in system keyring.",
    )
    login_parser.add_argument(
        "provider",
        choices=["gemini", "openai"],
        metavar="PROVIDER",
        help="Provider to authenticate with: gemini (Google) or openai (ChatGPT Plus/Pro)",
    )

    # logout command
    logout_parser = subparsers.add_parser(
        "logout",
        help="Remove stored OAuth credentials",
        description="Deletes stored access and refresh tokens for the specified provider.",
    )
    logout_parser.add_argument(
        "provider",
        choices=["gemini", "openai"],
        metavar="PROVIDER",
        help="Provider to logout from: gemini or openai",
    )

    # status command
    subparsers.add_parser(
        "status",
        help="Show authentication status for all providers",
        description="Displays authentication status and token expiration for Gemini and OpenAI.",
    )

    # refresh command
    refresh_parser = subparsers.add_parser(
        "refresh",
        help="Manually refresh access token",
        description="Force-refresh the access token using the stored refresh token.",
    )
    refresh_parser.add_argument(
        "provider",
        choices=["gemini", "openai"],
        metavar="PROVIDER",
        help="Provider to refresh token for: gemini or openai",
    )

    # init command
    subparsers.add_parser(
        "init",
        help="Bootstrap current repository for Stravinsky",
        description="Creates .stravinsky/ directory structure and copies default configuration files.",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    token_store = TokenStore()

    if args.command == "login":
        return cmd_login(args.provider, token_store)
    elif args.command == "logout":
        return cmd_logout(args.provider, token_store)
    elif args.command == "status":
        return cmd_status(token_store)
    elif args.command == "refresh":
        return cmd_refresh(args.provider, token_store)
    elif args.command == "init":
        print(bootstrap_repo())
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
