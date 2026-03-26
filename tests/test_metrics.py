"""Tests for metrics.py"""

import pytest
import tempfile
import json
import os
from metrics import MetricsTracker, get_tracker


class TestMetricsTracker:
    """Test suite for MetricsTracker class."""

    def test_init_creates_directory(self):
        """Should create metrics directory on init."""
        with tempfile.TemporaryDirectory() as tmpdir:
            metrics_dir = os.path.join(tmpdir, "metrics")
            tracker = MetricsTracker(metrics_dir=metrics_dir)
            assert os.path.exists(metrics_dir)

    def test_track_pr_review_basic(self):
        """Should track basic PR review."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = MetricsTracker(metrics_dir=tmpdir)
            
            result = {
                "is_slop": False,
                "skipped_llm": False,
                "security_hints": [],
                "review": "Looks good",
                "routing_info": {
                    "model": "claude-haiku-4.5",
                    "cost_per_million": 1.0,
                },
            }
            
            tracker.track_pr_review("owner/repo", 123, result, tokens_used=1000)
            
            summary = tracker.get_session_summary()
            assert summary["prs_analyzed"] == 1
            assert summary["total_tokens"] == 1000
            assert summary["total_cost"] == 0.001  # 1000 tokens * $1/M

    def test_track_pr_review_slop(self):
        """Should track slop detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = MetricsTracker(metrics_dir=tmpdir)
            
            result = {
                "is_slop": True,
                "skipped_llm": True,
                "security_hints": [],
            }
            
            tracker.track_pr_review("owner/repo", 123, result)
            
            summary = tracker.get_session_summary()
            assert summary["slop_detected"] == 1
            assert summary["total_tokens"] == 0

    def test_track_pr_review_security(self):
        """Should track security issues."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = MetricsTracker(metrics_dir=tmpdir)
            
            result = {
                "is_slop": False,
                "skipped_llm": False,
                "security_hints": ["SQL injection", "XSS risk"],
                "review": "Found issues",
                "routing_info": {"model": "claude-sonnet-4.5", "cost_per_million": 3.0},
            }
            
            tracker.track_pr_review("owner/repo", 123, result, tokens_used=2000)
            
            summary = tracker.get_session_summary()
            assert summary["security_issues"] == 2

    def test_track_pr_review_model_usage(self):
        """Should track model usage statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = MetricsTracker(metrics_dir=tmpdir)
            
            # Track 2 Haiku reviews
            result_haiku = {
                "is_slop": False,
                "skipped_llm": False,
                "review": "OK",
                "routing_info": {"model": "claude-haiku-4.5", "cost_per_million": 1.0},
            }
            tracker.track_pr_review("owner/repo", 1, result_haiku, tokens_used=500)
            tracker.track_pr_review("owner/repo", 2, result_haiku, tokens_used=500)
            
            # Track 1 Sonnet review
            result_sonnet = {
                "is_slop": False,
                "skipped_llm": False,
                "review": "Complex review",
                "routing_info": {"model": "claude-sonnet-4.5", "cost_per_million": 3.0},
            }
            tracker.track_pr_review("owner/repo", 3, result_sonnet, tokens_used=1000)
            
            summary = tracker.get_session_summary()
            assert summary["models_used"]["claude-haiku-4.5"] == 2
            assert summary["models_used"]["claude-sonnet-4.5"] == 1

    def test_get_daily_stats(self):
        """Should get daily statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = MetricsTracker(metrics_dir=tmpdir)
            
            result = {
                "is_slop": False,
                "skipped_llm": False,
                "review": "Review",
                "routing_info": {"model": "claude-haiku-4.5", "cost_per_million": 1.0},
                "performance": {"pr_size": "small"},
            }
            
            tracker.track_pr_review("owner/repo", 1, result, tokens_used=1000)
            tracker.track_pr_review("owner/repo", 2, result, tokens_used=1000)
            
            daily = tracker.get_daily_stats()
            assert daily["prs_analyzed"] == 2
            assert daily["total_tokens"] == 2000
            assert daily["pr_sizes"]["small"] == 2

    def test_get_daily_stats_no_data(self):
        """Should return empty stats for missing date."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = MetricsTracker(metrics_dir=tmpdir)
            
            daily = tracker.get_daily_stats("2020-01-01")
            assert daily["prs_analyzed"] == 0
            assert daily["total_cost"] == 0.0

    def test_get_all_time_stats(self):
        """Should aggregate all-time statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = MetricsTracker(metrics_dir=tmpdir)
            
            result = {
                "is_slop": False,
                "skipped_llm": False,
                "review": "Review",
                "routing_info": {"model": "claude-haiku-4.5", "cost_per_million": 1.0},
            }
            
            tracker.track_pr_review("owner/repo", 1, result, tokens_used=1000)
            
            all_time = tracker.get_all_time_stats()
            assert all_time["prs_analyzed"] == 1
            assert len(all_time["daily_breakdown"]) == 1

    def test_format_stats_report(self):
        """Should format stats as readable report."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = MetricsTracker(metrics_dir=tmpdir)
            
            result = {
                "is_slop": False,
                "skipped_llm": False,
                "review": "Review",
                "routing_info": {"model": "claude-haiku-4.5", "cost_per_million": 1.0},
            }
            
            tracker.track_pr_review("owner/repo", 1, result, tokens_used=1000)
            
            summary = tracker.get_session_summary()
            report = tracker.format_stats_report(summary)
            
            assert "PR-Sentry Metrics Report" in report
            assert "PRs Analyzed: 1" in report
            assert "claude-haiku-4.5" in report

    def test_avg_cost_per_pr(self):
        """Should calculate average cost per PR."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = MetricsTracker(metrics_dir=tmpdir)
            
            result = {
                "is_slop": False,
                "skipped_llm": False,
                "review": "Review",
                "routing_info": {"model": "claude-sonnet-4.5", "cost_per_million": 3.0},
            }
            
            # 3 PRs with 1000 tokens each = $0.003 each
            tracker.track_pr_review("owner/repo", 1, result, tokens_used=1000)
            tracker.track_pr_review("owner/repo", 2, result, tokens_used=1000)
            tracker.track_pr_review("owner/repo", 3, result, tokens_used=1000)
            
            summary = tracker.get_session_summary()
            assert summary["prs_analyzed"] == 3
            assert round(summary["avg_cost_per_pr"], 6) == 0.003


class TestGetTracker:
    """Test suite for global tracker."""

    def test_get_tracker_singleton(self):
        """Should return same tracker instance."""
        tracker1 = get_tracker()
        tracker2 = get_tracker()
        assert tracker1 is tracker2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
