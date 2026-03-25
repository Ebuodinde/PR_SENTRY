# PR-Sentry — Project Plan and Context

> This document is meant to survive being handed to another coding agent or session without losing context.  
> All decisions and rationale live here.

---

## 1. Starting Point — The Real Goal

**Primary goal:** get accepted into Anthropic's *Claude for Open Source Program*.

The program offers eligible open source developers **6 months of free Claude Max 20x** (normally about $100/month).  
Application deadline: **June 30, 2026**.

**Why this matters:**  
Claude Pro limits are too tight for heavy coding workflows. Claude Max 20x would remove that bottleneck and speed up both PR-Sentry and the parallel JARVIS project.

**Developer context:**
- 24-year-old engineering student in Turkey
- Hardware: Ryzen AI 350 + XDNA 2 NPU
- Parallel project: JARVIS (a personal cognitive digital twin system)
- GitHub profile is mostly private repositories right now, with little public contribution history

---

## 2. Program Requirements

The program has two tracks:

### Maintainer Track
- Requires a public repository with 5,000+ GitHub stars or 1M+ monthly npm downloads
- Requires merge rights and active contributions in the last 3 months
- **Not applicable right now**

### Ecosystem Impact Track *(Target track)*
- No 5,000-star requirement
- Focuses on projects that open source ecosystems meaningfully depend on
- Requires a 500-word written explanation plus Anthropic's discretion
- Evaluation signals: downstream dependents, usage breadth, project criticality, and the applicant's role

**Estimated acceptance chance:** roughly 30–40% if the story is strong and usage can be demonstrated.

---

## 3. Why PR-Sentry?

### JARVIS is not a fit
JARVIS is a personal system. Nothing downstream depends on it, so it does not satisfy the "downstream dependents" criterion. The Ecosystem Impact Track is looking for open source infrastructure.

### PR-Sentry is a fit because:
- It is developer tooling, which matches the program's target area
- It plugs into GitHub PR workflows, so downstream dependents are measurable
- It solves a real and immediate problem
- It is centered on Claude, which aligns with Anthropic's RSP goals

---

## 4. Problem Being Solved — Market Reality

### The AI Slop problem
AI tools have dramatically increased code generation speed, but review pipelines have not kept up. Maintainers are getting flooded with noisy, low-signal, or AI-generated PRs.

Examples from the ecosystem:
- curl's maintainer reported that a significant share of bug reports were AI-generated junk
- Godot, Blender, and VLC maintainers have reported massive PR queues
- PR volume is rising while merge rates are falling
- tldraw and Ghostty have reduced or closed external contribution channels

### Why current tools fail
- **Context blindness:** many tools only inspect the diff and ignore broader repo context
- **Noise:** they report things linters would already catch
- **Blind spots:** they do not flag plausible-looking but meaningless AI contributions

### Competitive snapshot

| Tool | Context | Noise | Slop Detection | OSS Fit |
|------|---------|-------|----------------|---------|
| CodeRabbit | Diff-only | High | No | Partial |
| GitHub Copilot | Diff-only | High | No | No (expensive) |
| Greptile | Very strong | Low | No | No ($30/user) |
| PR-Agent/Qodo | Medium | Medium | No | Yes, but hard to set up |
| **PR-Sentry** | **Medium-Strong** | **Very Low** | **Yes** | **Yes (plug-and-play)** |

---

## 5. MVP Scope — What We Build / Don't Build

### Included in the MVP

#### 1. GitHub Action infrastructure
The action runs automatically when a PR opens or updates. The user only adds one YAML file and PR-Sentry handles the rest.

Flow:
```
PR opens
→ GitHub Action triggers
→ Diff is fetched
→ Slop detection runs
→ Claude review runs
→ Comment is posted back to the PR
```

#### 2. Zero-Nitpick philosophy
The prompt layer enforces this without extra code.

Rules for the reviewer:
- Never comment on whitespace, style, or naming
- Never report anything ESLint/Prettier/Black would already catch
- Only report runtime crashes, security issues, race conditions, and memory leaks

#### 3. AI slop detection
Before the diff reaches Claude, run a lightweight statistical filter:
- Type-token ratio
- Buzzword density
- Consistency between commit messages, PR description, and code changes

High slop scores get flagged as `AI-Generated - Needs Human Context` or rejected before Claude is called.

### Not included in the MVP

#### sqlite-vec RAG pipeline
Not chosen because GitHub Actions are ephemeral and building a vector store on every run would be too slow and complex.

#### Model cascading
Not chosen because it is early optimization and adds unnecessary API complexity.

#### CLI / MCP server version
Not chosen because the public value proposition is GitHub PR review, not a general-purpose local CLI.

---

## 6. Technical Architecture — MVP

### File structure
```
pr-sentry/
├── .github/
│   └── workflows/
│       └── pr-sentry.yml
├── main.py
├── slop_detector.py
├── diff_parser.py
├── reviewer.py
├── github_commenter.py
├── action.yml
├── README.md
└── requirements.txt
```

### User setup
```yaml
# Add this as .github/workflows/pr-sentry.yml in the target repo
name: PR-Sentry Review
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  review:
    uses: YOUR_GITHUB_USERNAME/pr-sentry/.github/workflows/pr-sentry.yml@main
    secrets:
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

```text
# GitHub secret required:
ANTHROPIC_API_KEY=sk-ant-...
```

### Security
- `.env`, credential files, and certificates are excluded
- Secrets are masked in logs
- PR-Sentry never auto-merges; it only comments and reports status

---

## 7. Application Strategy

### Timeline to June 30, 2026

**Weeks 1–2: Preparation**
- Make the JARVIS repository public and give it a clean README
- Create the PR-Sentry repository and finalize the structure

**Weeks 3–4: MVP build**
- Finish the slop detector, diff parser, and Claude integration
- Wire the GitHub Action end to end
- Test it on your own repositories

**Weeks 5–6: Release and adoption**
- Publish to GitHub Marketplace
- Reach out to 10–20 small and medium active repositories
- Ask maintainers to try it for free

**Weeks 7–8: Application**
- Document downstream dependents
- Write the 500-word application
- Apply through `claude.com/open-source-max`

### Main argument for the application
> "PR-Sentry uses Claude's security reasoning to defend open source libraries against AI-generated vulnerabilities and slop pollution. By enforcing a human-in-the-loop workflow, it applies Anthropic's RSP goals directly in the GitHub supply chain."

---

## 8. Success Criteria

To apply with confidence, we need at least:
- PR-Sentry working in a public repository
- Active use in at least 10 different repositories
- Concrete downstream dependent evidence
- A public and active-looking JARVIS profile
- Recent GitHub contribution activity

---

## 9. Next Step

**Current task:** build the PR-Sentry MVP.

Starting point: `slop_detector.py` — it runs without any Claude API call, is independently testable, and is the most unique part of the project.

### Technologies to use
- Python 3.11+
- Anthropic Python SDK (`anthropic`)
- GitHub Actions YAML
- Standard library `urllib` for GitHub and local development HTTP calls

---

## 10. Notes for the Next Session

If another session opens this file:

1. Read this document and `PR-SENTRY-TODO.md`
2. Continue from the GitHub push / Actions test stage if the MVP is already complete
3. Otherwise, start with `slop_detector.py`
