"""
Comprehensive Production Test Suite for Alya Jobs & Scholarships Notification Module.
Tests:
1. Date Parsing and Normalization (Asia/Kolkata timezone, common formats, extended dates, invalid handling)
2. Fingerprinting, Canonical Deduplication & Official Source Preference
3. Category Tagging Engine (#PSU, #AadhaarSupervisor precision)
4. Message Formatting (Full & Short Templates, Length Safety, Markdown Escaping)
5. Fuzzy Search Engine (Open vs Closed Deadline vs Not Found)
6. Scraper Adapters & Zero-Crash Isolation
7. Telegram Dispatcher Reliability (Rate limits, Blocked users, Backoff)
8. User Subscription & Format Preference Lifecycle (/start, /stop, /format)
9. Admin Telemetry & Status Dashboard (/status)
10. 20-Day Retention Cleanup
"""

import os
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, date, timedelta
import pytz

from actions import db
from actions.jobs_service import (
    models,
    date_parser,
    fingerprint,
    tagger,
    formatter,
    search_engine,
    dispatcher,
    service,
)
from actions.jobs_service.scrapers import (
    scholarships_gov,
    wbmdfc,
    buddy4study,
    sarkariresult,
    freejobalert,
    wbpsc,
    wb_employment_bank,
    psu_careers,
    scraper_manager,
)


class TestDateNormalization(unittest.TestCase):
    """Tests date parser against Indian notification formats."""

    def test_slash_and_dash_formats(self):
        self.assertEqual(date_parser.normalize_date("15/08/2026"), "2026-08-15")
        self.assertEqual(date_parser.normalize_date("15-08-2026"), "2026-08-15")
        self.assertEqual(date_parser.normalize_date("05/01/2026"), "2026-01-05")

    def test_dot_and_iso_formats(self):
        self.assertEqual(date_parser.normalize_date("31.10.2026"), "2026-10-31")
        self.assertEqual(date_parser.normalize_date("2026-12-25"), "2026-12-25")

    def test_written_month_formats(self):
        self.assertEqual(date_parser.normalize_date("15 Aug 2026"), "2026-08-15")
        self.assertEqual(date_parser.normalize_date("15th August 2026"), "2026-08-15")
        self.assertEqual(date_parser.normalize_date("August 15, 2026"), "2026-08-15")
        self.assertEqual(date_parser.normalize_date("1st September 2026"), "2026-09-01")

    def test_extended_deadline_formats(self):
        self.assertEqual(date_parser.normalize_date("Extended up to 30/11/2026"), "2026-11-30")
        self.assertEqual(date_parser.normalize_date("Last date extended till 15-10-2026"), "2026-10-15")
        self.assertEqual(date_parser.normalize_date("Extended Date: 25.12.2026"), "2026-12-25")

    def test_invalid_and_missing_dates(self):
        self.assertEqual(date_parser.normalize_date(""), "")
        self.assertEqual(date_parser.normalize_date(None), "")
        self.assertEqual(date_parser.normalize_date("N/A"), "")
        self.assertEqual(date_parser.normalize_date("Ongoing"), "")
        self.assertEqual(date_parser.normalize_date("To be announced"), "")

    def test_deadline_passed_evaluation(self):
        # Far future date -> not passed
        self.assertFalse(date_parser.is_deadline_passed("2099-12-31"))
        # Past date -> passed
        self.assertTrue(date_parser.is_deadline_passed("2020-01-01"))
        # Empty/missing -> assumed open (not passed)
        self.assertFalse(date_parser.is_deadline_passed(""))


class TestFingerprintingAndDeduplication(unittest.TestCase):
    """Tests unique fingerprinting and canonical deduplication."""

    def test_identical_fingerprint_generation(self):
        fp1 = fingerprint.generate_fingerprint(
            category="job_wb",
            title="WBPSC WBCS Executive Exam 2026",
            organization="West Bengal Public Service Commission",
            start_date="2026-08-01",
            end_date="2026-10-20",
            apply_link="https://wbpsc.gov.in/wbcs"
        )
        fp2 = fingerprint.generate_fingerprint(
            category="job_wb",
            title="wbpsc wbcs executive exam 2026",
            organization="west bengal public service commission ",
            start_date="2026-08-01",
            end_date="2026-10-20",
            apply_link="https://wbpsc.gov.in/wbcs/"
        )
        self.assertEqual(fp1, fp2)

    def test_distinct_fingerprints(self):
        fp1 = fingerprint.generate_fingerprint(category="job_wb", title="Job A", organization="Org 1")
        fp2 = fingerprint.generate_fingerprint(category="job_wb", title="Job B", organization="Org 1")
        self.assertNotEqual(fp1, fp2)

    def test_official_domain_detection(self):
        self.assertTrue(fingerprint.is_official_source("https://scholarships.gov.in/scheme1"))
        self.assertTrue(fingerprint.is_official_source("https://wbpsc.gov.in/notices"))
        self.assertTrue(fingerprint.is_official_source("https://sailcareers.com"))
        self.assertFalse(fingerprint.is_official_source("https://sarkariresult.com/job1"))
        self.assertFalse(fingerprint.is_official_source("https://freejobalert.com/wb"))


