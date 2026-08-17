---
name: git-workflow
description: Standardized Git version control workflow, conventional commits, branch management, and Pull Request preparation.
---

# Git Workflow Skill

Standard operating procedures for managing Git repositories, commits, branch hygiene, and clean delivery.

## Commit Message Convention
Follow the Conventional Commits specification:
* `feat:` A new feature or capability
* `fix:` A bug fix
* `docs:` Documentation only changes
* `style:` Changes that do not affect the meaning of the code (formatting, missing semi-colons, etc.)
* `refactor:` Code change that neither fixes a bug nor adds a feature
* `perf:` Code change that improves performance
* `test:` Adding missing tests or correcting existing tests
* `chore:` Changes to the build process, dependency updates, or auxiliary tools

### Commit Format
```text
<type>(<scope>): <short summary in imperative mood>

[optional body explaining why and what changed]

[optional footer(s)]
```

## Branching Guidelines
1. Keep the `main` branch stable and deployable.
2. Create dedicated feature or bugfix branches:
   * `feature/<feature-name>`
   * `fix/<bug-name>`
   * `refactor/<scope>`
3. Always verify `git status` and `git diff` before staging changes to prevent committing unwanted files (e.g. `.env`, `.pem`, secrets, credentials).

## Staging & Committing Procedures
1. Check untracked and modified files:
   ```bash
   git status
   ```
2. Review exact changes:
   ```bash
   git diff
   ```
3. Stage specific files:
   ```bash
   git add <path/to/file>
   ```
4. Commit with descriptive message:
   ```bash
   git commit -m "feat(module): descriptive message"
   ```
5. Push to remote:
   ```bash
   git push origin <branch-name>
   ```
