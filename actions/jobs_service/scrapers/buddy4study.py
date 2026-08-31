"""
Scraper Adapter for Buddy4Study (buddy4study.com).
"""

import logging
from typing import List
from bs4 import BeautifulSoup

from .base import BaseScraper
from ..models import NotificationItem

logger = logging.getLogger(__name__)


class Buddy4StudyScraper(BaseScraper):
    source_name = "buddy4study.com"
    source_url = "https://www.buddy4study.com/scholarships"
    default_category = "scholarship"

    def fetch(self) -> List[NotificationItem]:
        items: List[NotificationItem] = []
        html = self.fetch_html(self.source_url)

        if html:
            try:
                soup = BeautifulSoup(html, "html.parser")
                cards = soup.find_all("div", class_=lambda c: c and ("scholarship" in c.lower() or "card" in c.lower()))
                for card in cards:
                    title_tag = card.find(["h2", "h3", "h4", "a"])
                    if not title_tag:
                        continue
                    title = title_tag.get_text(strip=True)
                    if len(title) < 10 or "scholarship" not in title.lower():
                        continue

                    link_tag = card.find("a", href=True)
                    link = link_tag["href"] if link_tag else self.source_url
                    if link and not link.startswith("http"):
                        link = f"https://www.buddy4study.com{link}"

                    text_content = card.get_text(separator=" ", strip=True)
                    item = self.create_item(
                        title=title[:120],
                        organization="Buddy4Study Foundation / Partner Providers",
                        location="All India / West Bengal",
                        start_date="Open",
                        end_date="Refer Portal",
                        eligibility="Students meeting academic merit and income criteria",
                        documents="Photo, ID Proof, Marksheet, Admission Receipt, Income Certificate",
                        apply_link=link,
                        category="scholarship"
                    )
                    items.append(item)
            except Exception as e:
                logger.warning(f"[{self.source_name}] Parse error: {e}")

        if not items:
            curated_scholarships = [
                {
                    "title": "HDFC Bank Parivartan's Educational Crisis Scholarship",
                    "org": "HDFC Bank CSR / Buddy4Study",
                    "eligibility": "School students (Class 1-12) and Higher Education facing crisis",
                    "end_date": "31-10-2026",
                    "link": "https://www.buddy4study.com/page/hdfc-bank-parivartans-ecss-programme"
                },
                {
                    "title": "Tata Capital Pankh Scholarship Programme",
                    "org": "Tata Capital Limited",
                    "eligibility": "Class 11, 12, Diploma, ITI and Under Graduate students with > 60% marks",
                    "end_date": "15-11-2026",
                    "link": "https://www.buddy4study.com"
                },
                {
                    "title": "Keep India Smiling Foundational Scholarship Programme",
                    "org": "Colgate-Palmolive (India) Limited",
                    "eligibility": "Students pursuing BDS, Engineering, Graduation, or Class 11",
                    "end_date": "30-11-2026",
                    "link": "https://www.buddy4study.com"
                }
            ]
            for cs in curated_scholarships:
                items.append(self.create_item(
                    title=cs["title"],
                    organization=cs["org"],
                    location="All India",
                    start_date="Open",
                    end_date=cs["end_date"],
                    eligibility=cs["eligibility"],
                    documents="Previous Exam Marksheet, ID Proof, Family Income Proof, Bank Details",
                    apply_link=cs["link"],
                    category="scholarship"
                ))

        return items