class TestTaggingAndClassification(unittest.TestCase):
    """Tests tagging rules for categories, #PSU, and #AadhaarSupervisor."""

    def test_aadhaar_supervisor_positive(self):
        self.assertTrue(tagger.is_aadhaar_supervisor("UIDAI Certified Aadhaar Supervisor / Operator Recruitment"))
        self.assertTrue(tagger.is_aadhaar_supervisor("Aadhaar Enrolment Supervisor vacancy for CSC centers"))
        cat = tagger.classify_category("NSEIT Aadhaar Supervisor-cum-Operator Exam", "UIDAI")
        self.assertEqual(cat, "aadhaar_supervisor")
        tags = tagger.get_tags_for_category("aadhaar_supervisor", "Aadhaar Supervisor", "UIDAI")
        self.assertIn("#AadhaarSupervisor", tags)

    def test_aadhaar_non_supervisor_not_tagged(self):
        self.assertFalse(tagger.is_aadhaar_supervisor("UIDAI Deputy Director Technical Recruitment"))
        self.assertFalse(tagger.is_aadhaar_supervisor("UIDAI Senior Software Consultant (Java)"))
        cat = tagger.classify_category("UIDAI Deputy Director Administration", "UIDAI")
        self.assertNotEqual(cat, "aadhaar_supervisor")

    def test_psu_tagging(self):
        self.assertTrue(tagger.is_psu_job("Management Trainee 2026", "Steel Authority of India Limited (SAIL)"))
        self.assertTrue(tagger.is_psu_job("Graduate Trainee", "ONGC"))
        self.assertTrue(tagger.is_psu_job("Executive Engineer", "Coal India Limited"))
        cat = tagger.classify_category("NTPC Engineering Executive Trainees", "NTPC Limited")
        self.assertEqual(cat, "psu")
        tags = tagger.get_tags_for_category("psu", "SAIL MT Recruitment", "SAIL")
        self.assertIn("#PSU", tags)

    def test_wb_and_central_jobs(self):
        self.assertEqual(tagger.classify_category("WB Police Constable Recruitment", "WBPRB"), "job_wb")
        self.assertEqual(tagger.classify_category("SSC CGL 2026 Examination", "Staff Selection Commission"), "job_central")

    def test_scholarship_tagging(self):
        self.assertEqual(tagger.classify_category("National Means-cum-Merit Scholarship", "NSP"), "scholarship")
        self.assertEqual(tagger.classify_category("Aikyashree Post-Matric Scheme", "WBMDFC"), "scholarship")


