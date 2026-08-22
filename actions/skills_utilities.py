import os
import re
import time
import json
import logging
import psutil
from datetime import datetime, date, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
import requests

from . import db
from .timezone_utils import (
    DEFAULT_TIMEZONE,
    resolve_timezone,
    parse_natural_datetime,
    to_utc_iso,
    from_utc_iso_to_user_tz,
    get_timezone_abbreviation,
    split_reminder_command,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 20. Reminders (Timezone-aware, IST default, single-execution)
# ---------------------------------------------------------------------------

_REMIND_USAGE_ERROR = (
    "⏰ I couldn't understand that time.\n\n"
    "**Usage:** `/remind <time> <message>`\n"
    "**Examples:**\n"
    "• `/remind in 2 hours Take medicine`\n"
    "• `/remind tomorrow at 9 AM Team standup`\n"
    "• `/remind 11:00 PM Lock the door`\n"
    "• `/remind every day at 8 AM Morning walk`"
)


def create_reminder(user_id: str, chat_id: str, text: str, time_str: str) -> str:
    """
    Creates a time-based reminder with exact timezone handling (default: Asia/Kolkata / IST).
    `time_str` can be '11:00 AM', 'at 11 AM', 'tomorrow at 9am', 'in 2 hours', '11 AM EST', etc.
    Invalid/unparseable times return a friendly usage error (no junk rows are ever created).
    """
    if not time_str or not time_str.strip():
        # No explicit time found by the splitter; maybe the whole input IS a time
        # expression like '/remind tomorrow'. If so, schedule with a generic label.
        candidate = (text or "").strip()
        try:
            parse_natural_datetime(candidate, user_tz=db.get_user_timezone(user_id))
            text, time_str = "Reminder", candidate
        except Exception:
            return _REMIND_USAGE_ERROR

    user_tz = db.get_user_timezone(user_id)
    try:
        due_dt, effective_tz, formatted_display, is_recurring, recurrence_pattern = parse_natural_datetime(
            time_str, user_tz=user_tz
        )
    except ValueError as e:
        return _REMIND_USAGE_ERROR

    due_utc_iso = to_utc_iso(due_dt)
    tz_name_str = str(effective_tz)

    # Deduplicate: one reminder definition -> exactly one scheduled job.
    existing = db.find_active_duplicate_reminder(user_id, text.strip(), due_utc_iso, "general")
    if existing:
        return (
            f"ℹ️ **You already have this reminder scheduled** (ID: #{existing['id']}).\n"
            f"• Note: **{text.strip()}**\n"
            f"• Scheduled for: `{formatted_display}`\n"
            f"_Use `/reminders` to view it or `/delremind {existing['id']}` to cancel._"
        )

    rem_id = db.add_reminder(
        user_id=user_id,
        chat_id=chat_id,
        text=text.strip(),
        due_time=due_utc_iso,
        reminder_type="general",
        is_recurring=int(is_recurring),
        recurrence_pattern=recurrence_pattern,
        timezone_name=tz_name_str,
    )

    rec_tag = " (🔁 Recurring Daily)" if is_recurring else ""
    return (
        f"✅ **Reminder Set (ID: #{rem_id})!**\n"
        f"• Note: **{text.strip()}**\n"
        f"• Scheduled for: `{formatted_display}`{rec_tag}\n"
        f"• Timezone: `{tz_name_str}`"
    )


def list_user_reminders(user_id: str) -> str:
    """Lists all active pending reminders for the user, rendered in their configured timezone."""
    user_tz = db.get_user_timezone(user_id)
    rems = db.get_active_reminders(user_id)
    if not rems:
        return "⏰ You have no pending reminders."

    lines = []
    for r in rems:
        rem_tz = resolve_timezone(r.get("timezone_name") or str(user_tz))
        due_dt = from_utc_iso_to_user_tz(r["due_time"], rem_tz)
        tz_abbr = get_timezone_abbreviation(due_dt)
        time_str = due_dt.strftime(f"%I:%M %p {tz_abbr} (%a, %b %d, %Y)")
        rec_str = " (🔁 Daily)" if r.get("is_recurring") else ""
        lines.append(f"• **[#{r['id']}]** {r['text']}\n  └ ⏰ Due: `{time_str}`{rec_str}")

    tz_name = db.get_user_timezone_str(user_id)
    return f"⏰ **Your Active Reminders (Timezone: {tz_name}):**\n\n" + "\n\n".join(lines)


def delete_user_reminder(user_id: str, reminder_id: int) -> str:
    """Cancels/deletes an active reminder."""
    success = db.delete_reminder(user_id, reminder_id)
    if success:
        return f"🗑️ **Reminder #{reminder_id} cancelled and deleted successfully.**"
    return f"❌ Reminder #{reminder_id} not found or already completed."


def set_user_timezone_preference(user_id: str, tz_input: str) -> str:
    """Configures the user's preferred timezone (e.g. 'Asia/Kolkata', 'America/New_York', 'UTC')."""
    if not tz_input.strip():
        curr_tz = db.get_user_timezone_str(user_id)
        return f"🌐 **Current Timezone Setting:** `{curr_tz}`\nUsage: `/timezone <timezone_name>` (e.g. `/timezone Asia/Kolkata`, `/timezone EST`, `/timezone UTC`)"

    resolved_tz = resolve_timezone(tz_input)
    db.set_user_timezone(user_id, str(resolved_tz))
    now_user = datetime.now(resolved_tz)
    tz_abbr = get_timezone_abbreviation(now_user)

    return (
        f"🌐 **Timezone Preference Updated!**\n\n"
        f"• **Timezone**: `{str(resolved_tz)}` ({tz_abbr})\n"
        f"• **Current Local Time**: `{now_user.strftime('%I:%M:%S %p (%A, %b %d, %Y)')}`\n\n"
        f"_All your future reminders and time queries will default to this timezone._"
    )


# -------------------------------------------------------------
# 21. Medicine Reminders
# -------------------------------------------------------------

def add_medicine_schedule(user_id: str, name: str, dosage: str, schedule_time: str, instructions: str = "") -> str:
    """
    Adds a recurring medicine reminder with proper timezone resolution.
    Rejects unparseable times and duplicate active schedules (no junk recurring jobs).
    """
    if not name or not name.strip() or not schedule_time or not schedule_time.strip():
        return (
            "💊 **Medicine Reminder Usage:** `/medremind <time> <medicine_name>`\n"
            "**Example:** `/medremind 9:00 AM Paracetamol 500mg`"
        )

    user_tz = db.get_user_timezone(user_id)
    try:
        due_dt, effective_tz, formatted_display, is_recurring, recurrence_pattern = parse_natural_datetime(
            schedule_time, user_tz=user_tz
        )
    except ValueError:
        return (
            "💊 I couldn't understand that time.\n\n"
            "**Usage:** `/medremind <time> <medicine_name>`\n"
            "**Examples:** `/medremind 9:00 AM Paracetamol` • `/medremind every day at 10 PM Azithral 500`"
        )

    due_utc_iso = to_utc_iso(due_dt)
    tz_name_str = str(effective_tz)
    reminder_text = f"{name.strip()} ({dosage}) - {instructions or 'Take with water'}"

    # Deduplicate: identical active medicine schedule -> single job only.
    existing = db.find_active_duplicate_reminder(user_id, reminder_text, due_utc_iso, "medicine")
    if existing:
        return (
            f"ℹ️ **This medicine schedule is already active** (Reminder ID: #{existing['id']}).\n"
            f"• Medicine: **{name.strip()}**\n"
            f"• Daily at: `{formatted_display}`\n"
            f"_Use `/delremind {existing['id']}` to cancel it first._"
        )

    # Add medicine entry
    med_id = db.add_medicine(user_id, name.strip(), dosage, formatted_display, instructions)
    # Add linked daily recurring reminder
    db.add_reminder(
        user_id=user_id,
        chat_id=user_id,
        text=reminder_text,
        due_time=due_utc_iso,
        reminder_type="medicine",
        is_recurring=1,
        recurrence_pattern="daily",
        timezone_name=tz_name_str,
    )

    return (
        f"💊 **Medicine Schedule Added (ID: #{med_id}):**\n"
        f"• Medicine: **{name.strip()}**\n"
        f"• Dosage: `{dosage}`\n"
        f"• Scheduled Time: `{formatted_display}` (Daily)\n"
        f"• Instructions: {instructions or 'Take with water'}"
    )


def list_medicine_schedules(user_id: str) -> str:
    """Lists scheduled medicines."""
    meds = db.get_medicines(user_id)
    if not meds:
        return "💊 No active medicine schedules found."

    lines = []
    for m in meds:
        lines.append(f"• **[#{m['id']}] {m['name']}** — `{m['dosage']}` at `{m['schedule_time']}` ({m['instructions'] or 'Take with water'})")
    return "💊 **Your Medicine Schedule:**\n\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
# 22. Note-Taking
# ---------------------------------------------------------------------------

def save_user_note(user_id: str, title: str, content: str, tags: str = "") -> str:
    """Saves a new note to SQLite."""
    note_id = db.add_note(user_id, title, content, tags)
    return f"📝 **Note Saved (ID: #{note_id})!**\n• Title: **{title}**\n• Tags: `{tags or 'general'}`"


def search_user_notes(user_id: str, query: Optional[str] = None) -> str:
    """Searches or lists recent notes."""
    notes = db.get_notes(user_id, query)
    if not notes:
        return f"📝 No notes found{' matching ' + query if query else ''}."

    lines = []
    for n in notes:
        lines.append(f"📌 **[#{n['id']}] {n['title']}** (Updated: `{n['updated_at'][:10]}`)\n   {n['content']}\n   _Tags: {n['tags'] or 'None'}_")
    return f"📝 **Your Notes ({len(notes)}):**\n\n" + "\n\n".join(lines)


# ---------------------------------------------------------------------------
# 23. Task / To-Do Manager
# ---------------------------------------------------------------------------

def add_user_todo(user_id: str, title: str, priority: str = "medium", due_date: Optional[str] = None) -> str:
    """Adds a task to the to-do list."""
    todo_id = db.add_todo(user_id, title, priority, due_date)
    return f"✅ **Task Added (ID: #{todo_id})!**\n• Task: **{title}**\n• Priority: `{priority.upper()}`\n• Due: `{due_date or 'No deadline'}`"


def list_user_todos(user_id: str, status: str = "pending") -> str:
    """Lists tasks by status."""
    todos = db.get_todos(user_id, status)
    if not todos:
        return f"📋 No {status} tasks found. You're all caught up!"

    lines = []
    for t in todos:
        p_icon = "🔴" if t['priority'] == "high" else "🟡" if t['priority'] == "medium" else "🟢"
        lines.append(f"• **[#{t['id']}]** {p_icon} {t['title']} (Due: `{t['due_date'] or 'N/A'}`)")
    return f"📋 **To-Do List ({status.upper()}):**\n\n" + "\n".join(lines)


def complete_user_todo(user_id: str, todo_id: int) -> str:
    """Marks a task as completed."""
    if db.complete_todo(user_id, todo_id):
        return f"🎉 **Task #{todo_id} marked as completed!** Great job!"
    return f"❌ Task #{todo_id} not found."


# ---------------------------------------------------------------------------
# 24. Expense & Finance Tracker
# ---------------------------------------------------------------------------

def log_user_expense(user_id: str, amount: float, category: str, description: str) -> str:
    """Logs a new expense."""
    exp_id = db.add_expense(user_id, amount, category, description)
    return f"💰 **Expense Logged (ID: #{exp_id}):**\n• Amount: **₹{amount:,.2f}**\n• Category: `{category.title()}`\n• Description: {description}"


def get_user_finance_summary(user_id: str, month: Optional[str] = None) -> str:
    """Generates monthly expense summary and category breakdown."""
    data = db.get_expense_summary(user_id, month)
    total = data["total"]
    m_str = data["month"]

    if total == 0.0:
        return f"📊 No expenses logged for `{m_str}`."

    cat_lines = []
    for c in data["categories"]:
        cat_lines.append(f"• **{c['category'].title()}**: ₹{c['cat_total']:,.2f} ({c['count']} transactions)")

    recent_lines = []
    for r in data["recent"]:
        recent_lines.append(f"  - `{r['expense_date']}`: ₹{r['amount']:,.2f} — {r['description']} (`{r['category']}`)")

    res = (
        f"📊 **Expense Summary for `{m_str}`:**\n\n"
        f"💵 **Total Spent: ₹{total:,.2f}**\n\n"
        f"**Category Breakdown:**\n" + "\n".join(cat_lines) + "\n\n"
        f"**Recent Transactions:**\n" + "\n".join(recent_lines)
    )
    return res


# ---------------------------------------------------------------------------
# 25. Bill & Utility Payment Reminders
# ---------------------------------------------------------------------------

def add_user_bill(user_id: str, title: str, amount: float, due_date: str) -> str:
    """Adds an upcoming bill."""
    bill_id = db.add_bill(user_id, title, amount, due_date)
    return f"🧾 **Bill Added (ID: #{bill_id}):**\n• Bill: **{title}**\n• Amount: **₹{amount:,.2f}**\n• Due Date: `{due_date}`"


def list_user_bills(user_id: str) -> str:
    """Lists unpaid and upcoming bills."""
    bills = db.get_bills(user_id, status="unpaid")
    if not bills:
        return "🧾 No unpaid bills pending! Everything is settled."

    lines = []
    for b in bills:
        lines.append(f"• **[#{b['id']}] {b['title']}** — **₹{b['amount']:,.2f}** (Due: `{b['due_date']}`)")
    return "🧾 **Upcoming & Unpaid Bills:**\n\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
# 26. Bank & UPI Transaction Alert Parser
# ---------------------------------------------------------------------------

def parse_bank_transaction_sms(user_id: str, message_text: str) -> str:
    """
    Parses SMS/email alert texts from Indian banks (SBI, HDFC, ICICI, Axis, Paytm, GPay, PhonePe).
    Auto-logs debit transactions to expenses!
    """
    # Regex patterns for amount, debit/credit, merchant, balance
    amt_match = re.search(r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{2})?)", message_text, re.IGNORECASE)
    type_match = re.search(r"\b(debited|spent|paid|credited|received)\b", message_text, re.IGNORECASE)
    acct_match = re.search(r"(?:a/c|account|card|vpa)\s*(?:no\.?)?\s*([xX\*\d]{4,})", message_text, re.IGNORECASE)
    bal_match = re.search(r"(?:avl\s*bal|balance|bal)\s*(?:is|:)?\s*(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d{2})?)", message_text, re.IGNORECASE)

    if not amt_match:
        return "⚠️ Could not parse a valid transaction amount from this text."

    raw_amt = amt_match.group(1).replace(",", "")
    amount = float(raw_amt)
    tx_type = type_match.group(1).lower() if type_match else "debited"
    acct = acct_match.group(1) if acct_match else "Bank A/c"
    balance = bal_match.group(1) if bal_match else "N/A"

    # Infer category
    category = "general"
    lower_txt = message_text.lower()
    if any(k in lower_txt for k in ["swiggy", "zomato", "restaurant", "food", "cafe"]):
        category = "food"
    elif any(k in lower_txt for k in ["uber", "ola", "metro", "fuel", "petrol", "transport"]):
        category = "transport"
    elif any(k in lower_txt for k in ["amazon", "flipkart", "myntra", "shopping"]):
        category = "shopping"
    elif any(k in lower_txt for k in ["electricity", "bill", "recharge", "wifi", "broadband"]):
        category = "utilities"

    if tx_type in ["debited", "spent", "paid"]:
        exp_id = db.add_expense(user_id, amount, category, f"Auto-parsed bank transaction ({acct})")
        return (
            f"🏦 **Bank Transaction Detected & Auto-Logged!**\n\n"
            f"• Type: 🔴 **Debit ({tx_type.upper()})**\n"
            f"• Amount: **₹{amount:,.2f}**\n"
            f"• Account: `{acct}`\n"
            f"• Auto Category: `{category.title()}`\n"
            f"• Available Balance: `₹{balance}`\n"
            f"• Saved to Expenses (ID: `#{exp_id}`)"
        )
    else:
        return (
            f"🏦 **Credit Transaction Detected!**\n\n"
            f"• Type: 🟢 **Credit ({tx_type.upper()})**\n"
            f"• Amount: **₹{amount:,.2f}**\n"
            f"• Account: `{acct}`\n"
            f"• Available Balance: `₹{balance}`"
        )


