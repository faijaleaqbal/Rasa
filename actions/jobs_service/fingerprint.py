"""
Deterministic Canonical Fingerprinting for Jobs & Scholarships Deduplication.
"""

import re
import hashlib
from typing import Optional, Dict, Any
from urllib.parse import urlparse, urlunparse

OFFICIAL_DOMAINS = {
    "scholarships.gov.in",
    "wbmdfcscholarship.wb.gov.in",
    "wbpsc.gov.in",
    "employmentbankwb.gov.in",
    "sail.co.in",
    "sailcareers.com",
    "ongcindia.com",
    "ntpc.co.in",
    "coalindia.in",
    "uidai.gov.in",
    "upsc.gov.in",
    "ssc.gov.in",
    "ssc.nic.in",
    "ibps.in",
    "indianrailways.gov.in",
    "rrbcdg.gov.in"
}


def normalize_text(text: Optional[str]) -> str:
    """Normalizes string for fingerprinting: lowercase, strip punctuation and extra spaces."""
    if not text:
        return ""
    clean = re.sub(r'[^\w\s]', ' ', text.lower())
    return " ".join(clean.split())


def normalize_url(url: Optional[str]) -> str:
    """Normalizes URL by stripping query parameters, fragment, and trailing slashes."""
    if not url:
        return ""
    try:
        parsed = urlparse(url.strip())
        # Clean scheme and netloc to lowercase, strip trailing slash
        path = parsed.path.rstrip("/")
        # Ignore common tracking params
        return f"{parsed.netloc.lower()}{path}"
    except Exception:
        return url.strip().lower().rstrip("/")


def generate_fingerprint(
    category: str,
    title: str,
    organization: str = "",
    start_date: str = "",
    end_date: str = "",
    apply_link: str = ""
) -> str:
    """
    Generates a canonical SHA-256 fingerprint from:
    normalized: category + title + organization + start_date + end_date + apply_link
    """
    norm_cat = normalize_text(category)
    norm_title = normalize_text(title)
    norm_org = normalize_text(organization)
    norm_start = (start_date or "").strip()
    norm_end = (end_date or "").strip()
    norm_link = normalize_url(apply_link)

    seed_str = f"{norm_cat}|{norm_title}|{norm_org}|{norm_start}|{norm_end}|{norm_link}"
    return hashlib.sha256(seed_str.encode("utf-8")).hexdigest()


def is_official_source(source_url_or_name: str) -> bool:
    """Checks if a source or URL belongs to an official government/portal domain."""
    if not source_url_or_name:
        return False
    lower = source_url_or_name.lower()
    for domain in OFFICIAL_DOMAINS:
        if domain in lower:
            return True
    return False
