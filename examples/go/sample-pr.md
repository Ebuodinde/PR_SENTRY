# Go Example PR

This example shows what PR-Sentry detects in a typical Go pull request.

## Sample Diff

```diff
diff --git a/pkg/database/db.go b/pkg/database/db.go
new file mode 100644
index 0000000..b2c3d4e
--- /dev/null
+++ b/pkg/database/db.go
@@ -0,0 +1,35 @@
+package database
+
+import (
+    "database/sql"
+    "fmt"
+    "os"
+)
+
+// ⚠️ PR-Sentry will flag these hardcoded credentials
+const (
+    DB_HOST     = "production-db.example.com"
+    DB_USER     = "admin"
+    DB_PASSWORD = "p@ssw0rd123!"
+    AWS_KEY     = "AKIAIOSFODNN7EXAMPLE"
+)
+
+func Connect() (*sql.DB, error) {
+    // ⚠️ Credentials exposed in connection string
+    connStr := fmt.Sprintf("postgres://%s:%s@%s/mydb", DB_USER, DB_PASSWORD, DB_HOST)
+    return sql.Open("postgres", connStr)
+}
+
+// ⚠️ SQL injection vulnerability
+func GetUserByName(db *sql.DB, name string) (*User, error) {
+    query := fmt.Sprintf("SELECT * FROM users WHERE name = '%s'", name)
+    row := db.QueryRow(query)
+    
+    var user User
+    err := row.Scan(&user.ID, &user.Name, &user.Email)
+    if err != nil {
+        return nil, err
+    }
+    return &user, nil
+}
```

## Expected PR-Sentry Output

### Security Report
- 🔐 **Hardcoded database password** detected on line 13
- 🔐 **AWS Access Key ID** detected on line 14 (matches AKIA pattern)
- ⚠️ **SQL Injection** - string formatting in SQL query (line 25)
- 🔐 **Database credentials in connection string**

### Code Review (LLM)
The LLM will suggest:
1. Use environment variables for all credentials
2. Use prepared statements/parameterized queries
3. Consider using a secrets manager (AWS Secrets Manager, HashiCorp Vault)
4. Add input validation and sanitization

## Fixed Version

```go
package database

import (
    "database/sql"
    "fmt"
    "os"
)

func Connect() (*sql.DB, error) {
    // ✅ Credentials from environment
    host := os.Getenv("DB_HOST")
    user := os.Getenv("DB_USER")
    pass := os.Getenv("DB_PASSWORD")
    
    connStr := fmt.Sprintf("postgres://%s:%s@%s/mydb", user, pass, host)
    return sql.Open("postgres", connStr)
}

// ✅ Parameterized query prevents SQL injection
func GetUserByName(db *sql.DB, name string) (*User, error) {
    query := "SELECT id, name, email FROM users WHERE name = $1"
    row := db.QueryRow(query, name)
    
    var user User
    err := row.Scan(&user.ID, &user.Name, &user.Email)
    if err != nil {
        return nil, err
    }
    return &user, nil
}
```
