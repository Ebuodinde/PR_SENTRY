import re
from typing import List, Dict, Any
from entropy_scanner import EntropyScanner


class DiffParser:
    """
    Takes raw diff data from GitHub and converts it into a clean format
    suitable for Claude.
    """

    # Potentially risky security patterns
    SENSITIVE_PATTERNS = [
        # Generic secrets
        (r'(?i)(password|passwd|pwd)\s*=\s*["\']?.+["\']?', "Hardcoded password"),
        (r'(?i)(api_key|apikey|api_secret)\s*=\s*["\']?.+["\']?', "Hardcoded API key"),
        (r'(?i)(secret|token)\s*=\s*["\']?[a-zA-Z0-9_\-]{8,}["\']?', "Hardcoded secret/token"),
        (r'(?i)-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----', "Private key"),
        
        # AWS Credentials
        (r'(?i)AKIA[0-9A-Z]{16}', "AWS Access Key ID"),
        (r'(?i)ABIA[0-9A-Z]{16}', "AWS STS Access Key"),
        (r'(?i)ACCA[0-9A-Z]{16}', "AWS Credential Access Key"),
        (r'(?i)ASIA[0-9A-Z]{16}', "AWS Temporary Access Key"),
        (r'(?i)["\'][a-zA-Z0-9/+=]{40}["\']', "AWS Secret Access Key (Potential)"),
        (r'(?i)arn:aws:[a-z0-9-]+:[a-z0-9-]*:\d{12}:', "AWS ARN"),
        
        # Azure Credentials
        (r'(?i)[a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12}', "Azure Subscription/Tenant ID"),
        (r'(?i)DefaultEndpointsProtocol=https?;AccountName=[^;]+;AccountKey=[^;]+', "Azure Storage Connection String"),
        (r'(?i)AccountKey=[a-zA-Z0-9+/=]{86,88}', "Azure Storage Account Key"),
        (r'(?i)SharedAccessSignature=sv=[^&]+&sig=[^&]+', "Azure SAS Token"),
        
        # GCP Credentials
        (r'(?i)AIza[0-9A-Za-z_-]{35}', "Google API Key"),
        (r'(?i)"type"\s*:\s*"service_account"', "GCP Service Account JSON"),
        (r'(?i)"private_key_id"\s*:\s*"[a-f0-9]{40}"', "GCP Private Key ID"),
        (r'(?i)[0-9]+-[a-z0-9]+\.apps\.googleusercontent\.com', "Google OAuth Client ID"),
        
        # Database Connection Strings
        (r'(?i)mongodb(\+srv)?://[^:]+:[^@]+@', "MongoDB Connection String"),
        (r'(?i)postgres(ql)?://[^:]+:[^@]+@', "PostgreSQL Connection String"),
        (r'(?i)mysql://[^:]+:[^@]+@', "MySQL Connection String"),
        (r'(?i)redis://[^:]+:[^@]+@', "Redis Connection String"),
        
        # Other Cloud/Service Tokens
        (r'(?i)sqp_[a-z0-9]{40}', "SonarQube Token"),
        (r'(?i)xox[baprs]-[0-9a-zA-Z]{10,48}', "Slack Token"),
        (r'(?i)ghp_[a-zA-Z0-9]{36}', "GitHub Personal Access Token"),
        (r'(?i)gho_[a-zA-Z0-9]{36}', "GitHub OAuth Token"),
        (r'(?i)ghu_[a-zA-Z0-9]{36}', "GitHub User Token"),
        (r'(?i)ghs_[a-zA-Z0-9]{36}', "GitHub Server Token"),
        (r'(?i)ghr_[a-zA-Z0-9]{36}', "GitHub Refresh Token"),
        (r'(?i)npm_[a-zA-Z0-9]{36}', "NPM Token"),
        (r'(?i)sk-[a-zA-Z0-9]{48}', "OpenAI API Key"),
        (r'(?i)sk-ant-[a-zA-Z0-9-]{95}', "Anthropic API Key"),
        (r'(?i)SG\.[a-zA-Z0-9_-]{22}\.[a-zA-Z0-9_-]{43}', "SendGrid API Key"),
        (r'(?i)sk_live_[a-zA-Z0-9]{24,}', "Stripe Live Secret Key"),
        (r'(?i)rk_live_[a-zA-Z0-9]{24,}', "Stripe Restricted Key"),
        (r'(?i)sq0csp-[a-zA-Z0-9_-]{43}', "Square Access Token"),
        (r'(?i)sq0atp-[a-zA-Z0-9_-]{22}', "Square OAuth Token"),
        (r'(?i)EAAC[a-zA-Z0-9]+', "Facebook Access Token"),
        (r'(?i)ya29\.[0-9A-Za-z_-]+', "Google OAuth Access Token"),
    ]

    def __init__(self):
        self.entropy_scanner = EntropyScanner()

    def parse_diff(self, raw_diff: str) -> List[Dict[str, Any]]:
        """
        Split a raw diff string into file-level chunks.

        Args:
            raw_diff: Raw unified diff text from the GitHub API

        Returns:
            A list containing one item per file:
            {
                "filename": str,
                "changes": str,       # added/removed lines only
                "additions": int,
                "deletions": int,
                "security_hints": list  # suspicious patterns
            }
        """
        if not raw_diff or not raw_diff.strip():
            return []

        files = []
        # Split each "diff --git" block
        file_blocks = re.split(r'(?=diff --git )', raw_diff)

        for block in file_blocks:
            if not block.strip():
                continue

            parsed = self._parse_file_block(block)
            if parsed:
                files.append(parsed)

        return files

    def _parse_file_block(self, block: str) -> Dict[str, Any] | None:
        """Parse a single file diff block."""

        # Extract the filename
        filename_match = re.search(r'diff --git a/.+ b/(.+)', block)
        if not filename_match:
            return None

        filename = filename_match.group(1).strip()

        # Keep only added (+) and removed (-) lines
        # Skip @@ hunk headers and metadata
        change_lines = []
        additions = 0
        deletions = 0

        for line in block.split('\n'):
            if line.startswith('+') and not line.startswith('+++'):
                change_lines.append(line)
                additions += 1
            elif line.startswith('-') and not line.startswith('---'):
                change_lines.append(line)
                deletions += 1

        if not change_lines:
            return None

        changes_text = '\n'.join(change_lines)

        # Security pattern scan
        security_hints = self._scan_for_sensitive_data(changes_text)

        return {
            "filename": filename,
            "changes": changes_text,
            "additions": additions,
            "deletions": deletions,
            "security_hints": security_hints
        }

    def _scan_for_sensitive_data(self, text: str) -> List[str]:
        """Scan changed lines for sensitive data patterns and high-entropy strings."""
        found = []
        
        # Regex-based pattern matching
        for pattern, description in self.SENSITIVE_PATTERNS:
            if re.search(pattern, text):
                found.append(description)
        
        # Entropy-based detection
        entropy_findings = self.entropy_scanner.scan_text(text)
        for finding in entropy_findings:
            # Avoid duplicates with regex findings
            entropy_hint = f"High-entropy string detected (entropy: {finding['entropy']})"
            if entropy_hint not in found:
                found.append(entropy_hint)
        
        return found

    def format_for_review(self, parsed_files: List[Dict[str, Any]], max_chars: int = 12000) -> str:
        """
        Turn parsed files into a readable string for Claude.

        max_chars: Character limit to avoid exceeding the token budget
        """
        if not parsed_files:
            return "No changes found."

        output = []
        total_chars = 0

        for file in parsed_files:
            block = f"""
### File: {file['filename']}
+{file['additions']} additions, -{file['deletions']} deletions
"""
            if file['security_hints']:
                hints = ', '.join(file['security_hints'])
                block += f"⚠️ Security warning: {hints}\n"

            block += f"```\n{file['changes']}\n```\n"

            # Truncate very large diffs
            if total_chars + len(block) > max_chars:
                output.append(f"\n### File: {file['filename']}\n[File too large, skipped]")
                continue

            output.append(block)
            total_chars += len(block)

        return '\n'.join(output)


    # --- Test Area ---
if __name__ == "__main__":
    parser = DiffParser()

    # A realistic test diff
    test_diff = """diff --git a/src/auth.py b/src/auth.py
index 1234567..abcdefg 100644
--- a/src/auth.py
+++ b/src/auth.py
@@ -10,6 +10,8 @@ def login(username, password):
     user = db.find_user(username)
-    if user.password == password:
+    API_KEY = "sk-1234567890abcdef"
+    if user and user.check_password(password):
         return generate_token(user)
     return None
diff --git a/README.md b/README.md
index 0000001..0000002 100644
--- a/README.md
+++ b/README.md
@@ -1,3 +1,5 @@
 # My Project
+
+## Installation
+Run `pip install -r requirements.txt` to get started.
"""

    print("=== Diff Parser Test ===\n")
    parsed = parser.parse_diff(test_diff)

    for f in parsed:
        print(f"File: {f['filename']}")
        print(f"  +{f['additions']} additions, -{f['deletions']} deletions")
        print(f"  Security warnings: {f['security_hints'] or 'None'}")
        print()

    print("=== Review Format ===\n")
    print(parser.format_for_review(parsed))
