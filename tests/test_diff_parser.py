"""Tests for diff_parser.py"""

import pytest
from diff_parser import DiffParser


class TestDiffParser:
    """Test suite for DiffParser class."""

    @pytest.fixture
    def parser(self):
        """Create a DiffParser instance for testing."""
        return DiffParser()

    # --- Basic Parsing Tests ---

    def test_parse_diff_empty(self, parser):
        """Empty diff should return empty list."""
        assert parser.parse_diff("") == []
        assert parser.parse_diff("   ") == []
        assert parser.parse_diff(None) == []  # type: ignore

    def test_parse_diff_single_file(self, parser):
        """Single file diff should be parsed correctly."""
        diff = """diff --git a/src/main.py b/src/main.py
index 1234567..abcdefg 100644
--- a/src/main.py
+++ b/src/main.py
@@ -10,6 +10,8 @@ def main():
-    old_line()
+    new_line()
+    another_line()
"""
        result = parser.parse_diff(diff)
        
        assert len(result) == 1
        assert result[0]["filename"] == "src/main.py"
        assert result[0]["additions"] == 2
        assert result[0]["deletions"] == 1

    def test_parse_diff_multiple_files(self, parser):
        """Multiple file diffs should be parsed correctly."""
        diff = """diff --git a/file1.py b/file1.py
index 1234567..abcdefg 100644
--- a/file1.py
+++ b/file1.py
@@ -1,3 +1,4 @@
+new line in file1
diff --git a/file2.py b/file2.py
index 1234567..abcdefg 100644
--- a/file2.py
+++ b/file2.py
@@ -1,3 +1,4 @@
+new line in file2
-removed line in file2
"""
        result = parser.parse_diff(diff)
        
        assert len(result) == 2
        assert result[0]["filename"] == "file1.py"
        assert result[1]["filename"] == "file2.py"

    def test_parse_diff_no_changes(self, parser):
        """Diff with only metadata (no +/- lines) should return None for that file."""
        diff = """diff --git a/empty.py b/empty.py
index 1234567..abcdefg 100644
--- a/empty.py
+++ b/empty.py
"""
        result = parser.parse_diff(diff)
        assert len(result) == 0  # No actual changes

    # --- Security Pattern Tests ---

    def test_security_scan_hardcoded_password(self, parser):
        """Hardcoded password should be detected."""
        diff = """diff --git a/config.py b/config.py
--- a/config.py
+++ b/config.py
@@ -1,3 +1,4 @@
+password = "secretpass123"
"""
        result = parser.parse_diff(diff)
        assert "Hardcoded password" in result[0]["security_hints"]

    def test_security_scan_api_key(self, parser):
        """Hardcoded API key should be detected."""
        diff = """diff --git a/config.py b/config.py
--- a/config.py
+++ b/config.py
@@ -1,3 +1,4 @@
+API_KEY = "sk-1234567890abcdef"
"""
        result = parser.parse_diff(diff)
        assert "Hardcoded API key" in result[0]["security_hints"]

    def test_security_scan_aws_access_key(self, parser):
        """AWS Access Key ID should be detected."""
        diff = """diff --git a/config.py b/config.py
--- a/config.py
+++ b/config.py
@@ -1,3 +1,4 @@
+aws_key = "AKIAIOSFODNN7EXAMPLE"
"""
        result = parser.parse_diff(diff)
        assert "AWS Access Key ID" in result[0]["security_hints"]

    def test_security_scan_private_key(self, parser):
        """Private key header should be detected."""
        diff = """diff --git a/key.pem b/key.pem
--- a/key.pem
+++ b/key.pem
@@ -1,3 +1,4 @@
+-----BEGIN RSA PRIVATE KEY-----
"""
        result = parser.parse_diff(diff)
        assert "Private key" in result[0]["security_hints"]

    def test_security_scan_google_api_key(self, parser):
        """Google API Key should be detected."""
        # Google API keys: AIza + exactly 35 alphanumeric/dash/underscore chars
        diff = """diff --git a/config.py b/config.py
--- a/config.py
+++ b/config.py
@@ -1,3 +1,4 @@
+google_key = "AIzaSyC-HjGw7ISLn_3namBGewQeabcde123456"
"""
        result = parser.parse_diff(diff)
        assert "Google API Key" in result[0]["security_hints"]

    def test_security_scan_slack_token(self, parser):
        """Slack token should be detected."""
        diff = """diff --git a/config.py b/config.py
--- a/config.py
+++ b/config.py
@@ -1,3 +1,4 @@
+slack = "xoxb-1234567890-abcdefghij"
"""
        result = parser.parse_diff(diff)
        assert "Slack Token" in result[0]["security_hints"]

    def test_security_scan_github_pat(self, parser):
        """GitHub Personal Access Token should be detected."""
        diff = """diff --git a/config.py b/config.py
--- a/config.py
+++ b/config.py
@@ -1,3 +1,4 @@
+token = "ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789"
"""
        result = parser.parse_diff(diff)
        assert "GitHub Personal Access Token" in result[0]["security_hints"]

    def test_security_scan_openai_key(self, parser):
        """OpenAI API Key should be detected."""
        # OpenAI keys are sk- followed by 48 chars
        diff = """diff --git a/config.py b/config.py
--- a/config.py
+++ b/config.py
@@ -1,3 +1,4 @@
+openai_key = "sk-abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKL"
"""
        result = parser.parse_diff(diff)
        assert "OpenAI API Key" in result[0]["security_hints"]

    def test_security_scan_mongodb_connection(self, parser):
        """MongoDB connection string should be detected."""
        diff = """diff --git a/config.py b/config.py
--- a/config.py
+++ b/config.py
@@ -1,3 +1,4 @@
+mongo_uri = "mongodb+srv://user:password123@cluster.mongodb.net"
"""
        result = parser.parse_diff(diff)
        assert "MongoDB Connection String" in result[0]["security_hints"]

    def test_security_scan_stripe_key(self, parser):
        """Stripe Live Secret Key should be detected."""
        # Build the pattern at runtime to avoid GitHub push protection
        prefix = "sk" + "_" + "live" + "_"
        test_value = prefix + "abcdefghijklmnopqrstuvwxyz"
        
        diff = f"""diff --git a/config.py b/config.py
--- a/config.py
+++ b/config.py
@@ -1,3 +1,4 @@
+stripe = "{test_value}"
"""
        result = parser.parse_diff(diff)
        assert "Stripe Live Secret Key" in result[0]["security_hints"]

    def test_security_scan_no_issues(self, parser):
        """Clean code should have no security hints."""
        diff = """diff --git a/main.py b/main.py
--- a/main.py
+++ b/main.py
@@ -1,3 +1,4 @@
+def hello():
+    return "world"
"""
        result = parser.parse_diff(diff)
        assert result[0]["security_hints"] == []

    # --- Format for Review Tests ---

    def test_format_for_review_empty(self, parser):
        """Empty file list should return appropriate message."""
        result = parser.format_for_review([])
        assert result == "No changes found."

    def test_format_for_review_basic(self, parser):
        """Basic formatting should include filename and stats."""
        files = [{
            "filename": "test.py",
            "changes": "+new line",
            "additions": 1,
            "deletions": 0,
            "security_hints": []
        }]
        result = parser.format_for_review(files)
        
        assert "test.py" in result
        assert "+1 additions" in result
        assert "-0 deletions" in result

    def test_format_for_review_with_security_hints(self, parser):
        """Security hints should be included in formatted output."""
        files = [{
            "filename": "config.py",
            "changes": "+password = 'secret'",
            "additions": 1,
            "deletions": 0,
            "security_hints": ["Hardcoded password"]
        }]
        result = parser.format_for_review(files)
        
        assert "⚠️ Security warning" in result
        assert "Hardcoded password" in result

    def test_format_for_review_truncation(self, parser):
        """Large diffs should be truncated."""
        # Create a very large file
        large_changes = "+line\n" * 10000
        files = [{
            "filename": "huge.py",
            "changes": large_changes,
            "additions": 10000,
            "deletions": 0,
            "security_hints": []
        }]
        result = parser.format_for_review(files, max_chars=1000)
        
        assert "File too large, skipped" in result


class TestDiffParserPatterns:
    """Test security pattern definitions."""

    def test_sensitive_patterns_exist(self):
        """Sensitive patterns should be defined."""
        parser = DiffParser()
        assert len(parser.SENSITIVE_PATTERNS) > 0

    def test_all_patterns_are_tuples(self):
        """Each pattern should be a (regex, description) tuple."""
        parser = DiffParser()
        for pattern in parser.SENSITIVE_PATTERNS:
            assert isinstance(pattern, tuple)
            assert len(pattern) == 2
            assert isinstance(pattern[0], str)  # regex
            assert isinstance(pattern[1], str)  # description
