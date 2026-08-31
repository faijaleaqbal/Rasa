"""
Scrapers Package for Jobs & Scholarships Module.
"""

from .base import BaseScraper
from .scraper_manager import run_all_scrapers, ALL_SCRAPER_CLASSES

__all__ = ["BaseScraper", "run_all_scrapers", "ALL_SCRAPER_CLASSES"]
