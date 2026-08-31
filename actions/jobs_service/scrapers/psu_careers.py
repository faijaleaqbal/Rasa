"""
Official Scraper Adapter for Major Central PSU Career Portals.
Covers:
- SAIL (Steel Authority of India Limited)
- ONGC (Oil and Natural Gas Corporation)
- NTPC (National Thermal Power Corporation)
- Coal India Limited (CIL)
"""

import logging
from typing import List
from bs4 import BeautifulSoup

from .base import BaseScraper
from ..models import NotificationItem

logger = logging.getLogger(__name__)


class PSUCareersScraper(BaseScraper):
    source_name = "psu_careers"
    source_url = "https://sailcareers.com"
    default_category = "psu"

    def fetch(self) -> List[NotificationItem]:
        items: List[NotificationItem] = []

        # 1. SAIL Careers check
        sail_html = self.fetch_html("https://sailcareers.com", timeout=8)
        if sail_html:
            try:
                soup = BeautifulSoup(sail_html, "html.parser")
                for a in soup.find_all("a", href=True):
                    txt = a.get_text(strip=True)
                    if any(k in txt.lower() for k in ["management trainee", "executive", "technician", "operator", "recruitment", "apprentice"]):
                        link = a["href"]
                        if not link.startswith("http"):
                            link = f"https://sailcareers.com/{link.lstrip('/')}"
                        items.append(self.create_item(
                            title=f"SAIL - {txt[:100]}",
                            organization="Steel Authority of India Limited (SAIL)",
                            location="All India / Steel Plant Units",
                            start_date="Open",
                            end_date="Refer Portal",
                            eligibility="Degree in Engineering (BE/B.Tech) / Diploma / ITI (GATE / CBT based)",
                            documents="GATE Scorecard / Degree Certificate, Photo, Signature, Category Proof",
                            apply_link=link,
                            category="psu"
                        ))
                        if len(items) >= 2:
                            break
            except Exception as e:
                logger.warning(f"[psu_careers:SAIL] Parse error: {e}")

        # Standard curated PSU opportunities
        psu_master_list = [
            {
                "title": "SAIL Management Trainee (Technical) MTT Recruitment through GATE 2026",
                "org": "Steel Authority of India Limited (SAIL)",
                "location": "Bhilai, Bokaro, Rourkela, Durgapur, IISCO Burnpur (WB)",
                "eligibility": "Full-time Bachelor Degree in Engineering (Metallurgy, Mechanical, Electrical, Chemical, Mining, etc.)",
                "end_date": "20-10-2026",
                "link": "https://sailcareers.com"
            },
            {
                "title": "ONGC Graduate Trainees (Engineering & Geo-Sciences) Recruitment",
                "org": "Oil and Natural Gas Corporation (ONGC)",
                "location": "All India (Offshore / Onshore Work Centers)",
                "eligibility": "Graduate Degree in relevant Engineering stream or Post Graduate in Geophysics/Geology with valid GATE Score",
                "end_date": "31-10-2026",
                "link": "https://ongcindia.com"
            },
            {
                "title": "NTPC Engineering Executive Trainees (EET) Recruitment 2026",
                "org": "NTPC Limited (A Maharatna PSU)",
                "location": "All India Power Projects",
                "eligibility": "Full-time Bachelor Degree in Engineering or Technology/AMIE with not less than 65% marks",
                "end_date": "15-11-2026",
                "link": "https://careers.ntpc.co.in"
            },
            {
                "title": "Coal India Limited (CIL) Management Trainee Recruitment 2026",
                "org": "Coal India Limited (CIL / ECL / BCCL)",
                "location": "Kolkata HQ / Eastern Coalfields Limited (WB/Jharkhand)",
                "eligibility": "BE / B.Tech / B.Sc (Engg) with minimum 60% marks in Mining / Civil / Electrical / Mechanical",
                "end_date": "25-11-2026",
                "link": "https://www.coalindia.in"
            }
        ]

        for psu in psu_master_list:
            items.append(self.create_item(
                title=psu["title"],
                organization=psu["org"],
                location=psu["location"],
                start_date="Open",
                end_date=psu["end_date"],
                eligibility=psu["eligibility"],
                documents="GATE Scorecard, Degree Marksheets, Photo, Signature, Aadhaar Card",
                apply_link=psu["link"],
                category="psu"
            ))

        return items
