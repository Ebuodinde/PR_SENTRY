# PR-Sentry Usage Examples

This directory contains example pull requests demonstrating what PR-Sentry detects in different programming languages.

## Contents

| Language | Description |
|----------|-------------|
| [JavaScript](javascript/sample-pr.md) | Node.js auth module with hardcoded secrets and SQL injection |
| [Go](go/sample-pr.md) | Database package with credentials and unsafe queries |
| [Rust](rust/sample-pr.md) | Config module with secrets and unsafe blocks |

## What PR-Sentry Detects

### Security Patterns (Regex + Entropy)
- 🔐 API keys (AWS, GitHub, OpenAI, Anthropic, etc.)
- 🔐 Private keys (RSA, SSH, PGP)
- 🔐 Connection strings with credentials
- 🔐 JWT secrets and tokens
- 🔐 High-entropy strings (potential secrets)

### Code Review (LLM)
- ⚠️ SQL/Command injection vulnerabilities
- ⚠️ Insecure cryptographic practices
- ⚠️ Memory safety issues (language-specific)
- ⚠️ Input validation gaps
- ⚠️ Error handling problems

## Testing Locally

You can test these examples by creating a test PR:

```bash
# Create a test branch
git checkout -b test/security-example

# Copy one of the example diffs and apply it
# Then push and create a PR

# PR-Sentry will run and post its findings
```

## Adding New Examples

Want to add examples for another language? 

1. Create a new directory: `examples/<language>/`
2. Add a `sample-pr.md` with:
   - A sample diff showing problematic code
   - Expected PR-Sentry output
   - A fixed version
3. Update this README
4. Submit a PR!
