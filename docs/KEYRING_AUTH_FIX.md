# Keyring Authentication Fix

## Problem

Users experienced persistent macOS Keychain password prompts when running `stravinsky-auth` commands across multiple terminal sessions, breaking the seamless authentication experience.

## Root Causes Identified

### 1. Early Return Bug in `token_store.py`

**Location:** `mcp_bridge/auth/token_store.py:176`

**Issue:** The `set_token()` method had an early `return` statement after successful keyring write, preventing the encrypted file fallback from ever being written:

```python
# BEFORE (Broken)
try:
    keyring.set_password(self.service_name, self._key(provider), data)
    return  # ❌ Early return prevents encrypted file creation
except Exception as e:
    pass

# Fall back to encrypted file storage
try:
    self._save_encrypted(provider, data)  # Never reached!
```

**Impact:** Tokens saved in Terminal A's keyring session were inaccessible in Terminal B, causing authentication failures.

### 2. Module-Level Keyring Import

**Location:** `mcp_bridge/auth/token_store.py:16`

**Issue:** `import keyring` at module level immediately registered the macOS Keychain backend, which then intercepted filesystem operations (like `mkdir()`) during `TokenStore` initialization, triggering password prompts before any actual keyring operations.

```python
# BEFORE (Broken)
import keyring  # ❌ Registers macOS Keychain backend immediately

class TokenStore:
    def __init__(self):
        self.FALLBACK_DIR.mkdir()  # Triggers Keychain prompt!
```

**Impact:** Password prompts appeared during module initialization, even before attempting to read or write tokens.

## Solutions Implemented

### 1. Dual-Write Fix

**File:** `mcp_bridge/auth/token_store.py` (lines 175-192)

Restructured `set_token()` to ALWAYS write to both keyring and encrypted files:

```python
# AFTER (Fixed)
# Lazy import to avoid triggering keychain prompts during module load
import keyring

# Try keyring first, but always also write to encrypted storage
keyring_failed = False
try:
    keyring.set_password(self.service_name, self._key(provider), data)
except Exception as e:
    # Log but don't fail - fall back to encrypted file
    keyring_failed = True

# Always write to encrypted file storage as fallback
try:
    self._save_encrypted(provider, data)
except Exception as e:
    # Only fail if both backends failed
    if keyring_failed:
        raise RuntimeError(
            f"Failed to save token to both keyring and encrypted storage: {e}"
        )
```

### 2. Lazy Keyring Import

**Files:** `mcp_bridge/auth/token_store.py` (lines 121, 176, 208)

Moved `import keyring` inside methods that actually use it, preventing backend registration during module initialization:

```python
# Removed from module level
# import keyring  # ❌ Old location

# Added inside methods
def get_token(self, provider: str) -> TokenData | None:
    # Lazy import to avoid triggering keychain prompts during module load
    import keyring
    # ... rest of method
```

### 3. Keyring Fail Backend Configuration (Final Solution)

**File:** `~/.config/python_keyring/keyringrc.cfg`

Configured Python keyring to use the fail backend, which bypasses all keyring operations and forces immediate fallback to encrypted file storage:

```ini
[backend]
default-keyring = keyring.backends.fail.Keyring
```

**Why this works:**
- No keyring operations = no password prompts
- Tokens are stored ONLY in encrypted files at `~/.stravinsky/tokens/`
- Works seamlessly across all terminal sessions
- No session-specific keyring state

## User Configuration

### One-Time Setup

```bash
# 1. Create keyring config directory
mkdir -p ~/.config/python_keyring

# 2. Configure keyring to use fail backend
cat <<EOT > ~/.config/python_keyring/keyringrc.cfg
[backend]
default-keyring = keyring.backends.fail.Keyring
EOT

# 3. Verify configuration
cat ~/.config/python_keyring/keyringrc.cfg
```

### Cleanup (If Needed)

If you encounter the error `[Errno 21] Is a directory: '/Users/username/.stravinsky/tokens/.key'`, clean up corrupted storage:

```bash
cd ~/.stravinsky/tokens
rmdir .key gemini_token.enc 2>/dev/null  # Remove empty directories
```

### Re-Authentication

```bash
# Authenticate (one time)
stravinsky-auth login gemini

# Test in a new terminal (should work without prompts)
stravinsky-auth status
```

## Technical Details

### Encrypted File Storage

- **Location:** `~/.stravinsky/tokens/`
- **Encryption:** Fernet symmetric encryption (AES-128-CBC)
- **Key storage:** `~/.stravinsky/tokens/.key` (auto-generated, 0o600 permissions)
- **Token files:** `gemini_token.enc`, `openai_token.enc` (0o600 permissions)

### Dual-Write Benefits

Even though keyring is configured to fail, the dual-write code ensures:
1. **Graceful degradation:** If keyring fails (expected), encrypted files work
2. **Future compatibility:** If users want to re-enable keyring, the code supports it
3. **No data loss:** Both backends attempted on every write

## Testing

### Verify Backend Configuration

```bash
python -c "import keyring; print('Backend:', keyring.get_keyring().__class__.__module__ + '.' + keyring.get_keyring().__class__.__name__)"
```

Expected output:
```
Backend: keyring.backends.fail.Keyring
```

### Verify Encrypted Files

```bash
ls -lah ~/.stravinsky/tokens/
```

Expected files:
```
-rw-------  1 user  staff   44B .key
-rw-------  1 user  staff  520B gemini_token.enc
```

### Cross-Terminal Test

1. **Terminal A:** Authenticate with `stravinsky-auth login gemini`
2. **Terminal B:** Check status with `stravinsky-auth status` (should show authenticated)
3. **Expected:** NO password prompts in Terminal B

## Deployment

This fix is included in Stravinsky v0.4.5+. Users should:

1. Upgrade to latest version:
   ```bash
   claude mcp remove stravinsky
   claude mcp add --global stravinsky -- uvx --python python3.13 stravinsky@latest
   ```

2. Configure keyring fail backend (see User Configuration above)

3. Re-authenticate once

## Future Improvements

- [ ] Add automatic keyring configuration check during `stravinsky-auth` initialization
- [ ] Provide `stravinsky-auth configure` command to set up keyring backend
- [ ] Add warning if keyring backend is not set to fail backend
- [ ] Consider migrating away from Python keyring library entirely
