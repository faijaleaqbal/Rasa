"""
Production-hardened Telegram UX helpers for Alya:
1. Dynamic Typing Indicator with background refresh and guaranteed cleanup.
2. Context-Aware Deterministic Emoji Reactions on incoming user messages.
"""

import os
import logging
import asyncio
import threading
import time
from typing import Optional, List, Union, Set, Tuple
import aiohttp
import requests

from addons.emoji_reaction_manager import (
    get_emoji_reaction_manager,
    CATEGORY_EMOJIS,
    CATEGORY_TELEGRAM_FALLBACKS,
    EmojiCategory,
)

logger = logging.getLogger(__name__)

# Verified Telegram Bot API standard reaction emojis (Telegram Bot API 7.0+)
DEFAULT_REACTION_EMOJIS = [
    "👍", "❤️", "🔥", "👎", "😎", "🎉", "😁", "😢", "😡", "🤔",
    "👏", "💯", "🥰", "🤩", "🙏", "👌", "🤣", "🤯", "😱", "⚡",
    "🏆", "💔", "🤨", "😐", "🤓", "👻", "🤝", "🫡", "🆒", "💘",
    "😘", "👾", "🤷", "👋", "😊", "🌅", "😄", "💕", "😔", "🫂",
    "💙", "😤", "😠", "🤦", "😕", "❓", "😳", "😮", "😆", "😂",
    "✅", "❌", "💡", "🙂"
]

VALID_TELEGRAM_REACTIONS = set(DEFAULT_REACTION_EMOJIS) | {
    "❤", "🤮", "💩", "🕊", "🤡", "🥱", "🥴", "😍", "🐳", "🌚",
    "🌭", "🍌", "🍓", "🍾", "💋", "🖕", "😈", "😴", "😭", "👨‍💻",
    "👀", "🎃", "🙈", "😇", "😨", "✍", "🎅", "🎄", "☃", "💅",
    "🤪", "🗿", "🙉", "🦄", "💊", "🙊", "🤷‍♂️", "🤷‍♀️", "⚡️", "✍️",
    "☃️", "🕊️", "🤗", "🤬"
}

# Guaranteed fallback emojis if a custom/primary emoji fails
FALLBACK_REACTION_EMOJIS = ["👍", "❤️", "🔥", "🎉", "👏", "💯", "😎"]

# Track reacted messages to prevent duplicate reaction attempts for the same message
_REACTED_MESSAGES_LOCK = threading.Lock()
_REACTED_MESSAGES: Set[str] = set()
_MAX_REACTED_CACHE_SIZE = 10000


def is_typing_enabled() -> bool:
    """Checks if Telegram typing indicator is enabled in configuration."""
    return os.getenv("TELEGRAM_TYPING_ENABLED", "true").strip().lower() in ("true", "1", "yes", "on")


def is_reaction_enabled() -> bool:
    """Checks if context-aware message reactions are enabled in configuration."""
    # If any reaction env var is explicitly set to false/disabled, disable reactions
    for key in ("TELEGRAM_CONTEXT_REACTIONS_ENABLED", "TELEGRAM_REACTIONS_ENABLED", "TELEGRAM_RANDOM_REACTION_ENABLED"):
        val = os.getenv(key)
        if val is not None and val.strip().lower() in ("false", "0", "no", "off"):
            return False

    for key in ("TELEGRAM_CONTEXT_REACTIONS_ENABLED", "TELEGRAM_REACTIONS_ENABLED", "TELEGRAM_RANDOM_REACTION_ENABLED"):
        val = os.getenv(key)
        if val is not None and val.strip().lower() in ("true", "1", "yes", "on"):
            return True

    return True


