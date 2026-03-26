# Contributing to PR-Sentry

First off, thank you for considering contributing to PR-Sentry! 🎉

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for everyone.

## How to Contribute

### 1. Fork and Clone

```bash
# Fork the repo on GitHub, then:
git clone https://github.com/YOUR_USERNAME/pr-sentry.git
cd pr-sentry
```

### 2. Set Up Development Environment

```bash
# Create a virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 3. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

### 4. Make Your Changes

- Write clean, readable code
- Follow existing code style (PEP 8 for Python)
- Add tests for new functionality
- Update documentation if needed

### 5. Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_slop_detector.py
```

### 6. Commit Your Changes

We use conventional commits format:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```bash
git commit -m "feat(security): add AWS credential pattern detection"
git commit -m "fix(parser): handle empty diff files"
git commit -m "docs: update README with Docker instructions"
```

### 7. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then open a Pull Request on GitHub.

## Development Guidelines

### Project Structure

```
pr-sentry/
├── main.py              # Entry point, GitHub API integration
├── reviewer.py          # LLM integration (Anthropic/OpenAI)
├── slop_detector.py     # AI-generated content detection
├── diff_parser.py       # Diff parsing, security scanning
├── github_commenter.py  # PR comment formatting
├── entropy_scanner.py   # Entropy-based secret detection
├── config_loader.py     # YAML config loading
├── locales/             # Translation files (en.json, tr.json)
├── tests/               # Pytest test suite
└── examples/            # Usage examples
```

### Adding New Security Patterns

Add patterns to `SENSITIVE_PATTERNS` in `diff_parser.py`:

```python
SENSITIVE_PATTERNS = [
    # ... existing patterns ...
    (r"your_regex_pattern", "Description of what it detects"),
]
```

Then add corresponding tests in `tests/test_diff_parser.py`.

### Adding New Languages (i18n)

1. Create a new file in `locales/` (e.g., `de.json`)
2. Copy the structure from `en.json`
3. Translate all values
4. Test with `SENTRY_LANG=de`

### Running Locally

```bash
# Using Docker
docker-compose up

# Or directly
export GITHUB_TOKEN="your_token"
export GITHUB_REPOSITORY="owner/repo"
export PR_NUMBER="123"
export ANTHROPIC_API_KEY="your_key"

python main.py
```

## Reporting Issues

When reporting bugs, please include:
- Python version (`python --version`)
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Any error messages or logs

## Feature Requests

We welcome feature requests! Please:
1. Open an issue describing the feature
2. Explain the use case and benefits
3. Provide examples if possible

## Questions?

Feel free to open an issue with the `question` label.

---

Thank you for contributing! 💚
