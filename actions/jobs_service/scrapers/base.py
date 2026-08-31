"""
Base Scraper Class for Job and Scholarship Data Adapters.
Ensures zero-crash isolation: one broken site never fails other scrapers or Alya.
"""

import time
import logging
import urllib3
from typing import List, Optional, Dict, Any
import requests
from bs4 import BeautifulSoup

from ..models import NotificationItem
from ..date_parser import normalize_date
from ..fingerprint import generate_fingerprint
from ..tagger import classify_category

# Suppress insecure SSL warnings for government websites with legacy SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 (Alya Bot/3.6)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,hi;q=0.8,bn;q=0.7",
}


class BaseScraper:
    source_name: str = "base"
    source_url: str = ""
    default_category: str = "job_central"

    def fetch_html(
        self,
        url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 12,
        verify_ssl: bool = False
    ) -> Optional[str]:
        """Safely fetches HTML content with timeout and error protection."""
        target_url = url or self.source_url
        req_headers = {**DEFAULT_HEADERS, **(headers or {})}

        try:
            resp = requests.get(target_url, headers=req_headers, timeout=timeout, verify=verify_ssl)
            if resp.status_code == 200:
                return resp.text
            else:
                logger.warning(f"[{self.source_name}] HTTP {resp.status_code} from {target_url}")
                return None
        except Exception as e:
            logger.warning(f"[{self.source_name}] Request failed for {target_url}: {e}")
            return None

    def create_item(
        self,
        title: str,
        organization: str = "",
        location: str = "",
        start_date: str = "",
        end_date: str = "",
        eligibility: str = "",
        documents: str = "",
        apply_link: str = "",
        category: Optional[str] = None
    ) -> NotificationItem:
        """Helper to create a fully validated and fingerprinted NotificationItem."""
        clean_title = title.strip()
        clean_org = organization.strip()
        norm_start = normalize_date(start_date)
        norm_end = normalize_date(end_date)
        norm_link = apply_link.strip() or self.source_url

        cat = category or classify_category(
            title=clean_title,
            org=clean_org,
            loc=location,
            source=self.source_name,
            default_cat=self.default_category
        )

        fp = generate_fingerprint(
            category=cat,
            title=clean_title,
            organization=clean_org,
            start_date=norm_start,
            end_date=norm_end,
            apply_link=norm_link
        )

        return NotificationItem(
            category=cat,
            title=clean_title,
            organization=clean_org,
            location=location.strip(),
            start_date=norm_start,
            end_date=norm_end,
            eligibility=eligibility.strip(),
            documents=documents.strip(),
            apply_link=norm_link,
            source=self.source_name,
            source_url=self.source_url,
            fingerprint=fp
        )

    def fetch(self) -> List[NotificationItem]:
        """Override in subclasses to perform scraping and return normalized items."""
        raise NotImplementedError
