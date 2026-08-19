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
from . import skills_super_pack as superpack
from . import mcp_client as mcp
try:
    from addons.image_tools import slash_bridge as img_bridge
except ImportError:
    img_bridge = None


logger = logging.getLogger(__name__)

import time
import threading

_LAST_USER_MEDIA: Dict[str, Dict[str, Any]] = {}
_LAST_USER_MEDIA_LOCK = threading.Lock()
MEDIA_CACHE_TTL_SECONDS = 3600  # 1 hour TTL


def set_last_user_media(user_id: str, file_path: str) -> None:
    """Caches the most recently uploaded user media file for subsequent commands with user isolation and TTL."""
    if not user_id or not file_path:
        return
    norm_path = os.path.abspath(file_path)
    if not os.path.exists(norm_path):
        return

    with _LAST_USER_MEDIA_LOCK:
        now = time.time()
        # Clean expired entries
        expired = [uid for uid, rec in _LAST_USER_MEDIA.items() if now - rec.get("ts", 0) > MEDIA_CACHE_TTL_SECONDS]
        for exp_uid in expired:
            _LAST_USER_MEDIA.pop(exp_uid, None)

        _LAST_USER_MEDIA[str(user_id)] = {
            "path": norm_path,
            "ts": now
        }


def get_last_user_media(user_id: str) -> Optional[str]:
    """Retrieves cached media file strictly scoped to user_id if valid and not expired."""
    if not user_id:
        return None
    with _LAST_USER_MEDIA_LOCK:
        rec = _LAST_USER_MEDIA.get(str(user_id))
        if not rec:
            return None
        if time.time() - rec.get("ts", 0) > MEDIA_CACHE_TTL_SECONDS:
            _LAST_USER_MEDIA.pop(str(user_id), None)
            return None
        fpath = rec.get("path")
        if fpath and os.path.exists(fpath):
            return fpath
        else:
            _LAST_USER_MEDIA.pop(str(user_id), None)
            return None


