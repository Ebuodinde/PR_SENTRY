"""Lightweight RAG (Retrieval-Augmented Generation) context builder.

This module provides code context for PR reviews using a simple
file-based approach without external databases. It:

1. Parses the repository to extract function/class signatures
2. Stores them in a SQLite database with FTS5 for text search
3. Finds relevant context based on changed code

No external embeddings API needed - uses SQLite FTS5 for search.
"""

import os
import re
import sqlite3
import hashlib
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CodeSymbol:
    """Represents a code symbol (function, class, etc.)."""
    
    name: str
    kind: str  # "function", "class", "method", "constant"
    file_path: str
    line_number: int
    signature: str  # Full signature/definition line
    docstring: str = ""
    parent: Optional[str] = None  # For methods: class name
    
    @property
    def full_name(self) -> str:
        """Get fully qualified name."""
        if self.parent:
            return f"{self.parent}.{self.name}"
        return self.name
    
    def to_context(self) -> str:
        """Format as context string for LLM."""
        location = f"{self.file_path}:{self.line_number}"
        doc = f"\n  {self.docstring}" if self.docstring else ""
        return f"[{self.kind}] {self.full_name} ({location})\n  {self.signature}{doc}"


@dataclass
class ContextResult:
    """Result of context search."""
    
    symbols: list[CodeSymbol] = field(default_factory=list)
    total_chars: int = 0
    
    def to_prompt(self, max_chars: int = 4000) -> str:
        """Format as prompt context, respecting character limit."""
        lines = ["## Related Code Context\n"]
        chars_used = len(lines[0])
        
        for sym in self.symbols:
            ctx = sym.to_context()
            if chars_used + len(ctx) + 2 > max_chars:
                lines.append("\n... (more context truncated)")
                break
            lines.append(ctx)
            lines.append("")
            chars_used += len(ctx) + 2
        
        self.total_chars = chars_used
        return "\n".join(lines)


