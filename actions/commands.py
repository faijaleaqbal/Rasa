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
from . import skills_extended as ext
from . import skills_indian_markets as markets
from . import skills_content as content
from . import skills_developer_tools as dev
from . import skills_converters_resume as conv
from . import skills_mobile_device as mob
from . import skills_android_controller as android
from . import skills_advanced as adv
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
            "**🌟 New Advanced Super-Skills:**\n"
            "• `/upi <vpa> [amount] [name] [note]` — Instant Dynamic UPI scan-and-pay QR code (GPay/PhonePe/Paytm)\n"
            "• `/search <query>` — Real-time live AI Web Search & Synthesis (Tavily & DDG)\n"
            "• `/transcribe [url_or_file]` — Groq Whisper audio & voice note transcription with AI summary\n"
            "• `/med <medicine>` — Clinical medicine uses, active salt, precautions & low-cost generic alternatives\n"
            "• `/ssl <domain>` — Real-time SSL certificate validity, expiry countdown & cipher check\n"
            "• `/whois <domain>` — ICANN RDAP domain registrar, registration & expiry lookup\n"
            "• `/ocr [url_or_file]` — High-accuracy image-to-text extractor (Tesseract + AI polish)\n\n"
            "**🌤️ Real-Time Free APIs:**\n"
            "• `/weather <city>` — Live weather (Default: Malda, WB)\n"
            "• `/news [topic]` — Top headlines (English)\n"
            "• `/currency <amt> <from> <to>` — Currency exchange conversion\n"
            "• `/crypto [coin]` — Live crypto prices & tickers\n"
            "• `/wallet <address>` — Multi-chain wallet balance & valuation (ETH/BTC/SOL)\n"
            "• `/gas` — Ethereum gas fee tracker (Etherscan)\n"
            "• `/wiki <topic>` — Wikipedia & books search\n"
            "• `/movie <title>` — Movie / TV ratings & plot (OMDb/TMDB)\n"
            "• `/holiday [country]` — Public holidays & festivals\n"
            "• `/image <query>` — Search HD photos (Unsplash/Pexels)\n"
            "• `/translate <text>` — Dictionary & translation\n"
            "• `/joke` — Random clean joke & inspirational quote\n"
            "• `/math <expression>` — WolframAlpha & SymPy solver\n"
            "• `/science` — NASA Astronomy Picture of the Day\n\n"
            "**💻 Developer, DB & MCP Supertools:**\n"
            "• `/screenshot <url>` — Live high-res website screenshot capture\n"
            "• `/py <code>` — Python code execution sandbox\n"
            "• `/sql <query>` — SQLite database query & table inspector\n"
            "• `/kg <add|list|search>` — Knowledge Graph & relational memory\n"
            "• `/social <url>` — Twitter/X, Reddit post content extractor\n"
            "• `/log [service]` — Inspect live server & bot logs\n"
            "• `/dns <domain>` — DNS records (A, MX, NS, TXT) lookup\n"
            "• `/http <url>` — HTTP status, response latency & headers\n"
            "• `/cron <expr>` — Translate cron syntax to plain English\n"
            "• `/json <text>` — Format, minify & validate JSON\n"
            "• `/ip [ip_address]` — Geo-IP location, ISP & ASN lookup\n"
            "• `/code <task>` — Delegate coding task via OpenCode server\n"
            "• `/github [repo]` — List GitHub repos, issues, and PRs\n\n"
            "**🔐 Privacy & Security:**\n"
            "• `/passgen [length]` — Cryptographically strong password generator\n"
            "• `/hash <text>` — MD5, SHA-1, SHA-256, Base64 converter\n"
            "• `/unshorten <url>` — Safe URL redirect expander\n"
            "• `/breach <email_or_pwd>` — Data breach check via XposedOrNot & HIBP\n"
            "• `/tempmail` — Generate disposable temporary email inbox\n"
            "• `/checkmail <login> <domain>` — Check OTP & incoming temporary emails\n\n"
            "**📊 Indian Markets & Wealth:**\n"
            "• `/stock <ticker>` — Live NSE/BSE & global stock quotes & day trend\n"
            "• `/nifty` & `/sensex` — Instant Indian index snapshots\n"
            "• `/gold` & `/silver` — Live 24K/22K 10g Gold & 1kg Silver bullion rates\n"
            "• `/fuel [city]` — Daily Petrol, Diesel & CNG prices\n\n"
            "**🚆 Travel & Indian Transit:**\n"
            "• `/pnr <10-digit PNR>` — IRCTC train booking & confirmation status\n"
            "• `/train <number_or_name>` — Indian Railways live schedule & NTES route\n"
            "• `/flight <flight_no>` — Live flight status, airline, and radar\n\n"
            "**📝 Smart Content & AI Summaries:**\n"
            "• `/youtube <url>` — YouTube video transcript & executive summary\n"
            "• `/summarize <url>` — Webpage / article instant markdown summary\n"
            "• `/briefing` — Consolidated morning briefing (Weather, News, Markets, Planner)\n\n"
            "**💰 Financial & Calculators:**\n"
            "• `/sip <monthly> <rate> <years>` — Mutual Fund SIP wealth compounding calculator\n"
            "• `/emi <loan> <rate> <years>` — Loan EMI, interest & amortization calculator\n"
            "• `/split <amount> <people>` — Restaurant bill & tip splitter\n"
            "• `/expense <amt> <cat> <desc>` — Log expense with analytics\n"
            "• `/expenses` — Monthly finance summary & breakdown\n"
            "• `/bill <name> <due> [amt]` — Add bill reminder alert\n\n"
            "**🏥 Health, Fitness & Writing:**\n"
            "• `/bmi <weight> <height>` — Body Mass Index & health category\n"
            "• `/calorie <food>` — Nutrition, protein, carbs & calorie profile\n"
            "• `/water [ml]` — Water hydration logging\n"
            "• `/grammar <text>` — Grammar, tone polish & rewriter\n"
            "• `/email <topic>` — Formal business & leave email drafter\n"
            "• `/synonym <word>` — Thesaurus, synonyms & antonyms\n\n"
            "**⏱️ Daily Productivity & Indian Services:**\n"
            "• `/qr <text_or_url>` — Generate HD QR code image\n"
            "• `/barcode <number>` — Generate Code128 barcode image\n"
            "• `/pincode <pin>` — India Post office & district lookup\n"
            "• `/ifsc <code>` — Bank branch & IFSC finder (Razorpay API)\n"
            "• `/shorten <url>` — Create short TinyURL link\n"
            "• `/remind <time> <msg>` — Time-based reminder scheduler\n"
            "• `/time <city>` — World clock & timezone converter\n"
            "• `/countdown <date>` — Event countdown tracker\n"
            "• `/traffic <from> to <to>` — Commute ETA & route\n"
            "• `/serverstatus` — EC2 CPU, RAM, Disk health\n"
            "• `/speedtest` — Internet speed test\n\n"
            "**🎮 Entertainment & Media:**\n"
            "• `/meme <top> | <bottom>` — Custom meme image generator\n"
            "• `/anime <title>` — MyAnimeList anime & manga ratings\n"
            "• `/recipe <dish>` — Cooking ingredients & instructions\n"
            "• `/riddle` — Fun brain teaser riddles\n"
            "• `/pick <opt1, opt2>` — Random decision maker & `/dice`, `/coinflip`\n\n"
            "**📁 Document Engines, Resumes & Formats:**\n"
            "• `/resume <role_or_skills>` — Professional ATS Resume generator (.pdf)\n"
            "• `/coverletter <company> <role>` — Formal Job Application Cover Letter (.pdf)\n"
            "• `/convert <format> <file>` — Convert image/doc format (PNG, JPG, WebP, PDF, TXT, Word)\n"
            "• `/pdf <title>` — Styled PDF document engine\n"
            "• `/excel <title>` — Styled Excel spreadsheet engine\n"
            "• `/doc <title>` — Styled Word (.docx) memo engine\n"
            "• `/gmail [query]` — Live Gmail reader\n"
            "• `/outlook` — Live Outlook email reader\n"
            "• `/drive [query]` — Google Drive search\n"
            "• `/calendar` — Google Calendar schedule\n\n"
            "💡 _Tip: You can tap the **[/] Menu** button next to your text bar to auto-complete any command!_"
        )
        return {"handled": True, "text": help_text}

    # 2. /weather <city>
    elif cmd == "/weather":
        city = args_str if args_str else "Malda, West Bengal, India"
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
        if args_str and (args_str.startswith(("0x", "1", "3", "bc1", "tb1")) or len(args_str) > 30):
            return {"handled": True, "text": apis.get_crypto_wallet_balance(args_str)}
        coins = args_str if args_str else "bitcoin,ethereum,solana,dogecoin"
        return {"handled": True, "text": apis.get_crypto_price(coins)}

    # 5b. /wallet <address> or /balance <address>
    elif cmd in ["/wallet", "/balance"]:
        if not args_str:
            return {"handled": True, "text": "Usage: `/wallet <crypto_address>`\nExample: `/wallet 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045` (ETH) or `/wallet 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa` (BTC)"}
        return {"handled": True, "text": apis.get_crypto_wallet_balance(args_str)}

    # 5c. /gas (Ethereum Gas Tracker)
    elif cmd in ["/gas", "/ethgas"]:
        return {"handled": True, "text": apis.get_etherscan_gas_price()}

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

    # 40. /dns <domain>
    elif cmd == "/dns":
        return {"handled": True, "text": ext.lookup_dns(args_str)}

    # 41. /http <url>
    elif cmd in ["/http", "/curl"]:
        return {"handled": True, "text": ext.test_http_endpoint(args_str)}

    # 42. /cron <expression>
    elif cmd == "/cron":
        return {"handled": True, "text": ext.explain_cron(args_str)}

    # 43. /json <raw_json>
    elif cmd == "/json":
        return {"handled": True, "text": ext.format_json(args_str)}

    # 44. /ip [ip_address]
    elif cmd == "/ip":
        return {"handled": True, "text": ext.lookup_ip(args_str)}

    # 45. /passgen [length]
    elif cmd in ["/passgen", "/password"]:
        l = int(args_str) if args_str.isdigit() else 16
        return {"handled": True, "text": ext.generate_password(l)}

    # 46. /hash <text>
    elif cmd == "/hash":
        return {"handled": True, "text": ext.calculate_hashes(args_str)}

    # 47. /unshorten <url>
    elif cmd == "/unshorten":
        return {"handled": True, "text": ext.unshorten_url(args_str)}

    # 48. /tempmail & /checkmail
    elif cmd in ["/tempmail", "/disposable"]:
        return {"handled": True, "text": ext.generate_tempmail()}
    elif cmd == "/checkmail":
        tokens = args_str.split()
        if len(tokens) >= 2:
            return {"handled": True, "text": ext.check_tempmail(tokens[0], tokens[1])}
        elif "@" in args_str:
            l, d = args_str.split("@", 1)
            return {"handled": True, "text": ext.check_tempmail(l, d)}
        return {"handled": True, "text": "Usage: `/checkmail <login> <domain>` or `/checkmail email@1secmail.com`"}

    # 49. /sip <monthly> <rate> <years>
    elif cmd == "/sip":
        tokens = args_str.split()
        if len(tokens) >= 3:
            try:
                return {"handled": True, "text": ext.calculate_sip(float(tokens[0]), float(tokens[1]), int(tokens[2]))}
            except ValueError:
                pass
        return {"handled": True, "text": "Usage: `/sip <monthly_amount> <expected_return_pct> <years>`\nExample: `/sip 5000 15 10`"}

    # 50. /emi <loan> <rate> <years>
    elif cmd == "/emi":
        tokens = args_str.split()
        if len(tokens) >= 3:
            try:
                return {"handled": True, "text": ext.calculate_emi(float(tokens[0]), float(tokens[1]), int(tokens[2]))}
            except ValueError:
                pass
        return {"handled": True, "text": "Usage: `/emi <loan_amount> <interest_rate_pct> <years>`\nExample: `/emi 500000 9.5 5`"}

    # 51. /split <amount> <people> [tip]
    elif cmd == "/split":
        tokens = args_str.split()
        if len(tokens) >= 2:
            try:
                amt = float(tokens[0])
                peop = int(tokens[1])
                tip = float(tokens[2]) if len(tokens) >= 3 else 0.0
                return {"handled": True, "text": ext.split_bill(amt, peop, tip)}
            except ValueError:
                pass
        return {"handled": True, "text": "Usage: `/split <total_amount> <number_of_people> [optional_tip_pct]`\nExample: `/split 1500 4 10`"}

    # 52. /bmi <weight_kg> <height_cm>
    elif cmd == "/bmi":
        tokens = args_str.split()
        if len(tokens) >= 2:
            try:
                return {"handled": True, "text": ext.calculate_bmi(float(tokens[0]), float(tokens[1]))}
            except ValueError:
                pass
        return {"handled": True, "text": "Usage: `/bmi <weight_in_kg> <height_in_cm>`\nExample: `/bmi 70 175`"}

    # 53. /calorie <food>
    elif cmd in ["/calorie", "/nutrition"]:
        return {"handled": True, "text": ext.lookup_calorie_nutrition(args_str)}

    # 54. /water [ml]
    elif cmd == "/water":
        ml = args_str if args_str else "250"
        return {"handled": True, "text": utils.record_habit_completion(user_id, f"Drank {ml}ml Water 💧")}

    # 55. /grammar <text>
    elif cmd in ["/grammar", "/fix"]:
        return {"handled": True, "text": ext.improve_grammar(args_str)}

    # 56. /email <topic>
    elif cmd == "/email":
        return {"handled": True, "text": ext.draft_email(args_str)}

    # 57. /synonym <word>
    elif cmd in ["/synonym", "/thesaurus"]:
        return {"handled": True, "text": ext.lookup_synonyms_thesaurus(args_str)}

    # 58. /time <city>
    elif cmd in ["/time", "/timezone"]:
        return {"handled": True, "text": ext.get_world_time(args_str)}

    # 59. /countdown <date>
    elif cmd == "/countdown":
        return {"handled": True, "text": ext.calculate_countdown(args_str)}

    # 60. /qr <text_or_url>
    elif cmd in ["/qr", "/qrcode"]:
        fpath = ext.generate_qr_code_file(args_str)
        return {"handled": True, "text": f"🏁 **QR Code Generated for:** `{args_str or 'Alya Bot'}`", "file_path": fpath, "file_type": "photo"}

    # 61. /barcode <code>
    elif cmd == "/barcode":
        fpath = ext.generate_barcode_file(args_str)
        return {"handled": True, "text": f"🏷️ **Barcode Generated for:** `{args_str or 'ALYA123'}`", "file_path": fpath, "file_type": "photo"}

    # 62. /meme <top> | <bottom>
    elif cmd == "/meme":
        parts_m = args_str.split("|")
        top_m = parts_m[0].strip() if len(parts_m) > 0 else "When Alya executes skills"
        bot_m = parts_m[1].strip() if len(parts_m) > 1 else "Zero Errors"
        meme_url = ext.generate_meme_url(top_m, bot_m)
        return {"handled": True, "text": f"🎭 **Generated Meme:**\n\n[View / Download Meme Image]({meme_url})"}

    # 63. /anime <title>
    elif cmd == "/anime":
        return {"handled": True, "text": ext.search_anime(args_str)}

    # 64. /riddle
    elif cmd == "/riddle":
        return {"handled": True, "text": ext.get_riddle()}

    # 65. /pick <options> | /dice | /coinflip
    elif cmd == "/pick":
        return {"handled": True, "text": ext.pick_random(args_str)}
    elif cmd in ["/dice", "/roll"]:
        return {"handled": True, "text": ext.pick_random("dice")}
    elif cmd in ["/coinflip", "/flip"]:
        return {"handled": True, "text": ext.pick_random("coin")}

    # 66. /recipe <dish>
    elif cmd in ["/recipe", "/cook"]:
        return {"handled": True, "text": ext.lookup_recipe(args_str)}

    # 67. /pincode <pin>
    elif cmd in ["/pincode", "/pin", "/postal"]:
        return {"handled": True, "text": ext.lookup_pincode(args_str)}

    # 68. /ifsc <code>
    elif cmd in ["/ifsc", "/bank"]:
        return {"handled": True, "text": ext.lookup_ifsc(args_str)}

    # 69. /shorten <url>
    elif cmd == "/shorten":
        return {"handled": True, "text": ext.shorten_url(args_str)}

    # 70. /stock <symbol> or /nifty or /sensex
    elif cmd in ["/stock", "/stocks"]:
        return {"handled": True, "text": markets.get_stock_quote(args_str)}
    elif cmd in ["/nifty", "/nifty50"]:
        return {"handled": True, "text": markets.get_stock_quote("NIFTY")}
    elif cmd in ["/sensex", "/bse"]:
        return {"handled": True, "text": markets.get_stock_quote("SENSEX")}

    # 71. /gold or /silver or /metals
    elif cmd in ["/gold", "/silver", "/metals", "/bullion"]:
        return {"handled": True, "text": markets.get_gold_silver_rates()}

    # 72. /fuel [city] or /petrol or /diesel
    elif cmd in ["/fuel", "/petrol", "/diesel"]:
        return {"handled": True, "text": markets.get_fuel_rates(args_str or "Malda")}

    # 73. /pnr <10-digit PNR>
    elif cmd == "/pnr":
        return {"handled": True, "text": markets.get_train_pnr_status(args_str)}

    # 74. /train <train_number_or_name>
    elif cmd in ["/train", "/railway"]:
        return {"handled": True, "text": markets.get_train_live_status(args_str)}

    # 75. /flight <flight_code>
    elif cmd in ["/flight", "/radar"]:
        return {"handled": True, "text": markets.get_flight_status(args_str)}

    # 76. /youtube <url> or /yt <url>
    elif cmd in ["/youtube", "/yt"]:
        return {"handled": True, "text": content.summarize_youtube_video(args_str)}

    # 77. /summarize <url> or /article <url>
    elif cmd in ["/summarize", "/article", "/webpage"]:
        return {"handled": True, "text": content.summarize_webpage(args_str)}

    # 78. /briefing or /morning
    elif cmd in ["/briefing", "/morning"]:
        return {"handled": True, "text": content.get_daily_briefing(user_id, args_str or "Malda")}

    # 79. /screenshot <url>
    elif cmd in ["/screenshot", "/webshot", "/capture"]:
        res_s = dev.capture_website_screenshot(args_str)
        if res_s.get("success"):
            return {"handled": True, "text": res_s.get("text", ""), "file_path": res_s.get("file_path"), "file_type": "photo"}
        return {"handled": True, "text": res_s.get("error", "⚠️ Screenshot failed.")}

    # 80. /py <code> or /python or /run
    elif cmd in ["/py", "/python", "/run", "/exec"]:
        return {"handled": True, "text": dev.run_python_code_sandbox(args_str)}

    # 81. /sql <query> or /db
    elif cmd in ["/sql", "/db", "/database"]:
        return {"handled": True, "text": dev.query_sqlite_database(args_str, user_id)}

    # 82. /kg <action> [args] or /memory
    elif cmd in ["/kg", "/knowledge", "/relations"]:
        parts_k = args_str.split(maxsplit=3)
        act_k = parts_k[0] if len(parts_k) > 0 else "list"
        e_k = parts_k[1] if len(parts_k) > 1 else ""
        r_k = parts_k[2] if len(parts_k) > 2 else ""
        t_k = parts_k[3] if len(parts_k) > 3 else ""
        return {"handled": True, "text": dev.manage_knowledge_graph(act_k, e_k, r_k, t_k, user_id)}

    # 83. /social <url> or /tweet
    elif cmd in ["/social", "/tweet", "/post"]:
        return {"handled": True, "text": dev.extract_social_media_info(args_str)}

    # 84. /invoice <text_or_ocr>
    elif cmd in ["/invoice", "/billtoexcel"]:
        res_i = dev.convert_receipt_to_excel(args_str, user_id)
        if res_i.get("success"):
            return {"handled": True, "text": res_i.get("text", ""), "file_path": res_i.get("file_path"), "file_type": "document"}
        return {"handled": True, "text": res_i.get("text", "⚠️ Invoice conversion completed.")}

    # 85. /log [service] or /logs
    elif cmd in ["/log", "/logs", "/syslog"]:
        return {"handled": True, "text": dev.view_server_logs(args_str or "rasa-bot", 15)}

    # 86. /resume <role_or_skills> or /cv
    elif cmd in ["/resume", "/cv", "/buildresume"]:
        res_r = conv.generate_resume_pdf(args_str, "Professional Candidate")
        if res_r.get("success"):
            return {"handled": True, "text": res_r.get("text", ""), "file_path": res_r.get("file_path"), "file_type": "document"}
        return {"handled": True, "text": res_r.get("error", "⚠️ Resume generation failed.")}

    # 87. /coverletter <company> <role>
    elif cmd in ["/coverletter", "/cl"]:
        res_cl = conv.generate_cover_letter_pdf(args_str, "Professional Candidate")
        if res_cl.get("success"):
            return {"handled": True, "text": res_cl.get("text", ""), "file_path": res_cl.get("file_path"), "file_type": "document"}
        return {"handled": True, "text": res_cl.get("error", "⚠️ Cover letter generation failed.")}

    # 88. /convert <format>
    elif cmd in ["/convert", "/format"]:
        parts_c = args_str.split(maxsplit=1)
        fmt = parts_c[0] if len(parts_c) > 0 else "png"
        src_path = parts_c[1].strip() if len(parts_c) > 1 else ""
        if not src_path:
            return {"handled": True, "text": "Usage: `/convert <target_format> <filepath_or_url>`\nExample: `/convert png /path/to/image.webp` or `/convert pdf /path/to/doc.txt`"}
        if src_path.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            res_c = conv.convert_image_file(src_path, fmt)
        else:
            res_c = conv.convert_document_file(src_path, fmt)

        if res_c.get("success"):
            return {"handled": True, "text": res_c.get("text", ""), "file_path": res_c.get("file_path"), "file_type": res_c.get("file_type", "document")}
        return {"handled": True, "text": res_c.get("error", "⚠️ File conversion failed.")}

    # 89. /speak <text> or /tts
    elif cmd in ["/speak", "/tts", "/voice"]:
        res_v = mob.generate_voice_speech(args_str, "hi")
        if res_v.get("success"):
            return {"handled": True, "text": res_v.get("text", ""), "file_path": res_v.get("file_path"), "file_type": "voice"}
        return {"handled": True, "text": res_v.get("error", "⚠️ Voice speech failed.")}

    # 90. /notify <title> | <message>
    elif cmd in ["/notify", "/alert", "/push"]:
        parts_n = args_str.split("|", maxsplit=1)
        t_n = parts_n[0].strip() if len(parts_n) > 0 else "Alya Alert"
        m_n = parts_n[1].strip() if len(parts_n) > 1 else args_str
        return {"handled": True, "text": mob.send_phone_push_notification(t_n, m_n, "high")}

    # 91. /findmyphone or /ringphone
    elif cmd in ["/findmyphone", "/ringphone", "/ring"]:
        return {"handled": True, "text": mob.find_and_ring_phone(user_id)}

    # 92. /clip <text> or /copy
    elif cmd in ["/clip", "/copy"]:
        return {"handled": True, "text": mob.sync_clipboard_to_phone(args_str)}

    # 93. /whatsapp <number> <message> or /wa
    elif cmd in ["/whatsapp", "/wa"]:
        parts_w = args_str.split(maxsplit=1)
        p_w = parts_w[0] if len(parts_w) > 0 else ""
        m_w = parts_w[1] if len(parts_w) > 1 else "Hello from Alya!"
        return {"handled": True, "text": mob.create_whatsapp_dispatch(p_w, m_w)}

    # 94. /skills or /directory
    elif cmd in ["/skills", "/directory", "/allskills"]:
        return {"handled": True, "text": mob.get_full_skills_directory()}

    # 95. /call <number>
    elif cmd in ["/call", "/dial", "/phonecall"]:
        return {"handled": True, "text": android.make_phone_call(args_str)}

    # 96. /sms <number> <message>
    elif cmd in ["/sms", "/sendtext"]:
        parts_s = args_str.split(maxsplit=1)
        p_s = parts_s[0] if len(parts_s) > 0 else ""
        m_s = parts_s[1] if len(parts_s) > 1 else "Hello from Alya!"
        return {"handled": True, "text": android.send_phone_sms(p_s, m_s)}

    # 97. /readsms [limit]
    elif cmd in ["/readsms", "/inboxsms"]:
        try:
            lim = int(args_str.strip())
        except Exception:
            lim = 5
        return {"handled": True, "text": android.read_recent_phone_sms(lim)}

    # 98. /alarm <time> [label]
    elif cmd in ["/alarm", "/setalarm"]:
        parts_a = args_str.split(maxsplit=1)
        t_a = parts_a[0] if len(parts_a) > 0 else "07:00 AM"
        l_a = parts_a[1] if len(parts_a) > 1 else "Alya Alarm"
        return {"handled": True, "text": android.set_phone_alarm(t_a, l_a)}

    # 99. /timer <duration> [label]
    elif cmd in ["/timer", "/settimer"]:
        parts_tm = args_str.split(maxsplit=1)
        d_tm = parts_tm[0] if len(parts_tm) > 0 else "5 minutes"
        l_tm = parts_tm[1] if len(parts_tm) > 1 else "Timer"
        return {"handled": True, "text": android.set_phone_timer(d_tm, l_tm)}

    # 100. /open <target>
    elif cmd in ["/open", "/launch", "/app"]:
        return {"handled": True, "text": android.open_file_or_app_on_phone(args_str)}

    # 101. /callscreen <caller_statement>
    elif cmd in ["/callscreen", "/screen", "/voicemail"]:
        return {"handled": True, "text": android.screen_incoming_call_message("Unknown Caller", args_str)}

    # 102. /upi <vpa> [amount] [name] [note]
    elif cmd in ["/upi", "/payqr", "/upiqr"]:
        if not args_str:
            return {
                "handled": True,
                "text": (
                    "**Usage:** `/upi <vpa_id> [amount] [name] [note]`\n"
                    "**Example:** `/upi 9876543210@paytm 500 \"Md Faijal\" \"Dinner\"`\n"
                    "**Or simple:** `/upi faijal@okaxis`"
                )
            }
        try:
            toks = shlex.split(args_str)
        except Exception:
            toks = args_str.split()

        vpa_id = toks[0]
        amt_val = None
        p_name = None
        p_note = None

        if len(toks) > 1:
            try:
                amt_val = float(toks[1])
            except ValueError:
                p_name = toks[1]
        if len(toks) > 2:
            if p_name is None:
                p_name = toks[2]
            else:
                p_note = toks[2]
        if len(toks) > 3:
            p_note = toks[3]

        return adv.generate_upi_qr(vpa=vpa_id, amount=amt_val, payee_name=p_name, note=p_note)

    # 103. /search <query>
    elif cmd in ["/search", "/google", "/websearch"]:
        if not args_str:
            return {"handled": True, "text": "Usage: `/search <query>`\nExample: `/search latest tech news 2026`"}
        return {"handled": True, "text": adv.search_live_web(args_str)}

    # 104. /transcribe [url_or_path]
    elif cmd in ["/transcribe", "/stt", "/voicetotext", "/audio"]:
        if not args_str:
            return {"handled": True, "text": "Usage: `/transcribe <audio_url_or_path>`\nExample: `/transcribe https://example.com/sample.mp3` or send a voice message directly in chat!"}
        return {"handled": True, "text": adv.transcribe_audio(args_str)}

    # 105. /med <medicine> or /medicine <medicine>
    elif cmd in ["/med", "/medicine", "/dawa", "/drug"]:
        if not args_str:
            return {"handled": True, "text": "Usage: `/med <medicine_name>`\nExample: `/med Dolo 650` or `/med Augmentin 625`"}
        return {"handled": True, "text": adv.lookup_medicine_info(args_str)}

    # 106. /ssl <domain>
    elif cmd in ["/ssl", "/tls", "/cert", "/certificate"]:
        if not args_str:
            return {"handled": True, "text": "Usage: `/ssl <domain>`\nExample: `/ssl google.com` or `/ssl github.com`"}
        return {"handled": True, "text": adv.inspect_ssl_certificate(args_str)}

    # 107. /whois <domain>
    elif cmd in ["/whois", "/rdap", "/domain"]:
        if not args_str:
            return {"handled": True, "text": "Usage: `/whois <domain>`\nExample: `/whois github.com` or `/whois openai.com`"}
        return {"handled": True, "text": adv.inspect_domain_whois(args_str)}

    # 108. /ocr [url_or_path]
    elif cmd in ["/ocr", "/extracttext", "/readimage"]:
        if not args_str:
            return {"handled": True, "text": "Usage: `/ocr <image_url_or_path>`\nExample: `/ocr https://example.com/receipt.png` or send a photo directly in chat!"}
        return {"handled": True, "text": adv.extract_ocr_text(args_str)}

    return {"handled": False}
