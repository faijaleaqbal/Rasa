"""
Comprehensive Test Suite for Alya Timezone-Aware Reminder & Scheduler System.
"""

import os
import unittest
import zoneinfo
from datetime import datetime, timedelta, timezone

from actions import db
from actions.timezone_utils import (
    DEFAULT_TIMEZONE,
    DEFAULT_TIMEZONE_NAME,
    resolve_timezone,
    parse_natural_datetime,
    to_utc_iso,
    from_utc_iso_to_user_tz,
    get_timezone_abbreviation,
    split_reminder_command,
)
from actions import skills_utilities as utils
from actions import scheduler


class TestTimezoneResolution(unittest.TestCase):
    def test_default_timezone_is_ist(self):
        tz = resolve_timezone(None)
        self.assertEqual(str(tz), "Asia/Kolkata")
        # Offset should be UTC+05:30
        now = datetime.now(tz)
        self.assertEqual(now.utcoffset(), timedelta(hours=5, minutes=30))

    def test_common_aliases(self):
        self.assertEqual(str(resolve_timezone("IST")), "Asia/Kolkata")
        self.assertEqual(str(resolve_timezone("EST")), "America/New_York")
        self.assertEqual(str(resolve_timezone("PST")), "America/Los_Angeles")
        self.assertEqual(str(resolve_timezone("CST")), "America/Chicago")
        self.assertEqual(str(resolve_timezone("UTC")), "UTC")
        self.assertEqual(str(resolve_timezone("GMT")), "UTC")
        self.assertEqual(str(resolve_timezone("BST")), "Europe/London")
        self.assertEqual(str(resolve_timezone("DUBAI")), "Asia/Dubai")
        self.assertEqual(str(resolve_timezone("TOKYO")), "Asia/Tokyo")


class TestReminderDatetimeParsing(unittest.TestCase):
    def test_11am_ist_reminder(self):
        """User: 'remind me at 11 AM' -> Exactly 11:00 AM IST."""
        ist = zoneinfo.ZoneInfo("Asia/Kolkata")
        now_ist = datetime.now(ist)

        dt, tz, display, is_rec, rec_pat = parse_natural_datetime("at 11:00 AM", user_tz=ist)
        self.assertEqual(str(tz), "Asia/Kolkata")
        self.assertEqual(dt.hour, 11)
        self.assertEqual(dt.minute, 0)
        self.assertEqual(dt.tzinfo, ist)
        self.assertIn("11:00 AM IST", display)

        # UTC conversion: 11:00 AM IST = 05:30 AM UTC
        utc_iso = to_utc_iso(dt)
        utc_dt = datetime.fromisoformat(utc_iso)
        self.assertEqual(utc_dt.hour, 5)
        self.assertEqual(utc_dt.minute, 30)

    def test_tomorrow_9am_ist_reminder(self):
        """User: 'remind me tomorrow at 9 AM' -> Tomorrow 9:00 AM IST."""
        ist = zoneinfo.ZoneInfo("Asia/Kolkata")
        now_ist = datetime.now(ist)
        expected_date = (now_ist + timedelta(days=1)).date()

        dt, tz, display, is_rec, rec_pat = parse_natural_datetime("tomorrow at 9 AM", user_tz=ist)
        self.assertEqual(dt.date(), expected_date)
        self.assertEqual(dt.hour, 9)
        self.assertEqual(dt.minute, 0)
        self.assertEqual(dt.tzinfo, ist)
        self.assertIn("09:00 AM IST", display)

    def test_relative_in_2_hours(self):
        """User: 'in 2 hours' -> Current IST + 2 hours."""
        ist = zoneinfo.ZoneInfo("Asia/Kolkata")
        before = datetime.now(ist)
        dt, tz, display, is_rec, rec_pat = parse_natural_datetime("in 2 hours", user_tz=ist)
        after = datetime.now(ist)

        diff = dt - before
        self.assertAlmostEqual(diff.total_seconds(), 7200, delta=5)
        self.assertEqual(dt.tzinfo, ist)

    def test_explicit_non_ist_timezone(self):
        """User: '11 AM EST' -> Respects explicit EST (America/New_York)."""
        dt, tz, display, is_rec, rec_pat = parse_natural_datetime("11 AM EST")
        self.assertEqual(str(tz), "America/New_York")
        self.assertEqual(dt.hour, 11)
        self.assertEqual(dt.minute, 0)
        # Should display EDT/EST
        self.assertTrue("EDT" in display or "EST" in display)

    def test_explicit_utc_timezone(self):
        """User: '5 PM UTC' -> Respects UTC."""
        dt, tz, display, is_rec, rec_pat = parse_natural_datetime("5 PM UTC")
        self.assertEqual(str(tz), "UTC")
        self.assertEqual(dt.hour, 17)
        self.assertEqual(dt.minute, 0)
        self.assertIn("UTC", display)

    def test_recurring_daily_reminder(self):
        """User: 'every day at 9 AM' -> Recurring daily flag set."""
        dt, tz, display, is_rec, rec_pat = parse_natural_datetime("every day at 9 AM")
        self.assertTrue(is_rec)
        self.assertEqual(rec_pat, "daily")
        self.assertEqual(dt.hour, 9)
        self.assertEqual(dt.minute, 0)


