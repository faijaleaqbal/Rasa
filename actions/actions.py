import os
import re
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Text

IST = timezone(timedelta(hours=5, minutes=30), name="IST")

from dotenv import load_dotenv
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from . import db
from . import scheduler
from . import skills_productivity as prod
from . import skills_documents as docs
from . import skills_free_apis as apis
from . import skills_utilities as utils
from . import skills_indian_markets as markets
from . import skills_content as content
from . import skills_developer_tools as dev
from . import skills_converters_resume as conv
from . import skills_mobile_device as mob
from . import skills_imei_device as imei_dev
from . import skills_advanced as adv
from . import skills_super_pack as superpack
from . import security_guardrails as security
from . import mcp_client as mcp
from . import jobs_service as js

logger = logging.getLogger(__name__)

# Start background reminder / monitor scheduler
scheduler.start_scheduler()


# ---------------------------------------------------------------------------
# Search helper
# ---------------------------------------------------------------------------
def search_the_web(query: str) -> str:
    """Performs live web search using Tavily, Serper, or DuckDuckGo fallback."""
    logger.info(f"Executing live web search for query: {query}")
    
    tavily_key = os.getenv("TAVILY_API_KEY")
    if tavily_key:
        try:
            from tavily import TavilyClient
            tavily = TavilyClient(api_key=tavily_key)
            results = tavily.search(query=query, search_depth="basic", max_results=4)
            summaries = []
            for r in results.get("results", []):
                summaries.append(f"Title: {r.get('title')}\nSnippet: {r.get('content')}\nURL: {r.get('url')}")
            if summaries:
                return "\n\n".join(summaries)
        except Exception as e:
            logger.warning(f"Tavily search error: {e}")

    serper_key = os.getenv("SERPER_API_KEY")
    if serper_key:
        try:
            import requests
            headers = {"X-API-KEY": serper_key, "Content-Type": "application/json"}
            resp = requests.post(
                "https://google.serper.dev/search",
                headers=headers,
                json={"q": query, "num": 4},
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                snippets = []
                for item in data.get("organic", []):
                    snippets.append(f"Title: {item.get('title')}\nSnippet: {item.get('snippet')}\nURL: {item.get('link')}")
                if snippets:
                    return "\n\n".join(snippets)
        except Exception as e:
            logger.warning(f"Serper search error: {e}")

    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=4))
            snippets = []
            for r in results:
                snippets.append(f"Title: {r.get('title')}\nSnippet: {r.get('body')}\nURL: {r.get('href')}")
            if snippets:
                return "\n\n".join(snippets)
    except Exception as e:
        logger.warning(f"Web search error: {e}")

    return "No recent search results found or web search failed."


# ---------------------------------------------------------------------------
# Weather Natural-Language City Extractor
# ---------------------------------------------------------------------------

# Weather filler / intent words in Hindi, Hinglish, and English that are NOT city names.
# These are stripped from natural language queries to extract only the actual location.
_WEATHER_FILLER_WORDS = {
    # Hindi / Hinglish weather words
    "aj", "aaj", "kal", "parso", "abhi", "abhi ka",
    "ka", "ki", "ke", "kya", "hai", "hain", "ho", "kaisa", "kaisi", "kaise",
    "mausam", "mausham", "mosam", "maosam",
    "weather", "forecast", "temperature", "temp", "taapmaan", "tapman",
    "batao", "bata", "btao", "bto", "dikhao", "dikha", "sunao", "suna",
    "batade", "bata de", "sunado", "suna do",
    "update", "report", "status", "info", "information",
    "hoga", "hogi", "hogi kya", "rahega", "rahegi", "rehga", "rehgi",
    "aaj ka", "aj ka", "kal ka", "aaj ki", "aj ki",
    "today", "tomorrow", "current", "now", "right now", "live",
    "please", "pls", "plz", "bhai", "bro", "dost", "yaar",
    "what", "whats", "what's", "how", "how's", "hows",
    "is", "the", "in", "for", "me", "my", "tell",
    "give", "get", "show", "check", "do",
    "barish", "baarish", "dhoop", "garmi", "sardi", "thand", "thandi",
    "hawa", "humidity", "wind",
    "kitna", "kitni", "kab", "kaha", "kahan",
}

# Precompiled regex for slash command stripping
_SLASH_WEATHER_RE = re.compile(r"^/weather\b\s*", re.IGNORECASE)

# Precompiled regex for prepositions and connectors before city name
_PREP_RE = re.compile(
    r"\b(?:in|of|for|at|ka|ki|ke|me|mein|mai|main|mei|ka weather|ki weather|ke weather)\s+",
    re.IGNORECASE,
)


def extract_city_from_weather_query(text: str) -> Optional[str]:
    """
    Extracts the actual city/location name from a natural-language weather query.

    Handles:
      - Slash commands: "/weather Delhi" → "Delhi"
      - English: "What's the weather in Kolkata?" → "Kolkata"
      - Hindi/Hinglish: "Aj kya weather hai" → None (default)
      - Hindi with city: "Kolkata ka weather kaisa hai?" → "Kolkata"
      - Hindi location: "Mumbai ka mausam" → "Mumbai"
      - "Delhi weather today" → "Delhi"

    Returns the extracted city name, or None (which signals get_weather_data to use default).
    """
    if not text or not text.strip():
        return None

    raw = text.strip()

    # 1. Handle slash command: "/weather <city>"
    if raw.startswith("/"):
        city = _SLASH_WEATHER_RE.sub("", raw).strip()
        return city if city else None

    # 2. Try structured pattern: "<City> ka/ki/ke weather/mausam"
    #    e.g., "Kolkata ka weather kaisa hai?" → "Kolkata"
    #    e.g., "Mumbai ka mausam" → "Mumbai"
    pattern_city_before = re.match(
        r"^(.+?)\s+(?:ka|ki|ke)\s+(?:weather|mausam|mausham|mosam|maosam|temperature|temp|forecast)\b",
        raw,
        re.IGNORECASE,
    )
    if pattern_city_before:
        candidate = pattern_city_before.group(1).strip()
        # Verify it's not just filler ("aaj ka weather" → candidate="aaj" → filler)
        candidate_lower_words = set(candidate.lower().split())
        if not candidate_lower_words.issubset(_WEATHER_FILLER_WORDS):
            # Strip any leading filler from the candidate
            clean_parts = [w for w in candidate.split() if w.lower() not in _WEATHER_FILLER_WORDS]
            if clean_parts:
                return " ".join(clean_parts)

    # 3. Try structured pattern: "weather/mausam in/of <City>"
    #    e.g., "Weather in Kolkata" → "Kolkata"
    #    e.g., "What's the weather in New Delhi?" → "New Delhi"
    pattern_city_after = re.search(
        r"(?:weather|mausam|mausham|mosam|maosam|temperature|temp|forecast)\s+"
        r"(?:in|of|for|at|me|mein|mai|main|mei)\s+(.+?)[\?\.\!]*$",
        raw,
        re.IGNORECASE,
    )
    if pattern_city_after:
        candidate = pattern_city_after.group(1).strip()
        clean_parts = [w for w in candidate.split() if w.lower() not in _WEATHER_FILLER_WORDS]
        if clean_parts:
            return " ".join(clean_parts)

    # 4. Try pattern: "<City> weather [today]"
    #    e.g., "Delhi weather today" → "Delhi"
    pattern_city_weather = re.match(
        r"^(.+?)\s+(?:weather|mausam|mausham|mosam|maosam|temperature|temp|forecast)\b",
        raw,
        re.IGNORECASE,
    )
    if pattern_city_weather:
        candidate = pattern_city_weather.group(1).strip()
        candidate_lower_words = set(candidate.lower().split())
        if not candidate_lower_words.issubset(_WEATHER_FILLER_WORDS):
            clean_parts = [w for w in candidate.split() if w.lower() not in _WEATHER_FILLER_WORDS]
            if clean_parts:
                return " ".join(clean_parts)

    # 5. No explicit city found → strip ALL known filler words and see if anything remains
    words = re.sub(r"[?\.\!,;:]+", "", raw).split()
    remaining = [w for w in words if w.lower() not in _WEATHER_FILLER_WORDS]
    # If remaining words look like a city (1-4 words, capitalized or proper noun)
    if remaining and len(remaining) <= 4:
        candidate = " ".join(remaining)
        # Sanity check: a city shouldn't be common Hindi sentence fragments
        skip_fragments = {"raha", "rahi", "rahe", "laga", "lagi", "lag", "niklegi",
                          "hogi", "hoga", "rahega", "rahegi", "acha", "achchha",
                          "accha", "theek", "thik", "kaisa", "kaisi"}
        if not set(w.lower() for w in remaining).issubset(skip_fragments):
            return candidate

    # 6. No city identified → return None (default city will be used)
    return None