def get_reaction_emojis() -> List[str]:
    """Parses configurable reaction emojis list from environment and validates against supported Telegram reactions."""
    raw = os.getenv("TELEGRAM_REACTION_EMOJIS")
    if raw:
        if raw.startswith("[") and raw.endswith("]"):
            import json
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list) and parsed:
                    filtered = [str(e).strip() for e in parsed if str(e).strip() in VALID_TELEGRAM_REACTIONS]
                    if filtered:
                        return filtered
            except Exception:
                pass
        parts = [e.strip() for e in raw.split(",") if e.strip() and e.strip() in VALID_TELEGRAM_REACTIONS]
        if parts:
            return parts
    return list(DEFAULT_REACTION_EMOJIS)


def validate_reaction_pool() -> int:
    """Validates the reaction pool and logs available count."""
    pool = get_reaction_emojis()
    logger.info(f"Telegram reaction pool validated with {len(pool)} supported standard emojis.")
    return len(pool)


def get_typing_interval() -> float:
    """Gets typing refresh interval in seconds (default 4.0s)."""
    try:
        return float(os.getenv("TELEGRAM_TYPING_INTERVAL_SECONDS", "4.0"))
    except ValueError:
        return 4.0


async def async_send_chat_action(
    chat_id: Union[str, int],
    action: str = "typing",
    bot_token: Optional[str] = None,
    session: Optional[aiohttp.ClientSession] = None,
) -> bool:
    """
    Sends chat action (e.g. 'typing') to Telegram Bot API asynchronously.
    """
    token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
    if not token or not chat_id:
        return False

    url = f"https://api.telegram.org/bot{token}/sendChatAction"
    payload = {"chat_id": str(chat_id), "action": action}

    try:
        if session and not session.closed:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                return resp.status == 200
        else:
            async with aiohttp.ClientSession() as temp_session:
                async with temp_session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    return resp.status == 200
    except Exception as e:
        logger.debug(f"Failed to send async chat action '{action}' to chat {chat_id}: {e}")
        return False


def sync_send_chat_action(
    chat_id: Union[str, int],
    action: str = "typing",
    bot_token: Optional[str] = None,
) -> bool:
    """Sends chat action synchronously (for non-async workers/scheduler)."""
    token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
    if not token or not chat_id:
        return False

    url = f"https://api.telegram.org/bot{token}/sendChatAction"
    payload = {"chat_id": str(chat_id), "action": action}
    try:
        resp = requests.post(url, json=payload, timeout=5)
        return resp.status_code == 200
    except Exception as e:
        logger.debug(f"Failed to send sync chat action to chat {chat_id}: {e}")
        return False