class TestCommandSplitting(unittest.TestCase):
    def test_split_reminder_commands(self):
        cases = [
            ("at 11 AM Call Rahul", ("at 11 AM", "Call Rahul")),
            ("11:00 AM Call doctor", ("11:00 AM", "Call doctor")),
            ("tomorrow at 9 AM Standup meeting", ("tomorrow at 9 AM", "Standup meeting")),
            ("in 2 hours Take medicine", ("in 2 hours", "Take medicine")),
            ("in 15 mins Check oven", ("in 15 mins", "Check oven")),
            ("11 AM EST US client call", ("11 AM EST", "US client call")),
            ("every day at 9 AM Morning workout", ("every day at 9 AM", "Morning workout")),
            ("Buy groceries in 2 hours", ("in 2 hours", "Buy groceries")),
            ('"tomorrow at 9am" Review PR code', ("tomorrow at 9am", "Review PR code")),
        ]
        for inp, (expected_time, expected_msg) in cases:
            t, m = split_reminder_command(inp)
            self.assertEqual(t.lower(), expected_time.lower(), f"Failed time split for: {inp}")
            self.assertEqual(m.lower(), expected_msg.lower(), f"Failed msg split for: {inp}")


class TestUserPreferencesAndDatabase(unittest.TestCase):
    def test_per_user_timezone_preference(self):
        import uuid
        user_id = f"test_user_tz_{uuid.uuid4().hex[:8]}"
        # Default is Asia/Kolkata
        self.assertEqual(db.get_user_timezone_str(user_id), "Asia/Kolkata")
        self.assertEqual(str(db.get_user_timezone(user_id)), "Asia/Kolkata")

        # Change to America/New_York
        db.set_user_timezone(user_id, "America/New_York")
        self.assertEqual(db.get_user_timezone_str(user_id), "America/New_York")
        self.assertEqual(str(db.get_user_timezone(user_id)), "America/New_York")

    def test_end_to_end_reminder_creation_and_listing(self):
        import uuid
        user_id = f"test_e2e_user_{uuid.uuid4().hex[:8]}"
        chat_id = f"test_chat_{uuid.uuid4().hex[:8]}"

        res = utils.create_reminder(user_id, chat_id, "Complete code audit", "tomorrow at 9 AM")
        self.assertIn("Reminder Set", res)
        self.assertIn("09:00 AM IST", res)
        self.assertIn("Asia/Kolkata", res)

        list_res = utils.list_user_reminders(user_id)
        self.assertIn("Complete code audit", list_res)
        self.assertIn("09:00 AM IST", list_res)



class TestDuplicatePreventionAndScheduler(unittest.TestCase):
    def test_atomic_claim_prevents_duplicate_executions(self):
        """Simulate concurrent threads attempting to fire the same reminder."""
        user_id = "test_concurrent_user_202"
        chat_id = "test_chat_202"

        # Add a reminder that is due right now
        past_utc_iso = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        rem_id = db.add_reminder(
            user_id=user_id,
            chat_id=chat_id,
            text="Time-sensitive alert",
            due_time=past_utc_iso,
            timezone_name="Asia/Kolkata",
        )

        now_utc = datetime.now(timezone.utc).isoformat()

        # Thread 1 claims
        claimed_thread_1 = db.claim_due_reminders(now_utc)
        ids_1 = [r["id"] for r in claimed_thread_1]
        self.assertIn(rem_id, ids_1)

        # Thread 2 claims simultaneously with same now_utc
        claimed_thread_2 = db.claim_due_reminders(now_utc)
        ids_2 = [r["id"] for r in claimed_thread_2]
        self.assertNotIn(rem_id, ids_2, "Duplicate claim occurred! Reminder claimed twice.")

        # Clean up
        db.delete_reminder(user_id, rem_id)

    def test_bot_recovery_preserves_due_time(self):
        """Verify bot restart does not shift reminder time."""
        user_id = "test_restart_user_303"
        chat_id = "test_chat_303"
        ist = zoneinfo.ZoneInfo("Asia/Kolkata")

        future_dt = datetime.now(ist) + timedelta(days=2, hours=3)
        future_utc_iso = to_utc_iso(future_dt)

        rem_id = db.add_reminder(
            user_id=user_id,
            chat_id=chat_id,
            text="Pre-restart reminder",
            due_time=future_utc_iso,
            timezone_name="Asia/Kolkata",
        )

        # Re-fetch from DB as if newly booted
        rems = db.get_active_reminders(user_id)
        matching = [r for r in rems if r["id"] == rem_id]
        self.assertEqual(len(matching), 1)

        recovered_dt = from_utc_iso_to_user_tz(matching[0]["due_time"], ist)
        self.assertEqual(recovered_dt.year, future_dt.year)
        self.assertEqual(recovered_dt.month, future_dt.month)
        self.assertEqual(recovered_dt.day, future_dt.day)
        self.assertEqual(recovered_dt.hour, future_dt.hour)
        self.assertEqual(recovered_dt.minute, future_dt.minute)

        # Clean up
        db.delete_reminder(user_id, rem_id)


if __name__ == "__main__":
    unittest.main()
