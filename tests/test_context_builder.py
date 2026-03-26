"""Tests for context_builder module."""

import pytest
import tempfile
import os
from pathlib import Path

from context_builder import (
    CodeSymbol, ContextResult, CodeParser, ContextStore, 
    RAGContextBuilder, build_context_for_pr
)


class TestCodeSymbol:
    """Test CodeSymbol dataclass."""
    
    def test_basic_symbol(self):
        """Test basic symbol creation."""
        sym = CodeSymbol(
            name="test_func",
            kind="function",
            file_path="test.py",
            line_number=10,
            signature="def test_func(x, y):"
        )
        assert sym.name == "test_func"
        assert sym.full_name == "test_func"
    
    def test_method_symbol(self):
        """Test method with parent."""
        sym = CodeSymbol(
            name="method",
            kind="method",
            file_path="test.py",
            line_number=15,
            signature="def method(self):",
            parent="MyClass"
        )
        assert sym.full_name == "MyClass.method"
    
    def test_to_context(self):
        """Test context formatting."""
        sym = CodeSymbol(
            name="calculate",
            kind="function",
            file_path="math.py",
            line_number=42,
            signature="def calculate(a, b):",
            docstring="Calculate sum"
        )
        ctx = sym.to_context()
        assert "[function]" in ctx
        assert "calculate" in ctx
        assert "math.py:42" in ctx
        assert "Calculate sum" in ctx


class TestContextResult:
    """Test ContextResult."""
    
    def test_empty_result(self):
        """Test empty context result."""
        result = ContextResult()
        prompt = result.to_prompt()
        assert "Related Code Context" in prompt
    
    def test_with_symbols(self):
        """Test result with symbols."""
        symbols = [
            CodeSymbol("func1", "function", "a.py", 1, "def func1():"),
            CodeSymbol("func2", "function", "b.py", 5, "def func2(x):"),
        ]
        result = ContextResult(symbols=symbols)
        prompt = result.to_prompt()
        assert "func1" in prompt
        assert "func2" in prompt
    
    def test_truncation(self):
        """Test context truncation."""
        symbols = [
            CodeSymbol(f"func_{i}", "function", "file.py", i, f"def func_{i}(): pass")
            for i in range(100)
        ]
        result = ContextResult(symbols=symbols)
        prompt = result.to_prompt(max_chars=500)
        assert len(prompt) <= 550  # Allow some buffer
        assert "truncated" in prompt


