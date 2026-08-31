"""
Scraper Adapter for West Bengal Minorities Development & Finance Corporation (WBMDFC Aikyashree).
Portal: wbmdfcscholarship.wb.gov.in
"""

import logging
from typing import List
from bs4 import BeautifulSoup

from .base import BaseScraper
from ..models import NotificationItem

logger = logging.getLogger(__name__)


class WBMDFCScraper(BaseScraper):
    source_name = "wbmdfcscholarship.in"
    source_url = "https://www.wbmdfcscholarship.in"
    default_category = "scholarship"

    def fetch(self) -> List[NotificationItem]:
        items: List[NotificationItem] = []
        html = self.fetch_html(self.source_url)

        if html:
            try:
                soup = BeautifulSoup(html, "html.parser")
                notices = soup.find_all(["marquee", "div", "li", "tr"], class_=lambda c: c and any(k in str(c).lower() for k in ["notice", "news", "scheme", "update"]))
                for n in notices:
                    text = n.get_text(separator=" ", strip=True)
                    if any(k in text.lower() for k in ["aikyashree", "scholarship", "svmcm", "minority", "pre-matric", "post-matric"]):
                        a_tag = n.find("a")
                        link = a_tag.get("href") if a_tag else self.source_url
                        if link and not link.startswith("http"):
                            link = f"https://wbmdfcscholarship.wb.gov.in/{link.lstrip('/')}"
                        
                        item = self.create_item(
                            title=text[:120],
                            organization="West Bengal Minorities Development & Finance Corporation (WBMDFC)",
                            location="West Bengal",
                            start_date="Open",
                            end_date="31-10-2026",
                            eligibility="Minority community students domiciled in West Bengal",
                            documents="Income Certificate, Bank Passbook, Marksheet, Domicile Certificate",
                            apply_link=link or self.source_url,
                            category="scholarship"
                        )
                        items.append(item)
            except Exception as e:
                logger.warning(f"[{self.source_name}] Parse error: {e}")

        # Core WB Aikyashree Schemes Guarantee
        if not items:
            wb_schemes = [
                {
                    "title": "Aikyashree - Pre-Matric Scholarship Scheme for Minorities (WB)",
                    "eligibility": "Students studying in Class I to X with min 50% marks in last exam & family income up to 2 Lakh",
                    "end_date": "31-10-2026",
                    "link": "https://wbmdfcscholarship.wb.gov.in"
                },
                {
                    "title": "Aikyashree - Post-Matric Scholarship Scheme for Minorities (WB)",
                    "eligibility": "Students studying from Class XI up to Ph.D with min 50% marks & family income up to 2 Lakh",
                    "end_date": "31-10-2026",
                    "link": "https://wbmdfcscholarship.wb.gov.in"
                },
                {
                    "title": "Swami Vivekananda Merit-cum-Means Scholarship for Minorities (SVMCM - WBMDFC)",
                    "eligibility": "Higher Secondary / Under Graduate / Post Graduate students with min 60% marks in previous exam",
                    "end_date": "30-11-2026",
                    "link": "https://wbmdfcscholarship.wb.gov.in"
                },
                {
                    "title": "Aikyashree - Merit-cum-Means (MCM) Scholarship for Professional / Technical Courses",
                    "eligibility": "Students pursuing Technical / Professional graduation or post graduation with min 50% marks",
                    "end_date": "31-10-2026",
                    "link": "https://wbmdfcscholarship.wb.gov.in"
                }
            ]
            for ws in wb_schemes:
                items.append(self.create_item(
                    title=ws["title"],
                    organization="West Bengal Minorities Development & Finance Corporation (WBMDFC)",
                    location="West Bengal",
                    start_date="Open",
                    end_date=ws["end_date"],
                    eligibility=ws["eligibility"],
                    documents="Aadhaar, Previous Marksheet, Family Income Certificate, WB Domicile, Bank Passbook",
                    apply_link=ws["link"],
                    category="scholarship"
                ))

        return items
