"""
Canonical Command Registry for Alya Rasa Bot (@Alya_Rasa_Bot).
Single Source of Truth for all slash commands, aliases, categories, permissions,
and native Telegram bot menu registration.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set
import logging

logger = logging.getLogger(__name__)


@dataclass
class CommandInfo:
    name: str  # Primary command name (without leading '/')
    syntax: str  # Usage syntax, e.g. "/weather <city>"
    description: str  # Human-readable summary
    category: str  # Category name with emoji
    aliases: List[str] = field(default_factory=list)
    admin_only: bool = False
    enabled: bool = True
    native_menu: bool = True  # Whether eligible for Telegram native [/] menu
    menu_description: Optional[str] = None  # Concise (<256 chars) description for Telegram menu


# Canonical Command Definitions
COMMAND_REGISTRY: List[CommandInfo] = [
    # 🖼️ Image Tools & Passport Studio
    CommandInfo(
        name="imagetools",
        syntax="/imagetools",
        description="Open Image Tools Studio & features guide",
        category="🖼️ Image Tools & Passport Studio",
        aliases=["imagehelp", "phototools"],
        native_menu=True,
        menu_description="🖼️ Image Tools & Photo Studio Guide"
    ),
    CommandInfo(
        name="presets",
        syntax="/presets",
        description="Browse Govt photo, Passport, Social Media & Print presets",
        category="🖼️ Image Tools & Passport Studio",
        aliases=["imagepresets"],
        native_menu=True,
        menu_description="📋 Govt photo, Passport & Social presets"
    ),
    CommandInfo(
        name="passport",
        syntax="/passport <file> [country]",
        description="Indian, US, UK, Schengen passport photo maker (300 DPI)",
        category="🖼️ Image Tools & Passport Studio",
        aliases=["visa"],
        native_menu=True,
        menu_description="🪪 Passport photo maker (300 DPI)"
    ),
    CommandInfo(
        name="compress",
        syntax="/compress <file>",
        description="Smart image & PDF compressor (Target KB/MB mode, JPG/PNG/WebP/PDF)",
        category="🖼️ Image Tools & Passport Studio",
        aliases=["reduce", "shrink"],
        native_menu=True,
        menu_description="🗜️ Image & PDF file compressor"
    ),
    CommandInfo(
        name="exif",
        syntax="/exif <file>",
        description="Photo EXIF metadata inspector & GPS location finder",
        category="🖼️ Image Tools & Passport Studio",
        aliases=["metadata", "photoinfo"],
        native_menu=True,
        menu_description="📷 Photo EXIF inspector & GPS location"
    ),
    CommandInfo(
        name="strip_exif",
        syntax="/strip_exif <file>",
        description="Remove GPS location and camera tags from photos for privacy",
        category="🖼️ Image Tools & Passport Studio",
        aliases=["stripexif", "cleanphoto"],
        native_menu=False
    ),

    # 🤖 AI & Super-Skills
    CommandInfo(
        name="solve",
        syntax="/solve <question_or_photo>",
        description="AI Question & Exam Problem Solver from photo or text",
        category="🤖 AI & Super-Skills",
        aliases=["ask", "answer", "mathsolve", "homework", "doubt"],
        native_menu=True,
        menu_description="🎓 AI Question & Exam Problem Solver"
    ),
    CommandInfo(
        name="search",
        syntax="/search <query>",
        description="Real-time live AI Web Search & Synthesis (Tavily & DDG)",
        category="🤖 AI & Super-Skills",
        aliases=["google", "websearch"],
        native_menu=True,
        menu_description="🔍 Real-time live AI Web Search"
    ),
    CommandInfo(
        name="transcribe",
        syntax="/transcribe [url_or_file]",
        description="Groq Whisper audio & voice note transcription + AI summary",
        category="🤖 AI & Super-Skills",
        aliases=["stt", "voicetotext", "audio"],
        native_menu=True,
        menu_description="🎙️ Audio & voice note transcription"
    ),
    CommandInfo(
        name="voice",
        syntax="/voice <text>",
        description="Realistic Neural Voice Note generator (Edge-TTS Hindi/English)",
        category="🤖 AI & Super-Skills",
        aliases=["tts", "speak", "voicenote"],
        native_menu=True,
        menu_description="🎙️ Realistic Neural Voice Note generator"
    ),
    CommandInfo(
        name="ocr",
        syntax="/ocr [url_or_file]",
        description="High-accuracy image-to-text extractor (Tesseract + AI polish)",
        category="🤖 AI & Super-Skills",
        aliases=["extracttext", "readimage"],
        native_menu=True,
        menu_description="📷 Extract text from photo/document"
    ),
    CommandInfo(
        name="compare",
        syntax="/compare <item1> vs <item2>",
        description="Side-by-side AI specs, pros/cons & tech comparison",
        category="🤖 AI & Super-Skills",
        aliases=["vs", "diff", "difference"],
        native_menu=True,
        menu_description="⚔️ Side-by-side AI specs comparison"
    ),
    CommandInfo(
        name="med",
        syntax="/med <medicine>",
        description="Clinical medicine uses, active salt, precautions & generic alternatives",
        category="🤖 AI & Super-Skills",
        aliases=["medicine", "dawa", "drug"],
        native_menu=True,
        menu_description="💊 Clinical medicine uses & generic salt"
    ),
    CommandInfo(
        name="today",
        syntax="/today",
        description="Today in History major events, milestones & famous birthdays",
        category="🤖 AI & Super-Skills",
        aliases=["history", "onthisday", "dayinhistory"],
        native_menu=True,
        menu_description="📜 Today in History milestones"
    ),
    CommandInfo(
        name="horoscope",
        syntax="/horoscope <zodiac_sign>",
        description="Daily astrological predictions, career, love & lucky numbers",
        category="🤖 AI & Super-Skills",
        aliases=["zodiac", "rashi", "kundali", "astrology"],
        native_menu=True,
        menu_description="🔮 Daily Zodiac & Horoscope guidance"
    ),
    CommandInfo(
        name="hackernews",
        syntax="/hackernews",
        description="Top 5 trending tech & startup stories from Hacker News",
        category="🤖 AI & Super-Skills",
        aliases=["hn", "technews", "techheadlines"],
        native_menu=True,
        menu_description="🔥 Top Hacker News tech stories"
    ),
    CommandInfo(
        name="slang",
        syntax="/slang <word>",
        description="Gen-Z slangs, internet jargon & idioms decoder",
        category="🤖 AI & Super-Skills",
        aliases=["idiom", "phrase", "jargon", "slangmeaning"],
        native_menu=True,
        menu_description="🗣️ Gen-Z slangs & idioms decoder"
    ),
    CommandInfo(
        name="wayback",
        syntax="/wayback <url>",
        description="Wayback Machine historical snapshots & deleted page viewer",
        category="🤖 AI & Super-Skills",
        aliases=["archive", "timemachine", "oldweb"],
        native_menu=True,
        menu_description="⏳ Wayback Machine history snapshot"
    ),
    CommandInfo(
        name="mergepdf",
        syntax="/mergepdf <file1> <file2> ...",
        description="Merge multiple PDF documents into a single PDF",
        category="🤖 AI & Super-Skills",
        aliases=["pdfmerge", "combinepdf"],
        native_menu=False
    ),
    CommandInfo(
        name="splitpdf",
        syntax="/splitpdf <file> <start> <end>",
        description="Extract page ranges from PDF document",
        category="🤖 AI & Super-Skills",
        aliases=["pdfsplit", "extractpdf"],
        native_menu=False
    ),
    CommandInfo(
        name="phish",
        syntax="/phish <url>",
        description="Anti-phishing, fake bank trap & link safety scanner",
        category="🤖 AI & Super-Skills",
        aliases=["safelink", "urlcheck", "scanlink"],
        native_menu=False
    ),
    CommandInfo(
        name="ping",
        syntax="/ping <host>",
        description="Server uptime & TCP latency ping",
        category="🤖 AI & Super-Skills",
        aliases=["latency", "hostping"],
        native_menu=False
    ),
    CommandInfo(
        name="ssl",
        syntax="/ssl <domain>",
        description="Real-time SSL certificate validity, expiry countdown & cipher check",
        category="🤖 AI & Super-Skills",
        aliases=["tls", "cert", "certificate"],
        native_menu=False
    ),
    CommandInfo(
        name="whois",
        syntax="/whois <domain>",
        description="ICANN RDAP domain registrar, registration & expiry lookup",
        category="🤖 AI & Super-Skills",
        aliases=["rdap", "domain"],
        native_menu=False
    ),

    # 📱 Mobile & Android Automation
    CommandInfo(
        name="call",
        syntax="/call <number>",
        description="Direct phone call dialer",
        category="📱 Mobile & Android Automation",
        aliases=["dial", "phonecall"],
        native_menu=True,
        menu_description="📞 Make phone call dialer"
    ),
    CommandInfo(
        name="sms",
        syntax="/sms <number> <msg>",
        description="Send SMS text message from phone",
        category="📱 Mobile & Android Automation",
        aliases=["sendtext"],
        native_menu=True,
        menu_description="💬 Send SMS text message"
    ),
    CommandInfo(
        name="readsms",
        syntax="/readsms [limit]",
        description="Read incoming SMS messages from phone inbox",
        category="📱 Mobile & Android Automation",
        aliases=["inboxsms"],
        native_menu=True,
        menu_description="📩 Read incoming SMS messages"
    ),
    CommandInfo(
        name="alarm",
        syntax="/alarm <time> [label]",
        description="Set phone alarm",
        category="📱 Mobile & Android Automation",
        aliases=["setalarm"],
        native_menu=True,
        menu_description="⏰ Set phone alarm"
    ),
    CommandInfo(
        name="timer",
        syntax="/timer <duration> [label]",
        description="Set countdown timer on phone",
        category="📱 Mobile & Android Automation",
        aliases=["settimer"],
        native_menu=True,
        menu_description="⏳ Set countdown timer on phone"
    ),
    CommandInfo(
        name="open",
        syntax="/open <app_or_file>",
        description="Launch application or open file on phone",
        category="📱 Mobile & Android Automation",
        aliases=["launch", "app"],
        native_menu=True,
        menu_description="📱 Launch phone app or open file"
    ),
    CommandInfo(
        name="callscreen",
        syntax="/callscreen <statement>",
        description="AI call screening & voicemail assistant",
        category="📱 Mobile & Android Automation",
        aliases=["screen", "voicemail"],
        native_menu=False
    ),
    CommandInfo(
        name="findmyphone",
        syntax="/findmyphone",
        description="Sound loud emergency alarm to locate your phone",
        category="📱 Mobile & Android Automation",
        aliases=["ringphone", "ring"],
        native_menu=True,
        menu_description="🔔 Ring phone loudly to locate it"
    ),
    CommandInfo(
        name="clip",
        syntax="/clip <text>",
        description="Sync text directly into phone clipboard",
        category="📱 Mobile & Android Automation",
        aliases=["copy"],
        native_menu=True,
        menu_description="📋 Sync text to phone clipboard"
    ),
    CommandInfo(
        name="whatsapp",
        syntax="/whatsapp <phone> <msg>",
        description="Direct WhatsApp message & link dispatch",
        category="📱 Mobile & Android Automation",
        aliases=["wa"],
        native_menu=True,
        menu_description="💬 Send WhatsApp message"
    ),
    CommandInfo(
        name="notify",
        syntax="/notify <title> | <msg>",
        description="Instant native push alert on phone lock screen",
        category="📱 Mobile & Android Automation",
        aliases=["alert", "push"],
        native_menu=True,
        menu_description="📲 Push alert to phone lockscreen"
    ),
    CommandInfo(
        name="skills",
        syntax="/skills",
        description="Full interactive skills directory catalog",
        category="📱 Mobile & Android Automation",
        aliases=["directory", "allskills"],
        native_menu=True,
        menu_description="🌟 Full interactive skills catalog"
    ),

    # 🇮🇳 Indian Utilities & Markets
    CommandInfo(
        name="upi",
        syntax="/upi <vpa> [amount] [name]",
        description="Instant Dynamic UPI scan-and-pay QR code (GPay/PhonePe/Paytm)",
        category="🇮🇳 Indian Utilities & Markets",
        aliases=["payqr", "upiqr"],
        native_menu=True,
        menu_description="💸 Instant dynamic UPI payment QR code"
    ),
    CommandInfo(
        name="pan",
        syntax="/pan <pan_no>",
        description="Indian PAN Card structure validator & category detector",
        category="🇮🇳 Indian Utilities & Markets",
        aliases=["pancard", "checkpan"],
        native_menu=True,
        menu_description="💳 Indian PAN Card validator"
    ),
    CommandInfo(
        name="gstin",
        syntax="/gstin <gstin_no>",
        description="Indian GSTIN number & state validator",
        category="🇮🇳 Indian Utilities & Markets",
        aliases=["gst", "checkgst"],
        native_menu=True,
        menu_description="🏢 Indian GSTIN number validator"
    ),
    CommandInfo(
        name="unit",
        syntax="/unit <val> <from> to <to>",
        description="Universal & Indian Land Unit converter (Bigha, Acre, Guntha, Gaj, SqFt)",
        category="🇮🇳 Indian Utilities & Markets",
        aliases=["convertunit", "units", "areaconvert"],
        native_menu=True,
        menu_description="📐 Universal & Land unit converter"
    ),
    CommandInfo(
        name="postoffice",
        syntax="/postoffice <pin_or_area>",
        description="India Post office branch finder & delivery status",
        category="🇮🇳 Indian Utilities & Markets",
        aliases=["dak", "postbranches"],
        native_menu=True,
        menu_description="📮 India Post office branch finder"
    ),
    CommandInfo(
        name="pincode",
        syntax="/pincode <pin_or_area>",
        description="India Post PIN code & area lookup",
        category="🇮🇳 Indian Utilities & Markets",
        aliases=["pin", "postal"],
        native_menu=True,
        menu_description="📮 India Post PIN code & area lookup"
    ),
    CommandInfo(
        name="ifsc",
        syntax="/ifsc <code>",
        description="Bank branch & IFSC finder (Razorpay API)",
        category="🇮🇳 Indian Utilities & Markets",
        aliases=["bank"],
        native_menu=True,
        menu_description="🏦 Bank branch & IFSC finder"
    ),
    CommandInfo(
        name="pnr",
        syntax="/pnr <10-digit PNR>",
        description="IRCTC train booking & confirmation status",
        category="🇮🇳 Indian Utilities & Markets",
        native_menu=True,
        menu_description="🚆 IRCTC PNR booking status"
    ),
    CommandInfo(
        name="train",
        syntax="/train <number_or_name>",
        description="Indian Railways live schedule & NTES route",
        category="🇮🇳 Indian Utilities & Markets",
        aliases=["railway"],
        native_menu=True,
        menu_description="🚆 Live train status & NTES route"
    ),
    CommandInfo(
        name="flight",
        syntax="/flight <flight_no>",
        description="Live flight status, airline, and radar",
        category="🇮🇳 Indian Utilities & Markets",
        aliases=["radar"],
        native_menu=True,
        menu_description="✈️ Live flight tracker & radar"
    ),
    CommandInfo(
        name="stock",
        syntax="/stock <ticker>",
        description="Live NSE/BSE & global stock quotes & day trend",
        category="🇮🇳 Indian Utilities & Markets",
        aliases=["stocks"],
        native_menu=True,
        menu_description="📈 Live Stock quote (NSE/BSE)"
    ),
    CommandInfo(
        name="nifty",
        syntax="/nifty",
        description="Instant Indian Nifty 50 index snapshot",
        category="🇮🇳 Indian Utilities & Markets",
        aliases=["nifty50"],
        native_menu=False
    ),
    CommandInfo(
        name="sensex",
        syntax="/sensex",
        description="Instant Indian BSE Sensex index snapshot",
        category="🇮🇳 Indian Utilities & Markets",
        aliases=["bse"],
        native_menu=False
    ),
    CommandInfo(
        name="gold",
        syntax="/gold",
        description="Live 24K/22K 10g Gold & 1kg Silver bullion rates",
        category="🇮🇳 Indian Utilities & Markets",
        aliases=["silver", "metals", "bullion"],
        native_menu=True,
        menu_description="🪙 Live Gold & Silver rates (India)"
    ),
    CommandInfo(
        name="fuel",
        syntax="/fuel [city]",
        description="Daily Petrol, Diesel & CNG prices",
        category="🇮🇳 Indian Utilities & Markets",
        aliases=["petrol", "diesel"],
        native_menu=False
    ),
    CommandInfo(
        name="ipo",
        syntax="/ipo",
        description="Indian Mainboard & SME IPO Calendar & Grey Market Premium (GMP)",
        category="🇮🇳 Indian Utilities & Markets",
        aliases=["ipogmp", "ipos"],
        native_menu=False
    ),
    CommandInfo(
        name="aqi",
        syntax="/aqi [city]",
        description="Real-time live Air Quality Index (PM2.5, PM10 & Health Advisory)",
        category="🇮🇳 Indian Utilities & Markets",
        aliases=["airquality", "pollution"],
        native_menu=True,
        menu_description="💨 Real-time Air Quality Index"
    ),

    # ⏱️ Reminders & Productivity
    CommandInfo(
        name="remind",
        syntax="/remind <time> <msg>",
        description="Timezone-aware reminder scheduler (IST default)",
        category="⏱️ Reminders & Productivity",
        aliases=["reminder", "setreminder"],
        native_menu=True,
        menu_description="⏰ Set timezone-aware reminder"
    ),
    CommandInfo(
        name="reminders",
        syntax="/reminders",
        description="View active scheduled reminders",
        category="⏱️ Reminders & Productivity",
        aliases=["myreminders", "listreminders", "active_reminders"],
        native_menu=False
    ),
    CommandInfo(
        name="delremind",
        syntax="/delremind <id>",
        description="Cancel active scheduled reminder",
        category="⏱️ Reminders & Productivity",
        aliases=["delreminder", "cancelreminder", "rmremind"],
        native_menu=False
    ),
    CommandInfo(
        name="set_timezone",
        syntax="/set_timezone <tz>",
        description="Set & check preferred timezone (e.g. Asia/Kolkata, EST, UTC)",
        category="⏱️ Reminders & Productivity",
        aliases=["settimezone", "mytimezone"],
        native_menu=True,
        menu_description="🌍 Set preferred timezone preference"
    ),
    CommandInfo(
        name="medremind",
        syntax="/medremind <time> <medicine>",
        description="Scheduled medicine dosage reminders",
        category="⏱️ Reminders & Productivity",
        native_menu=False
    ),
    CommandInfo(
        name="note",
        syntax="/note <text>",
        description="Save a persistent note to user notepad",
        category="⏱️ Reminders & Productivity",
        native_menu=True,
        menu_description="📝 Save a persistent note"
    ),
    CommandInfo(
        name="notes",
        syntax="/notes [query]",
        description="Search & list saved persistent notes",
        category="⏱️ Reminders & Productivity",
        native_menu=False
    ),
    CommandInfo(
        name="todo",
        syntax="/todo <task>",
        description="To-Do task manager with /done <id>",
        category="⏱️ Reminders & Productivity",
        native_menu=True,
        menu_description="✅ Add task to to-do list"
    ),
    CommandInfo(
        name="todos",
        syntax="/todos",
        description="List pending to-do tasks",
        category="⏱️ Reminders & Productivity",
        native_menu=False
    ),
    CommandInfo(
        name="habit",
        syntax="/habit [name]",
        description="Daily habit streak logger & tracker",
        category="⏱️ Reminders & Productivity",
        native_menu=True,
        menu_description="🎯 Daily habit streak tracker"
    ),
    CommandInfo(
        name="time",
        syntax="/time <city>",
        description="World clock & timezone converter",
        category="⏱️ Reminders & Productivity",
        aliases=["timezone"],
        native_menu=True,
        menu_description="🕒 World clock & timezone converter"
    ),
    CommandInfo(
        name="countdown",
        syntax="/countdown <date>",
        description="Event countdown tracker",
        category="⏱️ Reminders & Productivity",
        native_menu=True,
        menu_description="⏳ Event countdown timer"
    ),
    CommandInfo(
        name="traffic",
        syntax="/traffic <from> to <to>",
        description="Commute ETA & route navigation",
        category="⏱️ Reminders & Productivity",
        aliases=["distance", "eta"],
        native_menu=False
    ),
    CommandInfo(
        name="ride",
        syntax="/ride <from> to <to>",
        description="OpenRouteService distance & Ola/Uber fare estimator",
        category="⏱️ Reminders & Productivity",
        native_menu=False
    ),
    CommandInfo(
        name="track",
        syntax="/track <number>",
        description="Speed Post & courier package tracking",
        category="⏱️ Reminders & Productivity",
        native_menu=False
    ),

    # 💻 Developer & MCP Tools
    CommandInfo(
        name="code",
        syntax="/code <task>",
        description="(Advanced) OpenCode MCP shell execution & coding engine",
        category="💻 Developer & MCP Tools",
        aliases=["bash", "terminal"],
        native_menu=False  # Host shell access: functional but not exposed to ordinary users
    ),
    CommandInfo(
        name="sh",
        syntax="/sh <cmd>",
        description="Direct host terminal execution with stdout/stderr",
        category="💻 Developer & MCP Tools",
        aliases=["exec"],
        admin_only=True,
        native_menu=False
    ),
    CommandInfo(
        name="py",
        syntax="/py <code>",
        description="Python code execution sandbox runner",
        category="💻 Developer & MCP Tools",
        aliases=["python", "run"],
        admin_only=True,
        native_menu=False
    ),
    CommandInfo(
        name="sql",
        syntax="/sql <query>",
        description="SQLite database query & table inspector",
        category="💻 Developer & MCP Tools",
        aliases=["db", "database"],
        admin_only=True,
        native_menu=False
    ),
    CommandInfo(
        name="kg",
        syntax="/kg <add|list|search>",
        description="Knowledge Graph & relational memory explorer",
        category="💻 Developer & MCP Tools",
        aliases=["knowledge", "relations"],
        native_menu=False  # Internal memory tool: functional but not in the user menu
    ),
    CommandInfo(
        name="github",
        syntax="/github [repo]",
        description="List GitHub repos, issues, and PRs",
        category="💻 Developer & MCP Tools",
        native_menu=True,
        menu_description="🐙 GitHub repos, issues, PRs"
    ),
    CommandInfo(
        name="screenshot",
        syntax="/screenshot <url>",
        description="Live high-res website screenshot capture",
        category="💻 Developer & MCP Tools",
        aliases=["webshot", "capture"],
        native_menu=True,
        menu_description="📸 Live website screenshot"
    ),
    CommandInfo(
        name="social",
        syntax="/social <url>",
        description="Twitter/X, Reddit post content extractor",
        category="💻 Developer & MCP Tools",
        aliases=["tweet", "post"],
        native_menu=False
    ),
    CommandInfo(
        name="log",
        syntax="/log [service]",
        description="Inspect live server & bot logs",
        category="💻 Developer & MCP Tools",
        aliases=["logs", "syslog"],
        admin_only=True,
        native_menu=False
    ),
    CommandInfo(
        name="serverstatus",
        syntax="/serverstatus",
        description="EC2 CPU, RAM, Disk health",
        category="💻 Developer & MCP Tools",
        aliases=["health", "status"],
        native_menu=False
    ),
    CommandInfo(
        name="speedtest",
        syntax="/speedtest",
        description="Internet speed test runner",
        category="💻 Developer & MCP Tools",
        native_menu=False
    ),
    CommandInfo(
        name="dns",
        syntax="/dns <domain>",
        description="DNS records (A, MX, NS, TXT) lookup",
        category="💻 Developer & MCP Tools",
        native_menu=True,
        menu_description="🌐 DNS records lookup"
    ),
    CommandInfo(
        name="http",
        syntax="/http <url>",
        description="HTTP status, response latency & headers",
        category="💻 Developer & MCP Tools",
        aliases=["curl"],
        native_menu=False
    ),
    CommandInfo(
        name="cron",
        syntax="/cron <expr>",
        description="Translate cron syntax to plain English",
        category="💻 Developer & MCP Tools",
        native_menu=False
    ),
    CommandInfo(
        name="json",
        syntax="/json <text>",
        description="Format, minify & validate JSON",
        category="💻 Developer & MCP Tools",
        native_menu=True,
        menu_description="🔧 Format & validate JSON"
    ),
    CommandInfo(
        name="ip",
        syntax="/ip [ip_address]",
        description="Geo-IP location, ISP & ASN lookup",
        category="💻 Developer & MCP Tools",
        native_menu=True,
        menu_description="🌐 Geo-IP location lookup"
    ),

    # 📁 Documents, Resumes & Formats
    CommandInfo(
        name="resume",
        syntax="/resume <role_or_skills>",
        description="Professional ATS Resume generator (.pdf)",
        category="📁 Documents, Resumes & Formats",
        aliases=["cv", "buildresume"],
        native_menu=True,
        menu_description="📄 ATS Resume PDF generator"
    ),
    CommandInfo(
        name="coverletter",
        syntax="/coverletter <company> <role>",
        description="Formal Job Application Cover Letter (.pdf)",
        category="📁 Documents, Resumes & Formats",
        aliases=["cl"],
        native_menu=True,
        menu_description="✉️ Job Cover Letter PDF"
    ),
    CommandInfo(
        name="invoice",
        syntax="/invoice <text_or_ocr>",
        description="Receipt / bill parser to structured Excel (.xlsx)",
        category="📁 Documents, Resumes & Formats",
        aliases=["billtoexcel"],
        native_menu=True,
        menu_description="📊 Receipt & Bill OCR to Excel"
    ),
    CommandInfo(
        name="convert",
        syntax="/convert <format> <file>",
        description="Convert image/doc format (PNG, JPG, WebP, PDF, TXT, Word)",
        category="📁 Documents, Resumes & Formats",
        aliases=["format"],
        native_menu=True,
        menu_description="🔄 Image & document converter"
    ),
    CommandInfo(
        name="pdf",
        syntax="/pdf <title>",
        description="Styled PDF document engine",
        category="📁 Documents, Resumes & Formats",
        native_menu=True,
        menu_description="📄 Generate styled PDF document"
    ),
    CommandInfo(
        name="excel",
        syntax="/excel <title>",
        description="Styled Excel spreadsheet engine",
        category="📁 Documents, Resumes & Formats",
        native_menu=True,
        menu_description="📊 Generate Excel spreadsheet"
    ),
    CommandInfo(
        name="doc",
        syntax="/doc <title>",
        description="Styled Word (.docx) memo engine",
        category="📁 Documents, Resumes & Formats",
        native_menu=True,
        menu_description="📝 Generate Word (.docx) memo"
    ),
    CommandInfo(
        name="gmail",
        syntax="/gmail [query]",
        description="Live Gmail messages reader",
        category="📁 Documents, Resumes & Formats",
        native_menu=True,
        menu_description="✉️ Read Gmail messages"
    ),
    CommandInfo(
        name="outlook",
        syntax="/outlook [query]",
        description="Live Outlook emails reader",
        category="📁 Documents, Resumes & Formats",
        native_menu=False
    ),
    CommandInfo(
        name="drive",
        syntax="/drive [query]",
        description="Google Drive search",
        category="📁 Documents, Resumes & Formats",
        native_menu=True,
        menu_description="📁 Google Drive file search"
    ),
    CommandInfo(
        name="calendar",
        syntax="/calendar",
        description="Google Calendar schedule",
        category="📁 Documents, Resumes & Formats",
        native_menu=True,
        menu_description="📅 Google Calendar schedule"
    ),

    # 🔐 Privacy, Security & Web APIs
    CommandInfo(
        name="passgen",
        syntax="/passgen [length]",
        description="Cryptographically strong password generator",
        category="🔐 Privacy, Security & Web APIs",
        aliases=["password"],
        native_menu=True,
        menu_description="🔐 Strong password generator"
    ),
    CommandInfo(
        name="hash",
        syntax="/hash <text>",
        description="MD5, SHA-1, SHA-256, Base64 converter",
        category="🔐 Privacy, Security & Web APIs",
        native_menu=False
    ),
    CommandInfo(
        name="unshorten",
        syntax="/unshorten <url>",
        description="Safe URL redirect expander",
        category="🔐 Privacy, Security & Web APIs",
        native_menu=False
    ),
    CommandInfo(
        name="shorten",
        syntax="/shorten <url>",
        description="Create short TinyURL link",
        category="🔐 Privacy, Security & Web APIs",
        native_menu=True,
        menu_description="🔗 Shorten URL with TinyURL"
    ),
    CommandInfo(
        name="tempmail",
        syntax="/tempmail",
        description="Disposable temporary email inbox generator",
        category="🔐 Privacy, Security & Web APIs",
        aliases=["disposable"],
        native_menu=True,
        menu_description="📬 Temporary disposable email"
    ),
    CommandInfo(
        name="checkmail",
        syntax="/checkmail <login> <domain>",
        description="Check temporary inbox & OTP messages",
        category="🔐 Privacy, Security & Web APIs",
        native_menu=False
    ),
    CommandInfo(
        name="breach",
        syntax="/breach <email_or_pwd>",
        description="Data breach check via XposedOrNot & HIBP",
        category="🔐 Privacy, Security & Web APIs",
        native_menu=False
    ),
    CommandInfo(
        name="weather",
        syntax="/weather <city>",
        description="Live weather forecast (Default: Malda, WB)",
        category="🔐 Privacy, Security & Web APIs",
        native_menu=True,
        menu_description="🌤️ Real-time weather lookup"
    ),
    CommandInfo(
        name="news",
        syntax="/news [topic]",
        description="Top headlines and news digest",
        category="🔐 Privacy, Security & Web APIs",
        native_menu=True,
        menu_description="🗞️ Latest news digest & headlines"
    ),
    CommandInfo(
        name="currency",
        syntax="/currency <amt> <from> <to>",
        description="Currency exchange conversion",
        category="🔐 Privacy, Security & Web APIs",
        native_menu=True,
        menu_description="💱 Currency exchange conversion"
    ),
    CommandInfo(
        name="crypto",
        syntax="/crypto [coin]",
        description="Live crypto prices & tickers (BTC/ETH/SOL)",
        category="🔐 Privacy, Security & Web APIs",
        native_menu=True,
        menu_description="🪙 Live crypto prices (BTC/ETH/SOL)"
    ),
    CommandInfo(
        name="wallet",
        syntax="/wallet <address>",
        description="Multi-chain wallet balance & valuation (ETH/BTC/SOL)",
        category="🔐 Privacy, Security & Web APIs",
        aliases=["balance"],
        native_menu=False
    ),
    CommandInfo(
        name="gas",
        syntax="/gas",
        description="Ethereum gas fee tracker (Etherscan)",
        category="🔐 Privacy, Security & Web APIs",
        aliases=["ethgas"],
        native_menu=False
    ),
    CommandInfo(
        name="wiki",
        syntax="/wiki <topic>",
        description="Wikipedia encyclopedia search",
        category="🔐 Privacy, Security & Web APIs",
        aliases=["wikipedia"],
        native_menu=True,
        menu_description="📚 Wikipedia encyclopedia search"
    ),
    CommandInfo(
        name="movie",
        syntax="/movie <title>",
        description="Movie & TV ratings and plot (OMDb/TMDB)",
        category="🔐 Privacy, Security & Web APIs",
        aliases=["tv"],
        native_menu=True,
        menu_description="🎬 Movie/TV IMDb ratings & plot"
    ),
    CommandInfo(
        name="holiday",
        syntax="/holiday [country]",
        description="Public holidays & festivals calendar",
        category="🔐 Privacy, Security & Web APIs",
        aliases=["holidays"],
        native_menu=False
    ),
    CommandInfo(
        name="image",
        syntax="/image <query>",
        description="Search HD photos (Unsplash/Pexels)",
        category="🔐 Privacy, Security & Web APIs",
        native_menu=False
    ),
    CommandInfo(
        name="translate",
        syntax="/translate <text>",
        description="Dictionary definition & language translation",
        category="🔐 Privacy, Security & Web APIs",
        native_menu=True,
        menu_description="🌐 Translation & dictionary"
    ),
    CommandInfo(
        name="joke",
        syntax="/joke",
        description="Random clean joke & inspirational quote",
        category="🔐 Privacy, Security & Web APIs",
        aliases=["quote"],
        native_menu=True,
        menu_description="😄 Clean joke & inspirational quote"
    ),
    CommandInfo(
        name="math",
        syntax="/math <expression>",
        description="WolframAlpha & SymPy solver",
        category="🔐 Privacy, Security & Web APIs",
        native_menu=True,
        menu_description="🔢 WolframAlpha & SymPy solver"
    ),
    CommandInfo(
        name="science",
        syntax="/science",
        description="NASA Astronomy Picture of the Day",
        category="🔐 Privacy, Security & Web APIs",
        native_menu=False
    ),
    CommandInfo(
        name="vehicle",
        syntax="/vehicle <vin>",
        description="NHTSA 17-char VIN decode & specs",
        category="🔐 Privacy, Security & Web APIs",
        native_menu=False
    ),
    CommandInfo(
        name="shop",
        syntax="/shop <product>",
        description="Product & barcode lookup",
        category="🔐 Privacy, Security & Web APIs",
        native_menu=True,
        menu_description="🛒 Product & barcode lookup"
    ),

    # 💰 Financial, Health & Lifestyle
    CommandInfo(
        name="sip",
        syntax="/sip <monthly> <rate> <years>",
        description="Mutual Fund SIP wealth compounding calculator",
        category="💰 Financial, Health & Lifestyle",
        native_menu=True,
        menu_description="📈 Mutual Fund SIP calculator"
    ),
    CommandInfo(
        name="emi",
        syntax="/emi <loan> <rate> <years>",
        description="Loan EMI, interest & amortization calculator",
        category="💰 Financial, Health & Lifestyle",
        native_menu=True,
        menu_description="🏦 Loan EMI calculator"
    ),
    CommandInfo(
        name="split",
        syntax="/split <amount> <people>",
        description="Restaurant bill & tip splitter",
        category="💰 Financial, Health & Lifestyle",
        native_menu=True,
        menu_description="🧾 Bill & tip splitter"
    ),
    CommandInfo(
        name="expense",
        syntax="/expense <amt> <cat> <desc>",
        description="Log expense with category analytics",
        category="💰 Financial, Health & Lifestyle",
        native_menu=True,
        menu_description="💰 Log expense with category"
    ),
    CommandInfo(
        name="expenses",
        syntax="/expenses [month]",
        description="Monthly finance summary & breakdown",
        category="💰 Financial, Health & Lifestyle",
        native_menu=False
    ),
    CommandInfo(
        name="bill",
        syntax="/bill <name> <due> [amt]",
        description="Add bill reminder alert",
        category="💰 Financial, Health & Lifestyle",
        native_menu=True,
        menu_description="⏰ Bill reminder alert"
    ),
    CommandInfo(
        name="bmi",
        syntax="/bmi <weight> <height>",
        description="Body Mass Index & health category",
        category="💰 Financial, Health & Lifestyle",
        native_menu=True,
        menu_description="⚖️ Body Mass Index calculator"
    ),
    CommandInfo(
        name="calorie",
        syntax="/calorie <food>",
        description="Nutrition, protein, carbs & calorie profile",
        category="💰 Financial, Health & Lifestyle",
        aliases=["nutrition"],
        native_menu=True,
        menu_description="🥗 Nutrition & calorie profile"
    ),
    CommandInfo(
        name="water",
        syntax="/water [ml]",
        description="Water hydration logging",
        category="💰 Financial, Health & Lifestyle",
        native_menu=True,
        menu_description="💧 Water hydration logger"
    ),
    CommandInfo(
        name="grammar",
        syntax="/grammar <text>",
        description="Grammar, tone polish & rewriter",
        category="💰 Financial, Health & Lifestyle",
        aliases=["fix"],
        native_menu=True,
        menu_description="✍️ Grammar & tone rewriter"
    ),
    CommandInfo(
        name="email",
        syntax="/email <topic>",
        description="Formal business & leave email drafter",
        category="💰 Financial, Health & Lifestyle",
        native_menu=True,
        menu_description="📧 Professional email drafter"
    ),
    CommandInfo(
        name="synonym",
        syntax="/synonym <word>",
        description="Thesaurus, synonyms & antonyms",
        category="💰 Financial, Health & Lifestyle",
        aliases=["thesaurus"],
        native_menu=True,
        menu_description="📖 Thesaurus & synonyms"
    ),

    # 🎮 Entertainment & Media
    CommandInfo(
        name="qr",
        syntax="/qr <text_or_url>",
        description="Generate HD QR code image",
        category="🎮 Entertainment & Media",
        aliases=["qrcode"],
        native_menu=True,
        menu_description="📱 Generate HD QR code"
    ),
    CommandInfo(
        name="barcode",
        syntax="/barcode <number>",
        description="Generate Code128 barcode image",
        category="🎮 Entertainment & Media",
        native_menu=True,
        menu_description="📊 Generate Barcode image"
    ),
    CommandInfo(
        name="meme",
        syntax="/meme <top> | <bottom>",
        description="Custom meme image generator",
        category="🎮 Entertainment & Media",
        native_menu=True,
        menu_description="🎭 Custom meme generator"
    ),
    CommandInfo(
        name="anime",
        syntax="/anime <title>",
        description="MyAnimeList anime & manga ratings",
        category="🎮 Entertainment & Media",
        native_menu=True,
        menu_description="🌸 Anime & manga ratings"
    ),
    CommandInfo(
        name="recipe",
        syntax="/recipe <dish>",
        description="Cooking ingredients & instructions",
        category="🎮 Entertainment & Media",
        aliases=["cook"],
        native_menu=True,
        menu_description="🍳 Cooking recipes & guide"
    ),
    CommandInfo(
        name="riddle",
        syntax="/riddle",
        description="Fun brain teaser riddles",
        category="🎮 Entertainment & Media",
        native_menu=True,
        menu_description="🧩 Brain teaser riddles"
    ),
    CommandInfo(
        name="pick",
        syntax="/pick <opt1, opt2>",
        description="Random decision maker, /dice, /coinflip",
        category="🎮 Entertainment & Media",
        aliases=["dice", "roll", "coinflip", "flip"],
        native_menu=True,
        menu_description="🎲 Random decision /dice /coinflip"
    ),
    CommandInfo(
        name="youtube",
        syntax="/youtube <url>",
        description="YouTube video transcript & executive summary",
        category="🎮 Entertainment & Media",
        aliases=["yt"],
        native_menu=True,
        menu_description="▶️ YouTube transcript & summary"
    ),
    CommandInfo(
        name="summarize",
        syntax="/summarize <url>",
        description="Webpage / article instant markdown summary",
        category="🎮 Entertainment & Media",
        aliases=["article", "webpage"],
        native_menu=True,
        menu_description="📄 Webpage & article summary"
    ),
    CommandInfo(
        name="briefing",
        syntax="/briefing",
        description="Consolidated morning briefing (Weather, News, Markets, Planner)",
        category="🎮 Entertainment & Media",
        aliases=["morning"],
        native_menu=True,
        menu_description="🌅 Daily Morning AI Briefing"
    ),

    # 👥 Admin & Management
    CommandInfo(
        name="adduser",
        syntax="/adduser <user_id> [name]",
        description="(Admin) Grant bot access to a Telegram user",
        category="👥 Admin & Management",
        aliases=["authuser", "grantuser", "allowuser"],
        admin_only=True,
        native_menu=False
    ),
    CommandInfo(
        name="removeuser",
        syntax="/removeuser <user_id>",
        description="(Admin) Revoke bot access for a Telegram user",
        category="👥 Admin & Management",
        aliases=["deluser", "deleteuser", "revokeuser"],
        admin_only=True,
        native_menu=False
    ),
    CommandInfo(
        name="users",
        syntax="/users",
        description="(Admin) List all authorized Telegram users",
        category="👥 Admin & Management",
        aliases=["listusers", "authusers", "allowedusers"],
        admin_only=True,
        native_menu=False
    ),
]


# Lookup map for fast O(1) command / alias resolution
_CMD_LOOKUP: Dict[str, CommandInfo] = {}
for _info in COMMAND_REGISTRY:
    _CMD_LOOKUP[_info.name.lower()] = _info
    for _alias in _info.aliases:
        _CMD_LOOKUP[_alias.lower()] = _info


def get_command_by_name(cmd_name: str) -> Optional[CommandInfo]:
    """Resolves command or alias without leading slash."""
    clean = cmd_name.lstrip("/").lower()
    return _CMD_LOOKUP.get(clean)


def get_all_commands() -> List[CommandInfo]:
    """Returns the full list of canonical commands."""
    return list(COMMAND_REGISTRY)


def generate_help_text(user_id: Optional[str] = None) -> str:
    """
    Dynamically generates structured categorized markdown for /help, /menu, /commands.
    Admin-only commands are shown only to administrators (user_id=None shows all,
    which is used by tests/legacy callers).
    """
    show_admin = True
    if user_id is not None:
        try:
            from . import db as app_db
            show_admin = app_db.is_admin_user(str(user_id))
        except Exception:
            show_admin = False

    categories: Dict[str, List[CommandInfo]] = {}
    for cmd in COMMAND_REGISTRY:
        if not cmd.enabled:
            continue
        if cmd.admin_only and not show_admin:
            continue
        categories.setdefault(cmd.category, []).append(cmd)

    lines = ["✨ **Alya AI Assistant (@Alya_Rasa_Bot) — Slash Commands Menu** ✨\n"]

    for cat_name, cmds in categories.items():
        lines.append(f"**{cat_name}:**")
        for cmd in cmds:
            lines.append(f"• `{cmd.syntax}` — {cmd.description}")
        lines.append("")

    lines.append("💡 _Tip: You can tap the **[/] Menu** button next to your text bar to auto-complete any command!_")
    return "\n".join(lines).strip()


def generate_skills_directory() -> str:
    """
    Dynamically generates the skills directory for /skills and /directory.
    """
    categories: Dict[str, List[CommandInfo]] = {}
    for cmd in COMMAND_REGISTRY:
        if not cmd.enabled:
            continue
        categories.setdefault(cmd.category, []).append(cmd)

    lines = [f"🌟 **Alya Autonomous AI Agent — Complete Skills Directory ({len(COMMAND_REGISTRY)}+ Skills)** 🌟\n"]

    for cat_name, cmds in categories.items():
        lines.append(f"**{cat_name}:**")
        cmd_tokens = [f"`/{c.name}`" for c in cmds if not c.admin_only]
        if cmd_tokens:
            lines.append("• " + ", ".join(cmd_tokens))
        lines.append("")

    lines.append("💡 _You can trigger any skill simply by typing slash commands or talking naturally in Hinglish or English!_")
    return "\n".join(lines).strip()


def get_native_bot_commands() -> List[Dict[str, str]]:
    """
    Returns up to 100 native BotCommand objects for Telegram setMyCommands.
    Enforces Telegram Bot API constraints:
    - command name must be 1-32 chars, lowercase alphanumeric + underscore
    - description must be 3-256 chars
    - maximum 100 commands
    """
    native_list: List[Dict[str, str]] = []
    seen: Set[str] = set()

    # Always ensure 'help' is first
    native_list.append({
        "command": "help",
        "description": "📖 List all commands & skills menu"
    })
    seen.add("help")

    # Add curated native_menu commands from registry
    for cmd in COMMAND_REGISTRY:
        if len(native_list) >= 100:
            break
        if not cmd.enabled or not cmd.native_menu or cmd.admin_only:
            continue
        c_name = cmd.name.lower().replace("-", "_")
        if c_name in seen:
            continue

        desc = cmd.menu_description or cmd.description
        if len(desc) > 250:
            desc = desc[:247] + "..."

        native_list.append({
            "command": c_name,
            "description": desc
        })
        seen.add(c_name)

    return native_list


def audit_registry() -> Dict[str, Any]:
    """
    Audits registry for collision, duplicate aliases, Telegram compliance, and stats.
    """
    all_names: Set[str] = set()
    collisions: List[str] = []
    invalid_telegram_names: List[str] = []

    for cmd in COMMAND_REGISTRY:
        # Check primary name
        if cmd.name in all_names:
            collisions.append(f"Duplicate primary command: {cmd.name}")
        all_names.add(cmd.name)

        # Telegram command regex: ^[a-z0-9_]{1,32}$
        import re
        if not re.match(r"^[a-z0-9_]{1,32}$", cmd.name.lower()):
            invalid_telegram_names.append(cmd.name)

        # Check aliases
        for a in cmd.aliases:
            if a in all_names:
                collisions.append(f"Alias collision: {a} in {cmd.name}")
            all_names.add(a)

    native_cmds = get_native_bot_commands()

    return {
        "total_canonical_commands": len(COMMAND_REGISTRY),
        "total_aliases": sum(len(c.aliases) for c in COMMAND_REGISTRY),
        "total_lookup_triggers": len(_CMD_LOOKUP),
        "native_menu_count": len(native_cmds),
        "native_menu_within_telegram_limit": len(native_cmds) <= 100,
        "collisions": collisions,
        "invalid_telegram_names": invalid_telegram_names,
        "admin_commands": [c.name for c in COMMAND_REGISTRY if c.admin_only]
    }
