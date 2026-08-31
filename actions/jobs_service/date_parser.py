"""
Robust Date Normalization and Deadline Evaluator in Asia/Kolkata timezone.
"""

import re
import logging
from datetime import datetime, date, timezone, timedelta
from typing import Optional
import pytz

logger = logging.getLogger(__name__)

KOLKATA_TZ = pytz.timezone("Asia/Kolkata")

# Precompiled regex patterns for dates in Indian job/scholarship notices
DATE_PATTERNS = [
    # Extended patterns e.g. "Extended up to 31/08/2026" or "Extended till 15-09-2026"
    re.compile(r'(?:extended(?:\s+(?:up\s+to|till|to|upto))?[:\s]+)?(\d{1,2})[/-](\d{1,2})[/-](\d{4})', re.IGNORECASE),
    re.compile(r'(?:extended(?:\s+(?:up\s+to|till|to|upto))?[:\s]+)?(\d{1,2})\.(\d{1,2})\.(\d{4})', re.IGNORECASE),
    re.compile(r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})'),  # ISO YYYY-MM-DD
    # Written month e.g. "15th August 2026", "15 Aug 2026", "August 15, 2026"
    re.compile(r'(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)[,\s]+(\d{4})', re.IGNORECASE),
    re.compile(r'([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?[,\s]+(\d{4})', re.IGNORECASE),
    re.compile(r'(\d{1,2})-([A-Za-z]{3,9})-(\d{4})', re.IGNORECASE),
]

MONTH_MAP = {
    'jan': 1, 'january': 1,
    'feb': 2, 'february': 2,
    'mar': 3, 'march': 3,
    'apr': 4, 'april': 4,
    'may': 5,
    'jun': 6, 'june': 6,
    'jul': 7, 'july': 7,
    'aug': 8, 'august': 8,
    'sep': 9, 'sept': 9, 'september': 9,
    'oct': 10, 'october': 10,
    'nov': 11, 'november': 11,
    'dec': 12, 'december': 12
}


def get_current_date_kolkata() -> date:
    """Returns today's date in Asia/Kolkata timezone."""
    return datetime.now(KOLKATA_TZ).date()


def normalize_date(date_str: Optional[str]) -> str:
    """
    Normalizes a date string to 'YYYY-MM-DD'.
    Handles DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY, written months, extended dates.
    Returns empty string if date is missing or cannot be parsed.
    """
    if not date_str or not isinstance(date_str, str):
        return ""

    raw = date_str.strip()
    if not raw or raw.lower() in ("n/a", "na", "null", "none", "to be announced", "tba", "tbd", "ongoing", "not specified"):
        return ""

    # Check for "extended up to / till <date>" first to grab the latest extension date
    extended_match = re.search(r'(?:extended|last date extended)[\s\w]*?(\d{1,2}[./-]\d{1,2}[./-]\d{4}|\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+\s+\d{4})', raw, re.I)
    if extended_match:
        target_snippet = extended_match.group(1)
        res = _parse_date_token(target_snippet)
        if res:
            return res

    # Try standard token parsing
    parsed = _parse_date_token(raw)
    if parsed:
        return parsed

    # Fallback to dateutil if available
    try:
        from dateutil import parser as dparser
        # Note: in India day is usually first (dayfirst=True)
        dt = dparser.parse(raw, dayfirst=True, fuzzy=True)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        pass

    return ""


def _parse_date_token(token: str) -> Optional[str]:
    """Tries regex matching on token."""
    # 1. DD/MM/YYYY or DD-MM-YYYY
    m1 = re.search(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b', token)
    if m1:
        d, m, y = int(m1.group(1)), int(m1.group(2)), int(m1.group(3))
        # Swap if month > 12 (i.e. YYYY/MM/DD or MM/DD/YYYY)
        if m > 12 and d <= 12:
            d, m = m, d
        try:
            return date(y, m, d).strftime("%Y-%m-%d")
        except ValueError:
            pass

    # 2. DD.MM.YYYY
    m2 = re.search(r'\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b', token)
    if m2:
        d, m, y = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
        if m > 12 and d <= 12:
            d, m = m, d
        try:
            return date(y, m, d).strftime("%Y-%m-%d")
        except ValueError:
            pass

    # 3. YYYY-MM-DD (ISO)
    m3 = re.search(r'\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b', token)
    if m3:
        y, m, d = int(m3.group(1)), int(m3.group(2)), int(m3.group(3))
        try:
            return date(y, m, d).strftime("%Y-%m-%d")
        except ValueError:
            pass

    # 4. DD Month YYYY (e.g. 15 Aug 2026, 15th August 2026, 15-Aug-2026)
    m4 = re.search(r'\b(\d{1,2})(?:st|nd|rd|th)?[\s-]+([A-Za-z]{3,9})[\s-]+(\d{4})\b', token)
    if m4:
        d = int(m4.group(1))
        m_str = m4.group(2).lower()
        y = int(m4.group(3))
        m = MONTH_MAP.get(m_str)
        if m:
            try:
                return date(y, m, d).strftime("%Y-%m-%d")
            except ValueError:
                pass

    # 5. Month DD, YYYY (e.g. August 15, 2026)
    m5 = re.search(r'\b([A-Za-z]{3,9})\s+(\d{1,2})(?:st|nd|rd|th)?[,\s]+(\d{4})\b', token)
    if m5:
        m_str = m5.group(1).lower()
        d = int(m5.group(2))
        y = int(m5.group(3))
        m = MONTH_MAP.get(m_str)
        if m:
            try:
                return date(y, m, d).strftime("%Y-%m-%d")
            except ValueError:
                pass

    return None


def is_deadline_passed(end_date_str: Optional[str]) -> bool:
    """
    Checks if a deadline has passed in Asia/Kolkata timezone.
    If end_date is missing or invalid, returns False (assumed open).
    """
    if not end_date_str:
        return False
    norm = normalize_date(end_date_str)
    if not norm:
        return False
    try:
        deadline = datetime.strptime(norm, "%Y-%m-%d").date()
        today = get_current_date_kolkata()
        return deadline < today
    except Exception:
        return False


def is_vacancy_open(end_date_str: Optional[str]) -> bool:
    """Returns True if vacancy deadline is today or in the future or unknown."""
    return not is_deadline_passed(end_date_str)


def parse_deadline_date(end_date_str: Optional[str]) -> Optional[datetime]:
    """Parses date string into a datetime object via normalized format."""
    if not end_date_str:
        return None
    norm = normalize_date(end_date_str)
    if not norm:
        return None
    try:
        return datetime.strptime(norm, "%Y-%m-%d")
    except Exception:
        return None

