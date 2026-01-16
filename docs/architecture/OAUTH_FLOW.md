# OAuth Authentication Flow

This document details Stravinsky's OAuth authentication architecture for Gemini and OpenAI integration.

## Overview

Stravinsky uses an **OAuth-first with API fallback** strategy:
1. Try OAuth authentication first (better rate limits)
2. On 429 rate limit, fall back to API key for 5 minutes
3. Automatically retry OAuth after cooldown

```mermaid
stateDiagram-v2
    [*] --> OAuthMode: Default State

    OAuthMode --> TryOAuth: invoke_gemini()
    TryOAuth --> Success: Token Valid
    TryOAuth --> RefreshNeeded: Token Expired

    RefreshNeeded --> TryOAuth: Refresh Success
    RefreshNeeded --> LoginRequired: Refresh Failed

    TryOAuth --> RateLimited: 429 Response

    RateLimited --> APIOnlyMode: Has API Key
    RateLimited --> WaitOnly: No API Key

    APIOnlyMode --> Success: Use API Key
    APIOnlyMode --> CooldownCheck: Next Request

    CooldownCheck --> APIOnlyMode: < 5 minutes
    CooldownCheck --> OAuthMode: >= 5 minutes

    WaitOnly --> TryOAuth: After 5 min

    Success --> [*]
    LoginRequired --> [*]: User Must Re-auth
```

## Authentication Methods

### Gemini OAuth (Google Antigravity)

```mermaid
sequenceDiagram
    participant User
    participant CLI as stravinsky-auth
    participant Browser
    participant Google as Google OAuth
    participant KR as Keyring/File

    User->>CLI: stravinsky-auth login gemini
    CLI->>Browser: Open OAuth URL
    Browser->>Google: Authorization Request
    Google-->>Browser: Login Page
    User->>Google: Enter Credentials
    Google-->>Browser: Redirect with Code
    Browser->>CLI: Authorization Code
    CLI->>Google: Exchange for Tokens
    Google-->>CLI: Access + Refresh Tokens
    CLI->>KR: Store Tokens (encrypted)
    CLI-->>User: Login Successful
```

### OpenAI OAuth (ChatGPT Backend)

```mermaid
sequenceDiagram
    participant User
    participant CLI as stravinsky-auth
    participant Server as Local Server :1455
    participant Browser
    participant OpenAI as ChatGPT OAuth
    participant KR as Keyring/File

    User->>CLI: stravinsky-auth login openai
    CLI->>Server: Start HTTP Server
    CLI->>Browser: Open OAuth URL
    Browser->>OpenAI: Authorization Request
    User->>OpenAI: Login with ChatGPT
    OpenAI-->>Browser: Redirect to localhost:1455
    Browser->>Server: Authorization Code
    Server->>OpenAI: Exchange for Tokens
    OpenAI-->>Server: Access + Refresh Tokens
    Server->>KR: Store Tokens (encrypted)
    Server-->>CLI: Complete
    CLI-->>User: Login Successful

    Note over Server: Port 1455 shared with Codex CLI
```

## Token Storage Architecture

### Storage Priority

```mermaid
flowchart TB
    subgraph "Primary: System Keyring"
        KC[macOS Keychain]
        KL[Linux Secret Service]
        KW[Windows Credential Locker]
    end

    subgraph "Fallback: Encrypted Files"
        DIR[~/.stravinsky/tokens/]
        KEY[.key<br/>Fernet encryption key]
        GT[gemini_token<br/>encrypted JSON]
        OT[openai_token<br/>encrypted JSON]
    end

    STORE[Store Token] --> TRY{Try Keyring}

    TRY -->|macOS| KC
    TRY -->|Linux| KL
    TRY -->|Windows| KW

    KC -->|fail| DIR
    KL -->|fail| DIR
    KW -->|fail| DIR

    DIR --> KEY
    KEY -->|AES-128-CBC| GT
    KEY -->|AES-128-CBC| OT

    style KEY fill:#ff9999
    style GT fill:#99ff99
    style OT fill:#99ff99
```

### Token Data Structure

```python
{
    "access_token": "ya29.xxx...",
    "refresh_token": "1//xxx...",
    "expires_at": 1704567890.123,  # Unix timestamp
    "token_type": "Bearer",
    "scope": ["openid", "email", "profile"]
}
```

### File Permissions

| File | Permissions | Purpose |
|------|-------------|---------|
| `~/.stravinsky/tokens/` | `0o700` | Token directory |
| `.key` | `0o600` | Encryption key |
| `*_token` | `0o600` | Encrypted tokens |

## Token Refresh Flow

```mermaid
sequenceDiagram
    participant Tool as invoke_gemini()
    participant TS as TokenStore
    participant OAuth as OAuth Provider

    Tool->>TS: get_token("gemini")
    TS->>TS: Check expires_at

    alt Token Valid
        TS-->>Tool: Return Token
    else Token Expired
        TS->>OAuth: Refresh Token Request
        alt Refresh Success
            OAuth-->>TS: New Access Token
            TS->>TS: Update Storage
            TS-->>Tool: Return New Token
        else Refresh Failed
            TS-->>Tool: AuthenticationError
            Note over Tool: User must re-login
        end
    end
```

