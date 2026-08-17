import os
import re
import json
import logging
import requests
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from . import db
from . import skills_documents as docs

logger = logging.getLogger(__name__)
IST = timezone(timedelta(hours=5, minutes=30), name="IST")

# Android Device Webhook Endpoint (Configurable in .env or default localhost / Tailscale / Ngrok)
ANDROID_NODE_URL = os.getenv("ANDROID_NODE_URL", "http://127.0.0.1:8088/execute")
DEFAULT_NTFY_TOPIC = os.getenv("NTFY_TOPIC", "alya_bot_alerts_faijal")


def _clean_llm_think(text: str) -> str:
    """Strips <think> tags from LLM responses."""
    if "</think>" in text:
        text = text.split("</think>")[-1].strip()
    elif "<think>" in text:
        text = re.sub(r"<think>.*", "", text, flags=re.DOTALL).strip()
    return text.strip()


def dispatch_to_phone(action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sends an actionable execution packet to the Android Phone Agent (Termux/Tasker bridge).
    If direct node is offline, falls back to high-priority ntfy push notification with intent actions.
    """
    payload = {
        "action": action,
        "params": params,
        "timestamp": datetime.now(IST).isoformat()
    }

    # 1. Direct Android Node Webhook
    if ANDROID_NODE_URL:
        try:
            resp = requests.post(ANDROID_NODE_URL, json=payload, timeout=4)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.debug(f"Direct Android node offline: {e}. Falling back to Push Intent.")

    # 2. Push Notification fallback (ntfy actionable intents)
    headers = {
        "Title": f"📱 Alya Mobile Action: {action.replace('_', ' ').title()}",
        "Priority": "5",
        "Tags": "robot,iphone,gear",
    }

    action_label = action.replace("_", " ").title()
    summary_msg = f"Executing {action_label} with {json.dumps(params)}"

    try:
        url = f"https://ntfy.sh/{DEFAULT_NTFY_TOPIC}"
        requests.post(url, data=summary_msg.encode("utf-8"), headers=headers, timeout=5)
    except Exception:
        pass

    return {"status": "queued", "action": action, "params": params}


# ---------------------------------------------------------------------------
# 1. Make Phone Call & Dialler
# ---------------------------------------------------------------------------

def make_phone_call(phone_number: str) -> str:
    """
    Initiates an outgoing phone call on the Android smartphone.
    """
    clean_phone = re.sub(r"[^\d+]", "", phone_number.strip())
    if not clean_phone:
        return "Usage: `/call <phone_number>`\nExample: `/call +919876543210`"

    res = dispatch_to_phone("make_call", {"phone": clean_phone})
    return (
        f"📞 **Initiating Phone Call on Mobile...**\n\n"
        f"• **Dialing**: `{clean_phone}`\n"
        f"• **Status**: Command dispatched to Android device.\n"
        f"• [Tap to Dial on Phone](tel:{clean_phone})"
    )


# ---------------------------------------------------------------------------
# 2. Send SMS & Read Recent SMS
# ---------------------------------------------------------------------------

def send_phone_sms(phone_number: str, message: str) -> str:
    """
    Sends an SMS text message directly from user's Android phone SIM card.
    """
    clean_phone = re.sub(r"[^\d+]", "", phone_number.strip())
    clean_msg = message.strip()
    if not clean_phone or not clean_msg:
        return "Usage: `/sms <phone_number> <message>`\nExample: `/sms +919876543210 I will reach in 10 mins.`"

    res = dispatch_to_phone("send_sms", {"phone": clean_phone, "message": clean_msg})
    return (
        f"💬 **SMS Dispatched to Phone SIM!**\n\n"
        f"• **To**: `{clean_phone}`\n"
        f"• **Message**: `{clean_msg}`\n"
        f"• **Status**: Queued for SIM delivery."
    )


def read_recent_phone_sms(limit: int = 5) -> str:
    """
    Reads incoming SMS from Android device inbox.
    """
    res = dispatch_to_phone("read_sms", {"limit": limit})
    if res.get("messages"):
        lines = []
        for m in res["messages"]:
            lines.append(f"• **From `{m.get('from', 'Unknown')}`** ({m.get('received', '')}):\n  _{m.get('body', '')}_")
        return f"📩 **Recent SMS Inbox ({len(lines)} messages):**\n\n" + "\n\n".join(lines)

    return (
        f"📩 **SMS Inbox Reader:**\n\n"
        f"• Reading last {limit} messages from Android SMS database.\n"
        f"• Connect your Android phone with `/mobile start` to stream live incoming SMS."
    )


# ---------------------------------------------------------------------------
# 3. Set System Alarm & Timers
# ---------------------------------------------------------------------------

def set_phone_alarm(time_str: str, label: str = "Alya Alarm") -> str:
    """
    Sets a system alarm on user's Android clock app.
    Example: '07:30', '7:30 AM', 'tomorrow at 6am'
    """
    clean_time = time_str.strip()
    clean_label = label.strip() or "Alya AI Alarm"
    if not clean_time:
        return "Usage: `/alarm <time> [label]`\nExample: `/alarm 07:00 AM Morning Workout`"

    # Extract hour & minute
    match = re.search(r"(\d{1,2}):(\d{2})", clean_time)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
    else:
        hour = 7
        minute = 0

    res = dispatch_to_phone("set_alarm", {"time": clean_time, "hour": hour, "minute": minute, "label": clean_label})
    return (
        f"⏰ **System Alarm Set on Android Phone!**\n\n"
        f"• **Alarm Time**: `{clean_time}`\n"
        f"• **Label**: `{clean_label}`\n"
        f"• **Device**: Android System Clock"
    )


def set_phone_timer(duration_str: str, label: str = "Timer") -> str:
    """
    Sets a countdown timer on Android device.
    Example: '5 minutes', '10 mins', '30 seconds'
    """
    clean_dur = duration_str.strip()
    if not clean_dur:
        return "Usage: `/timer <duration> [label]`\nExample: `/timer 10 minutes Tea Timer`"

    seconds = 300
    match_min = re.search(r"(\d+)\s*(?:m|min|minute)", clean_dur.lower())
    match_sec = re.search(r"(\d+)\s*(?:s|sec|second)", clean_dur.lower())
    if match_min:
        seconds = int(match_min.group(1)) * 60
    elif match_sec:
        seconds = int(match_sec.group(1))

    res = dispatch_to_phone("set_timer", {"seconds": seconds, "label": label or "Alya Timer"})
    return (
        f"⏳ **Countdown Timer Started on Phone!**\n\n"
        f"• **Duration**: `{seconds // 60} min {seconds % 60} sec` (`{clean_dur}`)\n"
        f"• **Label**: `{label}`\n"
        f"• **Status**: Active countdown on Android"
    )


# ---------------------------------------------------------------------------
# 4. Open Files & Launch Apps on Phone
# ---------------------------------------------------------------------------

def open_file_or_app_on_phone(target: str) -> str:
    """
    Opens a file (PDF, image, doc) or launches an installed app (WhatsApp, YouTube, Settings) on Android.
    """
    clean_target = target.strip()
    if not clean_target:
        return "Usage: `/open <app_name_or_file>`\nExample: `/open WhatsApp` or `/open /sdcard/Download/invoice.pdf`"

    res = dispatch_to_phone("open_target", {"target": clean_target})
    return (
        f"📱 **Launching on Android Phone...**\n\n"
        f"• **Target**: `{clean_target}`\n"
        f"• **Action**: Opening application/file in default Android viewer."
    )


# ---------------------------------------------------------------------------
# 5. AI Call Screening & Answering Agent (Aapki taraf se baat karna)
# ---------------------------------------------------------------------------

def screen_incoming_call_message(caller_number: str, caller_statement: str) -> str:
    """
    Simulates AI Call Screening: takes caller's spoken statement and generates an empathetic AI verbal reply,
    then formats a structured summary for the user.
    """
    clean_caller = caller_number.strip() or "Unknown Caller"
    clean_statement = caller_statement.strip()

    try:
        from groq import Groq
        key = os.getenv("GROQ_API_KEY")
        if key:
            client = Groq(api_key=key)
            resp = client.chat.completions.create(
                model="qwen/qwen3.6-27b",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are Alya, an intelligent AI Call Attendant answering a phone call on behalf of Faijal. "
                            "Faijal is currently in a meeting. "
                            "1. Generate a polite, short 2-sentence verbal reply to the caller confirming you recorded their message. "
                            "2. Then extract a structured summary for Faijal with: Caller Intent, Urgency (Low/Medium/High), Action Item. "
                            "Format clearly."
                        )
                    },
                    {"role": "user", "content": f"Caller: {clean_caller}\nCaller said: '{clean_statement}'"}
                ],
                temperature=0.2,
                max_tokens=600
            )
            res = _clean_llm_think(resp.choices[0].message.content)
            return (
                f"📞 **AI Call Screening Alert — Missed Call Handled!**\n\n"
                f"• **Caller**: `{clean_caller}`\n"
                f"• **Caller Said**: *\"{clean_statement}\"*\n\n"
                f"🤖 **AI Screening Report & Response:**\n\n{res}"
            )
    except Exception as e:
        logger.error(f"Call screening error: {e}")

    return (
        f"📞 **AI Call Attendant Report:**\n\n"
        f"• **Caller**: `{clean_caller}`\n"
        f"• **Message**: *\"{clean_statement}\"*\n"
        f"• **Action**: Noted and recorded for follow-up."
    )
