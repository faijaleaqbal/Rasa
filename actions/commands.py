import os
import re
import shlex
import logging
from typing import Any, Dict, List, Optional, Tuple

from . import db
from . import skills_productivity as prod
from . import skills_documents as docs
from . import skills_free_apis as apis
from . import skills_utilities as utils
from . import mcp_client as mcp

logger = logging.getLogger(__name__)


def handle_slash_command(command_text: str, user_id: str, chat_id: str) -> Dict[str, Any]:
    """
    Directly processes Telegram slash commands with deterministic argument parsing.
    Returns a dict with:
      - 'handled': bool
      - 'text': str (Markdown response)
      - 'file_path': Optional[str] (Local file to send, e.g. PDF/Excel/Word)
      - 'file_type': str ('document' / 'photo')
    """
    clean_text = command_text.strip()
    if not clean_text.startswith("/"):
        return {"handled": False}

    parts = clean_text.split(maxsplit=1)
    raw_cmd = parts[0].lower()
    # Strip bot username if attached, e.g. /weather@Alya_Rasa_Bot
    cmd = raw_cmd.split("@")[0]
    args_str = parts[1].strip() if len(parts) > 1 else ""

    logger.info(f"Processing slash command: {cmd} with args '{args_str}' for user {user_id}")

    # 1. /help or /start
    if cmd in ["/start", "/help", "/commands"]:
        help_text = (
            "✨ **Alya AI Assistant (@Alya_Rasa_Bot) — Slash Commands Menu** ✨\n\n"
            "**🌤️ Real-Time Free APIs:**\n"
            "• `/weather <city>` — Live weather (e.g. `/weather Mumbai`)\n"
            "• `/news [topic]` — Top headlines (e.g. `/news tech`)\n"
            "• `/currency <amt> <from> <to>` — Currency conversion (e.g. `/currency 250 USD INR`)\n"
            "• `/crypto [coin]` — Live crypto prices & ETH gas (e.g. `/crypto btc,eth`)\n"
            "• `/wiki <topic>` — Wikipedia & books search (e.g. `/wiki Quantum Computing`)\n"
            "• `/movie <title>` — Movie / TV ratings & plot (e.g. `/movie Inception`)\n"
            "• `/holiday [country]` — Public holidays & festivals (e.g. `/holiday IN`)\n"
            "• `/image <query>` — Search HD photos (e.g. `/image sunset`)\n"
            "• `/translate <text>` — Dictionary & translation (e.g. `/translate Namaste`)\n"
            "• `/joke` — Random clean joke & inspirational quote\n"
            "• `/vehicle <vin>` — Vehicle VIN decoder & specs\n"
            "• `/shop <product>` — Product info & price comparison (e.g. `/shop Sony WH-1000XM5`)\n"
            "• `/breach <email_or_pwd>` — Data breach check via XposedOrNot & HIBP\n"
            "• `/math <expression>` — WolframAlpha & SymPy solver (e.g. `/math integrate x^2 sin(x)`)\n"
            "• `/science` — NASA Astronomy Picture of the Day\n\n"
            "**📋 Daily Life Utilities:**\n"
            "• `/remind <time> <msg>` — Set reminder (e.g. `/remind in 15 mins Team sync`)\n"
            "• `/medremind <time> <med>` — Medicine dosage reminder\n"
            "• `/note <text>` — Save a quick note\n"
            "• `/notes` — List saved notes\n"
            "• `/todo <task>` — Add task to to-do list\n"
            "• `/todos` — List pending tasks\n"
            "• `/expense <amt> <cat> <desc>` — Log expense (e.g. `/expense 450 food Lunch`)\n"
            "• `/expenses` — Monthly finance summary & breakdown\n"
            "• `/bill <name> <due> [amt]` — Bill reminder (e.g. `/bill WiFi 2026-08-25 1000`)\n"
            "• `/traffic <origin> to <destination>` — OpenRouteService ETA & distance\n"
            "• `/ride <from> to <to>` — Uber / Ola fare estimate & distance\n"
            "• `/track <order_id>` — Universal parcel tracking\n"
            "• `/habit [name]` — Daily habit streak tracker\n"
            "• `/serverstatus` — EC2 CPU, RAM, Disk & process diagnostics\n"
            "• `/speedtest` — Server internet bandwidth test\n\n"
            "**📁 Productivity & Files:**\n"
            "• `/pdf <title>` — Generate styled PDF document & send to chat\n"
            "• `/excel <title>` — Generate styled Excel sheet & send to chat\n"
            "• `/doc <title>` — Generate styled Word doc (.docx) & send to chat\n"
            "• `/gmail [query]` — Read recent Gmail messages\n"
            "• `/outlook` — Read recent Outlook emails\n"
            "• `/drive [query]` — Search Google Drive files\n"
            "• `/calendar` — View upcoming Google Calendar events\n"
            "• `/github [repo]` — List GitHub repos, issues, and PRs\n"
            "• `/code <task>` — Delegate coding task via OpenCode server\n\n"
            "💡 _Tip: You can tap the **[/] Menu** button next to your text bar to auto-complete any command!_"
        )
        return {"handled": True, "text": help_text}

    # 2. /weather <city>
    elif cmd == "/weather":
        city = args_str if args_str else "Delhi"
        return {"handled": True, "text": apis.get_weather_data(city)}

    # 3. /news [topic]
    elif cmd == "/news":
        return {"handled": True, "text": apis.get_news_digest(topic=args_str or None, country="in")}

    # 4. /currency <amount> <from> <to>
    elif cmd == "/currency":
        tokens = args_str.split()
        if len(tokens) >= 3:
            try:
                amt = float(tokens[0])
                from_c = tokens[1]
                to_c = tokens[2]
                return {"handled": True, "text": apis.get_currency_conversion(amt, from_c, to_c)}
            except ValueError:
                pass
        return {"handled": True, "text": "Usage: `/currency <amount> <from_currency> <to_currency>`\nExample: `/currency 150 USD INR`"}

    # 5. /crypto [coin]
    elif cmd == "/crypto":
        coins = args_str if args_str else "bitcoin,ethereum,solana,dogecoin"
        return {"handled": True, "text": apis.get_crypto_price(coins)}

    # 6. /wiki <topic>
    elif cmd in ["/wiki", "/wikipedia"]:
        if not args_str:
            return {"handled": True, "text": "Usage: `/wiki <topic>`\nExample: `/wiki Artificial Intelligence`"}
        return {"handled": True, "text": apis.lookup_wikipedia(args_str)}

    # 7. /movie <title>
    elif cmd in ["/movie", "/tv"]:
        if not args_str:
            return {"handled": True, "text": "Usage: `/movie <title>`\nExample: `/movie Inception`"}
        return {"handled": True, "text": apis.get_movie_info(args_str)}

    # 8. /holiday [country]
    elif cmd in ["/holiday", "/holidays"]:
        country = args_str.upper() if args_str else "IN"
        return {"handled": True, "text": apis.get_upcoming_holidays(country_code=country)}

    # 9. /image <query>
    elif cmd == "/image":
        if not args_str:
            return {"handled": True, "text": "Usage: `/image <query>`\nExample: `/image sunset mountains`"}
        return {"handled": True, "text": apis.search_stock_images(args_str)}

    # 10. /translate <text>
    elif cmd == "/translate":
        if not args_str:
            return {"handled": True, "text": "Usage: `/translate <text>`\nExample: `/translate Hello, how are you today?`"}
        # If single word, also offer dictionary meaning
        if len(args_str.split()) == 1:
            dict_res = apis.lookup_dictionary(args_str)
            trans_res = apis.translate_text(args_str, source_lang="en", target_lang="hi")
            return {"handled": True, "text": f"{dict_res}\n\n{trans_res}"}
        return {"handled": True, "text": apis.translate_text(args_str, source_lang="en", target_lang="hi")}

    # 11. /joke
    elif cmd in ["/joke", "/quote"]:
        joke = apis.get_random_joke()
        quote = apis.get_random_quote()
        return {"handled": True, "text": f"{joke}\n\n---\n\n{quote}"}

    # 12. /vehicle <query>
    elif cmd == "/vehicle":
        if not args_str:
            return {"handled": True, "text": "Usage: `/vehicle <17-character VIN>`\nExample: `/vehicle 1HGCR2F83HA000000`"}
        return {"handled": True, "text": apis.lookup_vehicle_vin(args_str)}

    # 13. /shop <product>
    elif cmd == "/shop":
        if not args_str:
            return {"handled": True, "text": "Usage: `/shop <product name or barcode>`\nExample: `/shop Sony WH-1000XM5`"}
        return {"handled": True, "text": apis.lookup_product_info(args_str)}

    # 14. /breach <email_or_password>
    elif cmd == "/breach":
        if not args_str:
            return {"handled": True, "text": "Usage: `/breach <email_or_password>`\nExample: `/breach user@example.com` or `/breach Password123`"}
        return {"handled": True, "text": apis.check_security_breach(args_str)}

    # 15. /math <expression>
    elif cmd == "/math":
        if not args_str:
            return {"handled": True, "text": "Usage: `/math <expression>`\nExample: `/math 3*x^2 - 12 = 0` or `/math (45 * 12) / 3`"}
        return {"handled": True, "text": apis.solve_math_expression(args_str)}

    # 16. /science [query]
    elif cmd == "/science":
        return {"handled": True, "text": apis.get_nasa_apod()}

    # 17. /remind <time> <message>
    elif cmd == "/remind":
        tokens = args_str.split(maxsplit=2)
        if len(tokens) >= 2:
            time_part = f"{tokens[0]} {tokens[1]}" if len(tokens) >= 2 and tokens[0] in ["in", "at", "every", "tomorrow"] else tokens[0]
            msg_part = tokens[2] if time_part.count(" ") > 0 and len(tokens) >= 3 else " ".join(tokens[1:])
            res = utils.create_reminder(user_id, chat_id, msg_part, time_part)
            return {"handled": True, "text": res}
        return {"handled": True, "text": "Usage: `/remind <time> <message>`\nExample: `/remind in 15 mins Join team sync`"}

    # 18. /medremind <time> <medicine>
    elif cmd == "/medremind":
        tokens = args_str.split(maxsplit=1)
        if len(tokens) >= 2:
            res = utils.add_medicine_schedule(user_id, name=tokens[1], dosage="1 dose", schedule_time=tokens[0])
            return {"handled": True, "text": res}
        return {"handled": True, "text": "Usage: `/medremind <time> <medicine_name>`\nExample: `/medremind 9:00AM Paracetamol 500mg`"}

    # 19. /note <text>
    elif cmd == "/note":
        if not args_str:
            return {"handled": True, "text": "Usage: `/note <text>`\nExample: `/note WiFi password for office is SecureNet2026`"}
        title = args_str[:30] + ("..." if len(args_str) > 30 else "")
        res = utils.save_user_note(user_id, title=title, content=args_str)
        return {"handled": True, "text": res}

    # 20. /notes
    elif cmd == "/notes":
        return {"handled": True, "text": utils.search_user_notes(user_id, args_str or None)}

    # 21. /todo <task>
    elif cmd == "/todo":
        if not args_str:
            return {"handled": True, "text": "Usage: `/todo <task description>`\nExample: `/todo Buy groceries and milk`"}
        res = utils.add_user_todo(user_id, title=args_str, priority="medium")
        return {"handled": True, "text": res}

    # 22. /todos
    elif cmd == "/todos":
        return {"handled": True, "text": utils.list_user_todos(user_id, status="pending")}

    # 23. /expense <amount> <category> [description]
    elif cmd == "/expense":
        tokens = args_str.split(maxsplit=2)
        if len(tokens) >= 2:
            try:
                amt = float(tokens[0])
                cat = tokens[1]
                desc = tokens[2] if len(tokens) > 2 else f"Expense on {cat}"
                res = utils.log_user_expense(user_id, amt, cat, desc)
                return {"handled": True, "text": res}
            except ValueError:
                pass
        return {"handled": True, "text": "Usage: `/expense <amount> <category> [description]`\nExample: `/expense 450 food Lunch with team`"}

    # 24. /expenses [month]
    elif cmd == "/expenses":
        return {"handled": True, "text": utils.get_user_finance_summary(user_id, month=args_str or None)}

    # 25. /bill <name> <due date> [amount]
    elif cmd == "/bill":
        tokens = args_str.split(maxsplit=2)
        if len(tokens) >= 2:
            title = tokens[0]
            due = tokens[1]
            try:
                amt = float(tokens[2]) if len(tokens) > 2 else 0.0
            except ValueError:
                amt = 0.0
            res = utils.add_user_bill(user_id, title, amt, due)
            return {"handled": True, "text": res}
        return {"handled": True, "text": "Usage: `/bill <name> <due_date> [amount]`\nExample: `/bill Electricity 2026-08-25 1250`"}

    # 26. /traffic [origin to] <destination>
    elif cmd in ["/traffic", "/distance", "/eta"]:
        if not args_str:
            return {"handled": True, "text": "Usage: `/traffic <destination>` or `/traffic <origin> to <destination>`\nExample: `/traffic Mumbai to Pune`"}
        if " to " in args_str:
            parts = args_str.split(" to ", 1)
            return {"handled": True, "text": utils.get_commute_eta(parts[0].strip(), parts[1].strip())}
        return {"handled": True, "text": utils.get_commute_eta("Delhi", args_str)}

    # 27. /ride <from> <to>
    elif cmd == "/ride":
        if " to " in args_str:
            parts = args_str.split(" to ", 1)
            orig, dest = parts[0].strip(), parts[1].strip()
            # Calculate distance using OpenRouteService for accurate fare
            eta_res = utils.get_commute_eta(orig, dest)
            import re
            m = re.search(r"(\d+\.?\d*)\s*km", eta_res)
            dist_km = float(m.group(1)) if m else 10.0
            cab_res = utils.estimate_cab_fare(dist_km)
            return {"handled": True, "text": f"{eta_res}\n\n{cab_res}"}
        return {"handled": True, "text": "Usage: `/ride <from_city> to <to_city>`\nExample: `/ride Mumbai to Pune`"}

    # 28. /track <order_id>
    elif cmd == "/track":
        if not args_str:
            return {"handled": True, "text": "Usage: `/track <tracking_number>`\nExample: `/track EM123456789IN`"}
        return {"handled": True, "text": utils.track_package(args_str)}

    # 29. /habit [name]
    elif cmd == "/habit":
        if args_str:
            return {"handled": True, "text": utils.record_habit_completion(user_id, args_str)}
        return {"handled": True, "text": utils.list_user_habits(user_id)}

    # 30. /serverstatus
    elif cmd in ["/serverstatus", "/health", "/status"]:
        return {"handled": True, "text": utils.get_server_system_health()}

    # 31. /speedtest
    elif cmd == "/speedtest":
        return {"handled": True, "text": utils.run_internet_speedtest()}

    # 32. /gmail [query]
    elif cmd == "/gmail":
        return {"handled": True, "text": prod.list_gmail_messages(query=args_str or "is:unread")}

    # 32b. /outlook [query]
    elif cmd == "/outlook":
        return {"handled": True, "text": prod.list_outlook_emails(max_results=5)}

    # 33. /drive [query]
    elif cmd == "/drive":
        return {"handled": True, "text": prod.list_drive_files(query=args_str or None)}

    # 34. /calendar
    elif cmd == "/calendar":
        return {"handled": True, "text": prod.list_calendar_events()}

    # 35. /github <repo>
    elif cmd == "/github":
        if not args_str:
            return {"handled": True, "text": prod.list_github_repos()}
        if "/" in args_str:
            issues = prod.list_github_issues(args_str)
            prs = prod.list_github_prs(args_str)
            return {"handled": True, "text": f"{issues}\n\n---\n\n{prs}"}
        return {"handled": True, "text": prod.list_github_repos(username_or_org=args_str)}

    # 36. /code <task>
    elif cmd == "/code":
        if not args_str:
            return {"handled": True, "text": "Usage: `/code <coding task description>`\nExample: `/code Write a Python script to monitor API uptime`"}
        return {"handled": True, "text": mcp.mcp_execute_coding_task("opencode", args_str)}

    # 37. /pdf <title> [content]
    elif cmd == "/pdf":
        title = args_str if args_str else "Document"
        content = f"Generated by @Alya_Rasa_Bot for user {user_id}.\n\nDocument Title: {title}\nCreated: {os.uname().nodename}"
        fpath, msg = docs.create_pdf_file(title, content)
        return {"handled": True, "text": msg, "file_path": fpath, "file_type": "document"}

    # 38. /excel <title>
    elif cmd == "/excel":
        sheet_title = args_str if args_str else "Data"
        headers = ["ID", "Item", "Category", "Amount", "Status"]
        rows = [
            ["1", "Server Hosting", "Infrastructure", "45.00", "Active"],
            ["2", "Domain Registration", "Domain", "12.00", "Active"],
            ["3", "SSL Certificate", "Security", "0.00", "Renewed"]
        ]
        fpath, msg = docs.create_excel_file(sheet_title, headers, rows)
        return {"handled": True, "text": msg, "file_path": fpath, "file_type": "document"}

    # 39. /doc <title> [content]
    elif cmd == "/doc":
        title = args_str if args_str else "Document"
        sections = [
            {"heading": "Executive Summary", "body": f"Document generated by @Alya_Rasa_Bot.\nTitle: {title}"},
            {"heading": "Key Points", "body": "- Feature 1: Automated Integration\n- Feature 2: High Reliability\n- Feature 3: Full Telegram Support"}
        ]
        fpath, msg = docs.create_word_file(title, sections)
        return {"handled": True, "text": msg, "file_path": fpath, "file_type": "document"}

    return {"handled": False}