## Rate Limit Handling

### 429 Detection and Fallback

```mermaid
flowchart TD
    REQ[invoke_gemini Request] --> AUTH{Get Auth Method}

    AUTH -->|OAuth Mode| OAUTH[Try OAuth Request]
    AUTH -->|API-Only Mode| API[Use API Key]

    OAUTH --> RESP{Response Code}

    RESP -->|200| OK[Return Result]
    RESP -->|429| RL[Rate Limited]
    RESP -->|401/403| NEXT[Try Next Endpoint]

    RL --> HASKEY{Has API Key?}
    HASKEY -->|Yes| SWITCH[Switch to API-Only Mode<br/>Set 5-min timer]
    HASKEY -->|No| WAIT[Return Rate Limit Error]

    SWITCH --> API
    API --> OK

    NEXT -->|More Endpoints| OAUTH
    NEXT -->|No More| FAIL[Auth Failed]
```

### State Machine

```python
# Global state variables
_GEMINI_OAUTH_429_TIMESTAMP: float | None = None
_OAUTH_COOLDOWN_SECONDS = 300  # 5 minutes

def _is_api_only_mode() -> bool:
    if _GEMINI_OAUTH_429_TIMESTAMP is None:
        return False
    elapsed = time.time() - _GEMINI_OAUTH_429_TIMESTAMP
    if elapsed >= _OAUTH_COOLDOWN_SECONDS:
        # Auto-reset after cooldown
        _GEMINI_OAUTH_429_TIMESTAMP = None
        return False
    return True

def _set_api_only_mode(reason: str):
    global _GEMINI_OAUTH_429_TIMESTAMP
    _GEMINI_OAUTH_429_TIMESTAMP = time.time()
    print(f"⚠️ OAuth rate-limited. Using API key for 5 minutes")
```

## Endpoint Fallback (Gemini)

Antigravity uses multiple endpoints for redundancy:

```mermaid
flowchart LR
    subgraph "Antigravity Endpoints"
        E1[us-autopush-cloud-aiplatform<br/>.sandbox.googleapis.com]
        E2[us-discoveryengine<br/>.sandbox.googleapis.com]
        E3[us-aiplatform<br/>.sandbox.googleapis.com]
    end

    REQ[Request] --> E1
    E1 -->|401/403/timeout| E2
    E2 -->|401/403/timeout| E3
    E3 -->|all fail| DIRECT[Direct API Key Mode]

    E1 -->|success| OK[Return Result]
    E2 -->|success| OK
    E3 -->|success| OK
    DIRECT -->|success| OK
```

## Auth Configuration Commands

### Login Commands

```bash
# Gemini OAuth
stravinsky-auth login gemini

# OpenAI OAuth (requires ChatGPT Plus/Pro)
stravinsky-auth login openai

# Check status
stravinsky-auth status

# Logout
stravinsky-auth logout gemini
stravinsky-auth logout openai
```

### API Key Fallback

```bash
# Add to .env file
GEMINI_API_KEY=your_api_key_here
# OR
GOOGLE_API_KEY=your_api_key_here
```

## Troubleshooting

### Password Prompts (macOS)

If experiencing persistent keychain prompts:

```bash
# Configure keyring to use encrypted files instead
mkdir -p ~/.config/python_keyring
cat > ~/.config/python_keyring/keyringrc.cfg << EOF
[backend]
default-keyring = keyring.backends.fail.Keyring
EOF

# Re-authenticate
stravinsky-auth login gemini
```

### Port 1455 Conflict

```bash
# OpenAI shares port with Codex CLI
# Stop Codex if running:
killall codex

# Then retry login
stravinsky-auth login openai
```

### Token Refresh Failures

```mermaid
flowchart TD
    FAIL[Refresh Failed] --> CHECK{Error Type}

    CHECK -->|invalid_grant| REVOKED[Token Revoked]
    CHECK -->|network_error| NETWORK[Network Issue]
    CHECK -->|server_error| RETRY[Retry Later]

    REVOKED --> RELOGIN[stravinsky-auth login]
    NETWORK --> FIX[Check Network]
    RETRY --> WAIT[Wait and Retry]

    FIX --> RELOGIN
    WAIT --> RELOGIN
```

## Security Considerations

### Token Protection

1. **Encrypted at rest**: Tokens stored with Fernet (AES-128-CBC)
2. **Restricted permissions**: Files readable only by owner (0o600)
3. **No environment exposure**: Tokens never in env vars or logs
4. **Automatic refresh**: Minimizes exposure of long-lived tokens

### Best Practices

- Use OAuth over API keys when possible
- Keep `.stravinsky/` directory permissions restricted
- Re-authenticate periodically to refresh credentials
- Use `stravinsky-auth logout` when done with a machine

## Related Documentation

- [Architecture Overview](ARCHITECTURE.md)
- [MCP Tool Flow](MCP_TOOL_FLOW.md)
- [Keyring Auth Fix](KEYRING_AUTH_FIX.md)
