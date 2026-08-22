"""
Centralized Timezone & Natural Language DateTime Processing for Alya.
Default timezone: Asia/Kolkata (IST, UTC+05:30).
"""

import re
import time
import zoneinfo
import logging
from datetime import datetime, date, time as dtime, timedelta, timezone
from typing import Optional, Tuple, Dict, Any
import parsedatetime as pdt
import dateutil.parser as dparser

logger = logging.getLogger(__name__)

DEFAULT_TIMEZONE_NAME = "Asia/Kolkata"
DEFAULT_TIMEZONE = zoneinfo.ZoneInfo(DEFAULT_TIMEZONE_NAME)

# Common timezone abbreviation aliases mapping to IANA canonical names
TIMEZONE_ALIASES: Dict[str, str] = {
    "IST": "Asia/Kolkata",
    "INDIA": "Asia/Kolkata",
    "UTC": "UTC",
    "GMT": "UTC",
    "Z": "UTC",
    "EST": "America/New_York",
    "EDT": "America/New_York",
    "ET": "America/New_York",
    "EASTERN": "America/New_York",
    "CST": "America/Chicago",
    "CDT": "America/Chicago",
    "CT": "America/Chicago",
    "CENTRAL": "America/Chicago",
    "MST": "America/Denver",
    "MDT": "America/Denver",
    "MT": "America/Denver",
    "MOUNTAIN": "America/Denver",
    "PST": "America/Los_Angeles",
    "PDT": "America/Los_Angeles",
    "PT": "America/Los_Angeles",
    "PACIFIC": "America/Los_Angeles",
    "BST": "Europe/London",
    "LONDON": "Europe/London",
    "UK": "Europe/London",
    "CET": "Europe/Paris",
    "CEST": "Europe/Paris",
    "PARIS": "Europe/Paris",
    "BERLIN": "Europe/Berlin",
    "GST": "Asia/Dubai",
    "DUBAI": "Asia/Dubai",
    "UAE": "Asia/Dubai",
    "SGT": "Asia/Singapore",
    "SINGAPORE": "Asia/Singapore",
    "JST": "Asia/Tokyo",
    "TOKYO": "Asia/Tokyo",
    "JAPAN": "Asia/Tokyo",
    "AEST": "Australia/Sydney",
    "AEDT": "Australia/Sydney",
    "SYDNEY": "Australia/Sydney",
    "HKT": "Asia/Hong_Kong",
    "HONGKONG": "Asia/Hong_Kong",
}

_CALENDAR = pdt.Calendar()


def resolve_timezone(tz_name: Optional[str]) -> zoneinfo.ZoneInfo:
    """
    Resolves a timezone name/alias to a zoneinfo.ZoneInfo object.
    Defaults to Asia/Kolkata (IST).
    """
    if not tz_name:
        return DEFAULT_TIMEZONE

    clean = tz_name.strip().upper()
    canonical = TIMEZONE_ALIASES.get(clean)
    if canonical:
        try:
            return zoneinfo.ZoneInfo(canonical)
        except Exception:
            pass

    try:
        return zoneinfo.ZoneInfo(tz_name.strip())
    except Exception:
        try:
            # Case-insensitive search in available timezones
            for available in zoneinfo.available_timezones():
                if available.lower() == tz_name.strip().lower():
                    return zoneinfo.ZoneInfo(available)
        except Exception:
            pass

    return DEFAULT_TIMEZONE


def get_timezone_abbreviation(dt: datetime) -> str:
    """Gets the short abbreviation for a datetime's timezone (e.g. 'IST', 'EDT', 'UTC')."""
    if dt.tzinfo is None:
        return "IST"
    tzname = dt.tzname()
    if tzname:
        return tzname
    # Fallback to offset string
    offset = dt.utcoffset()
    if offset is not None:
        hours = offset.total_seconds() / 3600
        if hours == 5.5:
            return "IST"
        elif hours == 0:
            return "UTC"
        return f"UTC{'+' if hours >= 0 else ''}{hours:.1f}"
    return "IST"


