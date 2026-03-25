import re
from typing import Dict, List, Any
 
 
class SlopDetector:
    """
    Analyzes PR text (title, description, commit messages) and estimates
    the likelihood of "AI slop."

    It runs before any expensive Claude API call — a lightweight filter.
    """
 
    def __init__(self):
        # Common AI buzzwords
        self.ai_buzzwords = [
            "delve", "tapestry", "leverage", "utilize", "seamless",
            "robust", "ensure", "foster", "meticulous", "realm",
            "embark", "comprehensive", "vital", "crucial", "testament",
            "intricate", "paradigm", "underscore", "pivotal", "streamline",
            "cutting-edge", "synergy", "holistic", "actionable", "scalable"
        ]
 
        # Slop threshold: values above this are considered slop
        self.SLOP_THRESHOLD = 60
 
    def _calculate_ttr(self, text: str) -> float:
        """
        Compute the type-token ratio (TTR).

        Note: TTR naturally drops on longer texts, so we combine it with
        other metrics instead of using it alone.
        """
        words = re.findall(r'\b\w+\b', text.lower())
        if not words:
            return 1.0
        return len(set(words)) / len(words)
 
    def _count_buzzwords(self, text: str) -> int:
        """Return the number of AI buzzwords in the text."""
        text_lower = text.lower()
        return sum(1 for word in self.ai_buzzwords if re.search(rf'\b{word}\b', text_lower))
 
    def _parse_commit_messages(self, commits: List[str]) -> str:
        """Join a list of commit messages into a single string."""
        return " ".join(commits) if isinstance(commits, list) else str(commits)
 
    def evaluate_pr(
        self,
        title: str,
        body: str,
        commit_messages: List[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze PR data and return a slop score.
 
        Args:
            title: PR title
            body: PR description
            commit_messages: Optional list of commit messages
 
        Returns:
            {
                "is_slop": bool,
                "slop_score": int (0-100),
                "reason": str,
                "metrics": dict
            }
        """
        commits_text = self._parse_commit_messages(commit_messages or [])
        full_text = f"{title}\n{body}\n{commits_text}".strip()
        words = re.findall(r'\b\w+\b', full_text)
        word_count = len(words)
 
        # Very short PRs are unreliable to analyze — let Claude handle them
        if word_count < 20:
            return {
                "is_slop": False,
                "slop_score": 0,
                "reason": "Text is too short to analyze reliably; forwarding to Claude",
                "metrics": {"word_count": word_count}
            }
 
        ttr = self._calculate_ttr(full_text)
        buzzword_count = self._count_buzzwords(full_text)
 
        score = 0
        reasons = []
 
        # Rule 1: Buzzword density
        buzzword_density = buzzword_count / max(word_count / 100, 1)
        if buzzword_density >= 2:
            points = min(int(buzzword_density * 10), 40)
            score += points
            reasons.append(f"High AI buzzword density ({buzzword_count} terms)")

        # Rule 1b: Absolute buzzword count (density can mislead on short texts)
        if buzzword_count >= 5:
            score += 25
            reasons.append(f"Too many AI buzzwords ({buzzword_count} total)")
 
        # Rule 2: TTR + length combination
        # Short texts naturally have a high TTR, so we only look at low
        # TTR for longer texts (50+ words).
        if word_count > 50 and ttr < 0.40:
            score += 25
            reasons.append(f"Low lexical diversity (TTR: {round(ttr, 3)})")
 
        # Rule 3: Long + buzzword-heavy text (strongest signal)
        if word_count > 100 and buzzword_count >= 4:
            score += 20
            reasons.append("Long and buzzword-heavy description")
 
        final_score = min(max(int(score), 0), 100)
        is_slop = final_score >= self.SLOP_THRESHOLD
 
        return {
            "is_slop": is_slop,
            "slop_score": final_score,
            "reason": " | ".join(reasons) if reasons else "Looks clean",
            "metrics": {
                "word_count": word_count,
                "type_token_ratio": round(ttr, 3),
                "buzzword_count": buzzword_count,
                "buzzword_density": round(buzzword_density, 2)
            }
        }
 
 
# --- Test Area ---
if __name__ == "__main__":
    detector = SlopDetector()
 
    # Test 1: Typical AI PR
    ai_pr = detector.evaluate_pr(
        title="Feature: Robust and Seamless API Integration",
        body="""
        This PR ensures a robust and seamless integration of the new API.
        It is crucial to leverage these new endpoints to foster a comprehensive
        user experience. We delve into the intricate details of the meticulous
        refactoring process, which acts as a testament to our pivotal architecture.
        The scalable solution will streamline all future development efforts.
        """,
        commit_messages=["feat: ensure robust utilization of new endpoints"]
    )
    print("Test 1 (AI PR):")
    print(f"  Slop? {ai_pr['is_slop']} | Score: {ai_pr['slop_score']}")
    print(f"  Reason: {ai_pr['reason']}")
    print(f"  Metrics: {ai_pr['metrics']}\n")
 
    # Test 2: Human PR
    human_pr = detector.evaluate_pr(
        title="Fix null pointer in auth flow",
        body="Fixed the crash when token is None. Added a guard clause before assignment. Closes #42.",
        commit_messages=["fix: add null check before token assignment"]
    )
    print("Test 2 (Human PR):")
    print(f"  Slop? {human_pr['is_slop']} | Score: {human_pr['slop_score']}")
    print(f"  Reason: {human_pr['reason']}")
    print(f"  Metrics: {human_pr['metrics']}\n")
 
    # Test 3: Short PR
    short_pr = detector.evaluate_pr(
        title="Update README",
        body="Fixed typo.",
        commit_messages=[]
    )
    print("Test 3 (Short PR):")
    print(f"  Slop? {short_pr['is_slop']} | Score: {short_pr['slop_score']}")
    print(f"  Reason: {short_pr['reason']}")
 
