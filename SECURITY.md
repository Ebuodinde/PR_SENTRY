# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.x     | :white_check_mark: |
| 1.x     | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in PR-Sentry, please report it responsibly:

1. **DO NOT** open a public GitHub issue
2. Email: [security contact to be added]
3. Or use GitHub's private vulnerability reporting feature

### What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Response Timeline

- **Initial response:** Within 48 hours
- **Status update:** Within 7 days
- **Fix timeline:** Depends on severity

### Scope

The following are in scope:
- Code injection vulnerabilities
- Authentication/authorization bypasses
- Secret exposure in logs or outputs
- Malicious code execution via crafted diffs

### Out of Scope

- Rate limiting issues
- Social engineering
- Vulnerabilities in dependencies (report to upstream)

## Security Features

PR-Sentry is designed with security in mind:

- **No secrets stored:** API keys are passed via environment variables
- **No external database:** All processing is ephemeral
- **Entropy scanning:** Detects hardcoded secrets in PRs
- **Pattern matching:** 50+ security vulnerability patterns

Thank you for helping keep PR-Sentry secure!