def extract_explicit_timezone(text: str) -> Tuple[str, Optional[zoneinfo.ZoneInfo], Optional[str]]:
    """
    Checks if the user string explicitly includes a timezone identifier (e.g. '11 AM EST', '5pm UTC').
    Returns (cleaned_text_without_tz, resolved_zoneinfo_or_None, tz_display_str_or_None).
    """
    words = text.split()
    for i, w in enumerate(words):
        clean_w = w.strip(",.;()[]").upper()
        if clean_w in TIMEZONE_ALIASES:
            tz_obj = resolve_timezone(clean_w)
            # Remove that word from string
            rem = [word for j, word in enumerate(words) if j != i]
            return (" ".join(rem).strip(), tz_obj, clean_w)

    return (text, None, None)


def parse_natural_datetime(
    time_str: str,
    user_tz: Optional[zoneinfo.ZoneInfo] = None,
) -> Tuple[datetime, zoneinfo.ZoneInfo, str, bool, str]:
    """
    Comprehensive, timezone-aware datetime parser.
    Supports:
      - 'in 15 mins', 'in 2 hours', 'in 3 days'
      - 'at 11:00 AM', '11am', '7:30 PM', '11:00'
      - 'tomorrow at 9 AM', 'tomorrow 9:00am'
      - 'every day at 9 AM', 'daily at 10 PM'
      - '11 AM EST', '5 PM UTC' (explicit timezone)
      - Standard ISO strings

    Returns:
      (due_datetime_aware, effective_tz, formatted_display, is_recurring, recurrence_pattern)
    """
    clean_input = time_str.strip()
    if not clean_input:
        effective_tz = user_tz or DEFAULT_TIMEZONE
        due_dt = datetime.now(effective_tz) + timedelta(hours=1)
        tz_abbr = get_timezone_abbreviation(due_dt)
        return (due_dt, effective_tz, due_dt.strftime(f"%I:%M %p {tz_abbr} (%A, %b %d, %Y)"), False, "")

    # 1. Check for explicit timezone in the string
    cleaned_time_str, explicit_tz, explicit_tz_name = extract_explicit_timezone(clean_input)
    effective_tz = explicit_tz or user_tz or DEFAULT_TIMEZONE

    # Current reference time in the effective timezone
    now = datetime.now(effective_tz)

    lower_text = cleaned_time_str.lower().strip()
    is_recurring = False
    recurrence_pattern = ""

    # Check recurring keywords
    if "every day" in lower_text or "daily" in lower_text or lower_text.startswith("every "):
        is_recurring = True
        recurrence_pattern = "daily"
        lower_text = lower_text.replace("every day", "").replace("daily", "").replace("every", "").strip()

    # Strip leading noise like "at ", "on ", "for "
    if lower_text.startswith("at "):
        lower_text = lower_text[3:].strip()
    elif lower_text.startswith("for "):
        lower_text = lower_text[4:].strip()

    due_dt: Optional[datetime] = None

    # 2. Match relative offsets (in X minutes / hours / days / seconds)
    rel_match = re.search(
        r"^(?:in\s+)?(\d+(?:\.\d+)?)\s*(second|sec|s|minute|min|m|hour|hr|h|day|d|week|w|month)s?$",
        lower_text
    )
    if rel_match:
        val = float(rel_match.group(1))
        unit = rel_match.group(2)
        if unit in ("second", "sec", "s"):
            due_dt = now + timedelta(seconds=val)
        elif unit in ("minute", "min", "m"):
            due_dt = now + timedelta(minutes=val)
        elif unit in ("hour", "hr", "h"):
            due_dt = now + timedelta(hours=val)
        elif unit in ("day", "d"):
            due_dt = now + timedelta(days=val)
        elif unit in ("week", "w"):
            due_dt = now + timedelta(weeks=val)
        elif unit == "month":
            due_dt = now + timedelta(days=val * 30)

    # 3. Match tomorrow at HH:MM AM/PM
    if not due_dt:
        tmrw_match = re.search(r"^tomorrow(?:\s+at)?\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$", lower_text)
        if tmrw_match:
            hr = int(tmrw_match.group(1))
            mn = int(tmrw_match.group(2)) if tmrw_match.group(2) else 0
            meridiem = tmrw_match.group(3)

            if meridiem:
                if meridiem == "pm" and hr < 12:
                    hr += 12
                elif meridiem == "am" and hr == 12:
                    hr = 0

            target_date = (now + timedelta(days=1)).date()
            due_dt = datetime(target_date.year, target_date.month, target_date.day, hr, mn, 0, tzinfo=effective_tz)

    # 4. Match clock time: e.g. "11:00 AM", "11 AM", "11am", "11:30pm", "23:00"
    if not due_dt:
        time_clock_match = re.search(r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$", lower_text)
        if time_clock_match:
            hr = int(time_clock_match.group(1))
            mn = int(time_clock_match.group(2)) if time_clock_match.group(2) else 0
            meridiem = time_clock_match.group(3)

            if meridiem:
                if meridiem == "pm" and hr < 12:
                    hr += 12
                elif meridiem == "am" and hr == 12:
                    hr = 0

            # Today at this hour/minute
            candidate = datetime(now.year, now.month, now.day, hr, mn, 0, tzinfo=effective_tz)
            # If the candidate time has already passed today, advance to tomorrow!
            if candidate <= now:
                due_dt = candidate + timedelta(days=1)
            else:
                due_dt = candidate

    # 5. Try parsedatetime with current time in effective timezone
    if not due_dt:
        try:
            # Parse with now as reference
            time_struct, parse_status = _CALENDAR.parse(lower_text, now.timetuple())
            if parse_status > 0:
                dt_naive = datetime(*time_struct[:6])
                due_dt = dt_naive.replace(tzinfo=effective_tz)
                # If parsedatetime returned a past time today for clock input, advance by 1 day
                if due_dt <= now and parse_status == 2:  # status 2 is time-only match
                    due_dt += timedelta(days=1)
        except Exception:
            pass

    # 6. Try dateutil parser fallback
    if not due_dt:
        try:
            parsed = dparser.parse(clean_input, default=now.replace(tzinfo=None))
            if parsed.tzinfo is None:
                due_dt = parsed.replace(tzinfo=effective_tz)
            else:
                due_dt = parsed.astimezone(effective_tz)
            if due_dt <= now:
                due_dt += timedelta(days=1)
        except Exception:
            # Unparseable time: raise instead of silently scheduling "+1 hour".
            # (Silent fallback previously created junk recurring reminders.)
            raise ValueError(
                f"Could not understand the time '{time_str}'. "
                "Try formats like 'in 2 hours', 'tomorrow at 9 AM', '11:00 PM', or 'every day at 8 AM'."
            )

    # Final guarantee: ensure timezone is set and valid
    if due_dt.tzinfo is None:
        due_dt = due_dt.replace(tzinfo=effective_tz)

    tz_abbr = get_timezone_abbreviation(due_dt)
    formatted = due_dt.strftime(f"%I:%M %p {tz_abbr} (%A, %b %d, %Y)")

    return (due_dt, effective_tz, formatted, is_recurring, recurrence_pattern)


def to_utc_iso(dt: datetime) -> str:
    """Converts any timezone-aware datetime to standard UTC ISO 8601 string for DB storage."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=DEFAULT_TIMEZONE)
    utc_dt = dt.astimezone(timezone.utc)
    return utc_dt.isoformat()


def from_utc_iso_to_user_tz(utc_iso_str: str, user_tz: Optional[zoneinfo.ZoneInfo] = None) -> datetime:
    """Converts a stored UTC ISO string into a timezone-aware datetime in user's timezone."""
    effective_tz = user_tz or DEFAULT_TIMEZONE
    try:
        # If it has 'Z', replace with '+00:00'
        clean_iso = utc_iso_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_iso)
        if dt.tzinfo is None:
            # If DB had naive string, assume it was UTC
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(effective_tz)
    except Exception:
        # Fallback
        return datetime.now(effective_tz)


