"""Tests for entropy_scanner.py"""

import pytest
from entropy_scanner import EntropyScanner


class TestEntropyCalculation:
    """Test Shannon entropy calculation."""

    @pytest.fixture
    def scanner(self):
        return EntropyScanner()

    def test_entropy_empty_string(self, scanner):
        """Empty string should have 0 entropy."""
        assert scanner.calculate_entropy("") == 0.0

    def test_entropy_single_char(self, scanner):
        """Single repeated char should have 0 entropy."""
        assert scanner.calculate_entropy("aaaaaaa") == 0.0

    def test_entropy_two_chars_equal(self, scanner):
        """Two equally distributed chars should have entropy of 1."""
        entropy = scanner.calculate_entropy("abababab")
        assert 0.99 <= entropy <= 1.01

    def test_entropy_high_random(self, scanner):
        """High entropy string (random-looking) should have high entropy."""
        # A realistic API key
        entropy = scanner.calculate_entropy("sk-proj-abc123XYZ789defGHI456jkl")
        assert entropy >= 4.0

    def test_entropy_low_pattern(self, scanner):
        """Patterned string should have lower entropy."""
        entropy = scanner.calculate_entropy("test1234test1234")
        assert entropy < 3.0


class TestEncodingDetection:
    """Test Base64 and Hex detection."""

    @pytest.fixture
    def scanner(self):
        return EntropyScanner()

    def test_is_base64_like_valid(self, scanner):
        """Valid Base64-like string should be detected."""
        assert scanner.is_base64_like("ABCDEFGHIJKLMNOPabcdef123456==") is True

    def test_is_base64_like_too_short(self, scanner):
        """Short string should not be detected."""
        assert scanner.is_base64_like("abc") is False

    def test_is_hex_like_valid(self, scanner):
        """Valid hex string should be detected."""
        assert scanner.is_hex_like("a1b2c3d4e5f6a7b8c9d0") is True

    def test_is_hex_like_invalid(self, scanner):
        """Non-hex string should not be detected."""
        assert scanner.is_hex_like("xyz123notahexstring") is False


class TestLineScanning:
    """Test scanning individual lines."""

    @pytest.fixture
    def scanner(self):
        return EntropyScanner()

    def test_scan_line_api_key(self, scanner):
        """API key in assignment should be detected."""
        line = 'API_KEY = "sk-proj-abc123XYZ789defGHI456jklMNO012pqr"'
        findings = scanner.scan_line(line)
        assert len(findings) >= 1

    def test_scan_line_jwt_token(self, scanner):
        """JWT token should be detected."""
        line = 'token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N"'
        findings = scanner.scan_line(line)
        assert len(findings) >= 1

    def test_scan_line_clean(self, scanner):
        """Clean code should have no findings."""
        line = 'def hello(): return "world"'
        findings = scanner.scan_line(line)
        assert len(findings) == 0

    def test_scan_line_uuid_ignored(self, scanner):
        """UUID should be ignored (false positive)."""
        line = 'id = "550e8400-e29b-41d4-a716-446655440000"'
        findings = scanner.scan_line(line)
        assert len(findings) == 0

    def test_scan_line_git_hash_ignored(self, scanner):
        """Git SHA should be ignored (false positive)."""
        line = 'commit = "da39a3ee5e6b4b0d3255bfef95601890afd80709"'
        findings = scanner.scan_line(line)
        assert len(findings) == 0


class TestTextScanning:
    """Test scanning multi-line text."""

    @pytest.fixture
    def scanner(self):
        return EntropyScanner()

    def test_scan_text_multiple_lines(self, scanner):
        """Multiple lines with secrets should be detected."""
        text = '''
config = {
    "api_key": "sk-proj-abc123XYZ789defGHI456jklMNO012pqr",
    "secret": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
}
'''
        findings = scanner.scan_text(text)
        # At least one high-entropy string should be detected
        assert len(findings) >= 1

    def test_scan_text_with_line_numbers(self, scanner):
        """Findings should include line numbers."""
        text = 'line1\nkey = "sk-proj-abc123XYZ789defGHI456jklMNO012pqr"\nline3'
        findings = scanner.scan_text(text)
        assert len(findings) >= 1
        assert findings[0]["line"] == 2

    def test_scan_text_empty(self, scanner):
        """Empty text should return no findings."""
        findings = scanner.scan_text("")
        assert len(findings) == 0


class TestFalsePositives:
    """Test false positive filtering."""

    @pytest.fixture
    def scanner(self):
        return EntropyScanner()

    def test_url_path_ignored(self, scanner):
        """URL paths should be ignored."""
        assert scanner._is_false_positive("/api/v1/users/profile/settings") is True

    def test_placeholder_ignored(self, scanner):
        """Placeholder text should be ignored."""
        assert scanner._is_false_positive("xxxxxxxxxxxxxxxx") is True

    def test_test_prefix_ignored(self, scanner):
        """Test prefixed strings should be ignored."""
        assert scanner._is_false_positive("test_key_value_12345678") is True

    def test_real_secret_not_ignored(self, scanner):
        """Real secrets should not be filtered."""
        assert scanner._is_false_positive("sk-proj-abc123XYZ789def") is False


class TestCustomThresholds:
    """Test custom threshold configuration."""

    def test_higher_threshold_less_sensitive(self):
        """Higher threshold should detect fewer secrets."""
        strict = EntropyScanner(base64_threshold=4.0)
        lenient = EntropyScanner(base64_threshold=5.5)
        
        test_line = 'key = "moderateEntropyString12345"'
        
        strict_findings = strict.scan_line(test_line)
        lenient_findings = lenient.scan_line(test_line)
        
        # Lenient should find same or fewer
        assert len(lenient_findings) <= len(strict_findings)
