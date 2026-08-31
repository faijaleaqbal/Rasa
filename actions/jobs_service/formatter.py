"""
Telegram Message Formatter for Jobs & Scholarships Notifications.
Adheres strictly to the specification formats for Full and Short notifications with Urgency Badges.
"""

import re
from datetime import datetime
from typing import Dict, Any, Optional, Union
from .models import NotificationItem
from .tagger import get_tags_for_category
from .date_parser import parse_deadline_date

MAX_TELEGRAM_MSG_LEN = 4000


def escape_markdown(text: Optional[str]) -> str:
    """Escapes problematic Markdown characters while preserving clean readability."""
    if not text:
        return ""
    clean = str(text).strip()
    clean = re.sub(r'\n{3,}', '\n\n', clean)
    return clean


def get_deadline_urgency_badge(end_date_str: Optional[str]) -> str:
    """
    Returns an attention-grabbing urgency indicator based on days remaining.
    """
    if not end_date_str:
        return "🟢 [Open]"

    dt = parse_deadline_date(end_date_str)
    if not dt:
        return "🟢 [Open]"

    now = datetime.now()
    days_left = (dt.date() - now.date()).days

    if days_left < 0:
        return "⚪ [Closed]"
    elif days_left == 0:
        return "🔴 [URGENT: Last Day Today!]"
    elif days_left <= 2:
        return f"🔴 [URGENT: Only {days_left} Days Left!]"
    elif days_left <= 7:
        return f"🟡 [Closing This Week ({days_left}d)]"
    else:
        return "🟢 [Active]"


def format_scholarship_full(item: Union[NotificationItem, Dict[str, Any]]) -> str:
    """
    Scholarship full template with urgency badge.
    """
    d = item.to_dict() if isinstance(item, NotificationItem) else item
    name = escape_markdown(d.get("title") or "Scholarship Announcement")
    start = d.get("start_date") or "Open"
    last = d.get("end_date") or "Refer Notification"
    eligibility = escape_markdown(d.get("eligibility") or "Refer Official Guidelines")
    docs = escape_markdown(d.get("documents") or "Marksheet, Income Cert, ID Proof, Bank Passbook")
    apply_link = d.get("apply_link") or d.get("source_url") or "https://scholarships.gov.in"
    badge = get_deadline_urgency_badge(d.get("end_date"))

    tags = get_tags_for_category("scholarship", name, d.get("organization", ""))
    tag_str = f"\n\n{' '.join(tags)}" if tags else ""

    msg = (
        f"🎓 SCHOLARSHIP: {name} {badge}\n"
        f"📅 Start Date: {start}\n"
        f"📅 Last Date: {last}\n"
        f"✅ Eligibility: {eligibility}\n"
        f"📄 Documents Required: {docs}\n"
        f"🔗 Apply Link: {apply_link}"
        f"{tag_str}"
    )
    return msg[:MAX_TELEGRAM_MSG_LEN]


def format_scholarship_short(item: Union[NotificationItem, Dict[str, Any]]) -> str:
    """
    Scholarship short template.
    """
    d = item.to_dict() if isinstance(item, NotificationItem) else item
    name = escape_markdown(d.get("title") or "Scholarship Announcement")
    last = d.get("end_date") or "Open"
    apply_link = d.get("apply_link") or d.get("source_url") or "https://scholarships.gov.in"
    badge = get_deadline_urgency_badge(d.get("end_date"))

    tags = get_tags_for_category("scholarship", name, d.get("organization", ""))
    tag_str = f" {' '.join(tags)}" if tags else ""

    msg = f"🎓 {name} {badge} | Last Date: {last} | Apply: {apply_link}{tag_str}"
    return msg[:MAX_TELEGRAM_MSG_LEN]


def format_job_full(item: Union[NotificationItem, Dict[str, Any]]) -> str:
    """
    Job full template with urgency badge.
    """
    d = item.to_dict() if isinstance(item, NotificationItem) else item
    cat = d.get("category", "job_central")
    title = escape_markdown(d.get("title") or "Job Vacancy")
    org = escape_markdown(d.get("organization") or "Government of India / West Bengal")
    loc = escape_markdown(d.get("location") or ("West Bengal" if cat == "job_wb" else "All India"))
    start = d.get("start_date") or "Open"
    last = d.get("end_date") or "Refer Notification"
    eligibility = escape_markdown(d.get("eligibility") or "Refer Official Notification")
    docs = escape_markdown(d.get("documents") or "Photo, Signature, Educational Certificates, ID Proof")
    apply_link = d.get("apply_link") or d.get("source_url") or "https://wbpsc.gov.in"
    badge = get_deadline_urgency_badge(d.get("end_date"))

    tags = get_tags_for_category(cat, title, org)
    tag_str = f"\n\n{' '.join(tags)}" if tags else ""

    msg = (
        f"💼 JOB: {title} {badge}\n"
        f"🏢 Organization: {org}\n"
        f"📍 Location: {loc}\n"
        f"📅 Start Date: {start}\n"
        f"📅 Last Date: {last}\n"
        f"✅ Eligibility: {eligibility}\n"
        f"📄 Documents Required: {docs}\n"
        f"🔗 Apply Link: {apply_link}"
        f"{tag_str}"
    )
    return msg[:MAX_TELEGRAM_MSG_LEN]


def format_job_short(item: Union[NotificationItem, Dict[str, Any]]) -> str:
    """
    Job short template with urgency badge.
    """
    d = item.to_dict() if isinstance(item, NotificationItem) else item
    cat = d.get("category", "job_central")
    title = escape_markdown(d.get("title") or "Job Vacancy")
    org = escape_markdown(d.get("organization") or "Government Agency")
    last = d.get("end_date") or "Open"
    apply_link = d.get("apply_link") or d.get("source_url") or "https://wbpsc.gov.in"
    badge = get_deadline_urgency_badge(d.get("end_date"))

    tags = get_tags_for_category(cat, title, org)
    tag_str = f" {' '.join(tags)}" if tags else ""

    msg = f"💼 {title} ({org}) {badge} | Last Date: {last} | Apply: {apply_link}{tag_str}"
    return msg[:MAX_TELEGRAM_MSG_LEN]


def format_notification(item: Union[NotificationItem, Dict[str, Any]], format_pref: str = "short") -> str:
    """Universal dispatcher for formatting based on item type and format_pref."""
    d = item.to_dict() if isinstance(item, NotificationItem) else item
    cat = d.get("category", "job_central")

    if cat == "scholarship":
        if format_pref == "full":
            return format_scholarship_full(d)
        return format_scholarship_short(d)
    else:
        if format_pref == "full":
            return format_job_full(d)
        return format_job_short(d)
