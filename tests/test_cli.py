"""Tests for CLI module."""

import pytest
from unittest.mock import patch, MagicMock
import sys
import io

import cli


class TestCLIHelp:
    """Test CLI help and version."""
    
    def test_help_text(self):
        """Test --help doesn't crash."""
        with patch.object(sys, 'argv', ['pr-sentry', '--help']):
            with pytest.raises(SystemExit) as exc:
                cli.main()
            assert exc.value.code == 0
    
    def test_version(self):
        """Test --version shows version."""
        with patch.object(sys, 'argv', ['pr-sentry', '--version']):
            with pytest.raises(SystemExit) as exc:
                cli.main()
            assert exc.value.code == 0
    
    def test_no_command_shows_help(self):
        """Test running without command shows help."""
        with patch.object(sys, 'argv', ['pr-sentry']):
            with pytest.raises(SystemExit) as exc:
                cli.main()
            assert exc.value.code == 1


class TestFormatResult:
    """Test result formatting."""
    
    def test_format_empty_result(self):
        """Test formatting empty result."""
        result = {}
        output = cli.format_result(result)
        assert "PR-Sentry Review Result" in output
    
    def test_format_slop_detected(self):
        """Test formatting slop detection."""
        result = {
            "is_slop": True,
            "slop_score": 85
        }
        output = cli.format_result(result)
        assert "AI SLOP DETECTED" in output
        assert "85" in output
    
    def test_format_security_hints(self):
        """Test formatting security hints."""
        result = {
            "security_hints": [
                "SQL injection risk",
                "Hardcoded secret detected"
            ]
        }
        output = cli.format_result(result)
        assert "Security Issues" in output
        assert "SQL injection risk" in output
        assert "Hardcoded secret detected" in output
    
    def test_format_review_text(self):
        """Test formatting review text."""
        result = {
            "review": "Code looks good overall."
        }
        output = cli.format_result(result)
        assert "Review:" in output
        assert "Code looks good overall." in output
    
    def test_format_routing_info(self):
        """Test formatting routing info."""
        result = {
            "routing_info": {
                "model": "claude-sonnet-4-20250514",
                "cost_per_million": 3.0
            }
        }
        output = cli.format_result(result)
        assert "claude-sonnet-4-20250514" in output
        assert "Cost:" in output
    
    def test_format_full_result(self):
        """Test formatting complete result."""
        result = {
            "is_slop": False,
            "slop_score": 25,
            "security_hints": ["XSS risk"],
            "review": "Check user input sanitization",
            "summary": "1 security issue found",
            "routing_info": {
                "model": "claude-haiku-3-5-20241022",
                "cost_per_million": 1.0
            }
        }
        output = cli.format_result(result)
        assert "XSS risk" in output
        assert "Check user input" in output
        assert "1 security issue" in output


class TestReviewCommand:
    """Test review command."""
    
    def test_review_requires_token(self):
        """Test review without token fails."""
        with patch.object(sys, 'argv', ['pr-sentry', 'review', '--repo', 'o/r', '--pr', '1']):
            with patch.dict('os.environ', {}, clear=True):
                with pytest.raises(SystemExit) as exc:
                    cli.main()
                assert exc.value.code == 1
    
    def test_review_requires_repo(self):
        """Test review without repo fails."""
        with patch.object(sys, 'argv', ['pr-sentry', 'review', '--pr', '1']):
            with patch.dict('os.environ', {'GITHUB_TOKEN': 'test'}):
                with pytest.raises(SystemExit) as exc:
                    cli.main()
                assert exc.value.code == 1
    
    def test_review_gitlab_requires_token(self):
        """Test GitLab review without token fails."""
        with patch.object(sys, 'argv', ['pr-sentry', 'review', '--gitlab', '--project-id', '123', '--pr', '1']):
            with patch.dict('os.environ', {}, clear=True):
                with pytest.raises(SystemExit) as exc:
                    cli.main()
                assert exc.value.code == 1


class TestAnalyzeCommand:
    """Test analyze command."""
    
    def test_analyze_empty_stdin(self):
        """Test analyze with empty stdin fails."""
        with patch.object(sys, 'argv', ['pr-sentry', 'analyze']):
            with patch.object(sys, 'stdin', io.StringIO('')):
                with pytest.raises(SystemExit) as exc:
                    cli.main()
                assert exc.value.code == 1


class TestStatsCommand:
    """Test stats command."""
    
    @patch('metrics.MetricsTracker')
    def test_stats_daily(self, mock_tracker_class):
        """Test daily stats."""
        mock_tracker = MagicMock()
        mock_tracker.get_daily_stats.return_value = {}
        mock_tracker.format_stats_report.return_value = "Daily stats"
        mock_tracker_class.return_value = mock_tracker
        
        with patch('builtins.print') as mock_print:
            cli.show_stats(daily=True)
            mock_print.assert_called()
    
    @patch('metrics.MetricsTracker')
    def test_stats_all_time(self, mock_tracker_class):
        """Test all-time stats."""
        mock_tracker = MagicMock()
        mock_tracker.get_all_time_stats.return_value = {}
        mock_tracker.format_stats_report.return_value = "All time stats"
        mock_tracker_class.return_value = mock_tracker
        
        with patch('builtins.print') as mock_print:
            cli.show_stats(all_time=True)
            mock_print.assert_called()