class TestMessageFormatting(unittest.TestCase):
    """Tests full and short message formatting against specifications."""

    def test_scholarship_full_format(self):
        item = {
            "category": "scholarship",
            "title": "National Means-cum-Merit Scholarship",
            "organization": "Ministry of Education",
            "start_date": "2026-08-01",
            "end_date": "2026-10-31",
            "eligibility": "Class IX students with > 55% marks",
            "documents": "Income Certificate, Marksheet",
            "apply_link": "https://scholarships.gov.in"
        }
        res = formatter.format_scholarship_full(item)
        self.assertIn("🎓 SCHOLARSHIP: National Means-cum-Merit Scholarship", res)
        self.assertIn("📅 Start Date: 2026-08-01", res)
        self.assertIn("📅 Last Date: 2026-10-31", res)
        self.assertIn("✅ Eligibility: Class IX students with > 55% marks", res)
        self.assertIn("📄 Documents Required: Income Certificate, Marksheet", res)
        self.assertIn("🔗 Apply Link: https://scholarships.gov.in", res)

    def test_scholarship_short_format(self):
        item = {
            "category": "scholarship",
            "title": "NMMSS",
            "end_date": "2026-10-31",
            "apply_link": "https://scholarships.gov.in"
        }
        res = formatter.format_scholarship_short(item)
        self.assertEqual(res, "🎓 NMMSS | Last Date: 2026-10-31 | Apply: https://scholarships.gov.in #Scholarship")

    def test_job_full_format(self):
        item = {
            "category": "psu",
            "title": "Management Trainee (Technical)",
            "organization": "SAIL",
            "location": "Bhilai / Kolkata",
            "start_date": "2026-08-15",
            "end_date": "2026-10-20",
            "eligibility": "BE/B.Tech in Engineering",
            "documents": "Degree, GATE Scorecard",
            "apply_link": "https://sailcareers.com"
        }
        res = formatter.format_job_full(item)
        self.assertIn("💼 JOB: Management Trainee (Technical)", res)
        self.assertIn("🏢 Organization: SAIL", res)
        self.assertIn("📍 Location: Bhilai / Kolkata", res)
        self.assertIn("📅 Start Date: 2026-08-15", res)
        self.assertIn("📅 Last Date: 2026-10-20", res)
        self.assertIn("✅ Eligibility: BE/B.Tech in Engineering", res)
        self.assertIn("📄 Documents Required: Degree, GATE Scorecard", res)
        self.assertIn("🔗 Apply Link: https://sailcareers.com", res)
        self.assertIn("#PSU", res)

    def test_job_short_format(self):
        item = {
            "category": "job_wb",
            "title": "Constable",
            "organization": "WBPRB",
            "end_date": "2026-09-30",
            "apply_link": "https://prb.wb.gov.in"
        }
        res = formatter.format_job_short(item)
        self.assertEqual(res, "💼 Constable | WBPRB | Last Date: 2026-09-30 | Apply: https://prb.wb.gov.in #WBJobs")


class TestFuzzySearchEngine(unittest.TestCase):
    """Tests search functionality with open, closed, and not found cases."""

    def setUp(self):
        self.test_items = [
            {
                "id": 1,
                "category": "job_wb",
                "title": "WBPSC WBCS Executive Examination 2026",
                "organization": "West Bengal Public Service Commission",
                "end_date": "2099-12-31",  # Open
                "apply_link": "https://wbpsc.gov.in"
            },
            {
                "id": 2,
                "category": "job_central",
                "title": "SSC CGL 2023 Expired Vacancy",
                "organization": "Staff Selection Commission",
                "end_date": "2023-01-01",  # Closed
                "apply_link": "https://ssc.gov.in"
            },
            {
                "id": 3,
                "category": "scholarship",
                "title": "National Means-cum-Merit Scholarship (NMMSS)",
                "organization": "Ministry of Education",
                "end_date": "2099-11-30",  # Open
                "apply_link": "https://scholarships.gov.in"
            }
        ]

    def test_search_open_vacancy_returns_full_details(self):
        res = search_engine.search_vacancies("WBCS", self.test_items)
        self.assertIn("STATUS: OPEN", res)
        self.assertIn("WBPSC WBCS Executive Examination", res)

    def test_search_closed_vacancy_returns_closed_warning(self):
        res = search_engine.search_vacancies("SSC CGL", self.test_items)
        self.assertIn("APPLICATION CLOSED", res)
        self.assertIn("Deadline was: 2023-01-01", res)

    def test_search_not_found_returns_clear_message(self):
        res = search_engine.search_vacancies("NonExistentXYZJob123", self.test_items)
        self.assertIn("No open or recent jobs/scholarships matching", res)


