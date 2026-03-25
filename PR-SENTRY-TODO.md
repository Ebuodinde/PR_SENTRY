# PR-Sentry — Progress and TODO

> This document exists so a new session can continue without losing context.
> All decisions, rationale, and next steps live here.

---

## Why We Are Building This

**Primary goal:** get accepted into Anthropic's *Claude for Open Source Program*.

The program offers eligible open source developers **6 months of free Claude Max 20x** (normally about $100/month).  
Application deadline: **June 30, 2026**.  
Application link: `claude.com/open-source-max`

**Target track:** Ecosystem Impact Track — no 5,000 star requirement, but Anthropic still decides at its discretion.

**Why not JARVIS?**  
JARVIS is a personal system. No other project depends on it, so it does not fit the "downstream dependents" requirement. PR-Sentry, as a GitHub Action, does.

---

## What We Have Done

### Completed Files

| File | What It Does | Status |
|------|--------------|--------|
| `slop_detector.py` | Analyzes PR text and produces an AI slop score | ✅ Tested and working |
| `diff_parser.py` | Parses unified diffs and scans for security patterns | ✅ Tested and working |
| `reviewer.py` | Combines slop detection, diff parsing, and LLM review | ✅ Tested with Claude |
| `github_commenter.py` | Posts the review result as a PR comment | ✅ Formatting tested |
| `main.py` | Main orchestrator invoked by GitHub Actions | ✅ Written |
| `action.yml` | GitHub Marketplace metadata | ✅ Written |
| `.github/workflows/pr-sentry.yml` | Workflow users can add to their repos | ✅ Written |
| `requirements.txt` | Python dependencies | ✅ Complete |
| `.gitignore` | Protects `.env` and other generated files | ✅ Complete |
| `README.md` | User guide and Anthropic application showcase | ✅ Complete |
| `.env` | API keys (never push this) | ✅ Local only, secret |
| `pr_sentry.md` | Strategic planning document | ✅ Complete |

### Tested Items

- `slop_detector.py`: 3/3 tests passed (AI PR, human PR, short PR)
- `diff_parser.py`: security pattern detection caught hardcoded secrets
- `reviewer.py`: end-to-end review worked with Claude
- `github_commenter.py`: both comment formats rendered correctly
- `main.py`: orchestration flow is wired correctly
- Python compile and smoke tests passed

---

## What Remains

### Critical

**1. Push the repository to GitHub**

```bash
cd "C:\Users\suygu\Desktop\pr sentry"
git init
git add .
git commit -m "feat: initial PR-Sentry MVP"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/pr-sentry.git
git push -u origin main
```

Make sure `.env` is not included. `.gitignore` already covers it, but verify with `git status`.

**2. Test GitHub Actions**

- Open a test PR against the `pr-sentry` repository
- Confirm the action runs
- Confirm it posts a comment on the PR
- Fix any workflow issues that appear

For this, add only the `ANTHROPIC_API_KEY` secret:

`Settings → Secrets and variables → Actions → New repository secret`

**3. Finalize the public workflow example**

The `README.md` example uses `YOUR_GITHUB_USERNAME`. Replace it with your GitHub username before publishing or fork usage.

**4. Publish to GitHub Marketplace**

- The repository already has `action.yml`
- Add the Marketplace metadata and publish entry

---

### Important Before the Anthropic Application

**5. Integrate with 10–20 repositories**

We need real downstream dependents for the Ecosystem Impact Track. Reach out to maintainers of small and medium active repositories:

> "Hey, I built PR-Sentry — a zero-config GitHub Action that catches security issues and filters AI-generated PRs before they reach your queue. It’s free and takes 2 minutes to set up. Would you be open to trying it?"

Target: **at least 10 active installations**

**6. Make JARVIS public**

Publishing JARVIS with a clean README will help make the profile look active and credible.

**7. Write the Anthropic application**

Prepare the 500-word explanation. Main argument:

> "PR-Sentry uses Claude's security reasoning to defend open source libraries against AI-generated vulnerabilities and slop pollution. By enforcing a human-in-the-loop workflow, it applies Anthropic's RSP goals directly in the GitHub supply chain."

---

### Nice to Have Later

- Add a lightweight `sqlite-vec` RAG pipeline for richer repository context
- Add model cascading: simple PRs to a cheaper model, complex PRs to Claude
- Add an MCP Server version for Claude Desktop
- Improve slop detection with more metrics

---

## Current Folder Structure

```
pr-sentry/
├── .github/
│   └── workflows/
│       └── pr-sentry.yml
├── slop_detector.py
├── diff_parser.py
├── reviewer.py
├── github_commenter.py
├── main.py
├── action.yml
├── requirements.txt
├── README.md
├── .env                  ← never push
├── .gitignore
└── PR-SENTRY-TODO.md     ← this file
```

---

## Technical Notes

**Provider setup:**
- `REVIEWER_PROVIDER=development` → local development
- `REVIEWER_PROVIDER=anthropic` → production
- Switching that one variable is enough

**Zero-Nitpick philosophy:**
`reviewer.py`'s `SYSTEM_PROMPT` should not be changed. That prompt is what keeps the bot from producing lint-style noise.

**Slop threshold:**
`slop_detector.py` uses `SLOP_THRESHOLD = 60`. If false positives are too high, raise it to 70. If too much slop slips through, lower it to 50.

**Known limitation:**
Development mode can still produce false positives. Production will use the Anthropic API.

---

## New Session Starting Point

1. Read this file and the session workspace `plan.md`
2. Say "we are at the GitHub push and Actions test stage"
3. Continue from the critical items above

---

*Last updated: MVP code is complete, GitHub push and Actions testing are next.*