TZ_REGEX_PATTERN = r"(?:\s+(?:IST|UTC|GMT|EST|EDT|ET|CST|CDT|CT|MST|MDT|MT|PST|PDT|PT|BST|CET|CEST|JST|AEST|AEDT|GST|SGT|HKT|[A-Za-z]+/[A-Za-z_]+))?"


def split_reminder_command(args_str: str) -> Tuple[str, str]:
    """
    Extracts (time_part, note_text) from a user reminder command string.
    Handles quotes, prefix times, suffix times, and natural language formatting.
    """
    clean = args_str.strip()
    if not clean:
        return ("", "")

    # 1. Check for quoted time: /remind "tomorrow at 9am" Message
    quote_match = re.match(r'^["\']([^"\']+)["\']\s+(.*)$', clean)
    if quote_match:
        return (quote_match.group(1).strip(), quote_match.group(2).strip())

    # 2. Check for leading time expressions
    patterns = [
        r"^(?:in\s+)?\d+(?:\.\d+)?\s*(?:seconds?|secs?|s|minutes?|mins?|m|hours?|hrs?|h|days?|d|weeks?|w|months?)\b",
        r"^tomorrow(?:\s+at)?\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?" + TZ_REGEX_PATTERN + r"\b",
        r"^(?:today|tonight)(?:\s+at)?\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?" + TZ_REGEX_PATTERN + r"\b",
        r"^(?:every\s+day|daily|every)\s+(?:at\s+)?\d{1,2}(?::\d{2})?\s*(?:am|pm)?" + TZ_REGEX_PATTERN + r"\b",
        r"^at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?" + TZ_REGEX_PATTERN + r"\b",
        r"^\d{1,2}(?::\d{2})?\s*(?:am|pm)" + TZ_REGEX_PATTERN + r"\b",
        r"^\d{1,2}:\d{2}" + TZ_REGEX_PATTERN + r"\b",
    ]

    for p in patterns:
        m = re.match(p, clean, re.IGNORECASE)
        if m:
            time_part = m.group(0).strip()
            msg_part = clean[m.end():].strip()
            if msg_part.lower().startswith("to "):
                msg_part = msg_part[3:].strip()
            elif msg_part.lower().startswith("that "):
                msg_part = msg_part[5:].strip()
            elif msg_part.startswith("- "):
                msg_part = msg_part[2:].strip()
            return (time_part, msg_part or "General reminder")

    # 3. Check for trailing relative time: e.g. "Buy groceries in 2 hours", "Call Rahul at 11 AM"
    trailing_patterns = [
        r"\b(?:in\s+)?\d+(?:\.\d+)?\s*(?:seconds?|secs?|s|minutes?|mins?|m|hours?|hrs?|h|days?|d|weeks?|w|months?)$",
        r"\b(?:at\s+)?\d{1,2}(?::\d{2})?\s*(?:am|pm)?" + TZ_REGEX_PATTERN + r"$",
        r"\btomorrow(?:\s+at)?\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?" + TZ_REGEX_PATTERN + r"$",
    ]
    for tp in trailing_patterns:
        m = re.search(tp, clean, re.IGNORECASE)
        if m and m.start() > 0:
            msg_part = clean[:m.start()].strip()
            time_part = m.group(0).strip()
            return (time_part, msg_part or "General reminder")

    # 4. Fallback: split on first space / first 2 words
    tokens = clean.split(maxsplit=2)
    if len(tokens) >= 3 and tokens[0].lower() in ("in", "at", "tomorrow", "every", "on"):
        return (f"{tokens[0]} {tokens[1]}", tokens[2])
    elif len(tokens) >= 2 and _looks_like_time_token(tokens[0]):
        return (tokens[0], " ".join(tokens[1:]))
    # No recognizable time expression found. Return empty time part so callers can
    # show a usage error instead of silently scheduling junk ("test argument" bug).
    return ("", clean)


def _looks_like_time_token(token: str) -> bool:
    """Cheap check whether the first token resembles a clock/relative time expression."""
    t = token.lower().strip(",.")
    return bool(re.match(r"^\d{1,2}(:\d{2})?\s*(am|pm)?$", t) or re.match(r"^(?:in|at|tomorrow|today|tonight|every|daily)$", t))

