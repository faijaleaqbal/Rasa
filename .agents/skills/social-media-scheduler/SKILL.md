---
name: social-media-scheduler
description: Social media post drafting, content repurposing, multi-language translation, and automated scheduling across platforms.
---

# Social Media Scheduler & Content Translation Skill

Orchestrates multi-channel content creation, cross-platform adaptation, translation, and scheduled publishing.

## Multi-Platform Content Adaptation
* **X (Twitter)**: Short, punchy hooks under 280 characters, relevant hashtags, thread structures.
* **LinkedIn**: Professional storytelling, line spacing, value takeaways, engagement questions.
* **Telegram / Discord**: Markdown formatted announcements, bullet summaries, call-to-action buttons.

## Multi-Language Translation Pipeline
* Support translation between English, Hindi, Hinglish, Spanish, French, and regional dialects.
* Maintain cultural context and idiomatic meaning rather than rigid literal word-for-word translation.

## Scheduling Engine
* Store scheduled posts in SQLite with timestamp and platform target.
* Background daemon checks queue every minute and invokes platform Webhook / API.
