---
name: multi-agent-orchestrator
description: Multi-agent coordination, subagent task delegation, supervisor routing, and autonomous inter-agent messaging frameworks.
---

# Multi-Agent Orchestrator Skill

Coordinates teams of specialized subagents, routes complex multi-domain queries, and resolves parallel work streams.

## Multi-Agent Topologies

### 1. Supervisor / Hierarchical Routing Pattern
* **Primary Supervisor Agent**: Interacts with user, evaluates intent, delegates sub-tasks to specialized subagents, synthesizes final response.
* **Specialized Subagents**:
  * *Researcher / Scraper Agent*: Fetches online or local document data.
  * *Coder / Sandbox Agent*: Generates, tests, and validates code.
  * *Critic / Reviewer Agent*: Audits correctness, security, and edge cases.

### 2. Autonomous Inter-Agent Communication
```json
{
  "sender": "supervisor",
  "recipient": "researcher_subagent",
  "task": "Fetch train availability for DL-BOM on 2026-08-20",
  "expected_format": "JSON array with train_number, departure, arrival, fare"
}
```

## Resilience Guidelines
* Set explicit iteration depth limits to prevent circular delegating loops.
* Require confidence thresholds before committing destructive actions.
