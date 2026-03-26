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

load_dotenv()

# Provider selection: production or development
ALLOWED_PROVIDERS = {"anthropic", "development"}
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4.5"  # Updated default to Sonnet


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


def _call_development_model(prompt: str, api_key: str, system_prompt: str = None) -> str:
    """Development API call for local testing with exponential backoff."""
    import time
    import random

    max_retries = 5
    base_delay = 1.0
    max_delay = 60.0
    
    effective_prompt = system_prompt or SYSTEM_PROMPT

    payload = json.dumps({
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": effective_prompt},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1000,
        "temperature": 0.2
    }).encode("utf-8")

    for attempt in range(max_retries):
        request = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
            break  # Success, exit retry loop
        except urllib.error.HTTPError as e:
            # Retry on rate limit (429) or server errors (5xx)
            if e.code in (429, 500, 502, 503, 504) and attempt < max_retries - 1:
                delay = min(base_delay * (2 ** attempt), max_delay)
                jitter = delay * 0.25 * (2 * random.random() - 1)
                time.sleep(delay + jitter)
                continue
            raise RuntimeError(f"OpenAI API error: {e.code} — {e.reason}") from e
        except urllib.error.URLError as e:
            if attempt < max_retries - 1:
                delay = min(base_delay * (2 ** attempt), max_delay)
                jitter = delay * 0.25 * (2 * random.random() - 1)
                time.sleep(delay + jitter)
                continue
            raise RuntimeError(f"Network error calling OpenAI: {e.reason}") from e
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON response from OpenAI: {e}") from e

    choices = data.get("choices")
    if not isinstance(choices, list) or len(choices) == 0:
        raise RuntimeError(f"Unexpected OpenAI response format: {data}")

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise RuntimeError(f"Unexpected OpenAI response format: {data}")

    message = first_choice.get("message")
    if not isinstance(message, dict) or "content" not in message:
        raise RuntimeError(f"Unexpected OpenAI response format: {data}")

    return message["content"]


def _call_anthropic(prompt: str, api_key: str, model: str, system_prompt: str = None) -> str:
    """Anthropic API call for production with exponential backoff."""
    import anthropic
    import time
    import random

    max_retries = 5
    base_delay = 1.0
    max_delay = 60.0
    
    effective_prompt = system_prompt or SYSTEM_PROMPT

    for attempt in range(max_retries):
        try:
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model=model,
                max_tokens=1000,
                system=effective_prompt,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except anthropic.RateLimitError as e:
            if attempt < max_retries - 1:
                # Exponential backoff: 1, 2, 4, 8, 16... capped at max_delay
                delay = min(base_delay * (2 ** attempt), max_delay)
                # Add jitter (±25%) to prevent thundering herd
                jitter = delay * 0.25 * (2 * random.random() - 1)
                time.sleep(delay + jitter)
                continue
            raise RuntimeError(f"Anthropic rate limit exceeded after {max_retries} attempts: {e}") from e
        except anthropic.APIError as e:
            if attempt < max_retries - 1:
                delay = min(base_delay * (2 ** attempt), max_delay)
                jitter = delay * 0.25 * (2 * random.random() - 1)
                time.sleep(delay + jitter)
                continue
            raise RuntimeError(f"Anthropic API error: {e}") from e