# ---------------------------------------------------------------------------
# 27. Website & Price Monitoring
# ---------------------------------------------------------------------------

def add_url_monitor(user_id: str, url: str, title: str, target_price: Optional[float] = None) -> str:
    """Adds a website URL for periodic uptime & price tracking."""
    mon_id = db.add_price_monitor(user_id, url, title, target_price)
    return f"🌐 **Website Monitor Active (ID: #{mon_id}):**\n• Target: [{title}]({url})\n• Alert Target Price: {f'₹{target_price}' if target_price else 'Any change'}"


def check_url_status(url: str) -> str:
    """Performs instant health/status check on a URL."""
    try:
        start_t = time.time()
        resp = requests.get(url, timeout=10, headers={"User-Agent": "AlyaMonitor/1.0"})
        latency_ms = int((time.time() - start_t) * 1000)
        status_icon = "🟢" if resp.status_code == 200 else "🟡" if resp.status_code < 400 else "🔴"
        return f"🌐 **Website Status Check:**\n• URL: `{url}`\n• Status: {status_icon} `{resp.status_code} {resp.reason}`\n• Latency: `{latency_ms} ms`\n• Content Size: `{len(resp.content):,} bytes`"
    except Exception as e:
        return f"🔴 **Website Unreachable:** {url}\n• Error: {str(e)}"


