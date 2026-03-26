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
  → Diff parsed + security pattern scan (regex + entropy analysis)
  → Claude 4.5 Haiku reviews (security issues, crashes, race conditions only)
  → PR summary generated (file stats, additions/deletions)
  → Single comment posted to PR
```

**Zero-Nitpick philosophy:** PR-Sentry never comments on style, formatting, or anything a linter can catch. Only runtime crashes, security vulnerabilities, race conditions, and memory leaks.

**Security scanning:**
- 35+ credential patterns (AWS, Azure, GCP, GitHub, OpenAI, Anthropic, databases)
- Shannon entropy-based secret detection (catches high-entropy strings)
- SQL injection, command injection, XSS detection

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
        uses: Ebuodinde/PR_SENTRY@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          # anthropic_model: "claude-4-5-haiku-20251015" (opsiyonel)
```

Then add your API key to **Settings → Secrets → Actions**:

```
ANTHROPIC_API_KEY = sk-ant-...
```

That's it. No provider selection. No extra keys. No servers. No databases.

---

## What PR-Sentry Reports

✅ **Always reports:**
- **Security issues:**
  - Hardcoded secrets, API keys, passwords (35+ patterns)
  - High-entropy strings (potential secrets)
  - SQL injection, command injection, XSS
  - Unsafe cryptography, path traversal
- **Runtime crashes:**
  - Null pointer / undefined behavior
  - Race conditions, deadlocks
  - Memory leaks, use-after-free
- **Logic errors:**
  - Edge case handling
  - Error handling gaps
  - Unvalidated user input

✅ **Also includes:**
- PR summary (file count, lines changed, file type breakdown)
- AI-generated content detection (slop score)

❌ **Never reports:**
- Code style or formatting
- Variable naming conventions
- Import organization
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

### Basic Configuration (GitHub Action)

| Input | Description | Default |
|---|---|---|
| `anthropic_api_key` | Anthropic API key | — |
| `anthropic_model` | Claude model to use | `claude-4-5-haiku-20251015` |
| `sentry_lang` | Report language (en/tr) | `en` |

### Advanced Configuration (Optional)

Create `.github/sentry-config.yml` in your repository:

```yaml
# Custom zero-nitpick rules
custom_rules:
  - "Focus on thread safety in async code"
  - "Flag potential integer overflows"
  - "Check for unvalidated user input"

# Files/paths to ignore during review
ignore_paths:
  - "test/"
  - "docs/"
  - "*.md"

# Patterns to ignore (regex)
ignore_patterns:
  - "^# Auto-generated"
  - "DO NOT EDIT"

# Slop detection threshold (0-100, higher = stricter)
slop_threshold: 70
```

### Multi-Language Support

Set the report language:

```yaml
- name: Run PR-Sentry
  uses: Ebuodinde/PR_SENTRY@v1
  with:
    anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
    sentry_lang: "tr"  # or "en"
```

### Docker Usage

Run locally with Docker:

```bash
docker-compose up

# Or build and run:
docker build -t pr-sentry .
docker run --env-file .env pr-sentry
```

---

## Examples

See real-world examples in the [`examples/`](examples/) directory:
- [JavaScript](examples/javascript/sample-pr.md) - Auth module with security issues
- [Go](examples/go/sample-pr.md) - Database package with credential leaks
- [Rust](examples/rust/sample-pr.md) - Config module with unsafe blocks

---

## Development

### Setup

```bash
# Clone and install dependencies
git clone https://github.com/Ebuodinde/PR_SENTRY.git
cd PR_SENTRY
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html
```

### Project Structure

```
pr-sentry/
├── main.py              # Entry point, async GitHub API integration
├── reviewer.py          # LLM integration (Anthropic/OpenAI)
├── slop_detector.py     # AI-generated content detection
├── diff_parser.py       # Diff parsing, security scanning
├── entropy_scanner.py   # Entropy-based secret detection
├── github_commenter.py  # PR comment formatting (i18n)
├── config_loader.py     # YAML config loading
├── locales/             # Translation files (en.json, tr.json)
├── tests/               # Pytest test suite (105 tests)
└── examples/            # Usage examples
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

---

## Privacy

- Your code never leaves GitHub's infrastructure during diff fetching
- API calls send only the changed lines (diff), never your full codebase
- No external databases, no persistent storage
- All secrets are masked in logs

---

## License

MIT — free for open source and commercial use.

---

## Roadmap

See [TODO.md](TODO.md) for planned features and improvements.
