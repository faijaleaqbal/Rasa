import os
import time
import asyncio
import threading
import logging
from datetime import datetime, timezone
import requests

from . import db

logger = logging.getLogger(__name__)

_SCHEDULER_RUNNING = False


def send_telegram_alert(chat_id: str, message: str) -> bool:
    """Sends a notification message to Telegram."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        return False
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": str(chat_id),
            "text": message,
            "parse_mode": "Markdown"
        }
        resp = requests.post(url, json=payload, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        logger.error(f"Failed to send Telegram alert: {e}")
        return False


def _check_and_fire_reminders():
    """Polls SQLite database for due reminders and dispatches Telegram notifications."""
    now_iso = datetime.now().isoformat()
    due_rems = db.get_due_reminders(now_iso)

    for r in due_rems:
        chat_id = r["chat_id"]
        rem_text = r["text"]
        rem_type = r.get("reminder_type", "general")
        rem_id = r["id"]

        if rem_type == "medicine":
            msg = f"💊 **Medicine Reminder Alert!**\n\nIt's time to take: **{rem_text}**"
        else:
            msg = f"⏰ **Reminder Alert!**\n\n**{rem_text}**"

        if send_telegram_alert(chat_id, msg):
            logger.info(f"Fired reminder #{rem_id} to chat {chat_id}")
            db.mark_reminder_fired(rem_id)


def _scheduler_loop():
    """Background polling loop executed in a separate daemon thread."""
    logger.info("Background Reminder & Monitor Scheduler loop started.")
    while True:
        try:
            _check_and_fire_reminders()
        except Exception as e:
            logger.error(f"Error in scheduler check: {e}")
        time.sleep(30)


def start_scheduler():
    """Starts the background scheduler if not already running."""
    global _SCHEDULER_RUNNING
    if not _SCHEDULER_RUNNING:
        _SCHEDULER_RUNNING = True
        t = threading.Thread(target=_scheduler_loop, daemon=True, name="AlyaBackgroundScheduler")
        t.start()
        logger.info("AlyaBackgroundScheduler thread launched.")
