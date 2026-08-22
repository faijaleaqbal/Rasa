#!/usr/bin/env python3
"""
One-time targeted cleanup of test/stale scheduler data from the PRODUCTION database.

Removes ONLY:
  1. Reminders created by automated tests        (user_id/chat_id starting with 'test_')
  2. Reminders created under a fake test user    (user_id '9999999999')
  3. Junk recurring medicine reminders produced by the old /medremind parsing bug
     (medicine name literally 'argument', schedule_time literally 'test')
  4. Matching junk rows in medicines / bills tables

Never touches legitimate user-created reminders, notes, todos, expenses, etc.
Run with --apply to execute; default is a dry-run report.
"""

import argparse
import sqlite3
import sys

DB_PATH = "storage/data.db"

DELETES = [
    (
        "reminders",
        "DELETE FROM reminders WHERE user_id LIKE 'test_%' OR chat_id LIKE 'test_%'",
        "Automated-test reminders (test_e2e_user_*, test_user_demo, ...)",
    ),
    (
        "reminders",
        "DELETE FROM reminders WHERE user_id = '9999999999'",
        "Fake-user reminders ('take tea' tests)",
    ),
    (
        "reminders",
        "DELETE FROM reminders WHERE reminder_type = 'medicine' AND text LIKE 'argument (%'",
        "Junk recurring medicine reminders from /medremind parse bug ('argument (1 dose)...')",
    ),
    (
        "medicines",
        "DELETE FROM medicines WHERE name = 'argument' AND schedule_time = 'test'",
        "Junk medicine schedule rows from /medremind parse bug",
    ),
    (
        "bills",
        "DELETE FROM bills WHERE title = 'test' AND due_date = 'argument'",
        "Junk bill rows from bad /bill argument order",
    ),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Alya targeted test-data cleanup")
    parser.add_argument("--apply", action="store_true", help="Actually delete (default: dry-run)")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    total = 0
    for table, sql, label in DELETES:
        count_sql = sql.replace("DELETE FROM", "SELECT COUNT(*) FROM", 1)
        cursor.execute(count_sql)
        n = cursor.fetchone()[0]
        print(f"[{table}] {label}: {n} row(s)")
        total += n
        if args.apply and n:
            cursor.execute(sql)

    if args.apply:
        conn.commit()
        print(f"\nAPPLIED: deleted {total} junk row(s) from {DB_PATH}")

        # Post-condition: no pending junk jobs remain that the scheduler could fire.
        cursor.execute(
            "SELECT COUNT(*) FROM reminders WHERE status = 'pending' AND "
            "(user_id LIKE 'test_%' OR chat_id LIKE 'test_%' OR user_id = '9999999999' "
            "OR (reminder_type = 'medicine' AND text LIKE 'argument (%'))"
        )
        leftover = cursor.fetchone()[0]
        print(f"Post-check pending junk reminders remaining: {leftover}")
        if leftover:
            print("ERROR: junk reminders still pending!", file=sys.stderr)
            return 1
    else:
        print(f"\nDRY-RUN only. Re-run with --apply to delete {total} row(s).")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
