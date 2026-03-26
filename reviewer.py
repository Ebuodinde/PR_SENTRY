import json
import os
import urllib.error
import urllib.request
from typing import Dict, Any, Optional

from dotenv import load_dotenv
from slop_detector import SlopDetector
from diff_parser import DiffParser
from config_loader import load_config, build_custom_prompt_additions, should_ignore_file
from llm_router import LLMRouter, calculate_pr_complexity
from performance import PerformanceOptimizer, estimate_pr_size
from metrics import get_tracker
from providers import get_provider, ProviderConfig

load_dotenv()

# Supported providers
ALLOWED_PROVIDERS = {"anthropic", "openai", "deepseek"}


# Zero-Nitpick system prompt (base)
SYSTEM_PROMPT = """You are PR-Sentry, a security-focused code reviewer for open source projects.

STRICT RULES:
- NEVER comment on code style, formatting, whitespace, or variable naming
- NEVER suggest things a linter (ESLint, Prettier, Black, Pylint) would catch
- ONLY report issues that could cause: runtime crashes, security vulnerabilities, race conditions, or memory leaks
- If you find no critical issues, say so clearly and briefly
- Be direct. No long explanations. No praise. No filler.

REPORT FORMAT:
If issues found:
🔴 CRITICAL: [issue] — [file:line if known] — [one sentence why it matters]

If no critical issues:
✅ No critical issues found. [one sentence summary of what was reviewed]

Remember: A false positive that wastes a developer's time is worse than a missed minor issue."""


class Reviewer:
    """
    Main module that combines slop_detector, diff_parser, and the LLM API.
    Supports multiple LLM providers via the providers module.
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.slop_detector = SlopDetector()
        self.diff_parser = DiffParser()
        self.config = config or load_config()
        self.perf_optimizer = PerformanceOptimizer()
        
        # Validate provider
        self.provider_name = (provider or "").strip().lower()
        if self.provider_name and self.provider_name not in ALLOWED_PROVIDERS:
            raise ValueError(f"Invalid provider: {self.provider_name}. Use: {', '.join(ALLOWED_PROVIDERS)}")
        
        # Initialize provider
        if not api_key:
            raise ValueError(f"API key required for {self.provider_name or 'provider'}")
        
        self.llm_provider = get_provider(
            provider_name=self.provider_name or None,
            api_key=api_key,
            model=model,
        )
        self.provider_name = self.llm_provider.name
        
        # Initialize LLM router for smart model selection (optional)
        try:
            self.llm_router = LLMRouter(config=self.config)
        except ValueError:
            self.llm_router = None
        
        # Build custom system prompt with user rules
        self.system_prompt = SYSTEM_PROMPT + build_custom_prompt_additions(self.config)
        
        # Update slop threshold from config
        if "slop_threshold" in self.config:
            self.slop_detector.SLOP_THRESHOLD = self.config["slop_threshold"]

    def review_pr(
        self,
        title: str,
        body: str,
        commit_messages: list,
        raw_diff: str
    ) -> Dict[str, Any]:
        """
        Analyze the PR.

        1. Slop detection — cheap and API-free
        2. Diff parsing + security scan (with file filtering)
        3. LLM review — only called if the PR is not slop

        Returns:
            {
                "is_slop": bool,
                "slop_score": int,
                "security_hints": list,
                "review": str,
                "provider": str,
                "skipped_llm": bool
            }
        """

        # Step 1: Slop detection
        slop_result = self.slop_detector.evaluate_pr(title, body, commit_messages)

        if slop_result["is_slop"]:
            return {
                "is_slop": True,
                "slop_score": slop_result["slop_score"],
                "security_hints": [],
                "review": f"⚠️ This PR appears to contain a high amount of AI-generated content (score: {slop_result['slop_score']}/100). Human review is required.",
                "provider": self.provider_name,
                "skipped_llm": True
            }

        # Step 2: Parse the diff
        parsed_files = self.diff_parser.parse_diff(raw_diff)
        
        # Performance optimization: Smart file filtering for large PRs
        pr_size = estimate_pr_size(parsed_files)
        perf_stats = {}
        
        if pr_size in ["large", "xlarge"]:
            max_files = self.config.get("max_files_analyzed", 50)
            max_lines = self.config.get("max_lines_analyzed", 5000)
            parsed_files, perf_stats = self.perf_optimizer.filter_large_pr(
                parsed_files,
                max_files=max_files,
                max_lines=max_lines
            )
        
        # Filter out ignored files based on config
        filtered_files = [
            f for f in parsed_files 
            if not should_ignore_file(f["filename"], self.config)
        ]
        
        # Calculate PR complexity for routing
        complexity_score = calculate_pr_complexity(filtered_files)
        
        # Collect security warnings from all files
        all_hints = []
        for f in parsed_files:
            all_hints.extend(f["security_hints"])
        
        has_security_patterns = len(all_hints) > 0
        
        max_diff_size = self.config.get("max_diff_size", 12000)
        formatted_diff = self.diff_parser.format_for_review(filtered_files, max_chars=max_diff_size)

        # Step 3: LLM review using provider
        prompt = f"""PR Title: {title}

