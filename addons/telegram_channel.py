import os
import re
import json
import ssl
import logging
import asyncio
from typing import Any, Dict, List, Optional, Text, Callable, Awaitable
from sanic import Blueprint, response
from sanic.request import Request
from sanic.response import HTTPResponse

import certifi
import aiohttp
import requests
from rasa.core.channels.channel import InputChannel, UserMessage, OutputChannel
from rasa.core.channels.telegram import TelegramInput, TelegramOutput
from rasa.shared.constants import INTENT_MESSAGE_PREFIX
from rasa.shared.core.constants import USER_INTENT_RESTART
from aiogram.types import Update

logger = logging.getLogger(__name__)

STORAGE_FILES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "storage", "files"))
os.makedirs(STORAGE_FILES_DIR, exist_ok=True)


def expand_env(val: Optional[str]) -> Optional[str]:
    if not val:
        return val
    if isinstance(val, str):
        if val.startswith("${") and val.endswith("}"):
            env_key = val[2:-1]
            return os.getenv(env_key, "")
        if val.startswith("$"):
            return os.getenv(val[1:], "")
    return str(val)


def download_telegram_file(bot_token: str, file_id: str, dest_filename: str) -> Optional[str]:
    """Downloads a file from Telegram using Bot API getFile and saves locally."""
    try:
        get_file_url = f"https://api.telegram.org/bot{bot_token}/getFile?file_id={file_id}"
        resp = requests.get(get_file_url, timeout=10)
        if resp.status_code == 200:
            file_info = resp.json().get("result", {})
            remote_path = file_info.get("file_path")
            if remote_path:
                download_url = f"https://api.telegram.org/file/bot{bot_token}/{remote_path}"
                file_resp = requests.get(download_url, timeout=30)
                if file_resp.status_code == 200:
                    local_path = os.path.join(STORAGE_FILES_DIR, dest_filename)
                    with open(local_path, "wb") as f:
                        f.write(file_resp.content)
                    logger.info(f"Downloaded Telegram file to {local_path}")
                    return local_path
    except Exception as e:
        logger.error(f"Failed to download Telegram file {file_id}: {e}")
    return None


def transcribe_audio_file(audio_path: str) -> Optional[str]:
    """Transcribes audio file using Groq Whisper API (whisper-large-v3-turbo)."""
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key or not os.path.exists(audio_path):
        return None

    try:
        from groq import Groq
        client = Groq(api_key=groq_key)
        with open(audio_path, "rb") as af:
            transcription = client.audio.transcriptions.create(
                file=af,
                model="whisper-large-v3-turbo",
                prompt="Hinglish conversational speech, English, Hindi",
                response_format="text"
            )
        text = str(transcription).strip()
        logger.info(f"Voice note transcribed: {text}")
        return text
    except Exception as e:
        logger.error(f"Whisper transcription failed: {e}")
        return None


def format_telegram_markdown(text: Optional[str]) -> str:
    """
    Normalizes standard Markdown (CommonMark/LLM generated) into Telegram Legacy Markdown:
    1. Preserves preformatted code blocks ```...``` and inline code `...`
    2. Converts Markdown headers (# Heading) to bold (*Heading*)
    3. Converts standard bold-italic (***text***) to (*_text_*)
    4. Converts standard bold (**text**) to Telegram legacy bold (*text*)
    5. Converts double underscore bold (__text__) to Telegram legacy bold (*text*)
    """
    if not text:
        return "" if text is None else str(text)

    # 1. Protect code blocks and inline code
    code_blocks = []
    def save_code_block(m):
        code_blocks.append(m.group(0))
        return f"TGCODEBLOCK{len(code_blocks)-1}TG"

    text = re.sub(r"```[\s\S]*?```", save_code_block, text)

    inline_codes = []
    def save_inline_code(m):
        inline_codes.append(m.group(0))
        return f"TGINLINECODE{len(inline_codes)-1}TG"

    text = re.sub(r"`[^`\n]+`", save_inline_code, text)

    # 2. Convert markdown headers (###, ##, #) to bold (*Header*)
    text = re.sub(r"^[ \t]*#{1,6}[ \t]+(.+?)[ \t]*$", r"*\1*", text, flags=re.MULTILINE)

    # 3. Convert standard markdown bold-italic ***text*** -> *_text_*
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"*_\1_*", text)

    # 4. Convert standard markdown bold **text** -> *text*
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)
    text = re.sub(r"(?<![a-zA-Z0-9])__(.+?)__(?![a-zA-Z0-9])", r"*\1*", text)

    # 5. Restore inline codes and code blocks
    for i, code in enumerate(inline_codes):
        text = text.replace(f"TGINLINECODE{i}TG", code)
    for i, code in enumerate(code_blocks):
        text = text.replace(f"TGCODEBLOCK{i}TG", code)

    return text


