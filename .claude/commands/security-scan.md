# Security Scan

Security vulnerability scanning for the specified directory or file.

**Model Tier**: HIGH (GPT-5.2 / Claude Opus Thinking)

## Usage

```
/security-scan <directory or file path>
```

## Workflow

1. **Discovery**
   - Identify all source files in scope
   - Map entry points and attack surface
   - Identify sensitive data flows
   
2. **Analysis** (using HIGH tier model)
   - Injection vulnerability detection (SQL, XSS, Command)
   - Authentication/authorization weaknesses
   - Secrets and credential exposure
   - Dependency vulnerability check
   - Input validation gaps
   - Error handling information leakage
   
3. **Classification**
   - CRITICAL: Immediate exploitation risk
   - HIGH: Significant vulnerability
   - MEDIUM: Potential weakness
   - LOW: Minor concern or best practice

## Output Format

```markdown
## Security Scan Report: <path>

### Summary
- Files scanned: N
- Vulnerabilities found: N (X critical, Y high, Z medium)

### Critical Findings
#### [CRITICAL] <vulnerability name>
- **Location**: file:line
- **Description**: [what's wrong]
- **Impact**: [potential damage]
- **Remediation**: [how to fix]

### High Findings
[...]

### Medium Findings
[...]

### Recommendations
1. [Priority-ordered security improvements]
```

## Checks Performed

- [ ] Hardcoded secrets/credentials
- [ ] SQL injection vectors
- [ ] XSS vulnerabilities
- [ ] Command injection
- [ ] Path traversal
- [ ] Insecure deserialization
- [ ] Authentication bypass
- [ ] Authorization flaws
- [ ] Sensitive data exposure
- [ ] Security misconfiguration

## Delegation

This skill uses `delphi` (GPT-5.2 HIGH tier) for deep security analysis.

$ARGUMENTS
