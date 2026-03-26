# PR-Sentry CLI

Zero-Nitpick AI code review for PR/MR.

## Installation

```bash
npm install -g @pr-sentry/cli
```

## Requirements

- Node.js 16+
- Python 3.9+
- Anthropic API key

## Usage

### Review GitHub PR

```bash
export GITHUB_TOKEN=your_token
export ANTHROPIC_API_KEY=your_key

pr-sentry review --repo owner/repo --pr 123
```

### Review GitLab MR

```bash
export GITLAB_TOKEN=your_token
export ANTHROPIC_API_KEY=your_key

pr-sentry review --gitlab --project-id 12345 --pr 67
```

### Analyze Diff

```bash
git diff HEAD~1 | pr-sentry analyze
# Or from file:
pr-sentry analyze --file changes.patch
```

### View Stats

```bash
pr-sentry stats           # Today's stats
pr-sentry stats --daily   # Daily breakdown
pr-sentry stats --all-time  # All-time stats
```

## Features

- 🛡️ Security-first: SQL injection, XSS, hardcoded secrets
- 🤖 AI Slop Detection: Filter AI-generated noise
- 💰 Cost Optimization: Smart model routing
- 🌍 Multi-platform: GitHub + GitLab support
- 📊 Metrics: Token/cost tracking

## License

MIT © Ebuodinde
