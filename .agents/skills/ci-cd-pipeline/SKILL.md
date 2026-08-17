---
name: ci-cd-pipeline
description: GitHub Actions workflows, continuous integration, automated testing suites, lint checks, artifact building, and automated deployment.
---

# CI / CD Pipeline Skill

Procedures for automating build, test, lint, and deployment workflows using GitHub Actions.

## Standard Pipeline Architecture

### 1. Pull Request / Push CI Workflow (`.github/workflows/ci.yml`)
* **Linting**: Check code format and style (`black`, `flake8`, `eslint`).
* **Security Scan**: Run static analysis (`bandit`, `npm audit`, `trivy`).
* **Validation**: Run `rasa data validate`.
* **Automated Tests**: Execute `pytest` and unit test suites.
* **Build Verification**: Build frontend web bundles or Android APK artifacts.

### 2. CD Deployment Workflow (`.github/workflows/deploy.yml`)
* Trigger on tag creation or merge to `main`.
* SSH into deployment server or use Docker image registry.
* Zero-downtime container rolling restart.
* Post-deployment smoke tests.

## Fast Local Validation
Before pushing commits that trigger CI:
```bash
# Check Python syntax and linting
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

# Validate Rasa data
/home/ubuntu/rasa-env/bin/rasa data validate
```
