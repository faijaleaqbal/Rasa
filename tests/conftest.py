"""
Global pytest configuration for Alya.

CRITICAL: Isolates every test run from production data.
- ALYA_DB_PATH points all actions.db access to a throwaway temp database,
  so tests can NEVER create reminders/medicines/bills in storage/data.db
  (the root cause of past 'test reminder' pollution).
- Telegram/GitHub credentials are stubbed so no live side effects occur.
"""

import os
import tempfile

# Must be set BEFORE any 'actions' module import (db.py reads it at import time).
_TEST_DB_DIR = tempfile.mkdtemp(prefix="alya_test_db_")
os.environ["ALYA_DB_PATH"] = os.path.join(_TEST_DB_DIR, "test_data.db")

# Stub secrets so tests never hit live Telegram / GitHub with real credentials.
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456:TEST_TOKEN_FOR_UNIT_TESTS")
os.environ.setdefault("TELEGRAM_BOT_USERNAME", "Alya_Rasa_Bot")
os.environ.setdefault("ALLOWED_TELEGRAM_USER_ID", "8433855679")
os.environ.setdefault("GITHUB_PERSONAL_ACCESS_TOKEN", "")
