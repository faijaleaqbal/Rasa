"""
Production-hardened Telegram UX helpers for Alya:
1. Dynamic Typing Indicator with background refresh and guaranteed cleanup.
2. Random Emoji Reactions on incoming user messages.
"""

import os
import random
import logging
import asyncio
import threading
import time
from typing import Optional, List, Union, Set
import aiohttp
import requests

logger = logging.getLogger(__name__)

# Default reaction emoji list (Expanded Telegram 250+ reaction set)
DEFAULT_REACTION_EMOJIS = [
    # Smileys & Emotion (70)
    "😀", "😃", "😄", "😁", "😆", "😅", "🤣", "😂", "🙂", "🙃",
    "😉", "😊", "😇", "🥰", "😍", "🤩", "😘", "😗", "😚", "😙",
    "😋", "😛", "😜", "🤪", "😝", "🤑", "🤗", "🤭", "🤫", "🤔",
    "🤐", "🤨", "😐", "😑", "😶", "😏", "😒", "🙄", "😬", "🤥",
    "😌", "😔", "😪", "🤤", "😴", "😷", "🤒", "🤕", "🤢", "🤮",
    "🤧", "🥵", "🥶", "🥴", "😵", "🤯", "🤠", "🥳", "🥸", "😎",
    "🤓", "🧐", "😕", "😟", "🙁", "😮", "😯", "😲", "😳", "🥺",

    # Hearts & Affection (20)
    "❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍", "🤎", "💔",
    "❤️‍🔥", "❤️‍🩹", "❣️", "💕", "💞", "💓", "💗", "💖", "💘", "💝",

    # Hand Gestures & Body (35)
    "👍", "👎", "👊", "✊", "🤛", "🤜", "👏", "🙌", "👐", "🤲",
    "🤝", "🙏", "✍️", "💅", "🤳", "💪", "🦾", "🦿", "🦵", "🦶",
    "👂", "🦻", "👃", "👀", "👁️", "👅", "👄", "🫦", "🧠", "🫀",
    "🫁", "👋", "🤚", "🖐️", "✋",

    # Fantasy, Characters & Fun (25)
    "🤖", "👾", "👽", "👻", "💀", "☠️", "🤡", "👹", "👺", "🎃",
    "😺", "😸", "😹", "😻", "😼", "😽", "🙀", "😿", "😾", "🙈",
    "🙉", "🙊", "🐵", "🐸", "🦄",

    # Celebration, Stars & Magic (25)
    "🎉", "🎊", "🎈", "🎂", "🎆", "🎇", "✨", "🌟", "⭐", "💫",
    "💥", "🔥", "⚡", "⚡️", "☄️", "🌈", "☀️", "🌤️", "🌙", "🪄",
    "🔮", "💎", "🏆", "🥇", "🥈",

    # Tech, Work, Science & Travel (35)
    "🚀", "🛸", "🛰️", "✈️", "⛵", "🏎️", "🏍️", "🚲", "🛴", "🗺️",
    "🧭", "📱", "💻", "🖥️", "⌨️", "🖱️", "🔋", "🔌", "💡", "🔦",
    "🕯️", "🧲", "🔬", "🔭", "📡", "🩺", "💊", "🩹", "🧬", "⚙️",
    "🔧", "🔨", "🛡️", "⚔️", "🗝️",

    # Activities, Sports & Games (25)
    "🎯", "🎲", "🎳", "🎮", "🕹️", "🎰", "🧩", "🎨", "🎬", "🎤",
    "🎧", "🎼", "🎹", "🥁", "🎷", "🎺", "🎸", "🪕", "🎻", "⚽",
    "🏀", "🏈", "⚾", "🎾", "🏐",

    # Food, Drinks & Nature (35)
    "🍎", "🍓", "🍒", "🍇", "🍉", "🍌", "🍍", "🥭", "🍑", "🥥",
    "🍕", "🍔", "🍟", "🌭", "🍿", "🍩", "🍪", "🍫", "🍬", "🍭",
    "☕", "🍵", "🧃", "🥤", "🧋", "🍺", "🍻", "🥂", "🍾", "🍷",
    "🌸", "🌺", "🌻", "🌹", "🍀"
]



# Track reacted messages to prevent duplicate reaction attempts for the same message
_REACTED_MESSAGES_LOCK = threading.Lock()
_REACTED_MESSAGES: Set[str] = set()
_MAX_REACTED_CACHE_SIZE = 10000


