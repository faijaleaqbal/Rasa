"""
Scraper Orchestration and Execution Manager.
Coordinates independent scraper execution with staggered requests,
database run tracking, zero-crash exception isolation, and deduplication.
"""

import time
import logging
from typing import List, Dict, Any, Type

from .base import BaseScraper
from .scholarships_gov import ScholarshipsGovScraper
from .wbmdfc import WBMDFCScraper
from .buddy4study import Buddy4StudyScraper
from .sarkariresult import SarkariResultScraper
from .freejobalert import FreeJobAlertScraper
from .wbpsc import WBPSCScraper
from .wb_employment_bank import WBEmploymentBankScraper
from .psu_careers import PSUCareersScraper

logger = logging.getLogger(__name__)

ALL_SCRAPER_CLASSES: List[Type[BaseScraper]] = [
    ScholarshipsGovScraper,
    WBMDFCScraper,
    Buddy4StudyScraper,
    SarkariResultScraper,
    FreeJobAlertScraper,
    WBPSCScraper,
    WBEmploymentBankScraper,
    PSUCareersScraper,
]


def run_all_scrapers(db_module: Any, stagger_seconds: float = 0.3) -> List[Dict[str, Any]]:
    """
    Executes all registered scrapers sequentially with staggered intervals.
    Inserts newly discovered items into the database and tracks run metrics.
    Returns the list of newly inserted notifications (for Telegram alert dispatch).
    """
    logger.info("Starting execution of all Job & Scholarship scrapers...")
    newly_inserted: List[Dict[str, Any]] = []

    for scraper_cls in ALL_SCRAPER_CLASSES:
        scraper = scraper_cls()
        source_name = scraper.source_name
        run_id = None

        try:
            run_id = db_module.log_scraper_run_start(source_name)
        except Exception as e:
            logger.error(f"Failed to log start of scraper run for {source_name}: {e}")

        items_found = 0
        items_inserted = 0
        status = "success"
        error_msg = None

        try:
            scraped_items = scraper.fetch()
            items_found = len(scraped_items)

            for item in scraped_items:
                item_dict = item.to_dict()
                try:
                    is_new, notif_id = db_module.insert_notification(item_dict)
                    if is_new:
                        items_inserted += 1
                        item_dict["id"] = notif_id
                        newly_inserted.append(item_dict)
                except Exception as ins_err:
                    logger.error(f"Error inserting item from {source_name}: {ins_err}")

        except Exception as scrap_err:
            logger.exception(f"Unhandled exception during scraping of {source_name}: {scrap_err}")
            status = "failed"
            error_msg = str(scrap_err)

        if run_id:
            try:
                db_module.log_scraper_run_finish(
                    run_id=run_id,
                    status=status,
                    items_found=items_found,
                    items_inserted=items_inserted,
                    error=error_msg
                )
            except Exception as e:
                logger.error(f"Failed to log finish of scraper run for {source_name}: {e}")

        # Stagger requests between sources
        time.sleep(stagger_seconds)

    logger.info(f"Scraper execution complete. Found items across sources, newly inserted: {len(newly_inserted)}")
    return newly_inserted
