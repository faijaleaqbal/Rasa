---
name: event-watchdog-monitor
description: Automated monitoring for website changes, price drops, stock availability, server health, and real-time alert dispatch.
---

# Event Watchdog & Change Monitor Skill

Periodically polls targets (e-commerce listings, API endpoints, web pages) and triggers immediate alerts upon detected diffs or thresholds.

## Monitoring Engine Patterns
1. **Price & Stock Drop Watcher**: Periodically fetch product page DOM, extract numerical price tag, compare against trigger threshold (e.g. `price < 40000`).
2. **Webpage Content Diff Detector**: Hash DOM body content (SHA-256) or track specific CSS selectors to notify when announcements or documentation updates occur.
3. **Notification Sinks**: Dispatch instant alerts to Telegram (`@Alya_Rasa_Bot`), WhatsApp, Webhook, or Discord.
