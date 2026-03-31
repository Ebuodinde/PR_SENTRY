# 🛡️ PR-Sentry

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-262%20passing-brightgreen)](https://github.com/Ebuodinde/PR_SENTRY)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![GitHub Release](https://img.shields.io/github/v/release/Ebuodinde/PR_SENTRY)](https://github.com/Ebuodinde/PR_SENTRY/releases)

**Zero-Nitpick AI code review for open source maintainers.**

PR-Sentry protects your repository from AI-generated slop and security vulnerabilities — without spamming your PR timeline with linter-style noise.

**Key Features:**
- 🤖 **AI Slop Detection** — Filters AI-generated noise before expensive LLM calls
- 🔄 **Multi-Provider Support** — Claude, GPT-4, DeepSeek — use any LLM you prefer
- 💰 **Smart Multi-LLM Routing** — 60% cost reduction with intelligent model cascading
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

### Option 1: Anthropic (Claude) — Recommended

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
        uses: Ebuodinde/PR_SENTRY@v3
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
```

### Option 2: OpenAI (GPT-4)

```yaml
      - name: Run PR-Sentry
        uses: Ebuodinde/PR_SENTRY@v3
        with:
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}
```

### Option 3: DeepSeek (Budget-Friendly)

```yaml
      - name: Run PR-Sentry
        uses: Ebuodinde/PR_SENTRY@v3
        with:
          deepseek_api_key: ${{ secrets.DEEPSEEK_API_KEY }}
```

### Option 4: Explicit Provider Selection

```yaml
      - name: Run PR-Sentry
        uses: Ebuodinde/PR_SENTRY@v3
        with:
          provider: "openai"
          api_key: ${{ secrets.OPENAI_API_KEY }}
          model: "gpt-4o"  # optional model override
```

**Get API keys:**
- [Anthropic Console](https://console.anthropic.com/)
- [OpenAI Platform](https://platform.openai.com/)
- [DeepSeek Platform](https://platform.deepseek.com/) (free tier available)

### Cost-Optimized Setup (Multi-Provider)

Use multiple providers for intelligent cost routing:

```yaml
      - name: Run PR-Sentry
        uses: Ebuodinde/PR_SENTRY@v3
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          deepseek_api_key: ${{ secrets.DEEPSEEK_API_KEY }}
```

**Routing Logic:**
- AI slop → Skip LLM entirely (free)
- Simple PR + DeepSeek key → Use DeepSeek (cheapest)
- Security patterns → Use premium Claude model
- Complex PR → Use premium Claude model

---

## 🤖 Using with AI Assistants

PR-Sentry works seamlessly with AI coding assistants. Just share this repository and ask them to set it up!

### Claude Code / Cursor / Windsurf / GitHub Copilot

Simply tell your AI assistant:

> "Add PR-Sentry to my repository for automated code review. Use this repo: https://github.com/Ebuodinde/PR_SENTRY"

Or be more specific:

> "Set up PR-Sentry workflow in my repo. I have an OpenAI API key stored as OPENAI_API_KEY in my GitHub secrets."

**The AI assistant will:**
1. Create `.github/workflows/pr-sentry.yml`
2. Configure the correct provider based on your available API keys
3. Set up proper permissions

### Copy-Paste Prompt

```
Add PR-Sentry (https://github.com/Ebuodinde/PR_SENTRY) to this repository:

1. Create .github/workflows/pr-sentry.yml
2. Use [ANTHROPIC_API_KEY / OPENAI_API_KEY / DEEPSEEK_API_KEY] from secrets
3. Trigger on pull_request opened and synchronize events
4. Grant pull-requests: write permission
```

### MCP Server (Model Context Protocol)

PR-Sentry is available as an MCP server for direct integration with Claude Code, Cursor, and other MCP-compatible tools.

**Setup in Claude Code:**

Add to your `~/.config/claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "pr-sentry": {
      "command": "python",
      "args": ["/path/to/pr-sentry/mcp_server.py"]
    }
  }
}
```

**Available Tools:**
- `review_diff` — Review code diff for security issues and bugs
- `check_slop` — Detect AI-generated content (slop score)
- `scan_security` — Scan for 50+ security vulnerability patterns

**Usage in Claude Code:**
```
> Use pr-sentry to review this diff: [paste diff]
> Check if this PR description is AI-generated slop
> Scan this code for security vulnerabilities
```

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

## How PR-Sentry Detects AI-Generated Pull Requests

Most tools that claim to detect AI-generated code rely on external APIs like GPTZero or Originality.ai, or on simple regex heuristics — both of which are unreliable and easy to bypass.

PR-Sentry takes a different approach: statistical NLP analysis that runs locally, before any LLM call is made. The slop detector computes a composite score from four signals: buzzword density (frequency of filler terms like "robust", "seamless", "leverage"), passive voice ratio, sentence length uniformity, and repetition score. These four dimensions capture the characteristic flatness of AI-generated text — high surface density, low semantic signal. A PR scoring above 60/100 is flagged as AI-generated content and skipped entirely, saving the LLM call.

For secret detection, PR-Sentry uses Shannon entropy analysis on every string in the diff. Human-written code rarely produces strings with entropy above 4.5 bits per character. API keys, tokens, and accidentally committed passwords almost always do. This entropy-based approach catches secrets that regex patterns miss — including novel key formats that no pattern library has seen yet.

When a PR passes both filters and reaches the LLM review stage, a strict zero-nitpick system prompt enforces one rule: report only runtime crashes, security vulnerabilities, race conditions, and memory leaks.

This is what separates PR-Sentry from tools like CodeRabbit or GitHub Copilot review, which function as verbose linters rather than security reviewers. If you're looking for a CodeRabbit alternative or a GitHub Copilot review alternative that focuses exclusively on what breaks in production — PR-Sentry is built for that.

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
| `provider` | LLM provider (anthropic, openai, deepseek) | Auto-detect |
| `api_key` | API key for selected provider | — |
| `anthropic_api_key` | Anthropic API key | — |
| `openai_api_key` | OpenAI API key | — |
| `deepseek_api_key` | DeepSeek API key | — |
| `model` | Model override | Provider default |
| `locale` | Report language (en/tr) | `en` |

### Supported Models

| Provider | Models |
|----------|--------|
| **Anthropic** | `claude-opus-4-6`, `claude-sonnet-4-6`, `claude-haiku-4-5-20251001` |
| **OpenAI** | `gpt-4o`, `gpt-4o-mini` |
| **DeepSeek** | `deepseek-chat`, `deepseek-coder` |

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
  uses: Ebuodinde/PR_SENTRY@v3
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
├── providers/           # Multi-provider LLM support
│   ├── __init__.py
│   ├── base.py          # BaseProvider interface
│   ├── factory.py       # Provider auto-detection
│   ├── anthropic_provider.py
│   ├── openai_provider.py
│   └── deepseek_provider.py
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
├── tests/               # Pytest test suite
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

Developed by [Şahin Uygutalp](https://github.com/Ebuodinde). Built with Claude (Anthropic).
