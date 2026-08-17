import os
import re
import json
import logging
import asyncio
import requests
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from . import db
from . import skills_documents as docs

logger = logging.getLogger(__name__)
IST = timezone(timedelta(hours=5, minutes=30), name="IST")

STORAGE_FILES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "storage", "files"))
os.makedirs(STORAGE_FILES_DIR, exist_ok=True)

# Default ntfy topic for user's phone push notifications
DEFAULT_NTFY_TOPIC = os.getenv("NTFY_TOPIC", "alya_bot_alerts_faijal")


def _clean_llm_think(text: str) -> str:
    """Strips <think> tags from LLM responses."""
    if "</think>" in text:
        text = text.split("</think>")[-1].strip()
    elif "<think>" in text:
        text = re.sub(r"<think>.*", "", text, flags=re.DOTALL).strip()
    return text.strip()


# ---------------------------------------------------------------------------
# 1. AI Neural Voice Generator (Text-to-Speech)
# ---------------------------------------------------------------------------

async def _synthesize_edge_tts(text: str, output_path: str, voice: str = "hi-IN-SwaraNeural") -> bool:
    """Async helper to generate neural audio with edge-tts."""
    try:
        import edge_tts
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)
        return True
    except Exception as e:
        logger.error(f"Edge TTS synthesis error: {e}")
        return False


def generate_voice_speech(text: str, voice_lang: str = "hi") -> Dict[str, Any]:
    """
    Synthesizes natural AI voice note in Hindi or Indian English and delivers as audio.
    """
    clean_text = text.strip()
    if not clean_text:
        return {"error": "Usage: `/speak <text>` or `/tts <text>`\nExample: `/speak Namaste! Aaj aapka din kaisa raha?`"}

    # Voice selection
    if voice_lang.lower() in ["en", "english"]:
        voice_model = "en-IN-NeerjaNeural"
    else:
        voice_model = "hi-IN-SwaraNeural"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"voice_{timestamp}.mp3"
    file_path = os.path.join(STORAGE_FILES_DIR, filename)

    try:
        # Run async TTS generator in sync loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success = loop.run_until_complete(_synthesize_edge_tts(clean_text, file_path, voice_model))
        loop.close()

        if success and os.path.exists(file_path):
            return {
                "success": True,
                "file_path": file_path,
                "file_type": "voice",
                "text": f"🎙️ **Voice Note Generated:** `{filename}`"
            }
        else:
            # Fallback to gTTS
            from gtts import gTTS
            tts = gTTS(text=clean_text, lang="hi" if voice_lang != "en" else "en")
            tts.save(file_path)
            return {
                "success": True,
                "file_path": file_path,
                "file_type": "voice",
                "text": f"🎙️ **Voice Audio Generated (gTTS):** `{filename}`"
            }
    except Exception as e:
        logger.error(f"TTS error: {e}")
        return {"error": f"⚠️ Voice generation failed: {e}"}


# ---------------------------------------------------------------------------
# 2. Instant Android Phone Push Notifications & Alarms
# ---------------------------------------------------------------------------

def send_phone_push_notification(title: str, message: str, priority: str = "high", topic: Optional[str] = None) -> str:
    """
    Sends an instant native push notification to user's Android phone using ntfy.sh.
    Features: Heads-up display, sound, custom vibration, click action.
    """
    target_topic = topic or DEFAULT_NTFY_TOPIC
    clean_title = title.strip() or "Alya AI Alert"
    clean_msg = message.strip() or "New notification from your AI assistant."

    priority_map = {
        "urgent": "5",
        "emergency": "5",
        "high": "4",
        "default": "3",
        "low": "2"
    }
    p_val = priority_map.get(priority.lower(), "4")

    headers = {
        "Title": clean_title,
        "Priority": p_val,
        "Tags": "robot,iphone,bell",
    }

    try:
        url = f"https://ntfy.sh/{target_topic}"
        resp = requests.post(url, data=clean_msg.encode("utf-8"), headers=headers, timeout=10)

        if resp.status_code == 200:
            return (
                f"📲 **Mobile Notification Dispatched to Phone!**\n\n"
                f"• **Title**: `{clean_title}`\n"
                f"• **Message**: `{clean_msg}`\n"
                f"• **Priority**: `{priority.upper()}`\n"
                f"• **Channel / Topic**: `ntfy.sh/{target_topic}`\n\n"
                f"_💡 Tip: If you have the free 'ntfy' Android app installed, subscribe to `{target_topic}` to receive instant screen popup alerts._"
            )
        else:
            return f"⚠️ Notification dispatch failed with status {resp.status_code}."
    except Exception as e:
        logger.error(f"Push notification error: {e}")
        return f"⚠️ Push notification error: {e}"


