# 🛡️ PR-Sentry

**Zero-Nitpick AI code review for open source maintainers.**

PR-Sentry protects your repository from AI-generated slop and security vulnerabilities — without spamming your PR timeline with linter-style noise.

---

## The Problem

AI coding tools have created an asymmetry: code is generated in seconds, but reviewing it still takes human time and attention. Open source maintainers are drowning in:

- **AI Slop** — syntactically correct but contextually meaningless PRs
- **False positives** — review bots that flag whitespace and variable names instead of real bugs
- **Review fatigue** — spending more time dismissing bot noise than catching actual issues

curl's author shut down their bug bounty program because 20% of reports were AI-generated garbage. Godot, Blender, and VLC maintainers report thousands of AI PRs flooding their queues.

PR-Sentry is the defense layer that was missing.

---

## How It Works

```
PR opened
  → Slop Detection (no API call, statistical analysis)
      → High slop score? Flag immediately, skip LLM.
      → Clean? Continue.
  → Diff parsed + security pattern scan
  → Claude reviews (security issues, crashes, race conditions only)
  → Single comment posted to PR
```

**Zero-Nitpick philosophy:** PR-Sentry never comments on style, formatting, or anything a linter can catch. Only runtime crashes, security vulnerabilities, race conditions, and memory leaks.

---

## Quick Start

Add this file to your repository as `.github/workflows/pr-sentry.yml`:

```yaml
name: PR-Sentry Review

on:
  pull_request:
    types: [opened, synchronize]

permissions:
  pull-requests: write

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - name: Run PR-Sentry
        uses: YOUR_GITHUB_USERNAME/pr-sentry@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
```

Then add your API key to **Settings → Secrets → Actions**:

```
ANTHROPIC_API_KEY = sk-ant-...
```

That's it. No provider selection. No extra keys. No servers. No databases.

---

## What PR-Sentry Reports

✅ **Reports:**
- Hardcoded secrets, API keys, passwords in diffs
- Null pointer / undefined behavior risks
- Security vulnerabilities (XSS, SQL injection, unsafe memory access)
- Race conditions
- Logic errors that cause runtime crashes

❌ **Never reports:**
- Code style or formatting
- Variable naming
- Anything ESLint / Prettier / Black / Pylint would catch
- Subjective architecture opinions

---

## Why Not CodeRabbit or Copilot?

| | CodeRabbit | GitHub Copilot | PR-Sentry |
|---|---|---|---|
| AI Slop detection | ❌ | ❌ | ✅ |
| Zero-Nitpick | ❌ | ❌ | ✅ |
| No external database | ❌ | ❌ | ✅ |
| Free for open source | Partial | ❌ | ✅ |
| Plug-and-play | ✅ | ✅ | ✅ |

CodeRabbit floods PR timelines with verbose comments on whitespace and naming. Copilot lacks security depth. Neither detects AI-generated contributions.

---

## Configuration

| Input | Description | Default |
|---|---|---|
| `anthropic_api_key` | Anthropic API key | — |

---

## Privacy

- Your code never leaves GitHub's infrastructure during diff fetching
- API calls send only the changed lines (diff), never your full codebase
- No external databases, no persistent storage
- All secrets are masked in logs

---

## License

MIT — free for open source and commercial use.
