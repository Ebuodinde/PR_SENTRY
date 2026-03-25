import re
from typing import List, Dict, Any


class DiffParser:
    """
    Takes raw diff data from GitHub and converts it into a clean format
    suitable for Claude.
    """

    # Potentially risky security patterns
    SENSITIVE_PATTERNS = [
        (r'(?i)(password|passwd|pwd)\s*=\s*["\']?.+["\']?', "Hardcoded password"),
        (r'(?i)(api_key|apikey|api_secret)\s*=\s*["\']?.+["\']?', "Hardcoded API key"),
        (r'(?i)(secret|token)\s*=\s*["\']?[a-zA-Z0-9_\-]{8,}["\']?', "Hardcoded secret/token"),
        (r'(?i)-----BEGIN (RSA |EC )?PRIVATE KEY-----', "Private key"),
    ]

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
        """Scan changed lines for sensitive data patterns."""
        found = []
        for pattern, description in self.SENSITIVE_PATTERNS:
            if re.search(pattern, text):
                found.append(description)
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