class CodeParser:
    """Parse source code to extract symbols."""
    
    # Patterns for different languages
    PATTERNS = {
        ".py": {
            "function": re.compile(r"^(\s*)def\s+(\w+)\s*\(([^)]*)\)"),
            "class": re.compile(r"^(\s*)class\s+(\w+)(?:\([^)]*\))?:"),
            "docstring": re.compile(r'^\s*"""(.+?)"""', re.DOTALL),
        },
        ".js": {
            "function": re.compile(r"^(\s*)(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)"),
            "arrow": re.compile(r"^(\s*)(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>"),
            "class": re.compile(r"^(\s*)class\s+(\w+)(?:\s+extends\s+\w+)?"),
        },
        ".ts": {
            "function": re.compile(r"^(\s*)(?:async\s+)?function\s+(\w+)\s*\([^)]*\)"),
            "arrow": re.compile(r"^(\s*)(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>"),
            "class": re.compile(r"^(\s*)class\s+(\w+)(?:\s+extends\s+\w+)?"),
            "interface": re.compile(r"^(\s*)interface\s+(\w+)"),
        },
        ".go": {
            "function": re.compile(r"^func\s+(?:\([^)]+\)\s*)?(\w+)\s*\([^)]*\)"),
            "struct": re.compile(r"^type\s+(\w+)\s+struct\s*\{"),
            "interface": re.compile(r"^type\s+(\w+)\s+interface\s*\{"),
        },
        ".rs": {
            "function": re.compile(r"^(\s*)(?:pub\s+)?(?:async\s+)?fn\s+(\w+)"),
            "struct": re.compile(r"^(\s*)(?:pub\s+)?struct\s+(\w+)"),
            "impl": re.compile(r"^impl(?:<[^>]*>)?\s+(\w+)"),
        },
    }
    
    # File extensions to language mapping
    LANG_MAP = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".kt": "kotlin",
    }
    
    def parse_file(self, file_path: str, content: str) -> list[CodeSymbol]:
        """Parse a file and extract symbols."""
        ext = Path(file_path).suffix.lower()
        patterns = self.PATTERNS.get(ext, {})
        
        if not patterns:
            return []
        
        symbols = []
        lines = content.split("\n")
        current_class = None
        
        for i, line in enumerate(lines, 1):
            # Check class pattern
            if "class" in patterns:
                m = patterns["class"].match(line)
                if m:
                    name = m.group(2) if len(m.groups()) >= 2 else m.group(1)
                    current_class = name
                    symbols.append(CodeSymbol(
                        name=name,
                        kind="class",
                        file_path=file_path,
                        line_number=i,
                        signature=line.strip(),
                    ))
                    continue
            
            # Check struct pattern (Go, Rust)
            if "struct" in patterns:
                m = patterns["struct"].match(line)
                if m:
                    name = m.group(2) if len(m.groups()) >= 2 else m.group(1)
                    symbols.append(CodeSymbol(
                        name=name,
                        kind="struct",
                        file_path=file_path,
                        line_number=i,
                        signature=line.strip(),
                    ))
                    continue
            
            # Check interface pattern
            if "interface" in patterns:
                m = patterns["interface"].match(line)
                if m:
                    name = m.group(2) if len(m.groups()) >= 2 else m.group(1)
                    symbols.append(CodeSymbol(
                        name=name,
                        kind="interface",
                        file_path=file_path,
                        line_number=i,
                        signature=line.strip(),
                    ))
                    continue
            
            # Check function pattern
            if "function" in patterns:
                m = patterns["function"].match(line)
                if m:
                    indent = m.group(1) if m.group(1) else ""
                    name = m.group(2) if len(m.groups()) >= 2 else m.group(1)
                    kind = "method" if current_class and len(indent) > 0 else "function"
                    parent = current_class if kind == "method" else None
                    
                    symbols.append(CodeSymbol(
                        name=name,
                        kind=kind,
                        file_path=file_path,
                        line_number=i,
                        signature=line.strip(),
                        parent=parent,
                    ))
            
            # Check arrow function pattern (JS/TS)
            if "arrow" in patterns:
                m = patterns["arrow"].match(line)
                if m:
                    name = m.group(2)
                    symbols.append(CodeSymbol(
                        name=name,
                        kind="function",
                        file_path=file_path,
                        line_number=i,
                        signature=line.strip(),
                    ))
            
            # Reset class context at top-level
            if ext == ".py" and line and not line[0].isspace():
                if not line.startswith("class "):
                    current_class = None
        
        return symbols


