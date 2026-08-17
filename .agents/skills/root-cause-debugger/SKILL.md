---
name: root-cause-debugger
description: Systematic root-cause debugging, stack trace analysis, memory leaks, race condition detection, and reproducible minimal test cases.
---

# Root Cause Debugger Skill

Methodologies for systematically identifying, isolating, and resolving stubborn software defects, crashes, and performance degradations.

## 5-Step Debugging Protocol

### Step 1: Exact Reproduction
* Capture the exact input payload, environment state, and triggers that reproduce the failure.
* Create a minimal, reproducible standalone script or curl command.

### Step 2: Trace & Inspect Logs
* Search logs for exceptions, traceback frames, and timestamps:
  ```bash
  grep -rn "ERROR" *.log | tail -n 50
  journalctl -xeu rasa.service -n 100 --no-pager
  ```

### Step 3: Hypothesis Generation & Isolation
* Formulate testable hypotheses (e.g. "Is it network timeout?", "Is it unhandled null in slot extraction?", "Is it SQLite locking?").
* Use isolated breakpoints or debug prints:
  ```python
  import logging
  logging.getLogger(__name__).info(f"DEBUG: Variable state: {repr(target_var)}")
  ```

### Step 4: Implement Surgical Fix
* Fix the underlying cause rather than masking symptoms with blanket try/except blocks.

### Step 5: Regression Proofing
* Write an automated test covering the exact scenario to ensure the bug never recurs.