class TestCodeParser:
    """Test CodeParser."""
    
    def setup_method(self):
        """Set up parser."""
        self.parser = CodeParser()
    
    def test_parse_python_function(self):
        """Test parsing Python function."""
        content = '''
def hello(name):
    """Say hello."""
    print(f"Hello, {name}")
'''
        symbols = self.parser.parse_file("test.py", content)
        assert len(symbols) == 1
        assert symbols[0].name == "hello"
        assert symbols[0].kind == "function"
    
    def test_parse_python_class(self):
        """Test parsing Python class."""
        content = '''
class MyClass:
    def __init__(self):
        pass
    
    def method(self):
        pass
'''
        symbols = self.parser.parse_file("test.py", content)
        assert len(symbols) == 3
        assert symbols[0].kind == "class"
        assert symbols[0].name == "MyClass"
        assert symbols[1].kind == "method"
        assert symbols[1].parent == "MyClass"
    
    def test_parse_javascript(self):
        """Test parsing JavaScript."""
        content = '''
function greet(name) {
    return `Hello, ${name}`;
}

const helper = (x) => x * 2;

class Component {
    render() {}
}
'''
        symbols = self.parser.parse_file("test.js", content)
        assert any(s.name == "greet" for s in symbols)
        assert any(s.name == "helper" for s in symbols)
        assert any(s.name == "Component" for s in symbols)
    
    def test_parse_typescript(self):
        """Test parsing TypeScript."""
        content = '''
interface User {
    name: string;
}

function getUser(): User {
    return { name: "test" };
}

class UserService {
    findAll() {}
}
'''
        symbols = self.parser.parse_file("test.ts", content)
        assert any(s.kind == "interface" and s.name == "User" for s in symbols)
        assert any(s.kind == "function" and s.name == "getUser" for s in symbols)
        assert any(s.kind == "class" and s.name == "UserService" for s in symbols)
    
    def test_parse_go(self):
        """Test parsing Go."""
        content = '''
type Server struct {
    Port int
}

func NewServer(port int) *Server {
    return &Server{Port: port}
}

func (s *Server) Start() error {
    return nil
}
'''
        symbols = self.parser.parse_file("main.go", content)
        assert any(s.kind == "struct" and s.name == "Server" for s in symbols)
        assert any(s.kind == "function" and s.name == "NewServer" for s in symbols)
    
    def test_parse_rust(self):
        """Test parsing Rust."""
        content = '''
pub struct Config {
    port: u16,
}

impl Config {
    pub fn new() -> Self {
        Config { port: 8080 }
    }
}

fn helper() -> bool {
    true
}
'''
        symbols = self.parser.parse_file("lib.rs", content)
        assert any(s.kind == "struct" and s.name == "Config" for s in symbols)
        assert any(s.kind == "function" for s in symbols)
    
    def test_unknown_extension(self):
        """Test unknown file extension returns empty."""
        symbols = self.parser.parse_file("file.xyz", "content here")
        assert symbols == []


class TestContextStore:
    """Test ContextStore."""
    
    def setup_method(self):
        """Set up in-memory store."""
        self.store = ContextStore(":memory:")
    
    def teardown_method(self):
        """Close store."""
        self.store.close()
    
    def test_add_and_search(self):
        """Test adding and searching symbols."""
        symbols = [
            CodeSymbol("authenticate", "function", "auth.py", 10, "def authenticate(user):"),
            CodeSymbol("authorize", "function", "auth.py", 20, "def authorize(role):"),
        ]
        self.store.add_symbols(symbols)
        
        results = self.store.search("auth")
        assert len(results) >= 1
    
    def test_search_empty(self):
        """Test searching empty database."""
        results = self.store.search("anything")
        assert results == []
    
    def test_search_by_signature(self):
        """Test searching by signature content."""
        symbols = [
            CodeSymbol("process", "function", "api.py", 1, "def process(request, response):"),
        ]
        self.store.add_symbols(symbols)
        
        results = self.store.search("request")
        assert len(results) >= 1
        assert results[0].name == "process"
    
    def test_clear_file(self):
        """Test clearing symbols for a file."""
        symbols = [
            CodeSymbol("func1", "function", "file1.py", 1, "def func1():"),
            CodeSymbol("func2", "function", "file2.py", 1, "def func2():"),
        ]
        self.store.add_symbols(symbols)
        
        self.store.clear_file("file1.py")
        
        results = self.store.search("func1")
        assert len(results) == 0
        
        results = self.store.search("func2")
        assert len(results) == 1
    
    def test_get_stats(self):
        """Test getting statistics."""
        symbols = [
            CodeSymbol("func", "function", "a.py", 1, "def func():"),
            CodeSymbol("Class", "class", "b.py", 1, "class Class:"),
            CodeSymbol("method", "method", "b.py", 5, "def method():", parent="Class"),
        ]
        self.store.add_symbols(symbols)
        
        stats = self.store.get_stats()
        assert stats["total_symbols"] == 3
        assert stats["file_count"] == 2
        assert "function" in stats["by_kind"]


