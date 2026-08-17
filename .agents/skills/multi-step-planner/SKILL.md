---
name: multi-step-planner
description: Multi-step task decomposition, Directed Acyclic Graph (DAG) planning, dependency resolution, and subtask execution orchestration.
---

# Multi-Step Planner Skill

Deconstructs complex user goals into atomic, verifiable subtasks and schedules their execution in logical order.

## Planning Protocol

### 1. Goal Deconstruction
* Parse high-level user objective (e.g. "Build a full travel itinerary with tickets, weather, and budget").
* Break it down into discrete steps:
  1. Input validation & parameter gathering.
  2. Independent subtasks (can run concurrently).
  3. Dependent subtasks (wait for prerequisites).
  4. Aggregation and final response rendering.

### 2. Plan Representation
```json
{
  "plan_id": "plan_001",
  "goal": "Book flight and notify user",
  "steps": [
    {"id": 1, "task": "fetch_flight_prices", "deps": [], "status": "pending"},
    {"id": 2, "task": "calculate_budget", "deps": [1], "status": "pending"},
    {"id": 3, "task": "send_telegram_notification", "deps": [2], "status": "pending"}
  ]
}
```

### 3. Execution & Checkpointing
* Update step status (`pending` -> `in_progress` -> `completed` / `failed`).
* Checkpoint state in SQLite (`storage/data.db`) to enable resumption upon interruption.