async def async_set_message_reaction(
    chat_id: Union[str, int],
    message_id: Union[str, int],
    emoji: Optional[str] = None,
    text: Optional[str] = None,
    bot_token: Optional[str] = None,
    session: Optional[aiohttp.ClientSession] = None,
    user_id: Optional[Union[str, int]] = None,
) -> Optional[str]:
    """
    Sets a context-aware emoji reaction to a specific user message using Telegram Bot API setMessageReaction.
    Attaches reaction directly to user's message.
    Returns the emoji used, or None if failed, disabled, or skipped.
    """
    if not is_reaction_enabled():
        return None

    token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
    if not token or not chat_id or not message_id:
        return None

    # Determine emoji reaction via EmojiReactionManager if not explicitly specified
    manager = get_emoji_reaction_manager()
    if emoji:
        chosen_emoji = emoji
    elif text is not None:
        chosen_emoji = manager.get_reaction(text=text, user_id=str(user_id or chat_id))
    else:
        # Fallback for bare API calls with neither emoji nor text specified
        chosen_emoji = "👍"

    if not chosen_emoji:
        return None

    # Deduplicate: react only once per message ID
    cache_key = f"{chat_id}:{message_id}"
    with _REACTED_MESSAGES_LOCK:
        if cache_key in _REACTED_MESSAGES:
            logger.debug(f"Message {message_id} in chat {chat_id} already reacted. Skipping duplicate.")
            return None
        if len(_REACTED_MESSAGES) >= _MAX_REACTED_CACHE_SIZE:
            _REACTED_MESSAGES.clear()
        _REACTED_MESSAGES.add(cache_key)

    url = f"https://api.telegram.org/bot{token}/setMessageReaction"

    async def _post_reaction(target_emoji: str) -> Tuple[bool, int, str]:
        req_payload = {
            "chat_id": str(chat_id),
            "message_id": int(message_id),
            "reaction": [{"type": "emoji", "emoji": target_emoji}],
            "is_big": False,
        }
        if session and not session.closed:
            async with session.post(url, json=req_payload, timeout=aiohttp.ClientTimeout(total=4)) as resp:
                resp_text = await resp.text()
                return (resp.status == 200, resp.status, resp_text)
        else:
            async with aiohttp.ClientSession() as temp_session:
                async with temp_session.post(url, json=req_payload, timeout=aiohttp.ClientTimeout(total=4)) as resp:
                    resp_text = await resp.text()
                    return (resp.status == 200, resp.status, resp_text)

    try:
        ok, status_code, resp_text = await _post_reaction(chosen_emoji)
        if ok:
            logger.info(f"Successfully applied Telegram reaction '{chosen_emoji}' to message {message_id} in chat {chat_id}")
            return chosen_emoji
        else:
            logger.warning(f"Telegram reaction '{chosen_emoji}' failed for message {message_id} in chat {chat_id}: HTTP {status_code} - {resp_text}")
            # If rejected due to invalid reaction, retry with category-aligned fallback
            if "REACTION_INVALID" in resp_text or "REACTION_EMOJI_INVALID" in resp_text:
                cat_fallback = manager.get_fallback_emoji(chosen_emoji)
                candidates = [cat_fallback] + [fb for fb in FALLBACK_REACTION_EMOJIS if fb != chosen_emoji and fb != cat_fallback]
                for fb_emoji in candidates:
                    fb_ok, fb_status, fb_text = await _post_reaction(fb_emoji)
                    if fb_ok:
                        logger.info(f"Successfully applied fallback Telegram reaction '{fb_emoji}' to message {message_id} in chat {chat_id}")
                        return fb_emoji
                    logger.warning(f"Telegram reaction fallback '{fb_emoji}' failed: HTTP {fb_status} - {fb_text}")
            return None
    except Exception as e:
        logger.warning(f"Telegram reaction error for message {message_id} in chat {chat_id}: {e}")
        return None


def sync_set_message_reaction(
    chat_id: Union[str, int],
    message_id: Union[str, int],
    emoji: Optional[str] = None,
    text: Optional[str] = None,
    bot_token: Optional[str] = None,
    user_id: Optional[Union[str, int]] = None,
) -> Optional[str]:
    """Synchronous version of setMessageReaction with context awareness and fallback."""
    if not is_reaction_enabled():
        return None

    token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
    if not token or not chat_id or not message_id:
        return None

    manager = get_emoji_reaction_manager()
    if emoji:
        chosen_emoji = emoji
    elif text is not None:
        chosen_emoji = manager.get_reaction(text=text, user_id=str(user_id or chat_id))
    else:
        chosen_emoji = "👍"

    if not chosen_emoji:
        return None

    cache_key = f"{chat_id}:{message_id}"
    with _REACTED_MESSAGES_LOCK:
        if cache_key in _REACTED_MESSAGES:
            return None
        if len(_REACTED_MESSAGES) >= _MAX_REACTED_CACHE_SIZE:
            _REACTED_MESSAGES.clear()
        _REACTED_MESSAGES.add(cache_key)

    url = f"https://api.telegram.org/bot{token}/setMessageReaction"

    def _post_reaction_sync(target_emoji: str) -> Tuple[bool, int, str]:
        req_payload = {
            "chat_id": str(chat_id),
            "message_id": int(message_id),
            "reaction": [{"type": "emoji", "emoji": target_emoji}],
            "is_big": False,
        }
        resp = requests.post(url, json=req_payload, timeout=4)
        return (resp.status_code == 200, resp.status_code, resp.text)

    try:
        ok, status_code, resp_text = _post_reaction_sync(chosen_emoji)
        if ok:
            logger.info(f"Successfully applied Telegram reaction '{chosen_emoji}' to message {message_id} in chat {chat_id}")
            return chosen_emoji
        else:
            logger.warning(f"Telegram reaction '{chosen_emoji}' failed for message {message_id} in chat {chat_id}: HTTP {status_code} - {resp_text}")
            if "REACTION_INVALID" in resp_text or "REACTION_EMOJI_INVALID" in resp_text:
                cat_fallback = manager.get_fallback_emoji(chosen_emoji)
                candidates = [cat_fallback] + [fb for fb in FALLBACK_REACTION_EMOJIS if fb != chosen_emoji and fb != cat_fallback]
                for fb_emoji in candidates:
                    fb_ok, fb_status, fb_text = _post_reaction_sync(fb_emoji)
                    if fb_ok:
                        logger.info(f"Successfully applied fallback Telegram reaction '{fb_emoji}' to message {message_id} in chat {chat_id}")
                        return fb_emoji
            return None
    except Exception as e:
        logger.warning(f"Telegram reaction error for message {message_id} in chat {chat_id}: {e}")
        return None


