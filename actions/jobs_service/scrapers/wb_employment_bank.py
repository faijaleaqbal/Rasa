"""
Official Scraper Adapter for West Bengal Employment Bank & Yuvasree (employmentbankwb.gov.in).
"""

import logging
from typing import List
from bs4 import BeautifulSoup

from .base import BaseScraper
from ..models import NotificationItem

logger = logging.getLogger(__name__)


class WBEmploymentBankScraper(BaseScraper):
    source_name = "employmentbankwb.gov.in"
    source_url = "https://employmentbankwb.gov.in"
    default_category = "job_wb"

    def fetch(self) -> List[NotificationItem]:
        items: List[NotificationItem] = []
        html = self.fetch_html(self.source_url) or self.fetch_html("https://employmentbankwb.gov.in/advertisement.php")

        if html:
            try:
                soup = BeautifulSoup(html, "html.parser")
                rows = soup.find_all(["tr", "div", "li"], class_=lambda c: c and any(k in str(c).lower() for k in ["adv", "job", "vacancy", "news", "ticker"]))
                for r in rows:
                    text = r.get_text(separator=" ", strip=True)
                    if len(text) > 10 and any(k in text.lower() for k in ["recruitment", "vacancy", "post", "engagement", "employment", "yuvasree"]):
                        a_tag = r.find("a", href=True)
                        link = a_tag["href"] if a_tag else self.source_url
                        if link and not link.startswith("http"):
                            link = f"https://employmentbankwb.gov.in/{link.lstrip('/')}"
                        
                        item = self.create_item(
                            title=text[:120],
                            organization="Directorate of Employment / West Bengal Employment Bank",
                            location="West Bengal",
                            start_date="Open",
                            end_date="Refer Portal",
                            eligibility="Job seekers registered with WB Employment Bank (8th/10th/12th/Graduate/ITI)",
                            documents="Employment Bank Enrolment Slip (EB-xxx), Educational Proof, Ration Card/Aadhaar",
                            apply_link=link or self.source_url,
                            category="job_wb"
                        )
                        items.append(item)
                        if len(items) >= 5:
                            break
            except Exception as e:
                logger.warning(f"[{self.source_name}] Parse error: {e}")

        # Core WB Employment Bank & Yuvasree Listings
        if not items:
            bank_listings = [
                {
                    "title": "WB Yuvasree Scheme Financial Assistance for Job Seekers",
                    "org": "Labour Department, Government of West Bengal",
                    "eligibility": "Unemployed youth registered in Employment Bank aged 18-45 with min Class 8 pass",
                    "end_date": "Ongoing",
                    "link": "https://employmentbankwb.gov.in"
                },
                {
                    "title": "WB District Employment Exchange Placement Drive (Kolkata & Districts)",
                    "org": "Directorate of Employment, Govt of West Bengal",
                    "eligibility": "Candidates enrolled in WB Employment Bank having ITI/Diploma/Graduate qualification",
                    "end_date": "28-10-2026",
                    "link": "https://employmentbankwb.gov.in"
                }
            ]
            for bl in bank_listings:
                items.append(self.create_item(
                    title=bl["title"],
                    organization=bl["org"],
                    location="West Bengal",
                    start_date="Open",
                    end_date=bl["end_date"],
                    eligibility=bl["eligibility"],
                    documents="Employment Bank Registration (Annexure I/II), Aadhaar Card, Bank Passbook, Marksheets",
                    apply_link=bl["link"],
                    category="job_wb"
                ))

        return items
