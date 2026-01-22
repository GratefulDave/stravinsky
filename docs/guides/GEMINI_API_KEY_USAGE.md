# Gemini API Key Authentication

Stravinsky uses an **OAuth-first with automatic API key fallback** architecture for Gemini authentication:

1. **OAuth** (Primary) - Configured via `stravinsky-auth login gemini`
2. **API Key** (Automatic Fallback) - Used when OAuth hits rate limits or is not configured

This guide focuses on API key configuration for the fallback mechanism.

## Quick Start: API Key Setup (Tier 3 Recommended)

### Step 1: Get Your API Key

Visit [Google AI Studio](https://aistudio.google.com/app/apikey) and create an API key.

**Recommendation:** Use a **Tier 3 API key** for optimal quotas when the fallback mechanism activates.

### Step 2: Add to Environment

**IMPORTANT:** The environment variable must be named **`GEMINI_API_KEY`** (NOT `GEMINI_API_TOKEN`).

Add your API key to `~/.stravinsky/.env` (user-global config):

```bash
# ~/.stravinsky/.env
# CRITICAL: Variable name is GEMINI_API_KEY (it's a KEY, not a TOKEN)
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

# Or use GOOGLE_API_KEY (same effect)
GOOGLE_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

**File locations checked (in priority order):**
1. `~/.stravinsky/.env` (RECOMMENDED - global for all projects)
2. `~/.env` (fallback - global for user)
3. Project-local `.env` (if using dotenv in your project)

### Step 3: Use Stravinsky

That's it! Stravinsky will automatically detect and use your API key:

```python
# In your code or via MCP
from mcp_bridge.tools.model_invoke import invoke_gemini
from mcp_bridge.auth.token_store import TokenStore

token_store = TokenStore()

response = await invoke_gemini(
    token_store=token_store,
    prompt="Explain async/await in Python",
    model="gemini-3-flash",
)

print(response)
```

## Authentication Priority

Stravinsky uses **OAuth-first with automatic API key fallback**:

1. **OAuth** (Primary) - If tokens exist from `stravinsky-auth login gemini`, OAuth is tried first
2. **API Key Fallback** - On OAuth 429 rate limit, automatically switches to API key for 5 minutes
3. **Cooldown Recovery** - After 5 minutes, retries OAuth

### Rate Limit Handling

```
OAuth Request --> 429 Rate Limited --> Switch to API-Only Mode (5 min timer)
                                              |
                                              v
                                       Use API Key (Tier 3 quotas)
                                              |
                                       Timer expires --> Retry OAuth
```

**Why this architecture?**
- OAuth is convenient (no API key management required)
- API keys (especially Tier 3) have higher rate limits for heavy workloads
- Automatic fallback means uninterrupted operation

## Comparison: OAuth vs API Key

| Feature | OAuth (Primary) | API Key (Fallback) |
|---------|-----------------|-------------------|
| **Setup** | `stravinsky-auth login gemini` | Add to `.env` file |
| **Rate Limits** | Lower (shared quota) | Higher (Tier 3 recommended) |
| **Best For** | Interactive use, typical workloads | Heavy usage, batch processing |
| **Token Refresh** | Automatic background refresh | Not needed (key doesn't expire) |
| **Requires** | Google Account + OAuth consent | API key from Google AI Studio |

## Recommended Configuration

For optimal reliability, configure **both** authentication methods:

### Step 1: Configure OAuth (Primary)

```bash
stravinsky-auth login gemini
```

### Step 2: Configure API Key Fallback

```bash
# Add Tier 3 API key to .env
echo "GEMINI_API_KEY=your_tier_3_key" >> ~/.stravinsky/.env
```

### Step 3: Verify Configuration

```bash
stravinsky-auth status
```

## When Each Method is Used

### OAuth is Used When:
- OAuth tokens exist and are valid
- No recent 429 rate limit errors (within 5-minute cooldown)

### API Key Fallback Activates When:
- OAuth returns 429 (rate limited)
- OAuth is not configured
- OAuth token refresh fails

## Forcing a Specific Authentication Method

### Force API Key Only (Skip OAuth)

Remove OAuth tokens to use API key exclusively:

```bash
# Logout from OAuth
stravinsky-auth logout gemini

# Ensure API key is configured
grep GEMINI_API_KEY ~/.stravinsky/.env
```

### Force OAuth Only (No Fallback)

Remove API key from environment:

```bash
# Remove API key from .env
# Edit ~/.stravinsky/.env and remove GEMINI_API_KEY line

# Or unset for current session
unset GEMINI_API_KEY
unset GOOGLE_API_KEY

# Ensure OAuth is configured
stravinsky-auth status
```

**Note:** Without API key fallback, you may experience interruptions during heavy usage due to OAuth rate limits.

## Testing Your Setup

Use the provided test script to verify both authentication methods:

```bash
# Install google-genai dependency (if not already installed)
uv pip install google-genai

# Run authentication tests
python tests/test_api_key_auth.py
```

Expected output:

```
==============================================================
  GEMINI AUTHENTICATION TEST SUITE
==============================================================
✅ Found API key: AIzaSyXXXXXXXXXXXXXX...XXXX

🧪 Testing Gemini API key authentication...

✅ Response: API key authentication works!

✅ SUCCESS: API key authentication is working!

🧪 Testing OAuth fallback (no API key)...

✅ Correctly fell back to OAuth (not authenticated)
   Run 'stravinsky-auth login gemini' to set up OAuth

==============================================================
  TEST RESULTS
==============================================================
  API Key Auth:    ✅ PASS
  OAuth Fallback:  ✅ PASS
==============================================================
```

## Model Compatibility

Both authentication methods support the same models:

- `gemini-3-flash` → Uses `gemini-3-flash-preview` (API key, Tier 3) or Antigravity (OAuth)
- `gemini-3-pro-low` → Uses `gemini-3-flash-preview` (API key, Tier 3) or Antigravity (OAuth)
- `gemini-3-pro-high` → Uses `gemini-3-pro-preview` (API key, Tier 3) or Antigravity (OAuth)

## Troubleshooting

### Error: "google-genai library not installed"

```bash
# Install the google-genai library
uv pip install google-genai

# Or add to pyproject.toml dependencies
google-genai>=0.2.0
```

### Error: "GEMINI_API_TOKEN is not a valid variable"

**CRITICAL:** The variable name is `GEMINI_API_KEY` (KEY, not TOKEN).

❌ WRONG variable names:
- `GEMINI_API_TOKEN` - doesn't exist
- `GOOGLE_API_TOKEN` - doesn't exist
- `GEMINI_TOKEN` - doesn't exist

✅ CORRECT variable names:
- `GEMINI_API_KEY` - recommended
- `GOOGLE_API_KEY` - alias for GEMINI_API_KEY

**Don't confuse with other tokens:**

| Variable | Purpose | Notes |
|----------|---------|-------|
| `GEMINI_API_KEY` | Gemini auth | It's a KEY (doesn't have "token" in name) |
| `PYPI_API_TOKEN` | PyPI publishing | This IS a token |
| `OPENAI_API_KEY` | OpenAI auth | Also a KEY |

### Error: "API key request failed"

**Possible causes:**

1. **Wrong variable name** - Must be `GEMINI_API_KEY`, not `GEMINI_API_TOKEN`
2. **Wrong file location** - Should be in `~/.stravinsky/.env`, not project `.env`
3. **Invalid API key** - Double-check your key from Google AI Studio
4. **API key not loaded** - Restart Claude Code after adding to `.env`
5. **Quota exceeded** - Check your usage at Google AI Studio
6. **Model not available** - Some models require special access

**Solution:**

```bash
# Step 1: Check file exists
cat ~/.stravinsky/.env
# Should show: GEMINI_API_KEY=AIza...

# Step 2: Verify variable name is correct (not GEMINI_API_TOKEN!)
grep "GEMINI_API_KEY" ~/.stravinsky/.env

# Step 3: Fix if wrong variable name
sed -i '' 's/GEMINI_API_TOKEN/GEMINI_API_KEY/g' ~/.stravinsky/.env

# Step 4: Verify it's loaded
python3 -c "import os; from pathlib import Path; from dotenv import load_dotenv; load_dotenv(Path.home() / '.stravinsky' / '.env'); print('GEMINI_API_KEY:', os.getenv('GEMINI_API_KEY')[:20] + '...' if os.getenv('GEMINI_API_KEY') else 'NOT FOUND')"

# Step 5: Restart Claude Code completely
```

### API Key Not Being Used as Fallback?

**Verify API key is configured:**

```python
import os

# Check if API key is available
print(os.getenv("GEMINI_API_KEY"))
print(os.getenv("GOOGLE_API_KEY"))

# If both print None, your .env isn't loaded
from dotenv import load_dotenv
from pathlib import Path

# Load from recommended location
load_dotenv(Path.home() / ".stravinsky" / ".env")

# Now try again
print(os.getenv("GEMINI_API_KEY"))
```

**Note:** API key is only used when:
1. OAuth returns 429 rate limit error, OR
2. OAuth is not configured

If OAuth is working, you won't see API key being used until rate limits are hit.

## Security Best Practices

### Do NOT commit API keys to git

```bash
# Add .env to .gitignore
echo ".env" >> .gitignore

# Verify .env is ignored
git check-ignore .env
# Should output: .env
```

### Use different keys for different environments

```bash
# .env.development
GEMINI_API_KEY=dev_key_here

# .env.production
GEMINI_API_KEY=prod_key_here
```

### Rotate keys regularly

1. Create new API key at Google AI Studio
2. Update `.env` with new key
3. Test that it works
4. Delete old key from Google AI Studio

## Tier 3 API Key Benefits

Tier 3 API keys provide significantly higher rate limits:

| Tier | Requests/Minute | Tokens/Minute | Best For |
|------|-----------------|---------------|----------|
| Free | 15 | 32,000 | Testing only |
| Tier 1 | 500 | 500,000 | Light usage |
| Tier 2 | 1,000 | 1,000,000 | Moderate usage |
| **Tier 3** | 2,000+ | 2,000,000+ | **Recommended for fallback** |

To upgrade your tier, visit [Google AI Studio](https://aistudio.google.com/app/apikey) and follow the billing setup instructions.

## Additional Resources

- [Google AI Studio](https://aistudio.google.com/)
- [Gemini API Documentation](https://ai.google.dev/gemini-api/docs)
- [google-genai Python SDK](https://googleapis.github.io/python-genai/)
- [OAuth Flow Architecture](../architecture/OAUTH_FLOW.md)
- [Keyring Auth Fix](../reports/KEYRING_AUTH_FIX.md)
