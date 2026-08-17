---
name: code-reviewer
description: Security auditing, code quality analysis, vulnerability scanning, and performance optimization guidelines.
---

# Code Reviewer & Security Audit Skill

Guidelines for auditing codebase quality, eliminating vulnerabilities, preventing secret leaks, and optimizing performance.

## Security Checklist

### 1. Secrets & Credentials Leak Prevention
* Ensure `.env`, API keys, private tokens, passwords, and `.pem`/`.keystore` files are listed in `.gitignore`.
* Never hardcode sensitive tokens or passwords inside python scripts or frontend templates.
* Use environment variables (`os.getenv()`, `process.env`) with safe fallbacks or runtime error handling.

### 2. Injection & Input Sanitization
* Validate and sanitize all incoming payloads from webhooks, REST APIs, or user input.
* In database operations (SQL / SQLite / ORM), always use parameterized queries to prevent SQL Injection.
* Sanitize shell executions (`subprocess.run`, `os.system`) to prevent command injection.

### 3. Error Handling & Logging
* Do not log sensitive credentials, authorization headers, or private user data in plaintext.
* Avoid bare `except:` blocks in Python; catch specific exceptions and provide meaningful context.

## Python Code Quality Standards
* Follow PEP 8 style guidelines.
* Ensure type annotations are added for public function signatures.
* Ensure modules and complex routines have clear docstrings.

## Frontend / JS Quality Standards
* Ensure no memory leaks with lingering event listeners or uncleaned subscriptions.
* Handle asynchronous error states cleanly with `try/catch` and appropriate user feedback.