class TelegramTypingScope:
    """
    Asynchronous context manager that immediately sends 'typing' to Telegram
    and maintains a background refresh loop until exiting the scope.
    Guarantees clean cancellation on normal exit, exceptions, or timeouts.
    """

    def __init__(
        self,
        chat_id: Union[str, int],
        bot_token: Optional[str] = None,
        interval: Optional[float] = None,
        session: Optional[aiohttp.ClientSession] = None,
    ):
        self.chat_id = str(chat_id)
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.interval = interval if interval is not None else get_typing_interval()
        self.session = session
        self._task: Optional[asyncio.Task] = None
        self._stopped = False

    async def __aenter__(self):
        if is_typing_enabled() and self.bot_token and self.chat_id:
            await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()

    async def start(self):
        """Immediately displays typing indicator and starts periodic refresh task."""
        if self._task and not self._task.done():
            return

        self._stopped = False
        # 1. Immediately send first typing action
        try:
            await async_send_chat_action(self.chat_id, action="typing", bot_token=self.bot_token, session=self.session)
        except Exception:
            pass

        # 2. Launch background periodic refresh
        try:
            loop = asyncio.get_running_loop()
            self._task = loop.create_task(self._refresh_loop(), name=f"TG_Typing_{self.chat_id}")
        except RuntimeError:
            pass

    async def _refresh_loop(self):
        """Background loop that refreshes typing every `self.interval` seconds."""
        try:
            while not self._stopped:
                await asyncio.sleep(self.interval)
                if self._stopped:
                    break
                await async_send_chat_action(self.chat_id, action="typing", bot_token=self.bot_token, session=self.session)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug(f"Typing refresh loop exception for chat {self.chat_id}: {e}")

    async def stop(self):
        """Cleanly stops and cancels the typing background task."""
        self._stopped = True
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await asyncio.gather(self._task, return_exceptions=True)
            except Exception:
                pass
            self._task = None


class SyncTelegramTypingScope:
    """
    Synchronous context manager using a background daemon thread for non-async environments.
    """

    def __init__(
        self,
        chat_id: Union[str, int],
        bot_token: Optional[str] = None,
        interval: Optional[float] = None,
    ):
        self.chat_id = str(chat_id)
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.interval = interval if interval is not None else get_typing_interval()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def __enter__(self):
        if is_typing_enabled() and self.bot_token and self.chat_id:
            self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        sync_send_chat_action(self.chat_id, action="typing", bot_token=self.bot_token)

        def _worker():
            while not self._stop_event.wait(self.interval):
                if self._stop_event.is_set():
                    break
                sync_send_chat_action(self.chat_id, action="typing", bot_token=self.bot_token)

        self._thread = threading.Thread(target=_worker, daemon=True, name=f"SyncTyping_{self.chat_id}")
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.2)
            self._thread = None