PR Description:
{body}

Code Changes:
{formatted_diff}"""

        try:
            response = self.llm_provider.review_code(prompt, self.system_prompt)
            review_text = response.content
            model_used = response.model
        except Exception as e:
            raise RuntimeError(f"LLM API error ({self.provider_name}): {e}")

        # Step 4: Generate PR summary (optional, based on config)
        summary_text = ""
        if self.config.get("enable_summary", True):
            summary_text = self._generate_summary(title, body, filtered_files)

        return {
            "is_slop": False,
            "slop_score": slop_result["slop_score"],
            "security_hints": all_hints,
            "review": review_text,
            "summary": summary_text,
            "provider": self.provider_name,
            "model": model_used,
            "skipped_llm": False,
            "performance": {
                "pr_size": pr_size,
                **perf_stats
            } if perf_stats else {"pr_size": pr_size}
        }

    def _generate_summary(self, title: str, body: str, files: list) -> str:
        """Generate a brief summary of the PR changes."""
        file_count = len(files)
        total_additions = sum(f["additions"] for f in files)
        total_deletions = sum(f["deletions"] for f in files)
        
        file_types = {}
        for f in files:
            ext = f["filename"].split(".")[-1] if "." in f["filename"] else "other"
            file_types[ext] = file_types.get(ext, 0) + 1
        
        type_summary = ", ".join(f"{count} {ext}" for ext, count in sorted(file_types.items(), key=lambda x: -x[1])[:3])
        
        summary = f"📊 **{file_count} files** changed (+{total_additions}/-{total_deletions})"
        if type_summary:
            summary += f" • {type_summary}"
        
        return summary


# --- Test Area ---
if __name__ == "__main__":
    # Auto-detect provider from environment
    provider = os.getenv("PR_SENTRY_PROVIDER", "")
    api_key = os.getenv("PR_SENTRY_API_KEY", "")
    
    # Fallback to provider-specific keys
    if not api_key:
        if os.getenv("ANTHROPIC_API_KEY"):
            provider = "anthropic"
            api_key = os.getenv("ANTHROPIC_API_KEY")
        elif os.getenv("OPENAI_API_KEY"):
            provider = "openai"
            api_key = os.getenv("OPENAI_API_KEY")
        elif os.getenv("DEEPSEEK_API_KEY"):
            provider = "deepseek"
            api_key = os.getenv("DEEPSEEK_API_KEY")
    
    if not api_key:
        print("Error: No API key found. Set ANTHROPIC_API_KEY, OPENAI_API_KEY, or DEEPSEEK_API_KEY")
        exit(1)
    
    reviewer = Reviewer(
        provider=provider,
        api_key=api_key,
        model=os.getenv("PR_SENTRY_MODEL"),
    )

    test_diff = """diff --git a/src/auth.py b/src/auth.py
index 1234567..abcdefg 100644
--- a/src/auth.py
+++ b/src/auth.py
@@ -10,6 +10,8 @@ def login(username, password):
     user = db.find_user(username)
-    if user.password == password:
+    if user and user.check_password(password):
         return generate_token(user)
+    return None
"""

    print("=== PR-Sentry Review Test ===\n")

    result = reviewer.review_pr(
        title="Fix authentication null pointer",
        body="Fixed the crash when user is not found. Added null check before password comparison.",
        commit_messages=["fix: add null check in login function"],
        raw_diff=test_diff
    )

    print(f"Slop? {result['is_slop']} (score: {result['slop_score']})")
    print(f"Security warnings: {result['security_hints'] or 'None'}")
    print(f"Provider: {result['provider']}")
    print(f"Model: {result.get('model', 'N/A')}")
    print(f"\nReview:\n{result['review']}")
