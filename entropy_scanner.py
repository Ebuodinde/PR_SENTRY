"""
Entropy-based secret detection module.

Uses Shannon entropy to detect high-entropy strings that may be secrets,
API keys, or tokens - even when they don't match known regex patterns.
"""

import math
import re
from typing import List, Tuple


class EntropyScanner:
    """
    Detects potential secrets using Shannon entropy analysis.
    
    High-entropy strings (random-looking) are likely to be:
    - API keys
    - Tokens
    - Passwords
    - Private keys
    - Connection strings
    """

    # Entropy thresholds (bits per character)
    # Base64: theoretical max ~6 bits, practical ~5.5
    # Hex: theoretical max 4 bits, practical ~3.5
    BASE64_THRESHOLD = 4.5
    HEX_THRESHOLD = 3.0
    
    # Minimum string length to analyze
    MIN_LENGTH = 16
    
    # Maximum string length (avoid analyzing huge blobs)
    MAX_LENGTH = 256
    
    # Characters that indicate a string is likely a secret
    BASE64_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=")
    HEX_CHARS = set("0123456789abcdefABCDEF")

    def __init__(
        self,
        base64_threshold: float = None,
        hex_threshold: float = None,
        min_length: int = None
    ):
        self.base64_threshold = base64_threshold or self.BASE64_THRESHOLD
        self.hex_threshold = hex_threshold or self.HEX_THRESHOLD
        self.min_length = min_length or self.MIN_LENGTH

    def calculate_entropy(self, text: str) -> float:
        """
        Calculate Shannon entropy of a string.
        
        Higher entropy = more random = more likely to be a secret.
        
        Returns entropy in bits per character.
        """
        if not text:
            return 0.0
        
        # Count character frequencies
        freq = {}
        for char in text:
            freq[char] = freq.get(char, 0) + 1
        
        # Calculate entropy
        length = len(text)
        entropy = 0.0
        for count in freq.values():
            probability = count / length
            entropy -= probability * math.log2(probability)
        
        return entropy

    def is_base64_like(self, text: str) -> bool:
        """Check if string looks like Base64 encoding."""
        if len(text) < self.min_length:
            return False
        # Allow some non-base64 chars (for JWT, etc.)
        base64_count = sum(1 for c in text if c in self.BASE64_CHARS)
        return base64_count / len(text) >= 0.9

    def is_hex_like(self, text: str) -> bool:
        """Check if string looks like hexadecimal."""
        if len(text) < self.min_length:
            return False
        return all(c in self.HEX_CHARS for c in text)

    def scan_line(self, line: str) -> List[Tuple[str, float, str]]:
        """
        Scan a single line for high-entropy strings.
        
        Returns list of (matched_string, entropy, encoding_type) tuples.
        """
        findings = []
        
        # Extract quoted strings and potential tokens
        patterns = [
            r'["\']([^"\']{16,256})["\']',  # Quoted strings
            r'=\s*([A-Za-z0-9+/=_-]{16,256})',  # Assignment values
            r':\s*([A-Za-z0-9+/=_-]{16,256})',  # JSON-like values
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, line):
                candidate = match.group(1)
                
                # Skip if too short or too long
                if len(candidate) < self.min_length or len(candidate) > self.MAX_LENGTH:
                    continue
                
                # Skip common false positives
                if self._is_false_positive(candidate):
                    continue
                
                entropy = self.calculate_entropy(candidate)
                
                # Check against thresholds based on encoding type
                if self.is_hex_like(candidate):
                    if entropy >= self.hex_threshold:
                        findings.append((candidate, entropy, "hex"))
                elif self.is_base64_like(candidate):
                    if entropy >= self.base64_threshold:
                        findings.append((candidate, entropy, "base64"))
                elif entropy >= self.base64_threshold:
                    # Generic high-entropy string
                    findings.append((candidate, entropy, "unknown"))
        
        return findings

    def scan_text(self, text: str) -> List[dict]:
        """
        Scan multi-line text for high-entropy strings.
        
        Returns list of findings with line numbers.
        """
        findings = []
        
        for line_num, line in enumerate(text.split('\n'), start=1):
            line_findings = self.scan_line(line)
            for matched, entropy, encoding in line_findings:
                findings.append({
                    "line": line_num,
                    "matched": self._truncate(matched),
                    "entropy": round(entropy, 2),
                    "encoding": encoding,
                    "description": f"High-entropy {encoding} string (entropy: {entropy:.2f})"
                })
        
        return findings

    def _truncate(self, text: str, max_len: int = 40) -> str:
        """Truncate string for safe display (don't leak full secrets)."""
        if len(text) <= max_len:
            return text
        return text[:max_len // 2] + "..." + text[-max_len // 4:]

    def _is_false_positive(self, text: str) -> bool:
        """Filter out common false positives."""
        lower = text.lower()
        
        # Skip common hash function outputs that are expected
        false_positive_patterns = [
            # Git commit hashes (40 hex chars)
            r'^[a-f0-9]{40}$',
            # Common placeholder patterns
            r'^x+$',
            r'^0+$',
            r'^test',
            r'^example',
            r'^placeholder',
            # UUIDs (common, not secrets)
            r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$',
            # File hashes in comments
            r'^sha256:',
            r'^md5:',
        ]
        
        for pattern in false_positive_patterns:
            if re.match(pattern, lower):
                return True
        
        # Skip if it looks like a URL path
        if '/' in text and text.count('/') >= 2:
            return True
        
        return False


# --- Test Area ---
if __name__ == "__main__":
    scanner = EntropyScanner()
    
    test_cases = [
        # Real secrets (should detect)
        'API_KEY = "sk-proj-abc123XYZ789defGHI456jklMNO012pqr"',
        'token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"',
        'aws_secret = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"',
        
        # False positives (should NOT detect)
        'hash = "da39a3ee5e6b4b0d3255bfef95601890afd80709"',  # Git SHA
        'uuid = "550e8400-e29b-41d4-a716-446655440000"',  # UUID
        'path = "/api/v1/users/profile/settings"',  # URL path
        
        # Low entropy (should NOT detect)
        'password = "aaaaaaaaaaaaaaaa"',
        'key = "test1234test1234"',
    ]
    
    print("=== Entropy Scanner Test ===\n")
    
    for line in test_cases:
        findings = scanner.scan_line(line)
        print(f"Input: {line[:60]}...")
        if findings:
            for matched, entropy, encoding in findings:
                print(f"  ⚠️  FOUND: entropy={entropy:.2f}, type={encoding}")
        else:
            print("  ✅ Clean")
        print()
