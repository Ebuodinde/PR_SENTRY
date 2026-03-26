# Rust Example PR

This example shows what PR-Sentry detects in a typical Rust pull request.

## Sample Diff

```diff
diff --git a/src/config.rs b/src/config.rs
new file mode 100644
index 0000000..c3d4e5f
--- /dev/null
+++ b/src/config.rs
@@ -0,0 +1,40 @@
+use std::env;
+
+// ⚠️ PR-Sentry will flag these hardcoded secrets
+pub const GITHUB_TOKEN: &str = "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx";
+pub const ANTHROPIC_KEY: &str = "sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx-xxxxx";
+pub const DATABASE_URL: &str = "postgres://admin:secret123@db.example.com/prod";
+
+pub struct Config {
+    pub api_key: String,
+    pub database_url: String,
+    pub debug_mode: bool,
+}
+
+impl Config {
+    pub fn new() -> Self {
+        Config {
+            // ⚠️ Fallback to hardcoded secret is a security risk
+            api_key: env::var("API_KEY").unwrap_or_else(|_| "default_secret_key".to_string()),
+            database_url: DATABASE_URL.to_string(),
+            debug_mode: true,
+        }
+    }
+}
+
+// ⚠️ Unsafe string handling
+pub fn execute_command(user_input: &str) -> std::io::Result<std::process::Output> {
+    std::process::Command::new("sh")
+        .arg("-c")
+        .arg(format!("echo {}", user_input))  // Command injection risk
+        .output()
+}
+
+// ⚠️ Memory safety issue - use after free potential
+pub fn process_data(data: &mut Vec<u8>) {
+    let ptr = data.as_ptr();
+    data.clear();
+    unsafe {
+        let _ = *ptr;  // Undefined behavior
+    }
+}
```

## Expected PR-Sentry Output

### Security Report
- 🔐 **GitHub Personal Access Token** detected on line 4
- 🔐 **Anthropic API Key** detected on line 5
- 🔐 **Database credentials in URL** detected on line 6
- ⚠️ **Hardcoded fallback secret** on line 18
- ⚠️ **Command injection risk** - unsanitized user input in shell command
- ⚠️ **Unsafe block** - potential memory safety issues

### Code Review (LLM)
The LLM will suggest:
1. Remove all hardcoded secrets, use environment variables
2. Fail fast if required env vars are missing (no fallback secrets)
3. Sanitize user input before shell commands (or avoid shell entirely)
4. Review unsafe block - consider safe alternatives
5. Add proper error handling

## Fixed Version

```rust
use std::env;

pub struct Config {
    pub api_key: String,
    pub database_url: String,
    pub debug_mode: bool,
}

impl Config {
    pub fn new() -> Result<Self, env::VarError> {
        // ✅ Fail if secrets are not provided
        Ok(Config {
            api_key: env::var("API_KEY")?,
            database_url: env::var("DATABASE_URL")?,
            debug_mode: env::var("DEBUG").map(|v| v == "true").unwrap_or(false),
        })
    }
}

// ✅ Avoid shell - use safe Rust APIs
pub fn echo_message(message: &str) -> String {
    // Validate input
    let sanitized: String = message
        .chars()
        .filter(|c| c.is_alphanumeric() || *c == ' ')
        .collect();
    
    format!("Message: {}", sanitized)
}
```

## Rust-Specific Patterns PR-Sentry Looks For

1. **Hardcoded secrets** in `const` or `static` declarations
2. **Unsafe blocks** with memory operations
3. **Command injection** via `std::process::Command`
4. **SQL injection** in raw SQL queries
5. **Path traversal** in file operations
6. **Deserialization vulnerabilities** (untrusted serde input)