def is_typing_enabled() -> bool:
    """Checks if Telegram typing indicator is enabled in configuration."""
    return os.getenv("TELEGRAM_TYPING_ENABLED", "true").strip().lower() in ("true", "1", "yes", "on")


def is_reaction_enabled() -> bool:
    """Checks if random message reactions are enabled in configuration."""
    return os.getenv("TELEGRAM_RANDOM_REACTION_ENABLED", "true").strip().lower() in ("true", "1", "yes", "on")


def get_reaction_emojis() -> List[str]:
    """Parses configurable reaction emojis list from environment or default pool."""
    raw = os.getenv("TELEGRAM_REACTION_EMOJIS")
    if raw:
        if raw.startswith("[") and raw.endswith("]"):
            import json
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list) and parsed:
                    return [str(e).strip() for e in parsed if str(e).strip()]
            except Exception:
                pass
        parts = [e.strip() for e in raw.split(",") if e.strip()]
        if parts:
            return parts
    return list(DEFAULT_REACTION_EMOJIS)


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
    bot_token: Optional[str] = None,
    session: Optional[aiohttp.ClientSession] = None,
) -> Optional[str]:
    """
    Sets a random emoji reaction to a specific user message using Telegram Bot API setMessageReaction.
    Attaches reaction directly to user's message.
    Returns the emoji used, or None if failed or disabled.
    """
    if not is_reaction_enabled():
        return None

    token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
    if not token or not chat_id or not message_id:
        return None

    # Deduplicate: react only once per message ID
    cache_key = f"{chat_id}:{message_id}"
    with _REACTED_MESSAGES_LOCK:
        if cache_key in _REACTED_MESSAGES:
            return None
        if len(_REACTED_MESSAGES) >= _MAX_REACTED_CACHE_SIZE:
            _REACTED_MESSAGES.clear()
        _REACTED_MESSAGES.add(cache_key)

    chosen_emoji = emoji or random.choice(get_reaction_emojis())
    url = f"https://api.telegram.org/bot{token}/setMessageReaction"
    payload = {
        "chat_id": str(chat_id),
        "message_id": int(message_id),
        "reaction": [{"type": "emoji", "emoji": chosen_emoji}],
        "is_big": False,
    }

    try:
        if session and not session.closed:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    logger.debug(f"Reacted with {chosen_emoji} to message {message_id} in chat {chat_id}")
                    return chosen_emoji
                else:
                    text = await resp.text()
                    logger.debug(f"Telegram setMessageReaction returned HTTP {resp.status}: {text}")
                    return None
        else:
            async with aiohttp.ClientSession() as temp_session:
                async with temp_session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        logger.debug(f"Reacted with {chosen_emoji} to message {message_id} in chat {chat_id}")
                        return chosen_emoji
                    return None
    except Exception as e:
        logger.debug(f"Failed to set message reaction on message {message_id} in chat {chat_id}: {e}")
        return None


def sync_set_message_reaction(
    chat_id: Union[str, int],
    message_id: Union[str, int],
    emoji: Optional[str] = None,
    bot_token: Optional[str] = None,
) -> Optional[str]:
    """Synchronous version of setMessageReaction."""
    if not is_reaction_enabled():
        return None

    token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
    if not token or not chat_id or not message_id:
        return None

    cache_key = f"{chat_id}:{message_id}"
    with _REACTED_MESSAGES_LOCK:
        if cache_key in _REACTED_MESSAGES:
            return None
        if len(_REACTED_MESSAGES) >= _MAX_REACTED_CACHE_SIZE:
            _REACTED_MESSAGES.clear()
        _REACTED_MESSAGES.add(cache_key)

    chosen_emoji = emoji or random.choice(get_reaction_emojis())
    url = f"https://api.telegram.org/bot{token}/setMessageReaction"
    payload = {
        "chat_id": str(chat_id),
        "message_id": int(message_id),
        "reaction": [{"type": "emoji", "emoji": chosen_emoji}],
        "is_big": False,
    }

    try:
        resp = requests.post(url, json=payload, timeout=5)
        if resp.status_code == 200:
            return chosen_emoji
        return None
    except Exception as e:
        logger.debug(f"Failed to sync set message reaction on message {message_id}: {e}")
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