def handle_slash_command(
    command_text: str,
    user_id: str,
    chat_id: str,
    attachment_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Directly processes Telegram slash commands with deterministic argument parsing.
    Returns a dict with:
      - 'handled': bool
      - 'text': str (Markdown response)
      - 'file_path': Optional[str] (Local file to send, e.g. PDF/Excel/Word)
      - 'file_type': str ('document' / 'photo' / 'audio')
    """
    clean_text = command_text.strip()
    if not clean_text.startswith("/"):
        return {"handled": False}

    if attachment_path and os.path.exists(attachment_path):
        set_last_user_media(user_id, attachment_path)

    parts = clean_text.split(maxsplit=1)
    raw_cmd = parts[0].lower()
    # Strip bot username if attached, e.g. /compress@Alya_Rasa_Bot -> /compress
    cmd = raw_cmd.split("@")[0]
    args_str = parts[1].strip() if len(parts) > 1 else ""

    logger.info(f"Processing slash command: {cmd} with args '{args_str}' for user {user_id} (attachment: {attachment_path})")

    # 1. /help or /start or /menu
    if cmd in ["/start", "/help", "/commands", "/menu", "/allcommands"]:
        from . import command_registry as reg
        return {"handled": True, "text": reg.generate_help_text(user_id=str(user_id))}


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
    elif cmd in ["/remind", "/reminder", "/setreminder"]:
        if not args_str.strip():
            return {
                "handled": True,
                "text": (
                    "⏰ **Alya Timezone-Aware Reminder Scheduler**\n\n"
                    "**Usage:** `/remind <time> <message>`\n"
                    "**Examples:**\n"
                    "• `/remind 11:00 AM Call Rahul`\n"
                    "• `/remind at 11 AM Buy groceries`\n"
                    "• `/remind tomorrow at 9 AM Team Standup meeting`\n"
                    "• `/remind in 2 hours Take medicine`\n"
                    "• `/remind in 15 mins Check oven`\n"
                    "• `/remind 11 AM EST US client sync call`\n"
                    "• `/remind every day at 9 AM Morning workout`\n\n"
                    "💡 *Default Timezone: Asia/Kolkata (IST). Change via `/set_timezone <tz>`*"
                )
            }
        from .timezone_utils import split_reminder_command
        time_part, msg_part = split_reminder_command(args_str)
        res = utils.create_reminder(user_id, chat_id, msg_part, time_part)
        return {"handled": True, "text": res}

    # 17b. /reminders, /myreminders (List user reminders)
    elif cmd in ["/reminders", "/myreminders", "/listreminders", "/active_reminders"]:
        return {"handled": True, "text": utils.list_user_reminders(user_id)}

    # 17c. /delremind <id>, /cancelreminder <id>
    elif cmd in ["/delremind", "/delreminder", "/cancelreminder", "/rmremind"]:
        if not args_str.strip() or not args_str.strip().isdigit():
            return {"handled": True, "text": "Usage: `/delremind <reminder_id>` (e.g. `/delremind 1`)\nUse `/reminders` to check IDs."}
        return {"handled": True, "text": utils.delete_user_reminder(user_id, int(args_str.strip()))}

    # 17d. /set_timezone <tz> or /mytimezone
    elif cmd in ["/set_timezone", "/settimezone", "/mytimezone"]:
        return {"handled": True, "text": utils.set_user_timezone_preference(user_id, args_str)}

    # 18. /medremind <time> <medicine>
    elif cmd == "/medremind":
        if not args_str.strip():
            return {"handled": True, "text": "Usage: `/medremind <time> <medicine_name>`\nExample: `/medremind 9:00 AM Paracetamol 500mg`"}
        from .timezone_utils import split_reminder_command
        time_part, med_part = split_reminder_command(args_str)
        res = utils.add_medicine_schedule(user_id, name=med_part, dosage="1 dose", schedule_time=time_part)
        return {"handled": True, "text": res}


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

    # 36. /code, /sh, /exec, /bash, /terminal <command or task>
    elif cmd in ["/code", "/sh", "/exec", "/bash", "/terminal", "/run"]:
        if not args_str:
            return {
                "handled": True,
                "text": "Usage: `/code <command or task>` (e.g. `/code ls -la`, `/code pwd`, `/code git status`)\nOr direct shell: `/sh ls -la`"
            }
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
        target_file = None
        if args_str and (os.path.exists(args_str.split()[0]) or args_str.startswith("http")):
            target_file = args_str.split()[0]
        elif attachment_path and os.path.exists(attachment_path):
            target_file = attachment_path
        else:
            target_file = get_last_user_media(user_id)

        if not target_file:
            return {"handled": True, "text": "Usage: `/transcribe <audio_url_or_path>`\nExample: `/transcribe https://example.com/sample.mp3` or send a voice message with `/transcribe` caption!"}
        return {"handled": True, "text": adv.transcribe_audio(target_file)}

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
        target_file = None
        if args_str and (os.path.exists(args_str.split()[0]) or args_str.startswith("http")):
            target_file = args_str.split()[0]
        elif attachment_path and os.path.exists(attachment_path):
            target_file = attachment_path
        else:
            target_file = get_last_user_media(user_id)

        if not target_file:
            return {"handled": True, "text": "Usage: `/ocr <image_url_or_path>`\nExample: `/ocr https://example.com/receipt.png` or send a photo with `/ocr` caption!"}
        return {"handled": True, "text": adv.extract_ocr_text(target_file)}

    # 109. /today or /history
    elif cmd in ["/today", "/history", "/onthisday", "/dayinhistory"]:
        return {"handled": True, "text": ext.get_today_in_history(args_str)}

    # 110. /pan <pan_number>
    elif cmd in ["/pan", "/pancard", "/checkpan"]:
        return {"handled": True, "text": ext.validate_pan_card(args_str)}

    # 111. /gstin <gstin_number> or /gst <gstin_number>
    elif cmd in ["/gstin", "/gst", "/checkgst"]:
        return {"handled": True, "text": ext.validate_gstin(args_str)}

    # 112. /unit <query> or /convertunit
    elif cmd in ["/unit", "/convertunit", "/units", "/areaconvert"]:
        return {"handled": True, "text": ext.convert_universal_unit(args_str)}

    # 113. /horoscope <sign> or /zodiac <sign> or /rashi
    elif cmd in ["/horoscope", "/zodiac", "/rashi", "/kundali", "/astrology"]:
        return {"handled": True, "text": ext.get_daily_horoscope(args_str)}

    # 114. /hackernews or /hn or /trending
    elif cmd in ["/hackernews", "/hn", "/technews", "/techheadlines"]:
        return {"handled": True, "text": ext.get_tech_hackernews_digest()}

    # 115. /slang <term> or /idiom <term>
    elif cmd in ["/slang", "/idiom", "/phrase", "/jargon", "/slangmeaning"]:
        return {"handled": True, "text": ext.lookup_slang_or_idiom(args_str)}

    # 116. /adduser <user_id> [name] (Admin only)
    elif cmd in ["/adduser", "/authuser", "/grantuser", "/allowuser"]:
        if not db.is_admin_user(str(user_id)):
            return {"handled": True, "text": "⚠️ **Access Denied:** Only bot administrators can grant user access."}

        if not args_str:
            return {
                "handled": True,
                "text": (
                    "👤 **Add Authorized User Usage:**\n"
                    "• `/adduser <numeric_telegram_user_id> [name_or_note]`\n\n"
                    "**Examples:**\n"
                    "• `/adduser 123456789 John`\n"
                    "• `/adduser 987654321`\n\n"
                    "_Tip: Forward any message from the user to @userinfobot or check server logs to get their numeric ID._"
                )
            }

        parts = args_str.split(maxsplit=1)
        target_uid = parts[0].strip()
        target_name = parts[1].strip() if len(parts) > 1 else ""

        if not target_uid.isdigit():
            return {
                "handled": True,
                "text": "❌ **Invalid User ID:** Telegram user ID must be numeric (e.g. `123456789`)."
            }

        success = db.add_authorized_user(target_uid, name=target_name, added_by=str(user_id))
        if success:
            label = f" ({target_name})" if target_name else ""
            return {
                "handled": True,
                "text": f"✅ **User Authorized!**\nTelegram User ID `{target_uid}`{label} ab bot use kar sakta hai."
            }
        else:
            return {"handled": True, "text": "❌ Failed to authorize user. Check server logs."}

    # 120. /removeuser <user_id> (Admin only)
    elif cmd in ["/removeuser", "/deluser", "/deleteuser", "/revokeuser"]:
        if not db.is_admin_user(str(user_id)):
            return {"handled": True, "text": "⚠️ **Access Denied:** Only bot administrators can revoke user access."}

        if not args_str:
            return {
                "handled": True,
                "text": (
                    "🚫 **Remove Authorized User Usage:**\n"
                    "• `/removeuser <numeric_telegram_user_id>`\n\n"
                    "**Example:** `/removeuser 123456789`"
                )
            }

        target_uid = args_str.split()[0].strip()
        admin_ids = db.get_admin_user_ids()
        if target_uid in admin_ids:
            return {
                "handled": True,
                "text": f"⚠️ Cannot remove primary administrator `{target_uid}` configured in environment variables."
            }

        removed = db.remove_authorized_user(target_uid)
        if removed:
            return {
                "handled": True,
                "text": f"✅ **Access Revoked!**\nUser `{target_uid}` ko authorized list se remove kar diya gaya hai."
            }
        else:
            return {
                "handled": True,
                "text": f"⚠️ User `{target_uid}` authorized list me nahi mila. Use `/users` to list current users."
            }

    # 121. /users or /listusers (Admin only)
    elif cmd in ["/users", "/listusers", "/authusers", "/allowedusers"]:
        if not db.is_admin_user(str(user_id)):
            return {"handled": True, "text": "⚠️ **Access Denied:** Only bot administrators can view the user directory."}

        admins = db.get_admin_user_ids()
        db_users = db.get_authorized_users()

        lines = ["👥 **Alya Bot — Authorized Users Directory:**\n"]
        lines.append("**👑 Primary Administrators (.env):**")
        if admins:
            for a in admins:
                lines.append(f"• `{a}` *(Superadmin)*")
        else:
            lines.append("• _Open access (No restriction configured)_")

        lines.append("\n**👤 Dynamically Authorized Users (SQLite DB):**")
        if db_users:
            for u in db_users:
                uname = f" — *{u.get('name')}*" if u.get('name') else ""
                lines.append(f"• `{u.get('user_id')}`{uname} (Added by `{u.get('added_by')}` on {str(u.get('created_at'))[:16]})")
        else:
            lines.append("• _No additional users added yet. Use `/adduser <id>` to grant access._")

        return {"handled": True, "text": "\n".join(lines)}

    # 122. /voice <text> or /tts <text> (Realistic Neural Voice Note)
    elif cmd in ["/voice", "/tts", "/audio", "/voicenote"]:
        if not args_str:
            return {"handled": True, "text": "🎙️ **Voice Note Usage:** `/voice <text>` (e.g. `/voice Namaste! Alya bot me aapka swagat hai.`)"}
        success, fpath, msg = superpack.generate_voice_note(args_str)
        if success and fpath:
            return {"handled": True, "text": msg, "file_path": fpath, "file_type": "audio"}
        else:
            return {"handled": True, "text": msg}

    # 123. /aqi [city] (Air Quality Index)
    elif cmd in ["/aqi", "/airquality", "/pollution"]:
        city = args_str if args_str else "Malda"
        return {"handled": True, "text": superpack.get_air_quality_index(city)}

    # 124. /exif [url_or_file] (Photo EXIF Inspector)
    elif cmd in ["/exif", "/metadata", "/photoinfo"]:
        target_file = None
        if args_str and (os.path.exists(args_str.split()[0]) or args_str.startswith("http")):
            target_file = args_str.split()[0]
        elif attachment_path and os.path.exists(attachment_path):
            target_file = attachment_path
        else:
            target_file = get_last_user_media(user_id)

        if not target_file:
            return {"handled": True, "text": "📷 **EXIF Inspector Usage:** `/exif <image_url_or_file>` (Inspects camera, lens & GPS location)"}
        success, text, _ = superpack.inspect_or_strip_image_exif(target_file, strip_exif=False)
        return {"handled": True, "text": text}

    # 125. /strip_exif [url_or_file] (Remove GPS/EXIF Privacy Stripper)
    elif cmd in ["/strip_exif", "/stripexif", "/cleanphoto"]:
        target_file = None
        if args_str and (os.path.exists(args_str.split()[0]) or args_str.startswith("http")):
            target_file = args_str.split()[0]
        elif attachment_path and os.path.exists(attachment_path):
            target_file = attachment_path
        else:
            target_file = get_last_user_media(user_id)

        if not target_file:
            return {"handled": True, "text": "🛡️ **Privacy EXIF Stripper Usage:** `/strip_exif <image_url_or_file>` (Removes all location & camera tags)"}
        success, text, out_file = superpack.inspect_or_strip_image_exif(target_file, strip_exif=True)
        if success and out_file:
            return {"handled": True, "text": text, "file_path": out_file, "file_type": "photo"}
        return {"handled": True, "text": text}

    # 126. /ipo (Indian IPO Calendar & GMP)
    elif cmd in ["/ipo", "/ipogmp", "/ipos"]:
        return {"handled": True, "text": superpack.get_live_ipo_data()}

    # 127. /phish <url> or /safelink <url> (Anti-Phishing Scanner)
    elif cmd in ["/phish", "/safelink", "/urlcheck", "/scanlink"]:
        if not args_str:
            return {"handled": True, "text": "🛡️ **Anti-Phishing Scanner Usage:** `/phish <url>` (e.g. `/phish https://example.com`)"}
        return {"handled": True, "text": superpack.scan_url_phishing_security(args_str)}

    # 128. /compress <file_path> (Media & Document Compressor)
    elif cmd in ["/compress", "/reduce", "/shrink"]:
        target_file = None
        if args_str:
            target_file = args_str.split()[0]
        elif attachment_path and os.path.exists(attachment_path):
            target_file = attachment_path
        else:
            target_file = get_last_user_media(user_id)

        if not target_file:
            return {
                "handled": True,
                "text": "🗜️ **Compressor Usage:** `/compress <file_path>` (or upload a photo/PDF with `/compress` caption)\nSupports JPG, PNG, WebP, PDF."
            }
        success, text, out_f = superpack.compress_media_file(target_file)
        if success and out_f:
            ftype = "photo" if out_f.endswith((".jpg", ".png", ".webp")) else "document"
            return {"handled": True, "text": text, "file_path": out_f, "file_type": ftype}
        return {"handled": True, "text": text}

    # Image Tools Module Slash Commands
    elif cmd in ["/imagetools", "/imagehelp", "/phototools", "/presets", "/imagepresets", "/passport", "/visa"]:
        if cmd in ["/passport", "/visa"]:
            parts = args_str.split()
            target_file = None
            preset_choice = "india"

            if parts and os.path.exists(parts[0]):
                target_file = parts[0]
                preset_choice = parts[1].lower() if len(parts) > 1 else "india"
            elif parts and not os.path.exists(parts[0]):
                preset_choice = parts[0].lower()
                target_file = attachment_path or get_last_user_media(user_id)
            else:
                target_file = attachment_path or get_last_user_media(user_id)

            if not target_file:
                return {
                    "handled": True,
                    "text": "🪪 **Passport & Visa Photo Maker Usage:** `/passport <file_path> [india|us|uk|schengen]`\n_Tip: You can also send a photo with caption `/passport india`!_"
                }

            if img_bridge:
                handled, text, out_f, ftype = img_bridge.handle_image_tool_command(cmd, f"{target_file} {preset_choice}")
                if handled:
                    if out_f:
                        return {"handled": True, "text": text, "file_path": out_f, "file_type": ftype}
                    return {"handled": True, "text": text}
        else:
            if img_bridge:
                handled, text, out_f, ftype = img_bridge.handle_image_tool_command(cmd, args_str)
                if handled:
                    if out_f:
                        return {"handled": True, "text": text, "file_path": out_f, "file_type": ftype}
                    return {"handled": True, "text": text}


    # 129. /postoffice <pincode_or_area> (India Post Branch Finder)
    elif cmd in ["/postoffice", "/dak", "/postbranches"]:
        if not args_str:
            return {"handled": True, "text": "📮 **India Post Finder Usage:** `/postoffice <6-digit PIN or Area Name>` (e.g. `/postoffice 732101` or `/postoffice Kolkata`)"}
        return {"handled": True, "text": superpack.get_post_office_branches(args_str)}

    # 130. /ping <host> (Server & Latency Ping)
    elif cmd in ["/ping", "/latency", "/hostping"]:
        if not args_str:
            return {"handled": True, "text": "🏓 **Host Ping Usage:** `/ping <domain_or_ip>` (e.g. `/ping google.com`)"}
        return {"handled": True, "text": superpack.ping_server_health(args_str)}

    # 131. /wayback <url> (Internet Archive Time Machine)
    elif cmd in ["/wayback", "/archive", "/timemachine", "/oldweb"]:
        if not args_str:
            return {"handled": True, "text": "🌐 **Wayback Machine Usage:** `/wayback <url>` (e.g. `/wayback https://apple.com`)"}
        return {"handled": True, "text": superpack.get_wayback_snapshots(args_str)}

    # 132. /mergepdf <file1> <file2> (Merge PDF files)
    elif cmd in ["/mergepdf", "/pdfmerge", "/combinepdf"]:
        paths = args_str.split()
        if len(paths) < 2:
            return {"handled": True, "text": "📄 **Merge PDF Usage:** `/mergepdf <file1.pdf> <file2.pdf> ...`"}
        success, msg, out_f = superpack.merge_pdf_documents(paths)
        if success and out_f:
            return {"handled": True, "text": msg, "file_path": out_f, "file_type": "document"}
        return {"handled": True, "text": msg}

    # 133. /splitpdf <file> <start> <end> (Extract PDF pages)
    elif cmd in ["/splitpdf", "/pdfsplit", "/extractpdf"]:
        tokens = args_str.split()
        if len(tokens) < 3:
            return {"handled": True, "text": "📄 **Split PDF Usage:** `/splitpdf <file_path> <start_page> <end_page>` (e.g. `/splitpdf doc.pdf 1 5`)"}
        try:
            sp = int(tokens[1])
            ep = int(tokens[2])
            success, msg, out_f = superpack.split_pdf_document(tokens[0], sp, ep)
            if success and out_f:
                return {"handled": True, "text": msg, "file_path": out_f, "file_type": "document"}
            return {"handled": True, "text": msg}
        except ValueError:
            return {"handled": True, "text": "❌ Page numbers must be integers (e.g. `/splitpdf doc.pdf 1 5`)."}

    # 134. /compare <item1> vs <item2> (AI Product / Tech Comparator)
    elif cmd in ["/compare", "/vs", "/diff", "/difference"]:
        if not args_str:
            return {"handled": True, "text": "⚔️ **AI Comparison Usage:** `/compare <Item1> vs <Item2>` (e.g. `/compare iPhone 15 vs S24` or `/compare Python vs Rust`)"}
        return {"handled": True, "text": superpack.compare_items_ai(args_str)}

    # 135. /solve <question_or_photo> (Universal AI Question & Exam Problem Solver)
    elif cmd in ["/solve", "/ask", "/answer", "/mathsolve", "/homework", "/doubt"]:
        resolved_img: Optional[str] = None
        resolved_text = args_str.strip() if args_str else ""

        # 1. Direct attachment provided in request
        if attachment_path and os.path.exists(attachment_path):
            resolved_img = attachment_path

        # 2. Check if args_str starts with an image file path or URL
        if not resolved_img and resolved_text:
            parts = resolved_text.split(maxsplit=1)
            first_tok = parts[0].strip()
            if first_tok.startswith(("http://", "https://")) or os.path.exists(first_tok) or first_tok.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                resolved_img = first_tok
                resolved_text = parts[1].strip() if len(parts) > 1 else ""

        # 3. Check cached user media (for recent photo uploads)
        if not resolved_img and user_id:
            cached = get_last_user_media(user_id)
            if cached and os.path.exists(cached):
                resolved_img = cached

        if not resolved_img and not resolved_text:
            return {
                "handled": True,
                "text": "🎓 **Universal AI Problem Solver Usage:**\n• `/solve <question text>`\n• `/solve <image_url_or_file>`\n_Or send a photo of any math, physics, coding or exam question directly in chat!_"
            }

        return {
            "handled": True,
            "text": superpack.solve_question_or_problem(
                query_or_file_path=resolved_text or resolved_img or "",
                image_path=resolved_img,
                caption=resolved_text
            )
        }


    # Fallback for unrecognized slash commands
    clean_cmd_name = cmd.lstrip("/")
    return {
        "handled": True,
        "text": f"❓ **Unknown Command:** `/{clean_cmd_name}` is not recognized.\nUse `/help` or `/menu` to see all available commands."
    }