class Reviewer:
    """
    Main module that combines slop_detector, diff_parser, and the LLM API.
    Supports custom configuration via sentry-config.yml.
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
        dev_llm_api_key: Optional[str] = None,
        anthropic_model: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.slop_detector = SlopDetector()
        self.diff_parser = DiffParser()
        self.config = config or load_config()
        
        # Initialize LLM router for smart model selection
        try:
            self.llm_router = LLMRouter(config=self.config)
        except ValueError:
            # No Anthropic key - will fail later if trying to use
            self.llm_router = None
        
        self.provider = (provider or "").strip()
        if self.provider not in ALLOWED_PROVIDERS:
            raise ValueError(f"Invalid REVIEWER_PROVIDER: {self.provider}. Use 'anthropic' or 'development'.")
        self.anthropic_api_key = (anthropic_api_key or "").strip()
        self.dev_llm_api_key = (dev_llm_api_key or "").strip()
        self.anthropic_model = (anthropic_model or DEFAULT_ANTHROPIC_MODEL).strip() or DEFAULT_ANTHROPIC_MODEL
        
        # Build custom system prompt with user rules
        self.system_prompt = SYSTEM_PROMPT + build_custom_prompt_additions(self.config)
        
        # Update slop threshold from config
        if "slop_threshold" in self.config:
            self.slop_detector.SLOP_THRESHOLD = self.config["slop_threshold"]

        if self.provider == "anthropic" and not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required when provider='anthropic'.")

        if self.provider == "development" and not self.dev_llm_api_key:
            raise ValueError("DEV_LLM_API_KEY is required when provider='development'.")

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
                "provider": self.provider,
                "skipped_llm": True
            }

        # Step 2: Parse the diff
        parsed_files = self.diff_parser.parse_diff(raw_diff)
        
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
        
        # Step 2.5: Smart model selection (if using router)
        selected_model = None
        if self.llm_router and self.provider == "anthropic":
            max_diff_size = self.config.get("max_diff_size", 12000)
            formatted_diff_preview = self.diff_parser.format_for_review(filtered_files, max_chars=max_diff_size)
            
            pr_analysis = {
                "is_slop": False,  # Already checked above
                "has_security_patterns": has_security_patterns,
                "file_count": len(filtered_files),
                "complexity_score": complexity_score,
                "diff_content": formatted_diff_preview
            }
            
            # Check if we should skip LLM entirely
            should_skip, skip_reason = self.llm_router.should_skip_llm(pr_analysis)
            if should_skip:
                return {
                    "is_slop": False,
                    "slop_score": slop_result["slop_score"],
                    "security_hints": all_hints,
                    "review": f"ℹ️ LLM review skipped: {skip_reason}",
                    "provider": self.provider,
                    "skipped_llm": True,
                    "routing_info": {
                        "reason": skip_reason,
                        "complexity": complexity_score
                    }
                }
            
            # Select best model
            selected_model = self.llm_router.select_model(pr_analysis)
            if selected_model:
                # Override the model if router suggests something different
                if selected_model.provider == "anthropic":
                    self.anthropic_model = selected_model.model
        
        max_diff_size = self.config.get("max_diff_size", 12000)
        formatted_diff = self.diff_parser.format_for_review(filtered_files, max_chars=max_diff_size)

        # Step 3: LLM review
        prompt = f"""PR Title: {title}

PR Description:
{body}

Code Changes:
{formatted_diff}"""

        if self.provider == "anthropic":
            review_text = _call_anthropic(prompt, self.anthropic_api_key, self.anthropic_model, self.system_prompt)
        elif self.provider == "development":
            review_text = _call_development_model(prompt, self.dev_llm_api_key, self.system_prompt)
        else:
            raise RuntimeError(f"Invalid reviewer provider state: {self.provider}")

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
            "provider": self.provider,
            "skipped_llm": False,
            "routing_info": {
                "model": selected_model.model if selected_model else self.anthropic_model,
                "provider": selected_model.provider if selected_model else self.provider,
                "complexity": complexity_score,
                "cost_per_million": selected_model.cost_per_million if selected_model else 3.0
            } if selected_model or self.llm_router else {}
        }

    def _generate_summary(self, title: str, body: str, files: list) -> str:
        """Generate a brief summary of the PR changes."""
        # Build a lightweight summary without LLM for simple cases
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
    reviewer = Reviewer(
        provider=os.getenv("REVIEWER_PROVIDER", "anthropic"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        dev_llm_api_key=os.getenv("DEV_LLM_API_KEY"),
        anthropic_model=os.getenv("ANTHROPIC_MODEL", DEFAULT_ANTHROPIC_MODEL),
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
    print(f"\nReview:\n{result['review']}")