class SmartTelegramOutput(TelegramOutput):
    """
    Resilient Telegram OutputChannel that:
    1. Avoids 'Event loop is closed' errors by binding session to running loop.
    2. Supports global Markdown parse_mode with automatic normalization.
    3. Gracefully falls back to plain text if Telegram API entity parsing fails.
    """

    def __init__(self, access_token: Optional[Text], parse_mode: Optional[Text] = "Markdown") -> None:
        super().__init__(access_token)
        self._default_parse_mode = parse_mode

    @property
    def session(self) -> aiohttp.ClientSession:
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        need_new_session = False
        if self._session is None or self._session.closed:
            need_new_session = True
        elif hasattr(self._session, "_loop"):
            if self._session._loop.is_closed():
                need_new_session = True
            elif current_loop and self._session._loop != current_loop:
                need_new_session = True

        if need_new_session:
            self._main_loop = current_loop
            connector_init = dict(self._connector_init)
            connector = self._connector_class(**connector_init)
            self._session = aiohttp.ClientSession(
                connector=connector,
                json_serialize=json.dumps
            )

        return self._session

    async def send_text_message(
        self, recipient_id: Text, text: Text, **kwargs: Any
    ) -> None:
        """Sends formatted text message with Markdown parse_mode and fallback."""
        if not text:
            return

        formatted_text = format_telegram_markdown(text)
        max_len = 4000
        chunks = []

        if len(formatted_text) > max_len:
            curr = []
            curr_len = 0
            for line in formatted_text.split("\n"):
                if curr_len + len(line) + 1 > max_len:
                    if curr:
                        chunks.append("\n".join(curr))
                    curr = [line]
                    curr_len = len(line)
                else:
                    curr.append(line)
                    curr_len += len(line) + 1
            if curr:
                chunks.append("\n".join(curr))
        else:
            chunks = [formatted_text]

        for chunk in chunks:
            if not chunk.strip():
                continue
            try:
                await self.send_message(
                    recipient_id,
                    chunk,
                    parse_mode=self._default_parse_mode
                )
            except Exception as e:
                logger.warning(
                    f"Telegram markdown send_message failed ({e}), falling back to plain text."
                )
                try:
                    await self.send_message(
                        recipient_id,
                        chunk,
                        parse_mode=None
                    )
                except Exception as ex2:
                    logger.error(f"Telegram plain send_message also failed: {ex2}")

    async def send_text_with_buttons(
        self,
        recipient_id: Text,
        text: Text,
        buttons: List[Dict[Text, Any]],
        button_type: Optional[Text] = "inline",
        **kwargs: Any,
    ) -> None:
        """Sends text message with buttons, Markdown parsing, and error fallback."""
        from aiogram.types import (
            InlineKeyboardMarkup,
            InlineKeyboardButton,
            ReplyKeyboardMarkup,
            KeyboardButton,
        )

        if button_type == "inline":
            reply_markup = InlineKeyboardMarkup()
            button_list = [
                InlineKeyboardButton(s["title"], callback_data=s["payload"])
                for s in buttons
            ]
            reply_markup.row(*button_list)
        elif button_type == "vertical":
            reply_markup = InlineKeyboardMarkup()
            for s in buttons:
                reply_markup.row(InlineKeyboardButton(s["title"], callback_data=s["payload"]))
        elif button_type == "reply":
            reply_markup = ReplyKeyboardMarkup(resize_keyboard=False, one_time_keyboard=True)
            for button in buttons:
                if isinstance(button, list):
                    reply_markup.add(*(KeyboardButton(s["title"]) for s in button))
                else:
                    reply_markup.add(KeyboardButton(button["title"]))
        else:
            logger.error(f"Trying to send text with buttons for unknown button type {button_type}")
            return

        formatted_text = format_telegram_markdown(text)
        try:
            await self.send_message(
                recipient_id,
                formatted_text,
                reply_markup=reply_markup,
                parse_mode=self._default_parse_mode
            )
        except Exception as e:
            logger.warning(f"Telegram markdown send_text_with_buttons failed ({e}), falling back to plain text.")
            try:
                await self.send_message(
                    recipient_id,
                    formatted_text,
                    reply_markup=reply_markup,
                    parse_mode=None
                )
            except Exception as ex2:
                logger.error(f"Telegram plain send_text_with_buttons failed: {ex2}")


