"""
Thread-safe, timezone-aware background reminder and monitor scheduler for Alya.
Guarantees single execution, zero duplicate firings, and exact timezone-aware delivery.
"""

import os
import time
import threading
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
import requests

from . import db
from .timezone_utils import (
    DEFAULT_TIMEZONE,
    resolve_timezone,
    from_utc_iso_to_user_tz,
    to_utc_iso,
    get_timezone_abbreviation,
)

logger = logging.getLogger(__name__)

_SCHEDULER_RUNNING = False
_SCHEDULER_LOCK = threading.Lock()
_CLAIM_LOCK = threading.Lock()  # extra in-process safety net on top of BEGIN IMMEDIATE
_MAX_RETRY_AGE_HOURS = 24  # one-shot reminders older than this are marked failed, not retried forever


def send_telegram_alert(chat_id: str, message: str) -> bool:
    """Sends a notification message to Telegram with Markdown formatting and error fallback."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        logger.warning(f"TELEGRAM_BOT_TOKEN not configured. Reminder simulated for chat_id={chat_id}: {message[:60]}")
        return False
    try:
        try:
            from addons.telegram_channel import format_telegram_markdown
            norm_message = format_telegram_markdown(message)
        except Exception:
            norm_message = message

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": str(chat_id),
            "text": norm_message,
            "parse_mode": "Markdown"
        }
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            return True
        elif resp.status_code == 400:
            # Fallback to plain text if markdown formatting errored
            logger.warning(f"Telegram alert markdown failed ({resp.text}), retrying with plain text...")
            payload_plain = {
                "chat_id": str(chat_id),
                "text": message
            }
            resp_plain = requests.post(url, json=payload_plain, timeout=10)
            return resp_plain.status_code == 200
        else:
            logger.error(f"Telegram alert returned HTTP {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        logger.error(f"Failed to send Telegram alert to {chat_id}: {e}")
        return False


def _check_and_fire_reminders() -> int:
    """
    Polls SQLite database for due reminders using UTC ISO comparison.
    Atomically claims due reminders to prevent duplicate execution across threads.
    """
    now_utc_iso = datetime.now(timezone.utc).isoformat()
    claimed_rems = db.claim_due_reminders(now_utc_iso)

    if not claimed_rems:
        return 0

    fired_count = 0
    for r in claimed_rems:
        rem_id = r["id"]
        chat_id = r["chat_id"]
        rem_text = r["text"]
        rem_type = r.get("reminder_type", "general")
        tz_name = r.get("timezone_name") or "Asia/Kolkata"
        is_rec = r.get("is_recurring", 0)
        due_iso = r["due_time"]

        # Resolve display time in user's timezone
        user_tz = resolve_timezone(tz_name)
        due_dt_user = from_utc_iso_to_user_tz(due_iso, user_tz)
        tz_abbr = get_timezone_abbreviation(due_dt_user)
        time_display = due_dt_user.strftime(f"%I:%M %p {tz_abbr}")

        if rem_type == "medicine":
            msg = (
                f"💊 **Medicine Reminder Alert!**\n\n"
                f"It's time to take: **{rem_text}**\n\n"
                f"_⏰ Scheduled for: {time_display}_"
            )
        else:
            msg = (
                f"⏰ **Reminder Alert!**\n\n"
                f"**{rem_text}**\n\n"
                f"_⏰ Scheduled for: {time_display}_"
            )

        # Dispatch alert
        sent = send_telegram_alert(chat_id, msg)
        logger.info(f"Fired reminder #{rem_id} ({rem_text[:30]}) for chat {chat_id} (sent: {sent})")

        # Handle recurring vs one-time
        if is_rec:
            # Advance to next day at same time in user's timezone
            next_dt_user = due_dt_user + timedelta(days=1)
            # Ensure next due is in the future
            now_user = datetime.now(user_tz)
            while next_dt_user <= now_user:
                next_dt_user += timedelta(days=1)
            next_utc_iso = to_utc_iso(next_dt_user)
            db.update_reminder_next_run(rem_id, next_utc_iso)
            logger.info(f"Advanced recurring reminder #{rem_id} to next run: {next_dt_user.isoformat()} ({next_utc_iso})")
        elif sent:
            db.mark_reminder_fired(rem_id)
        else:
            # Delivery failed (network/Telegram error): requeue for retry instead of
            # silently dropping the reminder. Give up only if it is >24h overdue.
            try:
                due_dt_utc = datetime.fromisoformat(due_iso.replace("Z", "+00:00"))
                if due_dt_utc.tzinfo is None:
                    due_dt_utc = due_dt_utc.replace(tzinfo=timezone.utc)
                overdue_hours = (datetime.now(timezone.utc) - due_dt_utc).total_seconds() / 3600
            except Exception:
                overdue_hours = 0.0
            if overdue_hours >= _MAX_RETRY_AGE_HOURS:
                db.mark_reminder_failed(rem_id)
                logger.error(f"Reminder #{rem_id} marked failed after {int(overdue_hours)}h of delivery retries.")
            else:
                retry_iso = (datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat()
                db.update_reminder_next_run(rem_id, retry_iso)
                logger.warning(f"Reminder #{rem_id} delivery failed; requeued for retry at {retry_iso}")

        fired_count += 1

    return fired_count


def _scheduler_loop():
    """Background polling loop executed in a single daemon thread."""
    logger.info("Alya Timezone-Aware Background Scheduler loop started.")
    # Crash recovery: requeue reminders stuck 'in_flight' from a previous process,
    # and expire one-shot reminders that are more than 24h overdue.
    try:
        db.reset_stale_in_flight_reminders()
    except Exception as e:
        logger.error(f"Scheduler startup recovery failed: {e}", exc_info=True)

    while True:
        try:
            with _CLAIM_LOCK:
                _check_and_fire_reminders()
        except Exception as e:
            logger.error(f"Error in scheduler check: {e}", exc_info=True)
        time.sleep(15)  # Poll every 15 seconds for responsiveness


def start_scheduler():
    """Starts the background scheduler as a thread-safe singleton."""
    global _SCHEDULER_RUNNING
    with _SCHEDULER_LOCK:
        if not _SCHEDULER_RUNNING:
            _SCHEDULER_RUNNING = True
            t = threading.Thread(target=_scheduler_loop, daemon=True, name="AlyaBackgroundScheduler")
            t.start()
            logger.info("AlyaBackgroundScheduler thread launched successfully.")
