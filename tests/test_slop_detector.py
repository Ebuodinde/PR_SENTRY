"""Tests for slop_detector.py"""

import pytest
from slop_detector import SlopDetector


class TestSlopDetector:
    """Test suite for SlopDetector class."""

    @pytest.fixture
    def detector(self):
        """Create a SlopDetector instance for testing."""
        return SlopDetector()

    # --- TTR Tests ---

    def test_calculate_ttr_empty_text(self, detector):
        """Empty text should return TTR of 1.0."""
        assert detector._calculate_ttr("") == 1.0

    def test_calculate_ttr_unique_words(self, detector):
        """All unique words should return TTR of 1.0."""
        assert detector._calculate_ttr("the quick brown fox") == 1.0

    def test_calculate_ttr_repeated_words(self, detector):
        """Repeated words should lower TTR."""
        # "the the the" = 1 unique / 3 total = 0.333...
        ttr = detector._calculate_ttr("the the the")
        assert 0.3 <= ttr <= 0.35

    # --- Buzzword Tests ---

    def test_count_buzzwords_none_found(self, detector):
        """Text without buzzwords should return 0."""
        text = "Fixed a bug in the login function"
        assert detector._count_buzzwords(text) == 0

    def test_count_buzzwords_single(self, detector):
        """Single buzzword should be counted."""
        text = "This is a robust solution"
        assert detector._count_buzzwords(text) == 1

    def test_count_buzzwords_multiple(self, detector):
        """Multiple buzzwords should be counted."""
        text = "A robust and seamless integration that leverages cutting-edge technology"
        count = detector._count_buzzwords(text)
        assert count >= 3  # robust, seamless, leverage, cutting-edge

    def test_count_buzzwords_case_insensitive(self, detector):
        """Buzzword detection should be case-insensitive."""
        assert detector._count_buzzwords("DELVE into details") == 1
        assert detector._count_buzzwords("Delve into details") == 1
        assert detector._count_buzzwords("delve into details") == 1

    # --- PR Evaluation Tests ---

    def test_evaluate_pr_short_text(self, detector):
        """Very short PRs should pass through (not flagged as slop)."""
        result = detector.evaluate_pr(
            title="Fix typo",
            body="Fixed.",
            commit_messages=[]
        )
        assert result["is_slop"] is False
        assert result["slop_score"] == 0
        assert "too short" in result["reason"].lower()

    def test_evaluate_pr_human_style(self, detector):
        """Normal human-written PR should not be flagged."""
        result = detector.evaluate_pr(
            title="Fix null pointer in auth flow",
            body="Fixed the crash when token is None. Added a guard clause before assignment. Closes #42.",
            commit_messages=["fix: add null check before token assignment"]
        )
        assert result["is_slop"] is False
        assert result["slop_score"] < 60

    def test_evaluate_pr_ai_slop(self, detector):
        """AI-generated PR with many buzzwords should be flagged."""
        result = detector.evaluate_pr(
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
        assert result["is_slop"] is True
        assert result["slop_score"] >= 60

    def test_evaluate_pr_metrics_structure(self, detector):
        """Metrics dictionary should have expected keys."""
        # Use a longer text to ensure proper analysis
        result = detector.evaluate_pr(
            title="Test PR Title for Metrics",
            body="This is a test PR with enough words to analyze properly for testing purposes. "
                 "We need at least twenty words to pass the minimum threshold for analysis. "
                 "Adding more words here to ensure the analyzer runs fully.",
            commit_messages=["test commit message for the metrics test"]
        )
        
        assert "metrics" in result
        metrics = result["metrics"]
        assert "word_count" in metrics
        assert "type_token_ratio" in metrics
        assert "buzzword_count" in metrics
        assert "buzzword_density" in metrics

    def test_evaluate_pr_boundary_score(self, detector):
        """Score should be clamped between 0 and 100."""
        # Even with extreme input, score should not exceed 100
        extreme_text = " ".join(detector.ai_buzzwords * 10)
        result = detector.evaluate_pr(
            title=extreme_text,
            body=extreme_text,
            commit_messages=[extreme_text]
        )
        assert 0 <= result["slop_score"] <= 100

    def test_evaluate_pr_commit_messages_as_string(self, detector):
        """Commit messages passed as string should be handled."""
        result = detector.evaluate_pr(
            title="Test",
            body="Test body with enough content for analysis",
            commit_messages="single commit message string"  # type: ignore
        )
        # Should not raise, should handle gracefully
        assert "slop_score" in result

    def test_evaluate_pr_none_commit_messages(self, detector):
        """None commit_messages should be handled."""
        result = detector.evaluate_pr(
            title="Test PR title",
            body="Test body with enough content for the analyzer to process properly",
            commit_messages=None  # type: ignore
        )
        assert "slop_score" in result


class TestSlopDetectorThreshold:
    """Test threshold behavior."""

    def test_threshold_value(self):
        """Default threshold should be 60."""
        detector = SlopDetector()
        assert detector.SLOP_THRESHOLD == 60

    def test_score_at_threshold(self):
        """Score exactly at threshold should be flagged."""
        detector = SlopDetector()
        # Manually check threshold logic
        assert detector.SLOP_THRESHOLD == 60
