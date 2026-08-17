---
name: penetration-testing-sec
description: Security hardening, OWASP Top 10 mitigation, secret scanning, dependency vulnerability audit, and header protections.
---

# Penetration Testing & Security Hardening Skill

Checklists and procedures for securing application endpoints, dependencies, and deployment servers.

## Key Security Vectors

### 1. OWASP Top 10 Protections
* **Broken Access Control**: Ensure endpoints that execute system actions require valid authentication.
* **Cryptographic Failures**: Never store plain-text passwords or unencrypted secrets in database tables.
* **Injection**: Use strict parameterized queries (`sqlite3.Cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))`).
* **Security Misconfiguration**: Disable debug mode (`DEBUG = False`) in production Flask/FastAPI applications.

### 2. HTTP Security Headers
Ensure Nginx returns security headers:
```nginx
add_header X-Frame-Options "DENY" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

### 3. Automated Vulnerability Scanning
```bash
# Python dependencies audit
/home/ubuntu/rasa-env/bin/pip-audit || pip install pip-audit && pip-audit

# Node dependencies audit
npm audit --production
```
