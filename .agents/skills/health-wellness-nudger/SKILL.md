---
name: health-wellness-nudger
description: Habit nudging, hydration reminders, sleep and step logging, workout routine reminders, and wellness analytics.
---

# Health & Wellness Nudger Skill

Proactively supports daily routines, fitness habits, hydration schedules, and sleep hygiene.

## Nudge Schedules & Triggers

### 1. Hydration & Movement Nudges
* Trigger interval: Every 90 minutes between 09:00 and 21:00.
* Condition: If user has been active at computer without break.
* Message: "💧 Time for a glass of water and a 2-minute stretch!"

### 2. Workout & Gym Routine
* Time: 18:30 on weekdays.
* Dynamic Check: If calendar has no conflict, send workout encouragement with today's target muscle group.

### 3. Sleep Routine Nudge
* Time: 23:00.
* Message: "🌙 Wind-down time. Log your water/step count and prep for 7-8 hours of sleep."

## Health Metrics Logging (`storage/data.db`)
* Daily tables: `health_logs (date, water_ml, steps, sleep_hours, workout_done)`.
