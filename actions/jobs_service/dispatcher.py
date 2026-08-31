"""
Resilient Telegram Notification Dispatcher and Queue for Job/Scholarship Alerts.
Handles:
- Telegram rate limits & 'RetryAfter' parameters
- Temporary API failures with exponential backoff
- Blocked / deactivated users detection and unsubscription
- Safe Markdown fallback
- Message length bounds
"""

import os
import time
import logging
from typing import List, Dict, Any, Optional
import requests

from .formatter import format_notification

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
DEFAULT_STAGGER_DELAY = 0.05  # 50ms pause between user dispatches to stay well within 30 msg/sec


def send_single_telegram_message(
    bot_token: str,
    chat_id: str,
    text: str,
    parse_mode: str = "Markdown"
) -> Dict[str, Any]:
    """
    Sends a message to Telegram with retry, rate limit backoff, and blocked user handling.
    Returns dict with {"success": bool, "blocked": bool, "error": Optional[str]}.
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": str(chat_id),
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(url, json=payload, timeout=12)
            if resp.status_code == 200:
                return {"success": True, "blocked": False, "error": None}

            status = resp.status_code
            try:
                resp_json = resp.json()
            except Exception:
                resp_json = {}

            desc = resp_json.get("description", "")

            # 1. Blocked or deactivated user
            if status == 403 or "blocked by the user" in desc.lower() or "user is deactivated" in desc.lower():
                logger.warning(f"User {chat_id} has blocked the bot or is deactivated: {desc}")
                return {"success": False, "blocked": True, "error": desc}

            # 2. Rate limit (429 Too Many Requests)
            if status == 429:
                retry_after = resp_json.get("parameters", {}).get("retry_after", 2)
                logger.warning(f"Telegram rate limited (429). Retrying after {retry_after}s for chat {chat_id}...")
                time.sleep(retry_after + 0.1)
                continue

            # 3. Bad request (usually Markdown syntax error)
            if status == 400 and parse_mode:
                logger.warning(f"Telegram parse_mode failed ({desc}). Retrying as plain text for chat {chat_id}...")
                payload.pop("parse_mode", None)
                resp_plain = requests.post(url, json=payload, timeout=12)
                if resp_plain.status_code == 200:
                    return {"success": True, "blocked": False, "error": None}
                return {"success": False, "blocked": False, "error": resp_plain.text}

            # 4. Server error (5xx)
            if status >= 500:
                logger.warning(f"Telegram 5xx error ({status}) on attempt {attempt}/{MAX_RETRIES}. Backing off...")
                time.sleep(1.0 * attempt)
                continue

            # Other 4xx errors
            return {"success": False, "blocked": False, "error": f"HTTP {status}: {desc}"}

        except (requests.ConnectionError, requests.Timeout) as net_err:
            logger.warning(f"Network error sending to {chat_id} (attempt {attempt}/{MAX_RETRIES}): {net_err}")
            time.sleep(1.0 * attempt)
        except Exception as e:
            logger.error(f"Unexpected error sending Telegram notification to {chat_id}: {e}")
            return {"success": False, "blocked": False, "error": str(e)}

    return {"success": False, "blocked": False, "error": "Max retries exceeded"}


def dispatch_new_notifications(
    new_items: List[Dict[str, Any]],
    db_module: Any
) -> Dict[str, int]:
    """
    Dispatches freshly discovered and fingerprinted vacancies to all active subscribers.
    Updates database automatically if users have blocked the bot.
    """
    if not new_items:
        return {"dispatched": 0, "failed": 0, "unsubscribed_blocked": 0}

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        logger.warning(f"TELEGRAM_BOT_TOKEN not set; skipping live Telegram alert dispatch for {len(new_items)} items.")
        return {"dispatched": 0, "failed": 0, "unsubscribed_blocked": 0}

    subscribers = db_module.get_all_subscribed_job_users()
    if not subscribers:
        logger.info(f"No active job alert subscribers in database. ({len(new_items)} new items saved)")
        return {"dispatched": 0, "failed": 0, "unsubscribed_blocked": 0}

    dispatched_count = 0
    failed_count = 0
    blocked_count = 0

    for user in subscribers:
        chat_id = str(user.get("telegram_id", ""))
        if not chat_id:
            continue
        format_pref = user.get("format_pref", "short")

        for item in new_items:
            msg_text = format_notification(item, format_pref=format_pref)
            result = send_single_telegram_message(bot_token, chat_id, msg_text)

            if result["success"]:
                dispatched_count += 1
            elif result["blocked"]:
                blocked_count += 1
                try:
                    db_module.unsubscribe_job_alert_user(chat_id)
                    logger.info(f"Unsubscribed blocked user {chat_id} from job alert notifications.")
                except Exception as ex:
                    logger.error(f"Failed to auto-unsubscribe blocked user {chat_id}: {ex}")
                # Break to next user since this user blocked the bot
                break
            else:
                failed_count += 1

            # Stagger dispatch slightly
            time.sleep(DEFAULT_STAGGER_DELAY)

    logger.info(f"Notification dispatch summary: dispatched={dispatched_count}, failed={failed_count}, blocked={blocked_count}")
    return {
        "dispatched": dispatched_count,
        "failed": failed_count,
        "unsubscribed_blocked": blocked_count
    }
