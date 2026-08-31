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
# 2. Universal Access & Unified Skills Directory
# ---------------------------------------------------------------------------

def get_full_skills_directory() -> str:
    """
    Returns an interactive catalog of ALL skills in Alya with their exact trigger commands.
    """
    from . import command_registry as reg
    return reg.generate_skills_directory()