# ---------------------------------------------------------------------------
# 28. Traffic & Commute ETA (OpenRouteService Matrix & Google Maps)
# ---------------------------------------------------------------------------

def get_commute_eta(origin: str, destination: str) -> str:
    """Calculates driving distance, duration, and ETA between two locations via OpenRouteService Matrix API."""
    ors_key = os.getenv("OPENROUTESERVICE_API_KEY")
    
    if ors_key:
        try:
            def geocode_ors(place: str):
                url = f"https://api.openrouteservice.org/geocode/search?api_key={ors_key}&text={requests.utils.quote(place)}"
                r = requests.get(url, timeout=8)
                if r.status_code == 200:
                    feat = r.json().get("features", [])
                    if feat:
                        return feat[0]["geometry"]["coordinates"]  # [lon, lat]
                return None

            c_orig = geocode_ors(origin)
            c_dest = geocode_ors(destination)

            if c_orig and c_dest:
                matrix_url = "https://api.openrouteservice.org/v2/matrix/driving-car"
                headers = {"Authorization": ors_key, "Content-Type": "application/json"}
                body = {
                    "locations": [c_orig, c_dest],
                    "metrics": ["distance", "duration"]
                }
                resp = requests.post(matrix_url, json=body, headers=headers, timeout=10)
                if resp.status_code == 200:
                    res_json = resp.json()
                    distances = res_json.get("distances", [[]])
                    durations = res_json.get("durations", [[]])

                    if distances and len(distances[0]) > 1 and durations and len(durations[0]) > 1:
                        meters = distances[0][1]
                        seconds = durations[0][1]

                        if meters is not None and seconds is not None:
                            km = meters / 1000.0
                            mins_total = int(seconds / 60)
                            hours = mins_total // 60
                            mins = mins_total % 60

                            dur_str = f"{hours} hr {mins} mins" if hours > 0 else f"{mins} mins"
                            return (
                                f"🚗 **Commute ETA & Distance (OpenRouteService):**\n"
                                f"• Route: **{origin}** ➔ **{destination}**\n"
                                f"• Driving Distance: **`{km:.1f} km`**\n"
                                f"• Estimated Travel Time: **`{dur_str}`**\n"
                                f"• Real-time Route Map: https://www.google.com/maps/dir/{requests.utils.quote(origin)}/{requests.utils.quote(destination)}"
                            )
        except Exception as e:
            logger.warning(f"OpenRouteService error: {e}")

    # Fallback to Google Maps if key present
    gmaps_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if gmaps_key:
        try:
            url = f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={requests.utils.quote(origin)}&destinations={requests.utils.quote(destination)}&mode=driving&key={gmaps_key}"
            resp = requests.get(url, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                el = data["rows"][0]["elements"][0]
                if el.get("status") == "OK":
                    dist = el["distance"]["text"]
                    dur = el["duration"]["text"]
                    return f"🚗 **Commute ETA (Google Maps):**\n• Route: **{origin}** ➔ **{destination}**\n• Distance: `{dist}`\n• Driving Time: **`{dur}`**"
        except Exception as e:
            logger.warning(f"Google Maps API error: {e}")

    # Fallback to search-based route estimate
    return f"🚗 **Commute Route:**\n• Route: **{origin}** ➔ **{destination}**\n• Check Live Traffic: https://www.google.com/maps/dir/{requests.utils.quote(origin)}/{requests.utils.quote(destination)}"


# ---------------------------------------------------------------------------
# 29. Ride & Cab Fare Estimate (Uber / Ola Pricing Model)
# ---------------------------------------------------------------------------

def estimate_cab_fare(distance_km: float, time_mins: Optional[float] = None) -> str:
    """Estimates ride fares for Uber & Ola across vehicle types."""
    if not time_mins:
        time_mins = distance_km * 3.0  # Approx 20 km/h in Indian city traffic

    # Dynamic pricing formula for Indian city cabs
    # Uber Auto / Ola Auto
    auto_fare = 30 + (distance_km * 15) + (time_mins * 1.5)
    # Uber Go / Ola Mini
    sedan_fare = 50 + (distance_km * 18) + (time_mins * 2.0)
    # Uber Premier / Ola Prime
    premier_fare = 80 + (distance_km * 24) + (time_mins * 2.5)
    # Moto / Bike
    bike_fare = 20 + (distance_km * 9) + (time_mins * 1.0)

    return (
        f"🚖 **Estimated Cab / Ride Fares ({distance_km:.1f} km, ~{int(time_mins)} mins):**\n\n"
        f"• 🛵 **Bike Taxi (Uber Moto / Rapido):** `₹{bike_fare:.0f} - ₹{bike_fare*1.2:.0f}`\n"
        f"• 🛺 **Auto Rickshaw:** `₹{auto_fare:.0f} - ₹{auto_fare*1.2:.0f}`\n"
        f"• 🚗 **Uber Go / Ola Mini:** `₹{sedan_fare:.0f} - ₹{sedan_fare*1.2:.0f}`\n"
        f"• 🚘 **Uber Premier / Prime Sedan:** `₹{premier_fare:.0f} - ₹{premier_fare*1.2:.0f}`\n\n"
        f"_Note: Actual prices may vary based on live surge and traffic._"
    )


# ---------------------------------------------------------------------------
# 30. Package & Order Delivery Tracking
# ---------------------------------------------------------------------------

def track_delivery_package(tracking_number: str) -> str:
    """Identifies courier service and provides parcel tracking status."""
    clean_num = tracking_number.strip().upper()

    # Detect carrier
    carrier = "Universal Courier"
    if clean_num.startswith(("EM", "EA", "CP", "RR")) and clean_num.endswith("IN"):
        carrier = "India Post (Speed Post)"
    elif len(clean_num) in [8, 9] and clean_num.isdigit():
        carrier = "Blue Dart"
    elif clean_num.startswith(("D", "B")) and len(clean_num) > 8:
        carrier = "DTDC"
    elif len(clean_num) == 12 and clean_num.isdigit():
        carrier = "FedEx / Delhivery"
    elif clean_num.startswith("1Z"):
        carrier = "UPS"

    return (
        f"📦 **Parcel Tracking for `{clean_num}`:**\n\n"
        f"• Detected Carrier: **{carrier}**\n"
        f"• 17Track Global: https://www.17track.net/en/track?nums={clean_num}\n"
        f"• AfterShip: https://www.aftership.com/track/{clean_num}"
    )


# ---------------------------------------------------------------------------
# 31. Movie & Event Showtimes Check
# ---------------------------------------------------------------------------

def search_movie_showtimes(movie_title: str, city: str = "Mumbai") -> str:
    """Searches showtimes and cinema availability."""
    clean_m = movie_title.strip()
    clean_c = city.strip().lower()
    bms_url = f"https://in.bookmyshow.com/explore/movies-{clean_c}?search={requests.utils.quote(clean_m)}"
    paytm_url = f"https://paytm.com/movies/{clean_c}"
    return (
        f"🎟️ **Showtimes & Cinema Check for '{clean_m}' in {city.title()}:**\n\n"
        f"• BookMyShow: [Check Theatres & Book Tickets]({bms_url})\n"
        f"• Paytm Movies: [Check Paytm Showtimes]({paytm_url})"
    )


# ---------------------------------------------------------------------------
# 32. Internet Speed Test Trigger
# ---------------------------------------------------------------------------

def run_internet_speedtest() -> str:
    """Executes internet speed test on the server using speedtest-cli."""
    try:
        import speedtest
        st = speedtest.Speedtest()
        st.get_best_server()
        download_mbps = st.download() / 1_000_000
        upload_mbps = st.upload() / 1_000_000
        ping_ms = st.results.ping

        return (
            f"⚡ **Internet Speed Test Results (Server):**\n\n"
            f"• 📥 **Download Speed:** `{download_mbps:.2f} Mbps`\n"
            f"• 📤 **Upload Speed:** `{upload_mbps:.2f} Mbps`\n"
            f"• 📶 **Ping Latency:** `{ping_ms:.1f} ms`\n"
            f"• 🏢 Server Host: `{st.results.server.get('sponsor')} ({st.results.server.get('name')})`"
        )
    except Exception as e:
        logger.warning(f"Speedtest error: {e}")
        return f"❌ Speed test failed: {str(e)}"


# ---------------------------------------------------------------------------
# 33. Habit Tracker
# ---------------------------------------------------------------------------

def record_habit_completion(user_id: str, habit_name: str) -> str:
    """Records daily completion of a habit and calculates streak."""
    # Ensure habit exists
    habits = db.get_habits(user_id)
    if not any(h["habit_name"].lower() == habit_name.lower() for h in habits):
        db.add_habit(user_id, habit_name)

    res = db.log_habit_done(user_id, habit_name)
    if res.get("already_done"):
        return f"🔥 **Habit '{habit_name}' already checked off for today!** Current streak: **{res['habit']['current_streak']} days**."

    return f"🎉 **Habit Completed: '{habit_name}'!**\n• Current Streak: **{res['streak']} days** 🔥\n• Best Streak: **{res['best_streak']} days** 🏆"


def list_user_habits(user_id: str) -> str:
    """Lists all tracked habits with streaks."""
    habits = db.get_habits(user_id)
    if not habits:
        return "🌱 No habits currently being tracked. Start one with `add habit workout`!"

    lines = []
    for h in habits:
        lines.append(f"• **{h['habit_name']}** — 🔥 `{h['current_streak']} day streak` (Best: `{h['best_streak']} days`, Last: `{h['last_completed_date'] or 'Never'}`)")
    return "🌱 **Your Daily Habits:**\n\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
# 34. Server & System Health Monitor (EC2 Instance)
# ---------------------------------------------------------------------------

def get_server_system_health() -> str:
    """Reports CPU, RAM, Disk, Uptime, and Rasa processes on this EC2 instance."""
    try:
        cpu_pct = psutil.cpu_percent(interval=0.5)
        cpu_count = psutil.cpu_count(logical=True)
        
        mem = psutil.virtual_memory()
        mem_used_mb = mem.used / (1024 * 1024)
        mem_total_mb = mem.total / (1024 * 1024)
        mem_pct = mem.percent

        disk = psutil.disk_usage('/')
        disk_used_gb = disk.used / (1024 ** 3)
        disk_total_gb = disk.total / (1024 ** 3)
        disk_pct = disk.percent

        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime_str = str(datetime.now() - boot_time).split('.')[0]

        # Check Rasa processes
        rasa_procs = []
        for p in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_info']):
            try:
                cmd = " ".join(p.info['cmdline'] or [])
                if "rasa run" in cmd:
                    rss_mb = p.info['memory_info'].rss / (1024 * 1024)
                    rasa_procs.append(f"PID {p.info['pid']} ({rss_mb:.1f} MB RAM)")
            except Exception:
                pass

        return (
            f"🖥️ **EC2 Server Health & Diagnostics:**\n\n"
            f"• ⚙️ **CPU Usage:** `{cpu_pct}%` ({cpu_count} vCPUs)\n"
            f"• 🧠 **RAM Memory:** `{mem_used_mb:,.0f} MB / {mem_total_mb:,.0f} MB` (**{mem_pct}%**)\n"
            f"• 💾 **Disk Storage (/):** `{disk_used_gb:.1f} GB / {disk_total_gb:.1f} GB` (**{disk_pct}%**)\n"
            f"• ⏱️ **System Uptime:** `{uptime_str}` (Booted: {boot_time.strftime('%Y-%m-%d %H:%M')})\n"
            f"• 🤖 **Active Rasa Services:** {', '.join(rasa_procs) if rasa_procs else 'Running via systemd'}"
        )
    except Exception as e:
        return f"❌ Failed to fetch system health: {str(e)}"


# ---------------------------------------------------------------------------
# 35. File Sharing & Storage
# ---------------------------------------------------------------------------

def list_stored_files(user_id: str) -> str:
    """Lists files saved by the user."""
    files = db.get_user_files(user_id)
    if not files:
        return "📁 No stored files found in your account."

    lines = []
    for f in files:
        lines.append(f"• **[#{f['id']}] {f['file_name']}** (`{f['file_type']}`, {f['file_size']//1024} KB) — Saved `{f['created_at'][:16]}`")
    return f"📁 **Your Stored Files ({len(files)}):**\n\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
# 36. Long-Term Memory (Persistent User Context Across Sessions)
# ---------------------------------------------------------------------------

def remember_user_fact(user_id: str, key: str, value: str, category: str = "general") -> str:
    """Saves a permanent fact into long-term memory."""
    db.save_memory(user_id, key, value, category)
    return f"🧠 **Got it! I will remember:** `{key}` = **{value}** (Category: `{category}`)"


def get_user_memory_context(user_id: str) -> str:
    """Retrieves all stored facts for user to inject into LLM system prompt."""
    mems = db.get_all_memories(user_id)
    if not mems:
        return ""

    lines = [f"- {m['key']}: {m['value']} ({m['category']})" for m in mems]
    return "Stored Memories about this user:\n" + "\n".join(lines)


def list_user_memories(user_id: str) -> str:
    """User-facing command to view all stored memories."""
    mems = db.get_all_memories(user_id)
    if not mems:
        return "🧠 I don't have any saved memories about you yet. Tell me facts with `remember that my favorite color is blue`!"

    lines = [f"• **{m['key'].title()}**: {m['value']} (`{m['category']}`)" for m in mems]
    return "🧠 **Long-Term Memories Saved About You:**\n\n" + "\n".join(lines)


def forget_user_fact(user_id: str, key: str) -> str:
    """Removes a fact from long-term memory."""
    if db.delete_memory(user_id, key):
        return f"🗑️ I have forgotten `{key}`."
    return f"❌ Fact `{key}` was not found in memory."


# ---------------------------------------------------------------------------
# 37. Package & Courier Tracking
# ---------------------------------------------------------------------------

def track_package(tracking_number: str) -> str:
    """
    Provides tracking portal details and status links for postal/courier shipments (India Post, BlueDart, DTDC, Delhivery, FedEx, DHL, etc.).
    """
    clean_no = tracking_number.strip().upper()
    if not clean_no:
        return "⚠️ Please provide a tracking number (e.g. `/track EM123456789IN` or `/track 123456789`)."

    # Identify courier pattern
    courier = "India Post / Speed Post"
    portal_url = "https://www.indiapost.gov.in/_layouts/15/dpt.cept.tracking/trackconsignment.aspx"
    if clean_no.startswith(("1Z", "T")) or len(clean_no) == 18:
        courier = "UPS"
        portal_url = f"https://www.ups.com/track?tracknum={clean_no}"
    elif len(clean_no) in (12, 15) and clean_no.isdigit():
        courier = "FedEx"
        portal_url = f"https://www.fedex.com/fedextrack/?trknbr={clean_no}"
    elif clean_no.startswith("D") or len(clean_no) == 9:
        courier = "Delhivery / DTDC"
        portal_url = f"https://www.delhivery.com/track/package/{clean_no}"
    elif re.match(r"^[A-Z]{2}\d{9}[A-Z]{2}$", clean_no):
        courier = "India Post Speed Post (EMS)"
        portal_url = "https://www.indiapost.gov.in/_layouts/15/dpt.cept.tracking/trackconsignment.aspx"

    universal_url = f"https://www.17track.net/en/track?nums={clean_no}"

    return (
        f"📦 **Package & Shipment Tracker — `{clean_no}`**\n\n"
        f"• **Identified Carrier:** {courier}\n"
        f"• **Tracking Number:** `{clean_no}`\n"
        f"• 🌐 **Official Carrier Portal:** [Track on {courier}]({portal_url})\n"
        f"• 🛰️ **Universal Multi-Carrier Tracking:** [Track on 17TRACK]({universal_url})\n\n"
        f"💡 _Tip: Click the link above to view real-time transit checkpoints, out-for-delivery status, and estimated arrival date._"
    )

