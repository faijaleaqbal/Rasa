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
from . import skills_android_controller as android
from . import security_guardrails as security
from . import mcp_client as mcp

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
            "description": "Get real-time weather, temperature, humidity, and wind conditions for any city.",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string", "description": "City or location name"}},
                "required": ["city"]
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
            "name": "find_and_ring_phone",
            "description": "Sound a high-priority loud alarm on user's phone to help locate it.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_whatsapp_dispatch",
            "description": "Prepare a direct WhatsApp message link and dispatch to mobile phone.",
            "parameters": {
                "type": "object",
                "properties": {
                    "phone_number": {"type": "string", "description": "Recipient phone number with country code, e.g. +919876543210"},
                    "message": {"type": "string", "description": "Message text to send"}
                },
                "required": ["phone_number", "message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_full_skills_directory",
            "description": "List all 95+ available skills and command triggers in the AI assistant.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "make_phone_call",
            "description": "Initiate an outgoing phone call on user's Android smartphone.",
            "parameters": {
                "type": "object",
                "properties": {"phone_number": {"type": "string", "description": "Phone number with country code"}},
                "required": ["phone_number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_phone_sms",
            "description": "Send an SMS text message directly from user's Android SIM card.",
            "parameters": {
                "type": "object",
                "properties": {
                    "phone_number": {"type": "string", "description": "Recipient phone number"},
                    "message": {"type": "string", "description": "SMS text content"}
                },
                "required": ["phone_number", "message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_recent_phone_sms",
            "description": "Read recent incoming SMS text messages from user's Android inbox.",
            "parameters": {
                "type": "object",
                "properties": {"limit": {"type": "integer", "description": "Number of recent SMS to read, default 5"}}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_phone_alarm",
            "description": "Set a system alarm on user's Android phone clock app.",
            "parameters": {
                "type": "object",
                "properties": {
                    "time_str": {"type": "string", "description": "Alarm time, e.g. '07:30 AM', '6:00'"},
                    "label": {"type": "string", "description": "Alarm label/title"}
                },
                "required": ["time_str"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_phone_timer",
            "description": "Set a countdown timer on user's Android phone clock.",
            "parameters": {
                "type": "object",
                "properties": {
                    "duration_str": {"type": "string", "description": "Duration, e.g. '5 minutes', '30 seconds'"},
                    "label": {"type": "string", "description": "Timer label"}
                },
                "required": ["duration_str"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_file_or_app_on_phone",
            "description": "Open a local file (PDF, doc) or launch an application on Android phone.",
            "parameters": {
                "type": "object",
                "properties": {"target": {"type": "string", "description": "App name (e.g. WhatsApp, YouTube) or file path"}},
                "required": ["target"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "screen_incoming_call_message",
            "description": "Screen and handle missed or incoming phone calls by taking message and generating AI verbal response.",
            "parameters": {
                "type": "object",
                "properties": {
                    "caller_number": {"type": "string", "description": "Phone number of caller"},
                    "caller_statement": {"type": "string", "description": "What caller said or wanted"}
                },
                "required": ["caller_statement"]
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
        elif tool_name == "send_phone_push_notification":
            return mob.send_phone_push_notification(args.get("title", "Alya Alert"), args.get("message", ""), args.get("priority", "high"))
        elif tool_name == "find_and_ring_phone":
            return mob.find_and_ring_phone(user_id)
        elif tool_name == "create_whatsapp_dispatch":
            return mob.create_whatsapp_dispatch(args.get("phone_number", ""), args.get("message", ""))
        elif tool_name == "get_full_skills_directory":
            return mob.get_full_skills_directory()
        elif tool_name == "make_phone_call":
            return android.make_phone_call(args.get("phone_number", ""))
        elif tool_name == "send_phone_sms":
            return android.send_phone_sms(args.get("phone_number", ""), args.get("message", ""))
        elif tool_name == "read_recent_phone_sms":
            return android.read_recent_phone_sms(int(args.get("limit", 5)))
        elif tool_name == "set_phone_alarm":
            return android.set_phone_alarm(args.get("time_str", "07:00 AM"), args.get("label", "Alya Alarm"))
        elif tool_name == "set_phone_timer":
            return android.set_phone_timer(args.get("duration_str", "5 minutes"), args.get("label", "Timer"))
        elif tool_name == "open_file_or_app_on_phone":
            return android.open_file_or_app_on_phone(args.get("target", "WhatsApp"))
        elif tool_name == "screen_incoming_call_message":
            return android.screen_incoming_call_message(args.get("caller_number", "Unknown"), args.get("caller_statement", ""))

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

        logger.info(f"action_llm_response triggered for user {user_id} message: {user_message}")

        # 0. Check if user is confirming or canceling a pending high-risk action
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
            f"You are Alya, a witty, warm, super friendly, and highly intelligent Hinglish-speaking AI chatbot "
            f"for Telegram (@Alya_Rasa_Bot).\n"
            f"Current DateTime: {current_date_str}.\n"
            f"{memory_prompt_block}\n\n"
            f"Personality & Tone Guidelines:\n"
            f"1. Language: Speak in natural, modern, conversational Hinglish (Hindi written in Roman/English alphabet mixed with English). "
            f"Example phrasing: 'Haan bhai, sab badhiya!', 'Arre tension mat lo yaar, main hu na!', 'Batao kya help chahiye aaj?'.\n"
            f"2. Tone: Friendly, casual, witty, confident, street-smart, and empathetic.\n"
            f"3. Capabilities & Skill Integrations: You are equipped with 37+ specialized tools covering Productivity (Gmail, Drive, Calendar, Outlook, GitHub, Coding MCPs), Document Creation (PDF, Excel, Word), Real-Time Free APIs (Weather, News, Forex, Crypto, Wikipedia, Books, Movies, Holidays, Translation, Dictionary, Jokes, Quotes, VIN, Threat checks, Sympy math, NASA), and Daily-Life Utilities (Reminders, Medicine schedules, Notes, To-Dos, Expenses, Bills, Bank SMS parsing, Commute ETA, Cab estimates, Speedtest, Habits, Server Health, Long-term memory).\n"
            f"4. Tool Usage Rule: Whenever the user asks for real-time information, actions, documents, calculations, or storage, ALWAYS call the corresponding dedicated tool instead of hallucinating data. Keep Groq strictly for conversational reasoning and synthesis.\n"
            f"5. Length & Format: Keep responses crisp, neatly formatted with Markdown, emojis, and bullet points for Telegram readability.\n"
            f"6. Never break character. Stay helpful, cheerful, and awesome!"
        )

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(past_dialogue)
        messages.append({"role": "user", "content": user_message})
        try:
            from .llm_provider import LLMProviderManager

            curr_messages = list(messages)
            tool_iterations = 0
            max_iterations = 3
            final_text = None

            while tool_iterations < max_iterations:
                content, tool_calls, provider_used = LLMProviderManager.call_chat_completion(
                    messages=curr_messages,
                    tools=LLM_TOOLS_SPEC,
                    temperature=0.7,
                    max_tokens=900
                )

                if not tool_calls:
                    final_text = content
                    break

                curr_messages.append({"role": "assistant", "content": content or "", "tool_calls": tool_calls})
                for tool_call in tool_calls:
                    fn_data = tool_call.get("function", {})
                    fn_name = fn_data.get("name")
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
                curr_messages.append({
                    "role": "user",
                    "content": "Please synthesize the above tool findings and reply in natural Hinglish."
                })
                synth_content, _, _ = LLMProviderManager.call_chat_completion(
                    messages=curr_messages,
                    temperature=0.7,
                    max_tokens=900
                )
                final_text = synth_content

            if final_text:
                dispatcher.utter_message(text=final_text)
            else:
                dispatcher.utter_message(text="Arre bhai, thoda sa network glitch aa gaya AI services mein! Ek baar dubara message karo?")
        except Exception as e:
            logger.error(f"ActionLLMResponse unexpected error: {e}", exc_info=True)
            dispatcher.utter_message(text="Sorry, AI service is temporarily unavailable, please try again in a moment.")

        except Exception as e:
            logger.error(f"Error in ActionLLMResponse: {e}", exc_info=True)
            dispatcher.utter_message(
                text="Arre bhai, thoda sa technical glitch aa gaya connection me. Thodi der baad try karo na!"
            )

        return []


# ---------------------------------------------------------------------------
# Direct Rasa Skill Actions
# ---------------------------------------------------------------------------

class ActionGetWeather(Action):
    def name(self) -> Text:
        return "action_get_weather"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        user_text = tracker.latest_message.get("text", "")
        # Strip slash command if present and extract requested city or fallback to default
        clean_text = user_text.replace("/weather", "").strip()
        city = clean_text if clean_text else "Malda, West Bengal, India"
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