def find_and_ring_phone(user_id: str, topic: Optional[str] = None) -> str:
    """
    Triggers an emergency loud alarm notification on user's phone to locate it.
    """
    target_topic = topic or DEFAULT_NTFY_TOPIC
    headers = {
        "Title": "🚨 ALYA FIND MY PHONE ALARM 🚨",
        "Priority": "5",  # Max priority (bypasses Do Not Disturb on Android)
        "Tags": "rotating_light,loudspeaker,siren",
    }
    msg = "🔊 RINGING PHONE! Your AI assistant is sounding this alarm to help you locate your device."

    try:
        url = f"https://ntfy.sh/{target_topic}"
        resp = requests.post(url, data=msg.encode("utf-8"), headers=headers, timeout=10)
        if resp.status_code == 200:
            return (
                f"🚨 **Find My Phone Alarm Triggered!**\n\n"
                f"• Maximum priority alarm dispatched to your phone on channel `{target_topic}`.\n"
                f"• Device will ring and vibrate loudly to help you find it."
            )
    except Exception as e:
        logger.error(f"Find my phone error: {e}")

    return "⚠️ Could not trigger alarm on phone."


# ---------------------------------------------------------------------------
# 3. Phone Clipboard Sync
# ---------------------------------------------------------------------------

def sync_clipboard_to_phone(text: str, topic: Optional[str] = None) -> str:
    """
    Copies text or link directly to phone clipboard via push notification action.
    """
    clean_text = text.strip()
    if not clean_text:
        return "Usage: `/clip <text_or_url>`\nExample: `/clip https://example.com/long-token`"

    target_topic = topic or DEFAULT_NTFY_TOPIC
    headers = {
        "Title": "📋 Clipboard Synced",
        "Priority": "3",
        "Tags": "clipboard",
        "Actions": f"copy, Copy to Clipboard, {clean_text}"
    }

    try:
        url = f"https://ntfy.sh/{target_topic}"
        resp = requests.post(url, data=clean_text.encode("utf-8"), headers=headers, timeout=10)
        if resp.status_code == 200:
            return f"📋 **Synced to Mobile Device!**\n\n• Text: `{clean_text[:100]}...`\n• You can tap the notification on your phone to copy immediately."
    except Exception as e:
        logger.error(f"Clipboard sync error: {e}")

    return "⚠️ Failed to sync clipboard to phone."


# ---------------------------------------------------------------------------
# 4. WhatsApp Direct Message & Link Engine
# ---------------------------------------------------------------------------

def create_whatsapp_dispatch(phone_number: str, message: str) -> str:
    """
    Formats instant WhatsApp direct dispatch link and executes messaging webhook.
    """
    clean_phone = re.sub(r"[^\d+]", "", phone_number.strip())
    if not clean_phone:
        return "Usage: `/whatsapp <phone_number_with_country_code> <message>`\nExample: `/whatsapp +919876543210 Hello from Alya!`"

    clean_msg = message.strip()
    import urllib.parse
    encoded_msg = urllib.parse.quote(clean_msg)
    wa_link = f"https://wa.me/{clean_phone.replace('+', '')}?text={encoded_msg}"

    # Also dispatch to Android bridge webhook if configured
    android_bridge_url = os.getenv("ANDROID_BRIDGE_WEBHOOK_URL")
    if android_bridge_url:
        try:
            payload = {
                "action": "send_whatsapp",
                "phone": clean_phone,
                "message": clean_msg
            }
            requests.post(android_bridge_url, json=payload, timeout=5)
        except Exception:
            pass

    return (
        f"💬 **WhatsApp Dispatch Prepared:**\n\n"
        f"• **Recipient**: `{clean_phone}`\n"
        f"• **Message**: `{clean_msg}`\n\n"
        f"👉 [Tap Here to Open & Send in WhatsApp]({wa_link})"
    )