class TestRAGContextBuilder:
    """Test RAGContextBuilder."""
    
    def setup_method(self):
        """Set up temp directory."""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up temp directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _write_file(self, rel_path: str, content: str):
        """Write file to temp directory."""
        path = Path(self.temp_dir) / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    
    def test_index_empty_repo(self):
        """Test indexing empty repository."""
        builder = RAGContextBuilder(self.temp_dir)
        stats = builder.index_repository()
        assert stats["total_symbols"] == 0
        builder.close()
    
    def test_index_python_files(self):
        """Test indexing Python files."""
        self._write_file("src/auth.py", """
def login(username, password):
    pass

def logout():
    pass

class AuthService:
    def validate(self):
        pass
""")
        self._write_file("src/api.py", """
def handle_request(req):
    pass
""")
        
        builder = RAGContextBuilder(self.temp_dir)
        stats = builder.index_repository()
        assert stats["total_symbols"] >= 4
        builder.close()
    
    def test_skip_node_modules(self):
        """Test skipping node_modules."""
        self._write_file("src/app.js", "function app() {}")
        self._write_file("node_modules/lib/index.js", "function lib() {}")
        
        builder = RAGContextBuilder(self.temp_dir)
        stats = builder.index_repository()
        
        # Should only index app.js
        results = builder.store.search("lib")
        assert len(results) == 0
        
        results = builder.store.search("app")
        assert len(results) >= 1
        builder.close()
    
    def test_find_context_from_diff(self):
        """Test finding context from diff."""
        self._write_file("auth.py", """
def authenticate(user, password):
    '''Authenticate user'''
    pass

def get_user_permissions(user_id):
    pass

class UserSession:
    def create(self):
        pass
""")
        
        diff = """
diff --git a/login.py b/login.py
+++ b/login.py
+def login(user):
+    auth_result = authenticate(user, get_password())
+    if auth_result:
+        session = UserSession()
+        session.create()
"""
        
        builder = RAGContextBuilder(self.temp_dir)
        builder.index_repository()
        
        result = builder.find_context(diff)
        
        # Should find authenticate, UserSession
        names = [s.name for s in result.symbols]
        assert any("authenticate" in name or "UserSession" in name for name in names)
        builder.close()
    
    def test_max_files_limit(self):
        """Test max files limit."""
        for i in range(10):
            self._write_file(f"file{i}.py", f"def func{i}(): pass")
        
        builder = RAGContextBuilder(self.temp_dir)
        stats = builder.index_repository(max_files=3)
        assert stats["file_count"] <= 3
        builder.close()


class TestBuildContextForPR:
    """Test convenience function."""
    
    def setup_method(self):
        """Set up temp directory."""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_build_context(self):
        """Test building context."""
        path = Path(self.temp_dir) / "test.py"
        path.write_text("def example_function(): pass")
        
        diff = "+result = example_function()"
        context = build_context_for_pr(self.temp_dir, diff)
        
        assert "Related Code Context" in context


class TestIdentifierExtraction:
    """Test identifier extraction from diffs."""
    
    def setup_method(self):
        """Set up builder."""
        self.temp_dir = tempfile.mkdtemp()
        self.builder = RAGContextBuilder(self.temp_dir)
    
    def teardown_method(self):
        """Clean up."""
        self.builder.close()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_extract_camel_case(self):
        """Test extracting CamelCase."""
        text = "const user = UserService.findAll()"
        idents = self.builder._extract_identifiers(text)
        assert "UserService" in idents
    
    def test_extract_snake_case(self):
        """Test extracting snake_case."""
        text = "result = get_user_by_id(user_id)"
        idents = self.builder._extract_identifiers(text)
        assert "get_user_by_id" in idents
    
    def test_filter_keywords(self):
        """Test filtering common keywords."""
        text = "if something: return value"
        idents = self.builder._extract_identifiers(text)
        assert "if" not in [i.lower() for i in idents]
        assert "return" not in [i.lower() for i in idents]
    
    def test_extract_function_calls(self):
        """Test extracting function calls."""
        text = "data = fetchData(params)"
        idents = self.builder._extract_identifiers(text)
        assert "fetchData" in idents
