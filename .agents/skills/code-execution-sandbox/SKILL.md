---
name: code-execution-sandbox
description: Safe local Python and Javascript code sandbox execution for automated computations, data processing, and scripting.
---

# Code Execution Sandbox Skill

Safely evaluates calculations, executes data manipulation scripts, generates plots/charts, and automates file workflows in isolated sandboxes.

## Safe Execution Patterns

### 1. Isolated Python Subprocess Runner
```python
import subprocess
import sys

def execute_code_snippet(code_string: str, timeout_sec: int = 10) -> dict:
    try:
        proc = subprocess.run(
            [sys.executable, "-c", code_string],
            capture_output=True,
            text=True,
            timeout=timeout_sec
        )
        return {
            "success": proc.returncode == 0,
            "stdout": proc.stdout,
            "stderr": proc.stderr
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Execution timed out"}
```

### 2. Math, Statistics & Charting Automation
* Use `matplotlib` and `seaborn` to output charts directly into `storage/files/` or `web/public/` for instant viewing.
* Clean up temporary runtime artifacts after execution.
