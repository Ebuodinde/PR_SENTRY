# 🛡️ PR-Sentry

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-219%20passing-brightgreen)](https://github.com/Ebuodinde/PR_SENTRY)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![GitHub Release](https://img.shields.io/github/v/release/Ebuodinde/PR_SENTRY)](https://github.com/Ebuodinde/PR_SENTRY/releases)

**Zero-Nitpick AI code review for open source maintainers.**

PR-Sentry protects your repository from AI-generated slop and security vulnerabilities — without spamming your PR timeline with linter-style noise.

**Key Features:**
- 🤖 **AI Slop Detection** — Filters AI-generated noise before expensive LLM calls
- 💰 **Smart Multi-LLM Routing** — 60% cost reduction with optional DeepSeek integration
- 🔒 **Advanced Security Scanning** — 50+ vulnerability patterns, entropy analysis, cloud credentials
- 🚫 **Zero-Nitpick** — Only reports crashes, security issues, race conditions—no style complaints
- ⚡ **Lightweight** — No external database, no servers, works out-of-the-box

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
  → AI Slop Detection (statistical analysis, no API call)
      → High slop score? Flag immediately, skip LLM.
      → Clean? Continue.
  → Smart Model Selection (complexity + security analysis)
      → Simple PR? Use fast model
      → Security patterns detected? Use premium model
      → Complex PR? Use premium model
  → Diff parsed + security pattern scan (regex + entropy analysis)
  → LLM review (security issues, crashes, race conditions only)
  → PR summary generated (file stats, additions/deletions)
  → Single comment posted to PR
```

**Estimated Cost:** ~$0.01-0.05 per average PR (varies by size and complexity)

**Zero-Nitpick philosophy:** PR-Sentry never comments on style, formatting, or anything a linter can catch. Only runtime crashes, security vulnerabilities, race conditions, and memory leaks.

**Smart Routing:**
- Default: Works with just Anthropic key (smart model cascading)
- Optional: Add DeepSeek key for additional cost savings on simple PRs
- Security-critical code always uses premium models

**Security scanning:**
- 50+ credential patterns (AWS, Azure, GCP, GitHub, OpenAI, Anthropic, databases)
- Shannon entropy-based secret detection (catches high-entropy strings)
- SQL injection, command injection, XSS detection
- Memory safety analysis (C/C++/Rust)

---

## Quick Start

### Basic Setup (Single API Key)

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
        uses: Ebuodinde/PR_SENTRY@v2
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
```

Then add your API key to **Settings → Secrets → Actions**:

```
ANTHROPIC_API_KEY = sk-ant-...
```

That's it. No provider selection. No extra keys. No servers. No databases.

### Cost-Optimized Setup (Optional)

Want to save 60% on API costs? Add DeepSeek:

```yaml
      - name: Run PR-Sentry
        uses: Ebuodinde/PR_SENTRY@v2
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          deepseek_api_key: ${{ secrets.DEEPSEEK_API_KEY }}  # Optional
```

Get API keys:
- [Anthropic Console](https://console.anthropic.com/) (required)
- [DeepSeek Platform](https://platform.deepseek.com/) (optional, free tier available)

**Routing Logic:**
- AI slop → Skip LLM entirely (free)
- Simple PR + DeepSeek key → Use DeepSeek (cheapest)
- Security patterns → Use premium Claude model
- Complex PR → Use premium Claude model

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

| Feature | CodeRabbit | GitHub Copilot | PR-Sentry |
|---|---|---|---|
| AI Slop detection | ❌ | ❌ | ✅ |
| Zero-Nitpick | ❌ | ❌ | ✅ |
| Cost optimization | ❌ | ❌ | ✅ (60% savings) |
| No external database | ❌ | ✅ | ✅ |
| Free for open source | Partial | ❌ | ✅ |
| Plug-and-play | ✅ | ✅ | ✅ |

CodeRabbit floods PR timelines with verbose comments on whitespace and naming. Copilot lacks security depth. Neither detects AI-generated contributions or optimizes costs.

---

## 💰 Cost Optimization

PR-Sentry is designed to minimize API costs while maximizing review quality.

### Estimated Costs

| PR Size | Estimated Cost |
|---------|----------------|
| Small (< 100 lines) | ~$0.005 - $0.01 |
| Medium (100-500 lines) | ~$0.01 - $0.03 |
| Large (500+ lines) | ~$0.03 - $0.05 |
| AI slop detected | $0 (skipped) |

**Monthly estimate (100 PRs/month):** $1-5 depending on PR complexity

### Cost Saving Strategies

1. **AI Slop Detection:** ~30% of PRs are flagged and skipped, saving 100% on those
2. **Smart Model Routing:** Simple PRs use cheaper models automatically
3. **DeepSeek Integration:** Optional - add DeepSeek key for additional savings on non-security PRs
4. **Large PR Filtering:** PRs with 50+ files are auto-filtered to essential files only

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
  uses: Ebuodinde/PR_SENTRY@v2
  with:
    anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
    locale: "tr"  # en, tr
```

### GitLab CI/CD Support

PR-Sentry also works with GitLab merge requests! Add to your `.gitlab-ci.yml`:

```yaml
pr-sentry-review:
  stage: test
  image: python:3.11-slim
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  before_script:
    - pip install git+https://github.com/Ebuodinde/PR_SENTRY.git
  script:
    - python -m pr_sentry.gitlab_runner
  allow_failure: true
```

Required CI/CD Variables:
- `ANTHROPIC_API_KEY`: Your Anthropic API key
- `GITLAB_TOKEN`: GitLab personal access token (api scope)

See [examples/gitlab-ci.yml](examples/gitlab-ci.yml) for full configuration.

### Docker Usage

Run locally with Docker:

```bash
docker-compose up

# Or build and run:
docker build -t pr-sentry .
docker run --env-file .env pr-sentry
```

### CLI Tool

Use PR-Sentry from the command line:

```bash
# Install
pip install git+https://github.com/Ebuodinde/PR_SENTRY.git

# Review a GitHub PR
export GITHUB_TOKEN=your_token
export ANTHROPIC_API_KEY=your_key
python cli.py review --repo owner/repo --pr 123

# Review a GitLab MR
export GITLAB_TOKEN=your_token
python cli.py review --gitlab --project-id 12345 --pr 67

# Analyze any diff
git diff HEAD~1 | python cli.py analyze

# View usage statistics
python cli.py stats --all-time
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
├── main.py              # Entry point, GitHub Actions integration
├── cli.py               # CLI tool for local reviews
├── reviewer.py          # LLM integration with smart routing
├── llm_router.py        # Multi-LLM cascading logic
├── performance.py       # Large PR optimization
├── metrics.py           # Token/cost tracking
├── context_builder.py   # Lightweight RAG context
├── gitlab_client.py     # GitLab CI/CD support
├── slop_detector.py     # AI-generated content detection
├── diff_parser.py       # Diff parsing, security scanning
├── entropy_scanner.py   # Entropy-based secret detection
├── github_commenter.py  # PR comment formatting (i18n)
├── config_loader.py     # YAML config loading
├── locales/             # Translation files (en, tr)
├── tests/               # Pytest test suite (219 tests)
└── examples/            # Usage examples (GitHub, GitLab)
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

## Credits

Developed by [Ebuodinde](https://github.com/Ebuodinde) with assistance from GitHub Copilot.
