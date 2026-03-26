"""
Multi-LLM Router for PR-Sentry.

Smart model selection with cascading logic:
- Tier 1 (Default): Claude Haiku → Sonnet (single Anthropic key)
- Tier 2 (Advanced): DeepSeek → Claude (optional cost optimization)

Zero friction: works with just Anthropic key.
Advanced users can add DeepSeek for 60% cost reduction.
"""

import os
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ModelConfig:
    """Model configuration with cost and performance characteristics."""
    provider: str
    model: str
    cost_per_million: float  # Input tokens
    speed: str  # "fast", "medium", "slow"
    description: str


class LLMRouter:
    """
    Smart LLM routing with cascading logic.
    
    Strategy:
    1. AI slop detected? Skip LLM entirely ($0 cost)
    2. Only Anthropic key? Use Claude Haiku→Sonnet cascade
    3. DeepSeek key available? Use DeepSeek→Claude cascade (60% cost reduction)
    """
    
    # Model configurations
    MODELS = {
        "ultra-cheap": ModelConfig(
            provider="deepseek",
            model="deepseek-v3",
            cost_per_million=0.25,
            speed="fast",
            description="Ultra-cheap model for simple PRs"
        ),
        "cheap": ModelConfig(
            provider="anthropic",
            model="claude-haiku-4.5",
            cost_per_million=1.00,
            speed="fast",
            description="Fast Claude model for simple PRs"
        ),
        "premium": ModelConfig(
            provider="anthropic",
            model="claude-sonnet-4.5",
            cost_per_million=3.00,
            speed="medium",
            description="Powerful Claude model for security analysis"
        ),
    }
    
    # Security keywords that trigger deep analysis
    SECURITY_KEYWORDS = {
        # Memory safety
        "unsafe", "malloc", "free", "delete", "memcpy", "strcpy", "buffer",
        # Concurrency
        "thread", "mutex", "lock", "atomic", "race", "deadlock",
        # Crypto
        "encrypt", "decrypt", "hash", "crypto", "password", "secret", "key",
        # Web security
        "sql", "query", "exec", "eval", "innerHTML", "dangerouslySet",
        # Auth
        "auth", "token", "session", "cookie", "jwt", "oauth",
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize router with optional configuration."""
        self.config = config or {}
        
        # Check available API keys
        self.has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY", "").strip())
        self.has_deepseek = bool(os.getenv("DEEPSEEK_API_KEY", "").strip())
        self.has_openai = bool(os.getenv("OPENAI_API_KEY", "").strip())
        
        if not self.has_anthropic:
            raise ValueError(
                "ANTHROPIC_API_KEY is required. "
                "Get your key from: https://console.anthropic.com/"
            )
    
    def select_model(
        self,
        pr_analysis: Dict[str, Any]
    ) -> Optional[ModelConfig]:
        """
        Select the best model based on PR characteristics.
        
        Args:
            pr_analysis: Dict containing:
                - is_slop: bool (AI-generated content detected)
                - has_security_patterns: bool (security-related changes)
                - file_count: int
                - complexity_score: int (0-10)
                - diff_content: str (for keyword detection)
        
        Returns:
            ModelConfig or None (if LLM should be skipped)
        """
        # Rule 1: AI slop? Skip LLM entirely
        if pr_analysis.get("is_slop", False):
            return None
        
        # Rule 2: Security patterns detected? Always use premium
        if pr_analysis.get("has_security_patterns", False):
            return self.MODELS["premium"]
        
        # Rule 3: Check for security keywords in diff
        diff_content = pr_analysis.get("diff_content", "").lower()
        has_security_keywords = any(
            keyword in diff_content 
            for keyword in self.SECURITY_KEYWORDS
        )
        
        if has_security_keywords:
            return self.MODELS["premium"]
        
        # Rule 4: Simple PR? Use cheap model
        file_count = pr_analysis.get("file_count", 0)
        complexity = pr_analysis.get("complexity_score", 0)
        
        is_simple = file_count < 5 and complexity < 3
        
        # Route based on available providers
        if is_simple:
            # Simple PR: use cheapest available
            if self.has_deepseek:
                return self.MODELS["ultra-cheap"]
            else:
                return self.MODELS["cheap"]  # Claude Haiku
        else:
            # Complex PR: use premium for safety
            return self.MODELS["premium"]
    
    def estimate_cost(
        self,
        model: ModelConfig,
        estimated_tokens: int
    ) -> float:
        """
        Estimate API cost for a given model and token count.
        
        Args:
            model: Selected model config
            estimated_tokens: Approximate input token count
        
        Returns:
            Estimated cost in USD
        """
        return (estimated_tokens / 1_000_000) * model.cost_per_million
    
    def get_provider_priority(self) -> list:
        """
        Get list of available providers in priority order.
        
        Returns:
            List of provider names
        """
        providers = []
        
        # Always have Anthropic (required)
        providers.append("anthropic")
        
        # Add optional providers
        if self.has_deepseek:
            providers.append("deepseek")
        
        if self.has_openai:
            providers.append("openai")
        
        return providers
    
    def should_skip_llm(self, pr_analysis: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Determine if LLM call should be skipped entirely.
        
        Args:
            pr_analysis: PR analysis results
        
        Returns:
            (should_skip, reason)
        """
        # AI slop? Skip and tag
        if pr_analysis.get("is_slop", False):
            slop_score = pr_analysis.get("slop_score", 0)
            return True, f"AI-generated content detected (score: {slop_score}/100)"
        
        # Empty PR? Skip
        if pr_analysis.get("file_count", 0) == 0:
            return True, "No files changed"
        
        # All files ignored? Skip
        if pr_analysis.get("all_files_ignored", False):
            return True, "All files match ignore patterns"
        
        return False, ""
    
    def get_cost_savings_message(self) -> str:
        """
        Get a message about potential cost savings if user adds more providers.
        
        Returns:
            Helpful message about optimization
        """
        if self.has_deepseek:
            return "✅ DeepSeek enabled — saving up to 60% on API costs"
        else:
            return (
                "💡 Want to reduce costs by 60%? Add DEEPSEEK_API_KEY "
                "(optional, see README)"
            )


def calculate_pr_complexity(parsed_files: list) -> int:
    """
    Calculate PR complexity score (0-10).
    
    Factors:
    - Number of files
    - Lines changed
    - Number of functions/classes touched
    
    Args:
        parsed_files: List of parsed file dicts from diff_parser
    
    Returns:
        Complexity score 0-10
    """
    if not parsed_files:
        return 0
    
    file_count = len(parsed_files)
    total_lines = sum(len(f.get("changes", "").split("\n")) for f in parsed_files)
    
    # Simple heuristic
    complexity = 0
    
    # File count contribution (0-4 points)
    if file_count > 20:
        complexity += 4
    elif file_count > 10:
        complexity += 3
    elif file_count > 5:
        complexity += 2
    elif file_count > 2:
        complexity += 1
    
    # Lines changed contribution (0-4 points)
    if total_lines > 1000:
        complexity += 4
    elif total_lines > 500:
        complexity += 3
    elif total_lines > 200:
        complexity += 2
    elif total_lines > 50:
        complexity += 1
    
    # Security patterns contribution (0-2 points)
    has_security = any(
        len(f.get("security_hints", [])) > 0 
        for f in parsed_files
    )
    if has_security:
        complexity += 2
    
    return min(complexity, 10)


if __name__ == "__main__":
    # Example usage
    router = LLMRouter()
    
    # Test case 1: Simple PR
    simple_pr = {
        "is_slop": False,
        "has_security_patterns": False,
        "file_count": 2,
        "complexity_score": 1,
        "diff_content": "function hello() { return 'world'; }"
    }
    
    model = router.select_model(simple_pr)
    if model:
        print(f"Simple PR → {model.provider}/{model.model} (${model.cost_per_million}/M tokens)")
    
    # Test case 2: Security PR
    security_pr = {
        "is_slop": False,
        "has_security_patterns": True,
        "file_count": 5,
        "complexity_score": 7,
        "diff_content": "const token = localStorage.getItem('auth_token');"
    }
    
    model = router.select_model(security_pr)
    if model:
        print(f"Security PR → {model.provider}/{model.model} (${model.cost_per_million}/M tokens)")
    
    # Test case 3: AI slop
    slop_pr = {
        "is_slop": True,
        "slop_score": 85,
    }
    
    model = router.select_model(slop_pr)
    print(f"AI Slop → {'Skipped (no LLM call)' if model is None else model.model}")
    
    print(f"\n{router.get_cost_savings_message()}")
