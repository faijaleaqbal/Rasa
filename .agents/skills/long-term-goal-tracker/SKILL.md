---
name: long-term-goal-tracker
description: Long-term goal setting, milestone tracking, weekly/monthly progress memory persistence, and periodic accountability checks.
---

# Long-Term Goal Tracker Skill

Tracks user goals across days, weeks, and months, maintaining contextual persistence and proactive progress reviews.

## Architecture & Storage
* Goals stored in SQLite `storage/data.db` under table `user_goals`.
* Fields: `goal_id`, `user_id`, `title`, `category`, `target_date`, `milestones_json`, `current_progress`, `last_checked`.

## Procedures

### 1. Goal Registration
```sql
INSERT INTO user_goals (user_id, title, category, target_date, milestones_json, current_progress)
VALUES ('user1', 'Save ₹50,000 for emergency fund', 'finance', '2026-12-31', '{"milestones": [{"title": "₹10,000", "done": true}, {"title": "₹30,000", "done": false}]}', 20.0);
```

### 2. Proactive Periodic Reviews
* Run weekly Sunday check-ins:
  * Fetch active goals with target dates.
  * Compare current vs target progress metrics.
  * Deliver motivational summary and recommend next weekly micro-targets via Telegram/WhatsApp.