class SmartTelegramInput(TelegramInput):
    """
    Enhanced Telegram InputChannel that:
    1. Dynamically expands environment variables from credentials.
    2. Configures Telegram parse_mode globally.
    3. Enforces strict Telegram User ID whitelisting across all message types.
    4. Handles voice messages (Whisper transcription).
    5. Handles documents (.pdf, .xlsx, .docx) and photos.
    6. Prevents 'Event loop is closed' errors with SmartTelegramOutput.
    """

    @classmethod
    def name(cls) -> Text:
        return "telegram"

    @classmethod
    def from_credentials(cls, credentials: Optional[Dict[Text, Any]]) -> "SmartTelegramInput":
        if not credentials:
            credentials = {}

        raw_token = credentials.get("access_token") or os.getenv("TELEGRAM_BOT_TOKEN", "")
        token = expand_env(raw_token) or ""

        raw_verify = credentials.get("verify") or os.getenv("TELEGRAM_BOT_USERNAME", "Alya_Rasa_Bot")
        verify = expand_env(raw_verify) or "Alya_Rasa_Bot"

        raw_webhook = credentials.get("webhook_url") or os.getenv("TELEGRAM_WEBHOOK_URL", "")
        webhook_url = expand_env(raw_webhook) or ""

        raw_parse_mode = credentials.get("parse_mode") or "Markdown"
        parse_mode = expand_env(raw_parse_mode) or "Markdown"

        return cls(access_token=token, verify=verify, webhook_url=webhook_url, parse_mode=parse_mode)

    def __init__(
        self,
        access_token: Optional[Text] = None,
        verify: Optional[Text] = "Alya_Rasa_Bot",
        webhook_url: Optional[Text] = None,
        parse_mode: Optional[Text] = "Markdown",
        debug_mode: bool = True,
    ) -> None:
        super().__init__(
            access_token=access_token,
            verify=verify,
            webhook_url=webhook_url,
            debug_mode=debug_mode
        )
        self.parse_mode = parse_mode
        self.is_valid_token = bool(
            self.access_token and re.match(r"^\d+:[A-Za-z0-9_-]+$", self.access_token)
        )

        if self.is_valid_token:
            logger.info(f"SmartTelegramInput initialized for bot @{self.verify}")
            try:
                self._register_telegram_commands()
            except Exception as e:
                logger.warning(f"Failed to register Telegram bot commands: {e}")
        else:
            logger.warning(
                "SmartTelegramInput: No valid Telegram bot token found. "
                "Set TELEGRAM_BOT_TOKEN in .env to activate Telegram channel."
            )

    def _register_telegram_commands(self) -> None:
        """Registers the native Telegram commands menu (the [/] button next to chat input)."""
        commands = [
            {"command": "help", "description": "📖 List all commands & skills"},
            {"command": "adduser", "description": "👤 Grant bot access to Telegram user ID"},
            {"command": "removeuser", "description": "🚫 Revoke bot access for Telegram user ID"},
            {"command": "users", "description": "📋 List all authorized users"},
            {"command": "search", "description": "🔍 Real-time live AI Web Search"},
            {"command": "upi", "description": "💸 Instant dynamic UPI payment QR code"},
            {"command": "transcribe", "description": "🎙️ Audio & voice note transcription (Whisper)"},
            {"command": "med", "description": "💊 Clinical medicine uses & alternatives"},
            {"command": "ssl", "description": "🔒 SSL certificate validity & expiry check"},
            {"command": "whois", "description": "🌐 Domain registration & WHOIS lookup"},
            {"command": "ocr", "description": "📷 Extract text from photo/image"},
            {"command": "today", "description": "📜 Today in History milestones & birthdays"},
            {"command": "pan", "description": "💳 Indian PAN Card structure validator"},
            {"command": "gstin", "description": "🏢 Indian GSTIN number & state validator"},
            {"command": "unit", "description": "📐 Universal & Land unit converter (Bigha/Acre)"},
            {"command": "horoscope", "description": "🔮 Daily Zodiac & Horoscope guidance"},
            {"command": "hackernews", "description": "🔥 Hacker News top tech & startup stories"},
            {"command": "slang", "description": "🗣️ Gen-Z slangs & jargon decoder"},
            {"command": "weather", "description": "🌤️ Real-time weather lookup"},
            {"command": "news", "description": "🗞️ Latest news digest & headlines"},
            {"command": "stock", "description": "📈 Live Stock quote (NSE/BSE)"},
            {"command": "crypto", "description": "🪙 Live crypto prices (BTC/ETH/SOL)"},
            {"command": "gold", "description": "🪙 Live Gold & Silver rates (India)"},
            {"command": "fuel", "description": "⛽ Daily Petrol & Diesel rates"},
            {"command": "currency", "description": "💱 Currency exchange conversion"},
            {"command": "wallet", "description": "💎 Crypto wallet balance in USD & INR"},
            {"command": "pnr", "description": "🚆 IRCTC PNR booking status"},
            {"command": "train", "description": "🚆 Live train status & schedule"},
            {"command": "flight", "description": "✈️ Live flight tracker & radar"},
            {"command": "youtube", "description": "🎬 YouTube video AI summary"},
            {"command": "summarize", "description": "📄 Webpage & article summary"},
            {"command": "briefing", "description": "🌅 Daily Morning AI Briefing"},
            {"command": "screenshot", "description": "📸 Live website screenshot"},
            {"command": "py", "description": "🐍 Python code sandbox runner"},
            {"command": "sql", "description": "🗄️ SQLite database query explorer"},
            {"command": "github", "description": "🐙 GitHub repos, issues, PRs"},
            {"command": "code", "description": "💻 Delegate coding via OpenCode"},
            {"command": "pdf", "description": "📄 Generate styled PDF document"},
            {"command": "excel", "description": "📊 Generate Excel spreadsheet"},
            {"command": "doc", "description": "📝 Generate Word (.docx) doc"},
            {"command": "resume", "description": "📄 ATS Resume PDF generator"},
            {"command": "coverletter", "description": "✉️ Job Cover Letter PDF"},
            {"command": "convert", "description": "🔄 Image & document converter"},
            {"command": "remind", "description": "⏰ Set time-based reminder"},
            {"command": "note", "description": "📝 Save a note"},
            {"command": "notes", "description": "📋 List saved notes"},
            {"command": "todo", "description": "✅ Add task to to-do list"},
            {"command": "todos", "description": "📌 List pending to-dos"},
            {"command": "expense", "description": "💰 Log expense with category"},
            {"command": "expenses", "description": "📊 Monthly finance summary"},
            {"command": "bill", "description": "🧾 Add bill payment reminder"},
            {"command": "sip", "description": "📈 Mutual Fund SIP calculator"},
            {"command": "emi", "description": "🏦 Loan EMI calculator"},
            {"command": "split", "description": "🧾 Bill & tip splitter"},
            {"command": "traffic", "description": "🚗 Commute ETA & route"},
            {"command": "pincode", "description": "📮 India Post PIN code & area"},
            {"command": "ifsc", "description": "🏦 Bank branch & IFSC finder"},
            {"command": "serverstatus", "description": "🖥️ EC2 CPU/RAM/Disk health"},
            {"command": "speedtest", "description": "⚡ Internet speed test"},
            {"command": "gmail", "description": "📬 Read recent Gmail messages"},
            {"command": "outlook", "description": "📧 Read recent Outlook emails"},
            {"command": "drive", "description": "📂 Search Google Drive files"},
            {"command": "calendar", "description": "📅 View Google Calendar events"},
            {"command": "dns", "description": "🌐 DNS records lookup"},
            {"command": "http", "description": "🔌 HTTP status & latency tester"},
            {"command": "cron", "description": "⏰ Translate cron expression"},
            {"command": "json", "description": "📋 Format & validate JSON"},
            {"command": "ip", "description": "🌍 Geo-IP location & ISP lookup"},
            {"command": "passgen", "description": "🔐 Strong password generator"},
            {"command": "hash", "description": "🔑 MD5/SHA-256 converter"},
            {"command": "unshorten", "description": "🔍 Expand shortened URL"},
            {"command": "shorten", "description": "🔗 Create short TinyURL link"},
            {"command": "tempmail", "description": "📬 Generate temporary disposable email"},
            {"command": "checkmail", "description": "📩 Check temporary inbox / OTP"},
            {"command": "breach", "description": "🚨 Check email/password breaches"},
            {"command": "bmi", "description": "🟢 BMI health assessment"},
            {"command": "calorie", "description": "🥗 Nutrition & calorie breakdown"},
            {"command": "water", "description": "💧 Water hydration logger"},
            {"command": "grammar", "description": "✍️ AI Grammar & tone polish"},
            {"command": "email", "description": "✉️ Professional email drafter"},
            {"command": "synonym", "description": "📖 Thesaurus & synonyms"},
            {"command": "time", "description": "🕒 World clock & timezone"},
            {"command": "countdown", "description": "⏳ Event countdown tracker"},
            {"command": "qr", "description": "🏁 Generate QR code image"},
            {"command": "barcode", "description": "🏷️ Generate barcode image"},
            {"command": "meme", "description": "🎭 Custom meme image generator"},
            {"command": "anime", "description": "🎬 MyAnimeList anime finder"},
            {"command": "recipe", "description": "🍲 Cooking recipe finder"},
            {"command": "riddle", "description": "🧩 Brain teaser riddle"},
            {"command": "pick", "description": "🎯 Random decision / dice / coin"},
            {"command": "math", "description": "🔢 WolframAlpha & SymPy solver"},
            {"command": "science", "description": "🚀 NASA Astronomy Picture of Day"},
            {"command": "wiki", "description": "📚 Wikipedia encyclopedia search"},
            {"command": "movie", "description": "🎬 Movie/TV IMDb ratings & plot"},
            {"command": "holiday", "description": "🎉 Public holidays & festivals"},
            {"command": "image", "description": "🖼️ Search HD stock images"},
            {"command": "translate", "description": "🌐 Dictionary & translation"},
            {"command": "joke", "description": "😂 Random joke & quote"}
        ]
        try:
            # Enforce Telegram 100 commands maximum constraint
            safe_commands = commands[:100]

            # 1. Set commands for default scope
            url_def = f"https://api.telegram.org/bot{self.access_token}/setMyCommands"
            r1 = requests.post(url_def, json={"commands": safe_commands, "scope": {"type": "default"}}, timeout=10)

            # 2. Set commands for private chats
            r2 = requests.post(url_def, json={"commands": safe_commands, "scope": {"type": "all_private_chats"}}, timeout=10)

            # 3. Explicitly set native chat menu button to 'commands'
            url_menu = f"https://api.telegram.org/bot{self.access_token}/setChatMenuButton"
            resp = requests.post(url_menu, json={"menu_button": {"type": "commands"}}, timeout=10)

            if resp.status_code == 200 and resp.json().get("ok"):
                logger.info(f"Successfully registered {len(safe_commands)} Telegram bot commands in native Menu & ChatMenuButton.")
            else:
                logger.warning(f"Telegram setChatMenuButton response: {resp.text}")
        except Exception as e:
            logger.warning(f"Error registering Telegram commands menu: {e}")

    def get_output_channel(self) -> OutputChannel:
        return SmartTelegramOutput(self.access_token, parse_mode=self.parse_mode)

    def blueprint(
        self, on_new_message: Callable[[UserMessage], Awaitable[Any]]
    ) -> Blueprint:
        if not self.is_valid_token:
            custom_webhook = Blueprint("telegram_webhook_placeholder", __name__)

            @custom_webhook.route("/", methods=["GET"])
            async def health(_: Request) -> HTTPResponse:
                return response.json({
                    "status": "waiting_for_telegram_token",
                    "message": "Set TELEGRAM_BOT_TOKEN in .env and restart rasa-bot."
                })

            @custom_webhook.route("/webhook", methods=["GET", "POST"])
            async def placeholder_webhook(_: Request) -> HTTPResponse:
                return response.json({
                    "status": "error",
                    "message": "Telegram webhook is inactive. Valid TELEGRAM_BOT_TOKEN required."
                }, status=503)

            return custom_webhook

        telegram_webhook = Blueprint("telegram_webhook", __name__)
        out_channel = self.get_output_channel()

        @telegram_webhook.route("/", methods=["GET"])
        async def health(_: Request) -> HTTPResponse:
            return response.json({"status": "ok", "bot": self.verify})

        @telegram_webhook.route("/set_webhook", methods=["GET", "POST"])
        async def set_webhook(_: Request) -> HTTPResponse:
            s = await out_channel.set_webhook(self.webhook_url)
            if s:
                logger.info(f"Webhook Setup Successful for @{self.verify} -> {self.webhook_url}")
                return response.text("Webhook setup successful")
            else:
                logger.warning("Webhook Setup Failed")
                return response.text("Invalid webhook")

        @telegram_webhook.route("/webhook", methods=["GET", "POST"])
        async def message(request: Request) -> Any:
            if request.method == "GET":
                return response.json({"status": "active", "bot": self.verify, "service": "Alya Telegram Webhook"})

            if request.method == "POST":
                request_dict = request.json
                if isinstance(request_dict, Text):
                    request_dict = json.loads(request_dict)
                update = Update(**request_dict)

                # 1. Verify Bot Credentials / Username
                try:
                    credentials = await out_channel.get_me()
                    if credentials.username.lower() != self.verify.lower():
                        logger.debug(
                            f"Telegram bot username mismatch: expected {self.verify}, got {credentials.username}"
                        )
                        return response.text("failed")
                except Exception as e:
                    logger.warning(f"Failed to verify bot credentials with Telegram API: {e}")

                # 2. Extract Message & Sender Details
                msg = None
                text = ""
                user_id = None

                if self._is_button(update):
                    msg = update.callback_query.message
                    text = update.callback_query.data
                    if update.callback_query.from_user:
                        user_id = update.callback_query.from_user.id
                elif self._is_edited_message(update):
                    msg = update.edited_message
                    text = update.edited_message.text
                    if update.edited_message.from_user:
                        user_id = update.edited_message.from_user.id
                else:
                    msg = update.message
                    if msg:
                        if msg.from_user:
                            user_id = msg.from_user.id

                        # Handle Voice Notes (Whisper transcription)
                        if msg.voice or msg.audio:
                            v_obj = msg.voice or msg.audio
                            f_id = v_obj.file_id
                            ext = "oga" if msg.voice else "mp3"
                            saved_f = download_telegram_file(self.access_token, f_id, f"voice_{f_id[:10]}.{ext}")
                            if saved_f:
                                transcript = transcribe_audio_file(saved_f)
                                if transcript:
                                    text = transcript
                                else:
                                    text = "I sent a voice note, but transcription failed."
                            else:
                                text = "Voice message received."

                        # Handle Document Attachments (PDF, Excel, Word)
                        elif msg.document:
                            doc_obj = msg.document
                            doc_name = doc_obj.file_name or f"doc_{doc_obj.file_id[:8]}"
                            saved_doc = download_telegram_file(self.access_token, doc_obj.file_id, doc_name)
                            caption = msg.caption or ""

                            # Extract document content preview
                            doc_preview = ""
                            if saved_doc:
                                from actions import skills_documents as doc_skills
                                from actions import db as app_db
                                app_db.save_file_record(str(user_id), doc_name, doc_name.split('.')[-1], saved_doc, doc_obj.file_size or 0)
                                if doc_name.lower().endswith(".pdf"):
                                    doc_preview = doc_skills.read_pdf_file(saved_doc)
                                elif doc_name.lower().endswith((".xlsx", ".xls")):
                                    doc_preview = doc_skills.read_excel_file(saved_doc)
                                elif doc_name.lower().endswith(".docx"):
                                    doc_preview = doc_skills.read_word_file(saved_doc)

                            text = f"User uploaded document '{doc_name}'.\n{doc_preview}\nCaption: {caption}".strip()

                        # Handle Photos with Vision OCR / AI Analysis
                        elif msg.photo:
                            p_obj = msg.photo[-1]
                            p_name = f"photo_{p_obj.file_id[:10]}.jpg"
                            saved_img = download_telegram_file(self.access_token, p_obj.file_id, p_name)
                            caption_text = msg.caption or ""
                            if saved_img:
                                from actions import skills_content as content_skills
                                vision_analysis = content_skills.analyze_image_vision(saved_img, caption_text)
                                text = f"User uploaded a photo. Visual Analysis:\n{vision_analysis}\nCaption: {caption_text}".strip()
                            else:
                                text = f"User uploaded a photo. Caption: {caption_text or 'Please see the attached photo.'}"

                        elif self._is_user_message(msg):
                            text = (msg.text or "").replace("/bot", "")
                        elif self._is_location(msg):
                            text = '{{"lng":{0}, "lat":{1}}}'.format(
                                msg.location.longitude, msg.location.latitude
                            )
                        else:
                            return response.text("success")

                if msg is None:
                    return response.text("success")

                if user_id is None and msg.chat:
                    user_id = msg.chat.id

                sender_id = msg.chat.id

                # 3. User Whitelist Check (BEFORE any NLU, Core, or Groq LLM processing)
                from actions import db as app_db
                if not app_db.is_user_authorized(str(user_id)):
                    logger.info(
                        f"[SECURITY] Unauthorized Telegram user blocked: user_id={user_id}, "
                        f"username={getattr(getattr(msg, 'from_user', None), 'username', 'unknown')}. "
                        f"Silently dropping message without invoking NLU/LLM."
                    )
                    # Silently drop the message - return HTTP 200 OK so Telegram doesn't resend
                    return response.text("success")

                # 3.5 Direct Slash Command Dispatcher (Instant execution & file delivery)
                if text and text.startswith("/") and text not in [INTENT_MESSAGE_PREFIX + USER_INTENT_RESTART]:
                    try:
                        from actions import commands
                        cmd_res = commands.handle_slash_command(text, str(user_id), str(sender_id))
                        if cmd_res.get("handled"):
                            reply_text = cmd_res.get("text", "")
                            file_path = cmd_res.get("file_path")
                            file_type = cmd_res.get("file_type", "document")

                            if file_path:
                                from actions import skills_documents as doc_skills
                                doc_skills.send_telegram_file(str(sender_id), file_path, caption=reply_text, file_type=file_type)
                            elif reply_text:
                                await out_channel.send_text_message(sender_id, reply_text)

                            return response.text("success")
                    except Exception as e:
                        logger.error(f"Error handling direct slash command: {e}", exc_info=True)

                # 4. Dispatch Authorized Message to Rasa
                metadata = self.get_metadata(request) or {}
                metadata["chat_id"] = str(sender_id)
                metadata["user_id"] = str(user_id)

                try:
                    if text == (INTENT_MESSAGE_PREFIX + USER_INTENT_RESTART):
                        await on_new_message(
                            UserMessage(
                                text,
                                out_channel,
                                sender_id,
                                input_channel=self.name(),
                                metadata=metadata,
                            )
                        )
                        await on_new_message(
                            UserMessage(
                                "/start",
                                out_channel,
                                sender_id,
                                input_channel=self.name(),
                                metadata=metadata,
                            )
                        )
                    else:
                        await on_new_message(
                            UserMessage(
                                text,
                                out_channel,
                                sender_id,
                                input_channel=self.name(),
                                metadata=metadata,
                            )
                        )
                except Exception as e:
                    logger.error(f"Exception when trying to handle message: {e}")
                    logger.debug(e, exc_info=True)
                    if self.debug_mode:
                        raise

                return response.text("success")

        return telegram_webhook