class ContextStore:
    """SQLite-based storage for code symbols with FTS5 search."""
    
    def __init__(self, db_path: str = ":memory:"):
        """Initialize database."""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self._create_tables()
    
    def _create_tables(self):
        """Create database tables."""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS symbols (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                full_name TEXT NOT NULL,
                kind TEXT NOT NULL,
                file_path TEXT NOT NULL,
                line_number INTEGER,
                signature TEXT,
                docstring TEXT,
                parent TEXT,
                file_hash TEXT
            );
            
            CREATE VIRTUAL TABLE IF NOT EXISTS symbols_fts USING fts5(
                name, full_name, signature, docstring, content=symbols, content_rowid=id
            );
            
            CREATE TRIGGER IF NOT EXISTS symbols_ai AFTER INSERT ON symbols BEGIN
                INSERT INTO symbols_fts(rowid, name, full_name, signature, docstring)
                VALUES (new.id, new.name, new.full_name, new.signature, new.docstring);
            END;
            
            CREATE TRIGGER IF NOT EXISTS symbols_ad AFTER DELETE ON symbols BEGIN
                INSERT INTO symbols_fts(symbols_fts, rowid, name, full_name, signature, docstring)
                VALUES ('delete', old.id, old.name, old.full_name, old.signature, old.docstring);
            END;
            
            CREATE INDEX IF NOT EXISTS idx_symbols_file ON symbols(file_path);
            CREATE INDEX IF NOT EXISTS idx_symbols_kind ON symbols(kind);
        """)
        self.conn.commit()
    
    def add_symbols(self, symbols: list[CodeSymbol], file_hash: str = ""):
        """Add symbols to the database."""
        for sym in symbols:
            self.conn.execute("""
                INSERT INTO symbols (name, full_name, kind, file_path, line_number, 
                                    signature, docstring, parent, file_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sym.name, sym.full_name, sym.kind, sym.file_path,
                sym.line_number, sym.signature, sym.docstring, sym.parent, file_hash
            ))
        self.conn.commit()
    
    def clear_file(self, file_path: str):
        """Remove all symbols from a file."""
        self.conn.execute("DELETE FROM symbols WHERE file_path = ?", (file_path,))
        self.conn.commit()
    
    def search(self, query: str, limit: int = 10) -> list[CodeSymbol]:
        """Search for symbols matching query."""
        # Escape special FTS5 characters
        escaped = re.sub(r'[^\w\s]', ' ', query)
        terms = escaped.split()
        
        if not terms:
            return []
        
        # Build FTS5 query with prefix matching
        fts_query = " OR ".join(f'"{t}"*' for t in terms if t)
        
        try:
            cursor = self.conn.execute(f"""
                SELECT s.name, s.kind, s.file_path, s.line_number, 
                       s.signature, s.docstring, s.parent
                FROM symbols s
                JOIN symbols_fts f ON s.id = f.rowid
                WHERE symbols_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (fts_query, limit))
            
            return [
                CodeSymbol(
                    name=row[0], kind=row[1], file_path=row[2],
                    line_number=row[3], signature=row[4] or "",
                    docstring=row[5] or "", parent=row[6]
                )
                for row in cursor.fetchall()
            ]
        except sqlite3.OperationalError:
            # FTS query syntax error, fallback to LIKE
            return self._search_fallback(query, limit)
    
    def _search_fallback(self, query: str, limit: int) -> list[CodeSymbol]:
        """Fallback search using LIKE."""
        cursor = self.conn.execute("""
            SELECT name, kind, file_path, line_number, signature, docstring, parent
            FROM symbols
            WHERE name LIKE ? OR full_name LIKE ? OR signature LIKE ?
            LIMIT ?
        """, (f"%{query}%", f"%{query}%", f"%{query}%", limit))
        
        return [
            CodeSymbol(
                name=row[0], kind=row[1], file_path=row[2],
                line_number=row[3], signature=row[4] or "",
                docstring=row[5] or "", parent=row[6]
            )
            for row in cursor.fetchall()
        ]
    
    def get_stats(self) -> dict:
        """Get database statistics."""
        cursor = self.conn.execute("""
            SELECT kind, COUNT(*) FROM symbols GROUP BY kind
        """)
        by_kind = dict(cursor.fetchall())
        
        cursor = self.conn.execute("SELECT COUNT(DISTINCT file_path) FROM symbols")
        file_count = cursor.fetchone()[0]
        
        return {
            "total_symbols": sum(by_kind.values()),
            "by_kind": by_kind,
            "file_count": file_count,
        }
    
    def close(self):
        """Close database connection."""
        self.conn.close()


class RAGContextBuilder:
    """Build context for PR reviews using lightweight RAG."""
    
    # Directories to skip
    SKIP_DIRS = {
        "node_modules", "vendor", "dist", "build", "__pycache__",
        ".git", ".svn", ".hg", "target", "bin", "obj", ".next",
        "coverage", ".pytest_cache", ".tox", "venv", ".venv",
    }
    
    # File extensions to index
    INDEX_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".kt"}
    
    def __init__(self, repo_path: str, db_path: Optional[str] = None):
        """Initialize context builder.
        
        Args:
            repo_path: Path to repository root
            db_path: Path to SQLite database (None = in-memory)
        """
        self.repo_path = Path(repo_path).resolve()
        self.parser = CodeParser()
        self.store = ContextStore(db_path or ":memory:")
        self._indexed = False
    
    def index_repository(self, max_files: int = 500) -> dict:
        """Index the repository for context search.
        
        Args:
            max_files: Maximum files to index (performance limit)
            
        Returns:
            Statistics about indexed content
        """
        indexed_files = 0
        total_symbols = 0
        
        for root, dirs, files in os.walk(self.repo_path):
            # Skip unwanted directories
            dirs[:] = [d for d in dirs if d not in self.SKIP_DIRS]
            
            for file in files:
                if indexed_files >= max_files:
                    break
                
                ext = Path(file).suffix.lower()
                if ext not in self.INDEX_EXTENSIONS:
                    continue
                
                file_path = Path(root) / file
                rel_path = str(file_path.relative_to(self.repo_path))
                
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    file_hash = hashlib.md5(content.encode()).hexdigest()[:12]
                    
                    symbols = self.parser.parse_file(rel_path, content)
                    if symbols:
                        self.store.add_symbols(symbols, file_hash)
                        total_symbols += len(symbols)
                    
                    indexed_files += 1
                except Exception:
                    continue
            
            if indexed_files >= max_files:
                break
        
        self._indexed = True
        return self.store.get_stats()
    
    def find_context(self, diff_text: str, max_results: int = 10) -> ContextResult:
        """Find relevant context for a diff.
        
        Args:
            diff_text: The diff/patch text
            max_results: Maximum symbols to return
            
        Returns:
            ContextResult with relevant symbols
        """
        if not self._indexed:
            self.index_repository()
        
        # Extract identifiers from diff
        identifiers = self._extract_identifiers(diff_text)
        
        # Search for each identifier
        all_symbols = []
        seen = set()
        
        for ident in identifiers[:20]:  # Limit queries
            results = self.store.search(ident, limit=3)
            for sym in results:
                key = (sym.file_path, sym.line_number, sym.name)
                if key not in seen:
                    seen.add(key)
                    all_symbols.append(sym)
        
        # Sort by relevance (kind priority)
        kind_priority = {"class": 0, "interface": 1, "struct": 1, "function": 2, "method": 3}
        all_symbols.sort(key=lambda s: kind_priority.get(s.kind, 4))
        
        return ContextResult(symbols=all_symbols[:max_results])
    
    def _extract_identifiers(self, text: str) -> list[str]:
        """Extract potential identifiers from text."""
        # Remove diff metadata
        lines = [
            line for line in text.split("\n")
            if not line.startswith(("---", "+++", "@@", "diff ", "index "))
        ]
        content = "\n".join(lines)
        
        # Find camelCase/PascalCase/snake_case identifiers
        pattern = r'\b([A-Z][a-z]+(?:[A-Z][a-z]+)*|[a-z]+(?:_[a-z]+)+|[A-Z][A-Z_]+)\b'
        matches = re.findall(pattern, content)
        
        # Also find function calls
        func_pattern = r'(\w+)\s*\('
        func_matches = re.findall(func_pattern, content)
        
        # Combine and deduplicate, prioritize longer names
        all_idents = list(set(matches + func_matches))
        all_idents.sort(key=lambda x: -len(x))
        
        # Filter out common keywords
        keywords = {
            "if", "else", "for", "while", "return", "import", "from",
            "def", "class", "function", "const", "let", "var", "async",
            "await", "try", "catch", "finally", "true", "false", "null",
            "None", "True", "False", "self", "this", "new", "delete",
        }
        
        return [i for i in all_idents if i.lower() not in keywords and len(i) > 2]
    
    def close(self):
        """Close resources."""
        self.store.close()


def build_context_for_pr(repo_path: str, diff_text: str, max_chars: int = 4000) -> str:
    """Convenience function to build context for a PR.
    
    Args:
        repo_path: Path to repository root
        diff_text: The PR diff
        max_chars: Maximum characters for context
        
    Returns:
        Formatted context string for LLM prompt
    """
    builder = RAGContextBuilder(repo_path)
    try:
        builder.index_repository()
        result = builder.find_context(diff_text)
        return result.to_prompt(max_chars)
    finally:
        builder.close()