# ---------------------------------------------------------------------------
# Comprehensive Tool Calling Dispatcher for Groq LLM
# ---------------------------------------------------------------------------

LLM_TOOLS_SPEC = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the live internet for recent news, live sports, real-time facts, or events.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Search query"}},
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get real-time weather, temperature, humidity, and wind conditions for any city. If the user does not mention a specific city, pass 'Malda, West Bengal, India' as the default. NEVER pass the user's full sentence as the city name — extract only the actual city/location.",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string", "description": "Actual city or location name only (e.g. 'Delhi', 'Mumbai', 'Kolkata'). Default: 'Malda, West Bengal, India'"}},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_news",
            "description": "Fetch top news digest or headlines on any topic or country.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "News topic or category"},
                    "country": {"type": "string", "description": "2-letter country code, e.g. in, us"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "convert_currency",
            "description": "Convert currency amount between currencies (e.g. USD, INR, EUR, GBP).",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {"type": "number", "description": "Amount to convert"},
                    "from_curr": {"type": "string", "description": "Source currency code, e.g. USD"},
                    "to_curr": {"type": "string", "description": "Target currency code, e.g. INR"}
                },
                "required": ["amount", "from_curr", "to_curr"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_crypto_prices",
            "description": "Fetch live cryptocurrency prices and 24h market trends (BTC, ETH, SOL, etc.).",
            "parameters": {
                "type": "object",
                "properties": {"coins": {"type": "string", "description": "Comma-separated coin names, e.g. bitcoin,ethereum,solana"}}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_book",
            "description": "Look up book details, author, publish year, and ratings on OpenLibrary.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Book title or author"}},
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_wikipedia",
            "description": "Lookup instant factual encyclopedia summary from Wikipedia.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Subject or topic"}},
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_movie_info",
            "description": "Lookup movie or TV show plot, IMDb rating, cast, director, and genre.",
            "parameters": {
                "type": "object",
                "properties": {"title": {"type": "string", "description": "Movie or series title"}},
                "required": ["title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_holidays",
            "description": "Get upcoming national and public holidays or festivals.",
            "parameters": {
                "type": "object",
                "properties": {
                    "country_code": {"type": "string", "description": "2-letter country code, default IN"},
                    "year": {"type": "integer", "description": "Year"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_dictionary",
            "description": "Lookup word definitions, phonetics, and examples in English dictionary.",
            "parameters": {
                "type": "object",
                "properties": {"word": {"type": "string", "description": "Word to define"}},
                "required": ["word"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "translate_text",
            "description": "Translate text across languages (e.g. English, Hindi, Spanish, French).",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to translate"},
                    "source_lang": {"type": "string", "description": "Source language code, default en"},
                    "target_lang": {"type": "string", "description": "Target language code, default hi"}
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_joke",
            "description": "Get a fun, clean joke.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_quote",
            "description": "Get an inspiring quote with author.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_vehicle_vin",
            "description": "Decode a vehicle VIN number to find make, model, year, and specs.",
            "parameters": {
                "type": "object",
                "properties": {"vin": {"type": "string", "description": "17-character VIN number"}},
                "required": ["vin"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_password_breach",
            "description": "Check if a password has been compromised in data breaches.",
            "parameters": {
                "type": "object",
                "properties": {"password": {"type": "string", "description": "Password to check"}},
                "required": ["password"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "solve_math",
            "description": "Solve algebraic equations, calculus, or arithmetic math expressions using SymPy.",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string", "description": "Math expression or equation"}},
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_nasa_apod",
            "description": "Fetch NASA's Astronomy Picture of the Day.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_reminder",
            "description": "Set a reminder for the user at a specified time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "What to remind about"},
                    "time_str": {"type": "string", "description": "When to remind, e.g. 'in 30 minutes', 'tomorrow at 9am', or ISO format"}
                },
                "required": ["text", "time_str"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_reminders",
            "description": "List all active reminders for the user.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_medicine_schedule",
            "description": "Set a recurring medicine dosage reminder.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Medicine name"},
                    "dosage": {"type": "string", "description": "Dosage, e.g. 500mg, 1 tablet"},
                    "schedule_time": {"type": "string", "description": "Time, e.g. 9:00 AM, After dinner"},
                    "instructions": {"type": "string", "description": "Special instructions"}
                },
                "required": ["name", "dosage", "schedule_time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_note",
            "description": "Save a note with title, content, and optional tags.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Note title"},
                    "content": {"type": "string", "description": "Note content"},
                    "tags": {"type": "string", "description": "Comma-separated tags"}
                },
                "required": ["title", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_notes",
            "description": "Search or list saved user notes.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Keyword to search or empty for recent"}}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_todo_task",
            "description": "Add a task to user's to-do list.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Task description"},
                    "priority": {"type": "string", "description": "low, medium, or high"},
                    "due_date": {"type": "string", "description": "Due date"}
                },
                "required": ["title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_todo_tasks",
            "description": "List to-do tasks (pending or completed).",
            "parameters": {
                "type": "object",
                "properties": {"status": {"type": "string", "description": "pending or completed"}}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "complete_todo_task",
            "description": "Mark a to-do task as completed by task ID.",
            "parameters": {
                "type": "object",
                "properties": {"todo_id": {"type": "integer", "description": "Task ID number"}},
                "required": ["todo_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "log_expense",
            "description": "Log an expense with amount, category, and description.",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {"type": "number", "description": "Amount in INR/currency"},
                    "category": {"type": "string", "description": "Category (food, transport, shopping, utilities, etc.)"},
                    "description": {"type": "string", "description": "Expense description"}
                },
                "required": ["amount", "description"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_expense_summary",
            "description": "Get monthly expense summary and category breakdown.",
            "parameters": {
                "type": "object",
                "properties": {"month": {"type": "string", "description": "Month in YYYY-MM format, default current"}}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_bill",
            "description": "Add an upcoming bill or utility payment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Bill name, e.g. Electricity, WiFi"},
                    "amount": {"type": "number", "description": "Amount due"},
                    "due_date": {"type": "string", "description": "Due date"}
                },
                "required": ["title", "amount", "due_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_bills",
            "description": "List upcoming and unpaid bills.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "parse_bank_sms",
            "description": "Parse an SMS or forwarded text alert for bank/UPI transactions and auto-log expense.",
            "parameters": {
                "type": "object",
                "properties": {"message_text": {"type": "string", "description": "Full bank SMS or alert text"}},
                "required": ["message_text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_commute_eta",
            "description": "Calculate driving distance and commute ETA between two locations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin": {"type": "string", "description": "Starting address or city"},
                    "destination": {"type": "string", "description": "Destination address or city"}
                },
                "required": ["origin", "destination"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "estimate_cab_fare",
            "description": "Estimate ride/cab fares for Uber/Ola (Bike, Auto, Sedan, Premier).",
            "parameters": {
                "type": "object",
                "properties": {
                    "distance_km": {"type": "number", "description": "Distance in kilometers"},
                    "time_mins": {"type": "number", "description": "Estimated time in minutes"}
                },
                "required": ["distance_km"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "track_package",
            "description": "Track a postal or courier delivery package by tracking number.",
            "parameters": {
                "type": "object",
                "properties": {"tracking_number": {"type": "string", "description": "Courier tracking number"}},
                "required": ["tracking_number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_internet_speedtest",
            "description": "Execute live internet speed test on the server (ping, download, upload speeds).",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "log_habit_done",
            "description": "Record daily habit completion and update streak.",
            "parameters": {
                "type": "object",
                "properties": {"habit_name": {"type": "string", "description": "Name of habit (e.g. workout, reading)"}},
                "required": ["habit_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_habits",
            "description": "List all tracked habits and current streaks.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_server_health",
            "description": "Check EC2 server system health, CPU load, RAM usage, Disk space, and Uptime.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_pdf_document",
            "description": "Create a styled PDF document file and send it to the user on Telegram.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Document title"},
                    "content": {"type": "string", "description": "Full document content/paragraphs"},
                    "filename": {"type": "string", "description": "Optional filename ending in .pdf"}
                },
                "required": ["title", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_excel_spreadsheet",
            "description": "Create a styled Excel (.xlsx) spreadsheet and send it to the user on Telegram.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sheet_title": {"type": "string", "description": "Spreadsheet title"},
                    "headers": {"type": "array", "items": {"type": "string"}, "description": "Column header names"},
                    "rows": {"type": "array", "items": {"type": "array", "items": {"type": "string"}}, "description": "2D list of row values"},
                    "filename": {"type": "string", "description": "Optional filename ending in .xlsx"}
                },
                "required": ["sheet_title", "headers", "rows"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_word_document",
            "description": "Create a styled Word (.docx) document file and send it to the user on Telegram.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Document title"},
                    "sections": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "heading": {"type": "string", "description": "Section header"},
                                "body": {"type": "string", "description": "Section text"}
                            }
                        },
                        "description": "List of sections"
                    },
                    "filename": {"type": "string", "description": "Optional filename ending in .docx"}
                },
                "required": ["title", "sections"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "remember_user_fact",
            "description": "Save a permanent fact about the user into long-term memory across chats.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Short identifier for the fact, e.g. favorite_color, brother_name"},
                    "value": {"type": "string", "description": "Detail to remember"},
                    "category": {"type": "string", "description": "Category, e.g. personal, work, preference"}
                },
                "required": ["key", "value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_memories",
            "description": "List all facts stored in long-term memory about the user.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gmail_list",
            "description": "List or search recent Gmail messages via Google OAuth.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query, default is:unread"},
                    "max_results": {"type": "integer", "description": "Number of emails to fetch"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gmail_send",
            "description": "Send an email from Gmail account.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email address"},
                    "subject": {"type": "string", "description": "Email subject"},
                    "body": {"type": "string", "description": "Email body content"}
                },
                "required": ["to", "subject", "body"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gdrive_list",
            "description": "List or search files in Google Drive.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Search keyword in file name"}}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gcalendar_list",
            "description": "List upcoming Google Calendar events.",
            "parameters": {
                "type": "object",
                "properties": {"max_results": {"type": "integer", "description": "Number of events"}}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gcalendar_create",
            "description": "Create a new Google Calendar event.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "Event title"},
                    "start_iso": {"type": "string", "description": "Start ISO datetime, e.g. 2026-08-18T10:00:00Z"},
                    "end_iso": {"type": "string", "description": "End ISO datetime, e.g. 2026-08-18T11:00:00Z"},
                    "description": {"type": "string", "description": "Description"}
                },
                "required": ["summary", "start_iso", "end_iso"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "outlook_list",
            "description": "List recent emails from Microsoft Outlook via Graph API.",
            "parameters": {
                "type": "object",
                "properties": {"max_results": {"type": "integer", "description": "Max emails to fetch"}}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "outlook_send",
            "description": "Send an email via Microsoft Outlook / Graph API.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email"},
                    "subject": {"type": "string", "description": "Subject"},
                    "body": {"type": "string", "description": "Body"}
                },
                "required": ["to", "subject", "body"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "github_repos",
            "description": "List repositories for a GitHub user, organization, or authenticated account.",
            "parameters": {
                "type": "object",
                "properties": {"username_or_org": {"type": "string", "description": "GitHub username or org"}}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "github_issues",
            "description": "List open/closed issues in a GitHub repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {"type": "string", "description": "owner/repo format"},
                    "state": {"type": "string", "description": "open or closed"}
                },
                "required": ["repo"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "github_prs",
            "description": "List pull requests in a GitHub repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {"type": "string", "description": "owner/repo format"},
                    "state": {"type": "string", "description": "open or closed"}
                },
                "required": ["repo"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mcp_coding_task",
            "description": "Delegate a coding, refactoring, or agentic task to GitHub MCP, OpenCode MCP, or Antigravity MCP.",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_type": {"type": "string", "description": "'github', 'opencode', or 'antigravity'"},
                    "instruction": {"type": "string", "description": "The coding task instruction"},
                    "context": {"type": "string", "description": "Additional context"}
                },
                "required": ["agent_type", "instruction"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_stock_quote",
            "description": "Fetch real-time stock price, gain/loss, and day high/low for NSE, BSE, Nifty, Sensex, or global stocks.",
            "parameters": {
                "type": "object",
                "properties": {"symbol": {"type": "string", "description": "Stock ticker or index (e.g. RELIANCE, TATAMOTORS, TCS, NIFTY, SENSEX, AAPL)"}},
                "required": ["symbol"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_gold_silver_rates",
            "description": "Fetch live 24K and 22K Gold (10g) and Silver (1kg) bullion prices in India.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_fuel_rates",
            "description": "Check daily Petrol, Diesel, and CNG fuel prices for Indian cities.",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string", "description": "City name, e.g. Delhi, Mumbai, Kolkata, Malda"}}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_train_pnr_status",
            "description": "Check Indian Railways IRCTC 10-digit PNR booking status.",
            "parameters": {
                "type": "object",
                "properties": {"pnr": {"type": "string", "description": "10-digit IRCTC PNR number"}},
                "required": ["pnr"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_train_live_status",
            "description": "Look up Indian Railways train route, schedule, and live running status.",
            "parameters": {
                "type": "object",
                "properties": {"train_number_or_name": {"type": "string", "description": "Train number (e.g. 12301) or train name"}},
                "required": ["train_number_or_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_flight_status",
            "description": "Track real-time flight route, status, airline, and radar.",
            "parameters": {
                "type": "object",
                "properties": {"flight_code": {"type": "string", "description": "Flight number (e.g. 6E205, AI101)"}},
                "required": ["flight_code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_youtube_video",
            "description": "Extract transcript from a YouTube video URL and generate an executive bullet-point summary.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "YouTube video link or ID"}},
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_webpage",
            "description": "Fetch and summarize the full text of any news article, blog, or webpage URL.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "Webpage or article URL"}},
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_daily_briefing",
            "description": "Generate a consolidated morning briefing with weather, top news, market snapshot, and user planner.",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string", "description": "City for weather, default Delhi or Malda"}}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "capture_website_screenshot",
            "description": "Capture high-resolution screenshot image of any website URL.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "Website URL to capture"}},
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_python_code_sandbox",
            "description": "Execute Python code in an isolated sandbox environment and get stdout output.",
            "parameters": {
                "type": "object",
                "properties": {"code": {"type": "string", "description": "Python code snippet to execute"}},
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_sqlite_database",
            "description": "Execute SQL queries or inspect user database tables (notes, todos, expenses, bills, habits).",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "SQL query or table name to inspect"}},
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "manage_knowledge_graph",
            "description": "Store or query deep relational memory in the Knowledge Graph (Entity -> Relation -> Target).",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "description": "add, search, list, or delete"},
                    "entity": {"type": "string", "description": "Subject entity"},
                    "relation": {"type": "string", "description": "Relationship type"},
                    "target": {"type": "string", "description": "Target entity or value"}
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "extract_social_media_info",
            "description": "Extract content, author, and key takeaways from a Twitter/X, Reddit, or LinkedIn post URL.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "Social media post URL"}},
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "view_server_logs",
            "description": "Check real-time application and system logs for debugging.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service_name": {"type": "string", "description": "rasa-bot, rasa-actions, or nginx"},
                    "lines": {"type": "integer", "description": "Number of log lines, default 15"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_resume_pdf",
            "description": "Create a high-impact, professional ATS-friendly Resume and deliver as styled PDF.",
            "parameters": {
                "type": "object",
                "properties": {
                    "role_or_details": {"type": "string", "description": "Target job title, skills, or professional experience"},
                    "candidate_name": {"type": "string", "description": "Full name of candidate"}
                },
                "required": ["role_or_details"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_cover_letter_pdf",
            "description": "Generate a tailored formal job application Cover Letter and deliver as styled PDF.",
            "parameters": {
                "type": "object",
                "properties": {
                    "company_and_role": {"type": "string", "description": "Company name and target job position"},
                    "candidate_name": {"type": "string", "description": "Candidate full name"}
                },
                "required": ["company_and_role"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_voice_speech",
            "description": "Synthesize a natural AI Voice audio message in Hindi or Indian English and deliver via Telegram.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Message text to speak"},
                    "voice_lang": {"type": "string", "description": "'hi' for Hindi or 'en' for English"}
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_phone_push_notification",
            "description": "Send a real-time native push alert to user's Android phone screen with sound and vibration.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Notification title"},
                    "message": {"type": "string", "description": "Notification body content"},
                    "priority": {"type": "string", "description": "'urgent', 'high', or 'default'"}
                },
                "required": ["title", "message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_full_skills_directory",
            "description": "List all available skills and command triggers in the AI assistant.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_imei_device",
            "description": "Perform full 15-digit IMEI analysis on mobile phones (iPhone, Android, Tablets). Extracts make/model, GSMA TAC, Luhn validity, 5G/4G network bands, and Blacklist/CEIR India status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "imei": {"type": "string", "description": "15-digit IMEI number (e.g. 352011112345678)"}
                },
                "required": ["imei"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "decode_device_serial",
            "description": "Decode Apple, Samsung, and Android hardware serial numbers to decipher factory origin, manufacture year/month, and model verification.",
            "parameters": {
                "type": "object",
                "properties": {
                    "serial_number": {"type": "string", "description": "Device serial number"},
                    "brand": {"type": "string", "description": "Optional brand hint, e.g. 'Apple', 'Samsung'"}
                },
                "required": ["serial_number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "decode_apple_model",
            "description": "Decodes Apple iPhone/iPad Part and Model numbers (e.g. MQ023HN/A, A2849) to identify Brand New vs Refurbished vs Replacement status and country/region.",
            "parameters": {
                "type": "object",
                "properties": {
                    "model_number": {"type": "string", "description": "Apple model/part number (e.g. MQ023HN/A)"}
                },
                "required": ["model_number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_mac_address",
            "description": "Look up MAC address IEEE OUI vendor and check if the MAC is randomized/private or hardware burned-in.",
            "parameters": {
                "type": "object",
                "properties": {
                    "mac_address": {"type": "string", "description": "MAC address (e.g. 00:03:93:11:22:33)"}
                },
                "required": ["mac_address"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_ceir_blocking_guide",
            "description": "Get official Indian DoT Sanchar Saathi & CEIR portal stolen phone blocking, police report, and tracing procedure.",
            "parameters": {
                "type": "object",
                "properties": {
                    "imei": {"type": "string", "description": "Optional 15-digit IMEI of the stolen device"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_upi_qr",
            "description": "Generate dynamic UPI scan-and-pay QR code for GPay, PhonePe, Paytm, BHIM with amount, payee name and note.",
            "parameters": {
                "type": "object",
                "properties": {
                    "vpa": {"type": "string", "description": "Payee UPI VPA ID, e.g. username@okaxis or 9876543210@paytm"},
                    "amount": {"type": "number", "description": "Optional payment amount in INR"},
                    "payee_name": {"type": "string", "description": "Optional name of payee/business"},
                    "note": {"type": "string", "description": "Optional transaction remark/note"}
                },
                "required": ["vpa"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_live_web",
            "description": "Perform live internet search and get synthesized real-time facts, news, and links.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query for real-time web search"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_medicine_info",
            "description": "Get detailed clinical pharmacology guide, uses, side effects, precautions, and low-cost generic alternatives for medicines in India.",
            "parameters": {
                "type": "object",
                "properties": {
                    "medicine_name": {"type": "string", "description": "Name of medicine or active salt (e.g. Dolo 650, Augmentin, Paracetamol)"}
                },
                "required": ["medicine_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "inspect_ssl_cert",
            "description": "Inspect real-time SSL/TLS certificate validity, expiry date, days left, issuer CA, and encryption cipher for a domain.",
            "parameters": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Domain name to inspect (e.g. google.com, github.com)"}
                },
                "required": ["domain"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "inspect_domain_whois",
            "description": "Lookup ICANN RDAP WHOIS records, domain registrar, creation date, expiry date, and nameservers for a website domain.",
            "parameters": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Domain name (e.g. openai.com, amazon.in)"}
                },
                "required": ["domain"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "extract_ocr_text",
            "description": "Extract and transcribe text from an image, document, receipt, bill, or photo via OCR.",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_path_or_url": {"type": "string", "description": "Local path or URL of the image"}
                },
                "required": ["image_path_or_url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "transcribe_audio",
            "description": "Transcribe audio file or voice note into text using Groq Whisper model.",
            "parameters": {
                "type": "object",
                "properties": {
                    "audio_path_or_url": {"type": "string", "description": "Local file path or URL of audio/voice recording"}
                },
                "required": ["audio_path_or_url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_voice_note",
            "description": "Generate a natural realistic voice note / audio speech from text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The text to convert to realistic speech"}
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_air_quality_index",
            "description": "Get real-time live Air Quality Index (AQI), PM2.5, PM10, pollution level, and medical health advisory for any city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name (e.g. Delhi, Mumbai, Malda, Kolkata)"}
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_live_ipos",
            "description": "Get live, current, and upcoming Indian Stock Market IPOs, issue price, dates, and GMP Grey Market Premium.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "scan_url_phishing",
            "description": "Scan a URL or link for phishing, malware, fake bank traps, suspicious TLDs, and SSL risks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The website URL to scan for phishing/security risks"}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_post_office_info",
            "description": "Look up India Post branch offices, speed post delivery status, and circle by PIN code or area.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pincode_or_area": {"type": "string", "description": "6-digit Indian PIN code or area name"}
                },
                "required": ["pincode_or_area"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ping_host",
            "description": "Test server or domain DNS resolution, TCP handshake latency, and uptime response.",
            "parameters": {
                "type": "object",
                "properties": {
                    "host": {"type": "string", "description": "Domain name or IP address to ping (e.g. google.com)"}
                },
                "required": ["host"]
            }
        }
    }
]


def execute_tool_call(tool_name: str, args: Dict[str, Any], user_id: str, chat_id: str) -> str:
    """Dispatches tool call to appropriate skill module with security guardrail check."""
    # Check security verification for high-risk actions
    v_check = security.check_and_request_verification(tool_name, args, user_id)
    if v_check and v_check.get("needs_verification"):
        return v_check["text"]

    try:
        if tool_name == "web_search":
            return search_the_web(args.get("query", ""))
        elif tool_name == "get_weather":
            return apis.get_weather_data(args.get("city", "Malda, West Bengal, India"))
        elif tool_name == "get_news":
            return apis.get_news_digest(args.get("topic"), args.get("country", "in"))
        elif tool_name == "convert_currency":
            return apis.get_currency_conversion(float(args.get("amount", 1)), args.get("from_curr", "USD"), args.get("to_curr", "INR"))
        elif tool_name == "get_crypto_prices":
            return apis.get_crypto_price(args.get("coins", "bitcoin,ethereum,solana"))
        elif tool_name == "lookup_book":
            return apis.lookup_book_openlibrary(args.get("query", ""))
        elif tool_name == "lookup_wikipedia":
            return apis.lookup_wikipedia(args.get("query", ""))
        elif tool_name == "get_movie_info":
            return apis.get_movie_info(args.get("title", ""))
        elif tool_name == "get_holidays":
            return apis.get_upcoming_holidays(args.get("country_code", "IN"), args.get("year"))
        elif tool_name == "lookup_dictionary":
            return apis.lookup_dictionary(args.get("word", ""))
        elif tool_name == "translate_text":
            return apis.translate_text(args.get("text", ""), args.get("source_lang", "en"), args.get("target_lang", "hi"))
        elif tool_name == "get_joke":
            return apis.get_random_joke()
        elif tool_name == "get_quote":
            return apis.get_random_quote()
        elif tool_name == "lookup_vehicle_vin":
            return apis.lookup_vehicle_vin(args.get("vin", ""))
        elif tool_name == "check_password_breach":
            return apis.check_password_breach(args.get("password", ""))
        elif tool_name == "solve_math":
            return apis.solve_math_expression(args.get("expression", ""))
        elif tool_name == "get_nasa_apod":
            return apis.get_nasa_apod()
        elif tool_name == "create_reminder":
            return utils.create_reminder(user_id, chat_id, args.get("text", ""), args.get("time_str", "in 1 hour"))
        elif tool_name == "list_reminders":
            return utils.list_user_reminders(user_id)
        elif tool_name == "add_medicine_schedule":
            return utils.add_medicine_schedule(user_id, args.get("name", ""), args.get("dosage", ""), args.get("schedule_time", ""), args.get("instructions", ""))
        elif tool_name == "save_note":
            return utils.save_user_note(user_id, args.get("title", "Note"), args.get("content", ""), args.get("tags", ""))
        elif tool_name == "search_notes":
            return utils.search_user_notes(user_id, args.get("query"))
        elif tool_name == "add_todo_task":
            return utils.add_user_todo(user_id, args.get("title", ""), args.get("priority", "medium"), args.get("due_date"))
        elif tool_name == "list_todo_tasks":
            return utils.list_user_todos(user_id, args.get("status", "pending"))
        elif tool_name == "complete_todo_task":
            return utils.complete_user_todo(user_id, int(args.get("todo_id", 0)))
        elif tool_name == "log_expense":
            return utils.log_user_expense(user_id, float(args.get("amount", 0)), args.get("category", "general"), args.get("description", ""))
        elif tool_name == "get_expense_summary":
            return utils.get_user_finance_summary(user_id, args.get("month"))
        elif tool_name == "add_bill":
            return utils.add_user_bill(user_id, args.get("title", ""), float(args.get("amount", 0)), args.get("due_date", ""))
        elif tool_name == "list_bills":
            return utils.list_user_bills(user_id)
        elif tool_name == "parse_bank_sms":
            return utils.parse_bank_transaction_sms(user_id, args.get("message_text", ""))
        elif tool_name == "get_commute_eta":
            return utils.get_commute_eta(args.get("origin", ""), args.get("destination", ""))
        elif tool_name == "estimate_cab_fare":
            return utils.estimate_cab_fare(float(args.get("distance_km", 5)), args.get("time_mins"))
        elif tool_name == "track_package":
            return utils.track_package(args.get("tracking_number", ""))
        elif tool_name == "run_internet_speedtest":
            return utils.run_internet_speedtest()
        elif tool_name == "log_habit_done":
            return utils.record_habit_completion(user_id, args.get("habit_name", ""))
        elif tool_name == "list_habits":
            return utils.list_user_habits(user_id)
        elif tool_name == "get_server_health":
            return utils.get_server_system_health()
        elif tool_name == "create_pdf_document":
            fpath, msg = docs.create_pdf_file(args.get("title", "Document"), args.get("content", ""), args.get("filename"))
            if fpath and chat_id:
                docs.send_telegram_file(chat_id, fpath, caption=f"📄 {args.get('title')}")
            return msg
        elif tool_name == "create_excel_spreadsheet":
            fpath, msg = docs.create_excel_file(args.get("sheet_title", "Sheet1"), args.get("headers", []), args.get("rows", []), args.get("filename"))
            if fpath and chat_id:
                docs.send_telegram_file(chat_id, fpath, caption=f"📊 {args.get('sheet_title')}")
            return msg
        elif tool_name == "create_word_document":
            fpath, msg = docs.create_word_file(args.get("title", "Document"), args.get("sections", []), args.get("filename"))
            if fpath and chat_id:
                docs.send_telegram_file(chat_id, fpath, caption=f"📝 {args.get('title')}")
            return msg
        elif tool_name == "remember_user_fact":
            return utils.remember_user_fact(user_id, args.get("key", ""), args.get("value", ""), args.get("category", "general"))
        elif tool_name == "list_memories":
            return utils.list_user_memories(user_id)
        elif tool_name == "gmail_list":
            return prod.list_gmail_messages(args.get("query", "is:unread"), int(args.get("max_results", 5)))
        elif tool_name == "gmail_send":
            return prod.send_gmail(args.get("to", ""), args.get("subject", ""), args.get("body", ""))
        elif tool_name == "gdrive_list":
            return prod.list_drive_files(args.get("query"), int(args.get("max_results", 6)))
        elif tool_name == "gcalendar_list":
            return prod.list_calendar_events(int(args.get("max_results", 5)))
        elif tool_name == "gcalendar_create":
            return prod.create_calendar_event(args.get("summary", ""), args.get("start_iso", ""), args.get("end_iso", ""), args.get("description", ""))
        elif tool_name == "outlook_list":
            return prod.list_outlook_emails(int(args.get("max_results", 5)))
        elif tool_name == "outlook_send":
            return prod.send_outlook_email(args.get("to", ""), args.get("subject", ""), args.get("body", ""))
        elif tool_name == "github_repos":
            return prod.list_github_repos(args.get("username_or_org"), int(args.get("max_results", 6)))
        elif tool_name == "github_issues":
            return prod.list_github_issues(args.get("repo", ""), args.get("state", "open"))
        elif tool_name == "github_prs":
            return prod.list_github_prs(args.get("repo", ""), args.get("state", "open"))
        elif tool_name == "mcp_coding_task":
            return mcp.mcp_execute_coding_task(args.get("agent_type", "antigravity"), args.get("instruction", ""), args.get("context"))
        elif tool_name == "get_stock_quote":
            return markets.get_stock_quote(args.get("symbol", "RELIANCE"))
        elif tool_name == "get_gold_silver_rates":
            return markets.get_gold_silver_rates()
        elif tool_name == "get_fuel_rates":
            return markets.get_fuel_rates(args.get("city", "Delhi"))
        elif tool_name == "get_train_pnr_status":
            return markets.get_train_pnr_status(args.get("pnr", ""))
        elif tool_name == "get_train_live_status":
            return markets.get_train_live_status(args.get("train_number_or_name", ""))
        elif tool_name == "get_flight_status":
            return markets.get_flight_status(args.get("flight_code", ""))
        elif tool_name == "summarize_youtube_video":
            return content.summarize_youtube_video(args.get("url", ""))
        elif tool_name == "summarize_webpage":
            return content.summarize_webpage(args.get("url", ""))
        elif tool_name == "get_daily_briefing":
            return content.get_daily_briefing(user_id, args.get("city", "Malda"))
        elif tool_name == "capture_website_screenshot":
            res = dev.capture_website_screenshot(args.get("url", ""))
            if res.get("file_path") and chat_id:
                docs.send_telegram_file(chat_id, res["file_path"], caption=res.get("text", "📸 Website Screenshot"), file_type="photo")
            return res.get("text") or res.get("error", "Screenshot processed.")
        elif tool_name == "run_python_code_sandbox":
            return dev.run_python_code_sandbox(args.get("code", ""))
        elif tool_name == "query_sqlite_database":
            return dev.query_sqlite_database(args.get("query", ""), user_id)
        elif tool_name == "manage_knowledge_graph":
            return dev.manage_knowledge_graph(args.get("action", "list"), args.get("entity", ""), args.get("relation", ""), args.get("target", ""), user_id)
        elif tool_name == "extract_social_media_info":
            return dev.extract_social_media_info(args.get("url", ""))
        elif tool_name == "view_server_logs":
            return dev.view_server_logs(args.get("service_name", "rasa-bot"), int(args.get("lines", 15)))
        elif tool_name == "generate_resume_pdf":
            res = conv.generate_resume_pdf(args.get("role_or_details", ""), args.get("candidate_name", "Candidate"))
            if res.get("file_path") and chat_id:
                docs.send_telegram_file(chat_id, res["file_path"], caption=res.get("text", "📄 Resume PDF"), file_type="document")
            return res.get("text", "Resume generated.")
        elif tool_name == "generate_cover_letter_pdf":
            res = conv.generate_cover_letter_pdf(args.get("company_and_role", ""), args.get("candidate_name", "Candidate"))
            if res.get("file_path") and chat_id:
                docs.send_telegram_file(chat_id, res["file_path"], caption=res.get("text", "✉️ Cover Letter PDF"), file_type="document")
            return res.get("text", "Cover letter generated.")
        elif tool_name == "generate_voice_speech":
            res_v = mob.generate_voice_speech(args.get("text", ""), args.get("voice_lang", "hi"))
            if res_v.get("file_path") and chat_id:
                docs.send_telegram_file(chat_id, res_v["file_path"], caption=res_v.get("text", "🎙️ Voice Message"), file_type="voice")
            return res_v.get("text", "Voice generated.")
        elif tool_name == "get_full_skills_directory":
            return mob.get_full_skills_directory()
        elif tool_name == "analyze_imei_device":
            res_im = imei_dev.analyze_imei(args.get("imei", ""))
            return res_im.get("text", res_im.get("error", "IMEI analysis failed."))
        elif tool_name == "decode_device_serial":
            res_sn = imei_dev.decode_serial_number(args.get("serial_number", ""), args.get("brand"))
            return res_sn.get("text", res_sn.get("error", "Serial decoding failed."))
        elif tool_name == "decode_apple_model":
            res_m = imei_dev.decode_apple_model_number(args.get("model_number", ""))
            return res_m.get("text", res_m.get("error", "Model decoding failed."))
        elif tool_name == "lookup_mac_address":
            res_mac = imei_dev.lookup_mac_oui(args.get("mac_address", ""))
            return res_mac.get("text", res_mac.get("error", "MAC lookup failed."))
        elif tool_name == "get_ceir_blocking_guide":
            res_ceir = imei_dev.generate_ceir_blocking_guide(args.get("imei"))
            return res_ceir.get("text", "CEIR guide generated.")
        elif tool_name == "generate_upi_qr":
            res_u = adv.generate_upi_qr(
                vpa=args.get("vpa", ""),
                amount=float(args.get("amount", 0)) if args.get("amount") else None,
                payee_name=args.get("payee_name"),
                note=args.get("note")
            )
            if res_u.get("file_path") and chat_id:
                docs.send_telegram_file(chat_id, res_u["file_path"], caption=res_u.get("text", "⚡ UPI QR"), file_type="photo")
            return res_u.get("text", "UPI QR Code generated.")
        elif tool_name == "search_live_web":
            return adv.search_live_web(args.get("query", ""))
        elif tool_name == "lookup_medicine_info":
            return adv.lookup_medicine_info(args.get("medicine_name", ""))
        elif tool_name == "inspect_ssl_cert":
            return adv.inspect_ssl_certificate(args.get("domain", ""))
        elif tool_name == "inspect_domain_whois":
            return adv.inspect_domain_whois(args.get("domain", ""))
        elif tool_name == "extract_ocr_text":
            return adv.extract_ocr_text(args.get("image_path_or_url", ""))
        elif tool_name == "transcribe_audio":
            return adv.transcribe_audio(args.get("audio_path_or_url", ""))
        elif tool_name == "generate_voice_note":
            ok, fpath, msg = superpack.generate_voice_note(args.get("text", ""))
            return msg if ok else f"⚠️ Voice note creation failed: {msg}"
        elif tool_name == "get_air_quality_index":
            return superpack.get_air_quality_index(args.get("city", "Malda"))
        elif tool_name == "get_live_ipos":
            return superpack.get_live_ipo_data()
        elif tool_name == "scan_url_phishing":
            return superpack.scan_url_phishing_security(args.get("url", ""))
        elif tool_name == "get_post_office_info":
            return superpack.get_post_office_branches(args.get("pincode_or_area", ""))
        elif tool_name == "ping_host":
            return superpack.ping_server_health(args.get("host", ""))

    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
        return f"❌ Tool execution error ({tool_name}): {str(e)}"

    return f"⚠️ Tool {tool_name} not recognized."


# ---------------------------------------------------------------------------
# Main Action: ActionLLMResponse
# ---------------------------------------------------------------------------

class ActionLLMResponse(Action):
    def name(self) -> Text:
        return "action_llm_response"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:

        user_message = tracker.latest_message.get("text", "")
        sender_id = str(tracker.sender_id)
        chat_id = str(tracker.current_state().get("latest_message", {}).get("metadata", {}).get("chat_id") or sender_id)
        user_id = sender_id

        # 0a. Check if message is a slash command
        if user_message.strip().startswith("/"):
            from . import commands
            cmd_res = commands.handle_slash_command(user_message, user_id, chat_id)
            if cmd_res.get("handled"):
                dispatcher.utter_message(text=cmd_res.get("text", ""))
                return []

        # 0b. Check if user is confirming or canceling a pending high-risk action
        was_v, verified_action, v_msg = security.handle_user_verification_response(user_message, user_id)
        if was_v:
            if verified_action:
                act = verified_action["action"]
                par = verified_action["params"]
                if act == "make_phone_call":
                    res_exec = android.make_phone_call(par.get("phone_number") or par.get("phone", ""))
                elif act == "send_phone_sms":
                    res_exec = android.send_phone_sms(par.get("phone_number") or par.get("phone", ""), par.get("message", ""))
                elif act == "execute_sql_query":
                    res_exec = dev.execute_sqlite_query(par.get("query", ""))
                elif act == "run_python_sandbox":
                    res_exec = dev.run_python_sandbox_code(par.get("code", ""))
                else:
                    res_exec = f"✅ Executed {act} successfully."
                dispatcher.utter_message(text=f"{v_msg}\n\n{res_exec}")
            else:
                dispatcher.utter_message(text=v_msg)
            return []

        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key or groq_api_key.startswith("your_"):
            warning_msg = (
                "Arre dost! Meri Groq API key configure nahi hai abhi. "
                "Please `.env` file me valid `GROQ_API_KEY` provide karein so I can chat freely!"
            )
            dispatcher.utter_message(text=warning_msg)
            return []

        # Load long-term memory context for this user
        user_memory_context = utils.get_user_memory_context(user_id)

        # Build conversation history from the last 6 messages
        history_messages: List[Dict[str, str]] = []
        events = tracker.events
        for event in reversed(events):
            event_type = event.get("event")
            if event_type == "user" and event.get("text"):
                history_messages.append({"role": "user", "content": event.get("text")})
            elif event_type == "bot" and event.get("text"):
                history_messages.append({"role": "assistant", "content": event.get("text")})
            
            if len(history_messages) >= 7:
                break

        history_messages.reverse()
        if history_messages and history_messages[-1]["role"] == "user" and history_messages[-1]["content"] == user_message:
            past_dialogue = history_messages[:-1]
        else:
            past_dialogue = history_messages[-6:]

        current_date_str = datetime.now(IST).strftime("%A, %B %d, %Y (%I:%M %p IST)")

        memory_prompt_block = f"\n\n[Persistent User Memories & Preferences]:\n{user_memory_context}" if user_memory_context else ""

        system_prompt = (
            f"You are Alya, a fast, witty, warm, super friendly, and highly intelligent Hinglish-speaking AI assistant "
            f"for Telegram (@Alya_Rasa_Bot).\n"
            f"Current DateTime: {current_date_str}.\n"
            f"{memory_prompt_block}\n\n"
            f"STRICT SHORT REPLY MODE & CONVERSATION RULES:\n"
            f"1. Core Rule: Answer first. Keep it short. Alya is a fast Telegram assistant, not an essay writer. Target: User asks -> Alya answers directly -> stop.\n"
            f"2. Normal Conversation:\n"
            f"   - Default: 1–2 short sentences.\n"
            f"   - Maximum: 30–40 words.\n"
            f"   - Do NOT repeat the user's message.\n"
            f"   - Do NOT explain unnecessary details or internal logic.\n"
            f"   - Do NOT add filler phrases or generate long paragraphs.\n"
            f"   - Do NOT say the same thing in multiple ways.\n"
            f"   - Examples:\n"
            f"     * User: 'Kya kar rahi hai?' -> 'Bas tumse baat kar rahi hoon 😄'\n"
            f"     * User: 'Thanks' -> 'Anytime! 😊'\n"
            f"     * User: 'Good morning' -> 'Good morning! ☀️'\n"
            f"     * User: 'Kya scene hai?' -> 'Sab chill 😎 Tu bata?'\n"
            f"3. Tool & Command Responses:\n"
            f"   - When using tools or checking data, NEVER expose internal reasoning or unnecessary progress narration.\n"
            f"   - Do NOT generate: 'Actually mere paas...', 'Wait, ek second...', 'Chalo, abhi sorted karte hain...', 'Ho sakta hai...', 'Main check karke batati hoon...', or long explanations about what the tool is doing.\n"
            f"   - Instead: Use short status like '🔎 Reminders check kar raha hoon...', then provide only the result.\n"
            f"   - Examples for reminders/data check:\n"
            f"     * If found: 'Mil gaya 👍 Kal 1 PM ka reminder set hai.'\n"
            f"     * If not found: 'Nahi mil raha 😅 Kal wala reminder save nahi hua tha.'\n"
            f"   - For commands (/weather, /reminders, /notes, /todos, /briefing, /search, /summarize): Return the actual result first and keep the explanation minimal. Do not turn command results into conversational essays.\n"
            f"4. Error Responses:\n"
            f"   - Keep errors short, useful, and polite (e.g. '⚠️ Weather service unavailable hai. Thodi der baad try karo.'). Never give long technical explanations.\n"
            f"5. Language & Tone:\n"
            f"   - Speak in natural, modern, conversational Hinglish (Hindi written in Roman script mixed with English).\n"
            f"   - Tone: Friendly, casual, witty, confident, street-smart, and empathetic.\n"
            f"6. Emojis:\n"
            f"   - Use 0–2 relevant emojis maximum. Never use emojis randomly just to make the response longer.\n"
            f"7. Capabilities & Tool Usage Rule:\n"
            f"   - You have 37+ specialized tools. Always call the corresponding dedicated tool when real-time information, actions, documents, calculations, or storage is needed instead of hallucinating."
        )

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(past_dialogue)
        messages.append({"role": "user", "content": user_message})
        try:
            from .llm_provider import (
                LLMProviderManager,
                STRUCTURED_OUTPUT_TOOLS,
                CHAT_MAX_TOKENS,
                SYNTHESIS_CONCISE_MAX_TOKENS,
                STRUCTURED_MAX_TOKENS,
            )

            curr_messages = list(messages)
            tool_iterations = 0
            max_iterations = 3
            final_text = None
            executed_tools = []

            while tool_iterations < max_iterations:
                has_structured_tool = any(t in STRUCTURED_OUTPUT_TOOLS for t in executed_tools)
                if tool_iterations == 0:
                    current_max_tokens = CHAT_MAX_TOKENS
                elif has_structured_tool:
                    current_max_tokens = STRUCTURED_MAX_TOKENS
                else:
                    current_max_tokens = SYNTHESIS_CONCISE_MAX_TOKENS

                content, tool_calls, provider_used = LLMProviderManager.call_chat_completion(
                    messages=curr_messages,
                    tools=LLM_TOOLS_SPEC if tool_iterations < max_iterations - 1 else None,
                    temperature=0.3,
                    max_tokens=current_max_tokens
                )

                if not tool_calls:
                    final_text = content
                    break

                curr_messages.append({"role": "assistant", "content": content or "", "tool_calls": tool_calls})
                for tool_call in tool_calls:
                    fn_data = tool_call.get("function", {})
                    fn_name = fn_data.get("name")
                    if fn_name:
                        executed_tools.append(fn_name)
                    try:
                        fn_args = json.loads(fn_data.get("arguments", "{}"))
                    except Exception:
                        fn_args = {}

                    tool_output = execute_tool_call(fn_name, fn_args, user_id, chat_id)
                    curr_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.get("id"),
                        "name": fn_name,
                        "content": str(tool_output)
                    })

                tool_iterations += 1
            else:
                has_structured_tool = any(t in STRUCTURED_OUTPUT_TOOLS for t in executed_tools)
                if has_structured_tool:
                    synth_tokens = STRUCTURED_MAX_TOKENS
                    synth_instruction = (
                        "Synthesize the above tool findings into a clean, direct Markdown response in natural Hinglish. "
                        "Return the result first. Keep explanation minimal."
                    )
                else:
                    synth_tokens = SYNTHESIS_CONCISE_MAX_TOKENS
                    synth_instruction = (
                        "Provide a short, direct 1–2 sentence answer in natural Hinglish with the exact result. "
                        "Answer first, keep it under 30-40 words. No filler, no internal narration. Use 0-2 emojis."
                    )

                curr_messages.append({
                    "role": "user",
                    "content": synth_instruction
                })
                synth_content, _, _ = LLMProviderManager.call_chat_completion(
                    messages=curr_messages,
                    temperature=0.3,
                    max_tokens=synth_tokens
                )
                final_text = synth_content

            if final_text:
                dispatcher.utter_message(text=final_text)
            else:
                dispatcher.utter_message(text="⚠️ AI service unavailable hai. Thodi der baad try karo.")
        except Exception as e:
            logger.error(f"ActionLLMResponse unexpected error: {e}", exc_info=True)
            dispatcher.utter_message(text="⚠️ AI service unavailable hai. Thodi der baad try karo.")

        return []


# ---------------------------------------------------------------------------
# Direct Rasa Skill Actions
# ---------------------------------------------------------------------------

class ActionGetWeather(Action):
    def name(self) -> Text:
        return "action_get_weather"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        user_text = tracker.latest_message.get("text", "")
        city = extract_city_from_weather_query(user_text)
        res = apis.get_weather_data(city)
        dispatcher.utter_message(text=res)
        return []


class ActionGetNews(Action):
    def name(self) -> Text:
        return "action_get_news"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        res = apis.get_news_digest(country="in")
        dispatcher.utter_message(text=res)
        return []


class ActionGetCrypto(Action):
    def name(self) -> Text:
        return "action_get_crypto"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        res = apis.get_crypto_price("bitcoin,ethereum,solana,dogecoin")
        dispatcher.utter_message(text=res)
        return []


class ActionServerHealth(Action):
    def name(self) -> Text:
        return "action_server_health"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        user_msg = tracker.latest_message.get("text", "").strip().lower()
        if user_msg.startswith(("/status", "/scraperstatus", "/jobstatus")) or "scraper" in user_msg:
            res = js.get_status_text(db, str(tracker.sender_id))
        else:
            res = utils.get_server_system_health()
        dispatcher.utter_message(text=res)
        return []


class ActionSpeedTest(Action):
    def name(self) -> Text:
        return "action_speed_test"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        dispatcher.utter_message(text="⏳ Running internet speed test on server, ek second...")
        res = utils.run_internet_speedtest()
        dispatcher.utter_message(text=res)
        return []


class ActionListHabits(Action):
    def name(self) -> Text:
        return "action_list_habits"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        res = utils.list_user_habits(str(tracker.sender_id))
        dispatcher.utter_message(text=res)
        return []


class ActionListTodos(Action):
    def name(self) -> Text:
        return "action_list_todos"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        res = utils.list_user_todos(str(tracker.sender_id))
        dispatcher.utter_message(text=res)
        return []


class ActionListNotes(Action):
    def name(self) -> Text:
        return "action_list_notes"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        res = utils.search_user_notes(str(tracker.sender_id))
        dispatcher.utter_message(text=res)
        return []


# -------------------------------------------------------------
# Jobs & Scholarships Rasa Actions
# -------------------------------------------------------------

class ActionGetJobs(Action):
    def name(self) -> Text:
        return "action_get_jobs"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        sender_id = str(tracker.sender_id)
        res = js.get_latest_jobs_text(db, user_id=sender_id, limit=5)
        dispatcher.utter_message(text=res)
        return []


class ActionGetScholarships(Action):
    def name(self) -> Text:
        return "action_get_scholarships"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        sender_id = str(tracker.sender_id)
        res = js.get_latest_scholarships_text(db, user_id=sender_id, limit=5)
        dispatcher.utter_message(text=res)
        return []


class ActionGetPsuJobs(Action):
    def name(self) -> Text:
        return "action_get_psu_jobs"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        sender_id = str(tracker.sender_id)
        res = js.get_latest_psu_text(db, user_id=sender_id, limit=5)
        dispatcher.utter_message(text=res)
        return []


class ActionSearchVacancies(Action):
    def name(self) -> Text:
        return "action_search_vacancies"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        user_msg = tracker.latest_message.get("text", "").strip()
        # Clean slash command if present
        clean_query = re.sub(r"^/search\s*", "", user_msg, flags=re.IGNORECASE).strip()
        if not clean_query:
            clean_query = user_msg
        res = js.search_vacancies_text(db, clean_query)
        dispatcher.utter_message(text=res)
        return []


class ActionSubscribeAlerts(Action):
    def name(self) -> Text:
        return "action_subscribe_alerts"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        sender_id = str(tracker.sender_id)
        res = js.subscribe_user(db, sender_id)
        dispatcher.utter_message(text=res)
        return []


class ActionUnsubscribeAlerts(Action):
    def name(self) -> Text:
        return "action_unsubscribe_alerts"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        sender_id = str(tracker.sender_id)
        res = js.unsubscribe_user(db, sender_id)
        dispatcher.utter_message(text=res)
        return []


class ActionSetAlertFormat(Action):
    def name(self) -> Text:
        return "action_set_alert_format"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        sender_id = str(tracker.sender_id)
        user_msg = tracker.latest_message.get("text", "").lower()
        fmt = "full" if "full" in user_msg else "short"
        res = js.set_user_format_pref(db, sender_id, fmt)
        dispatcher.utter_message(text=res)
        return []

