# JavaScript Example PR

This example shows what PR-Sentry detects in a typical JavaScript/Node.js pull request.

## Sample Diff

```diff
diff --git a/src/auth.js b/src/auth.js
new file mode 100644
index 0000000..a1b2c3d
--- /dev/null
+++ b/src/auth.js
@@ -0,0 +1,25 @@
+const jwt = require('jsonwebtoken');
+
+// ⚠️ PR-Sentry will flag this as a security issue
+const JWT_SECRET = "super_secret_key_12345";
+const API_KEY = "sk-1234567890abcdef1234567890abcdef12345678901234567890";
+
+function generateToken(user) {
+    return jwt.sign({ userId: user.id }, JWT_SECRET, { expiresIn: '1h' });
+}
+
+function verifyToken(token) {
+    try {
+        return jwt.verify(token, JWT_SECRET);
+    } catch (err) {
+        return null;
+    }
+}
+
+// ⚠️ SQL injection risk - PR-Sentry will warn about this
+async function getUser(userId) {
+    const query = `SELECT * FROM users WHERE id = ${userId}`;
+    return db.query(query);
+}
+
+module.exports = { generateToken, verifyToken, getUser };
```

## Expected PR-Sentry Output

### Security Report
- 🔐 **Hardcoded JWT secret** detected on line 4
- 🔐 **OpenAI API key pattern** detected on line 5
- ⚠️ **SQL Injection risk** - string interpolation in SQL query

### Code Review (LLM)
The LLM review will likely suggest:
1. Move secrets to environment variables
2. Use parameterized queries instead of string interpolation
3. Add input validation for `userId`

## Fixed Version

```javascript
const jwt = require('jsonwebtoken');

// ✅ Secrets from environment
const JWT_SECRET = process.env.JWT_SECRET;
const API_KEY = process.env.OPENAI_API_KEY;

function generateToken(user) {
    return jwt.sign({ userId: user.id }, JWT_SECRET, { expiresIn: '1h' });
}

// ✅ Parameterized query
async function getUser(userId) {
    const query = 'SELECT * FROM users WHERE id = ?';
    return db.query(query, [userId]);
}
```