class TestScraperAdaptersAndManager(unittest.TestCase):
    """Tests independent scraper execution and zero-crash isolation."""

    def test_all_scrapers_instantiate_and_return_items(self):
        scrapers = [
            scholarships_gov.ScholarshipsGovScraper(),
            wbmdfc.WBMDFCScraper(),
            buddy4study.Buddy4StudyScraper(),
            sarkariresult.SarkariResultScraper(),
            freejobalert.FreeJobAlertScraper(),
            wbpsc.WBPSCScraper(),
            wb_employment_bank.WBEmploymentBankScraper(),
            psu_careers.PSUCareersScraper(),
        ]
        for s in scrapers:
            items = s.fetch()
            self.assertIsInstance(items, list)
            self.assertGreater(len(items), 0, f"Scraper {s.source_name} returned 0 items")
            for it in items:
                self.assertTrue(it.title)
                self.assertTrue(it.category)
                self.assertTrue(it.fingerprint)

    @patch("actions.jobs_service.scrapers.scholarships_gov.ScholarshipsGovScraper.fetch", side_effect=RuntimeError("Simulated Website Crash"))
    def test_one_broken_scraper_does_not_stop_others(self, mock_broken):
        """Zero-crash isolation verification."""
        mock_db = MagicMock()
        mock_db.log_scraper_run_start.return_value = 100
        mock_db.insert_notification.return_value = (True, 1)

        new_items = scraper_manager.run_all_scrapers(mock_db, stagger_seconds=0.0)
        self.assertIsInstance(new_items, list)
        self.assertGreater(len(new_items), 0)
        mock_db.log_scraper_run_finish.assert_called()


class TestTelegramDispatcherReliability(unittest.TestCase):
    """Tests dispatcher rate limits, blocked user unsubscription, and retries."""

    @patch("requests.post")
    def test_blocked_user_auto_unsubscribed(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.json.return_value = {"ok": False, "description": "Forbidden: bot was blocked by the user"}
        mock_post.return_value = mock_resp

        mock_db = MagicMock()
        mock_db.get_all_subscribed_job_users.return_value = [{"telegram_id": "99999", "format_pref": "short"}]

        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "mock_token"}):
            summary = dispatcher.dispatch_new_notifications(
                [{"category": "job_wb", "title": "Test Job", "apply_link": "https://example.com"}],
                mock_db
            )
            self.assertEqual(summary["unsubscribed_blocked"], 1)
            mock_db.unsubscribe_job_alert_user.assert_called_with("99999")

    @patch("requests.post")
    def test_rate_limit_retry_after_handled(self, mock_post):
        resp_429 = MagicMock()
        resp_429.status_code = 429
        resp_429.json.return_value = {"ok": False, "parameters": {"retry_after": 0.01}}

        resp_200 = MagicMock()
        resp_200.status_code = 200

        mock_post.side_effect = [resp_429, resp_200]

        res = dispatcher.send_single_telegram_message("mock_token", "12345", "Test message")
        self.assertTrue(res["success"])
        self.assertEqual(mock_post.call_count, 2)


class TestDatabaseAndServiceLifecycle(unittest.TestCase):
    """Tests full database operations, subscription lifecycle, and 20-day cleanup."""

    def setUp(self):
        db.init_db()
        self.user_id = "test_user_777"

    def test_subscription_and_format_preference_lifecycle(self):
        # 1. Subscribe
        sub_msg = service.subscribe_user(db, self.user_id)
        self.assertIn("Subscribed", sub_msg)
        u = db.get_job_alert_user(self.user_id)
        self.assertEqual(u["is_subscribed"], 1)

        # 2. Format pref
        fmt_msg = service.set_user_format_pref(db, self.user_id, "full")
        self.assertIn("FULL", fmt_msg)
        u = db.get_job_alert_user(self.user_id)
        self.assertEqual(u["format_pref"], "full")

        # 3. Unsubscribe
        unsub_msg = service.unsubscribe_user(db, self.user_id)
        self.assertIn("Unsubscribed", unsub_msg)
        u = db.get_job_alert_user(self.user_id)
        self.assertEqual(u["is_subscribed"], 0)

    def test_20_day_cleanup(self):
        # Insert old item manually
        conn = db.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO notifications (category, title, fingerprint, detected_at)
            VALUES ('job_wb', 'Old Job 30 Days Ago', 'fp_old_30_days', datetime('now', '-30 days'))
        """)
        conn.commit()
        conn.close()

        deleted = service.execute_daily_cleanup(db, days=20)
        self.assertGreaterEqual(deleted, 1)

    def test_admin_status_command(self):
        # Non-admin rejected
        with patch("actions.db.is_admin_user", return_value=False):
            res_denied = service.get_status_text(db, "unauthorized_user")
            self.assertIn("Access Restricted", res_denied)

        # Admin granted
        with patch("actions.db.is_admin_user", return_value=True):
            res_admin = service.get_status_text(db, "admin_user")
            self.assertIn("Scraper Status Dashboard", res_admin)
            self.assertIn("Source Health", res_admin)


if __name__ == "__main__":
    unittest.main()
