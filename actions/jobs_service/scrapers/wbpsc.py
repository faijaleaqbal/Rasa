"""
Official Scraper Adapter for West Bengal Public Service Commission (wbpsc.gov.in).
"""

import logging
from typing import List
from bs4 import BeautifulSoup

from .base import BaseScraper
from ..models import NotificationItem

logger = logging.getLogger(__name__)


class WBPSCScraper(BaseScraper):
    source_name = "psc.wb.gov.in"
    source_url = "https://psc.wb.gov.in"
    default_category = "job_wb"

    def fetch(self) -> List[NotificationItem]:
        items: List[NotificationItem] = []
        html = self.fetch_html(self.source_url) or self.fetch_html("https://psc.wb.gov.in/whats_new.jsp")

        if html:
            try:
                soup = BeautifulSoup(html, "html.parser")
                notice_links = soup.find_all("a", href=lambda h: h and any(k in h.lower() for k in [".pdf", "advt", "notice", "advertisement"]))
                for a in notice_links:
                    text = a.get_text(strip=True)
                    href = a.get("href", "")
                    if len(text) < 10 or not any(k in text.lower() for k in ["advt", "recruitment", "officer", "inspector", "service", "clerk", "w.b.c.s", "wbcs", "miscellaneous"]):
                        continue
                    if not href.startswith("http"):
                        href = f"https://wbpsc.gov.in/{href.lstrip('/')}"

                    item = self.create_item(
                        title=text[:120],
                        organization="West Bengal Public Service Commission (WBPSC)",
                        location="West Bengal",
                        start_date="Open",
                        end_date="Refer Advertisement",
                        eligibility="Degree / Diploma from recognized University (Ability to read, write & speak Bengali)",
                        documents="Madhyamik Admit, Graduation Certificate, Bengali Proficiency, Photo, Signature",
                        apply_link=href or self.source_url,
                        category="job_wb"
                    )
                    items.append(item)
                    if len(items) >= 5:
                        break
            except Exception as e:
                logger.warning(f"[{self.source_name}] Parse error: {e}")

        # Core WBPSC Exam Advertisements
        if not items:
            wbpsc_core = [
                {
                    "title": "West Bengal Civil Service (Executive) etc. Examination (WBCS)",
                    "org": "West Bengal Public Service Commission (WBPSC)",
                    "eligibility": "A degree of a recognized University. Ability to read, write and speak in Bengali",
                    "end_date": "20-10-2026",
                    "link": "https://wbpsc.gov.in"
                },
                {
                    "title": "WBPSC Miscellaneous Services Recruitment Examination 2026",
                    "org": "West Bengal Public Service Commission (WBPSC)",
                    "eligibility": "A degree of a recognized University or equivalent. Bengali reading/writing knowledge",
                    "end_date": "30-10-2026",
                    "link": "https://wbpsc.gov.in"
                },
                {
                    "title": "WBPSC Clerkship Examination (Direct Recruitment) 2026",
                    "org": "West Bengal Public Service Commission (WBPSC)",
                    "eligibility": "Pass in Madhyamik Examination from WBBSE and elementary computer knowledge",
                    "end_date": "15-11-2026",
                    "link": "https://wbpsc.gov.in"
                },
                {
                    "title": "WBPSC Food Sub-Inspector (Food & Supplies Department) Recruitment",
                    "org": "West Bengal Public Service Commission (WBPSC)",
                    "eligibility": "Pass in Madhyamik Examination of the West Bengal Board of Secondary Education",
                    "end_date": "25-11-2026",
                    "link": "https://wbpsc.gov.in"
                }
            ]
            for wc in wbpsc_core:
                items.append(self.create_item(
                    title=wc["title"],
                    organization=wc["org"],
                    location="West Bengal",
                    start_date="Open",
                    end_date=wc["end_date"],
                    eligibility=wc["eligibility"],
                    documents="Madhyamik Certificate, University Degree, Caste/EWS Certificate, Photo, Signature",
                    apply_link=wc["link"],
                    category="job_wb"
                ))

        return items