# ---------------------------------------------------------------------------
# 5. Universal Access & Unified Skills Directory
# ---------------------------------------------------------------------------

def get_full_skills_directory() -> str:
    """
    Returns an interactive catalog of ALL skills in Alya with their exact trigger commands.
    """
    return (
        "🌟 **Alya Autonomous AI Agent — Complete Skills Directory (95+ Skills)** 🌟\n\n"
        "**📱 Mobile & Voice Automation:**\n"
        "• `/speak <text>` / `/tts` — AI Voice reply in natural Hindi/English neural voice\n"
        "• `/notify <title> | <msg>` — Instant native push alert on phone lock screen\n"
        "• `/findmyphone` — Sound loud emergency alarm to locate your phone\n"
        "• `/clip <text>` — Push text directly into phone clipboard\n"
        "• `/whatsapp <phone> <msg>` — Direct WhatsApp message & link dispatch\n\n"
        "**📊 Indian Markets & Commodities:**\n"
        "• `/stock <ticker>` — Real-time NSE/BSE quotes (Reliance, TCS, Tata Motors, etc.)\n"
        "• `/nifty` & `/sensex` — Live Indian stock indices\n"
        "• `/gold` & `/silver` — Live 24K/22K 10g Gold & 1kg Silver bullion rates\n"
        "• `/fuel [city]` — Daily Petrol, Diesel & CNG rates\n\n"
        "**🚆 Travel & Indian Transit:**\n"
        "• `/pnr <10-digit>` — IRCTC train booking confirmation status\n"
        "• `/train <number>` — Live train route, halts & NTES tracker\n"
        "• `/flight <code` — Live flight radar, airline & arrival gate tracker\n\n"
        "**📄 Resumes, Documents & Converters:**\n"
        "• `/resume <role>` — ATS-friendly executive Resume PDF builder\n"
        "• `/coverletter <company> <role>` — Formal job application cover letter PDF\n"
        "• `/convert <format> <file>` — Convert image/doc format (PNG, JPG, WebP, PDF, TXT, Word)\n"
        "• `/pdf`, `/excel`, `/doc` — Styled document engines\n"
        "• `/invoice` — Bill & receipt OCR to structured Excel (.xlsx)\n\n"
        "**💻 Developer, DB & MCP:**\n"
        "• `/screenshot <url>` — Live 1200x800 website screenshot generator\n"
        "• `/py <code>` — Isolated Python code sandbox execution\n"
        "• `/sql <query>` — SQLite database query & table explorer\n"
        "• `/kg <add|list|search>` — Knowledge graph & deep relational memory\n"
        "• `/social <url>` — Twitter/X, Reddit post extractor\n"
        "• `/log [service]` — Real-time server diagnostics\n\n"
        "**📝 Content & Daily Briefing:**\n"
        "• `/youtube <url>` — YouTube video transcript & executive summary\n"
        "• `/summarize <url>` — Webpage / article instant markdown summary\n"
        "• `/briefing` — Daily morning digest (Weather, News, Markets, Planner)\n\n"
        "**🌤️ Real-Time Free APIs & Utilities:**\n"
        "• `/weather`, `/news`, `/crypto`, `/currency`, `/wiki`, `/movie`, `/math`, `/holiday`\n"
        "• `/remind`, `/note`, `/todo`, `/expense`, `/bill`, `/sip`, `/emi`, `/split`, `/qr`\n\n"
        "💡 _You can trigger any skill simply by talking naturally in Hinglish or English!_"
    )
