import os
import sqlite3
import json
import logging
from datetime import datetime, date, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Production DB lives in storage/data.db. Tests MUST set ALYA_DB_PATH (see tests/conftest.py)
# so they never read/write production user data.
DB_PATH = os.environ.get("ALYA_DB_PATH") or os.path.join(
    os.path.dirname(__file__), "..", "storage", "data.db"
)


def get_db_connection() -> sqlite3.Connection:
    """Returns a SQLite connection with row factory configured."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initializes all required database tables."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Notes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            tags TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. To-Do Tasks
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            priority TEXT DEFAULT 'medium',
            due_date TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 3. Expenses
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT DEFAULT 'general',
            description TEXT NOT NULL,
            expense_date TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 4. Reminders
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            chat_id TEXT NOT NULL,
            reminder_type TEXT DEFAULT 'general',
            text TEXT NOT NULL,
            due_time TEXT NOT NULL,
            is_recurring INTEGER DEFAULT 0,
            recurrence_pattern TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 5. Medicines
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS medicines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            dosage TEXT NOT NULL,
            schedule_time TEXT NOT NULL,
            instructions TEXT DEFAULT '',
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 6. Bills & Utility Payments
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            amount REAL NOT NULL,
            due_date TEXT NOT NULL,
            status TEXT DEFAULT 'unpaid',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 7. Habits
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            habit_name TEXT NOT NULL,
            current_streak INTEGER DEFAULT 0,
            best_streak INTEGER DEFAULT 0,
            last_completed_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 8. Habit Logs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS habit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id INTEGER NOT NULL,
            user_id TEXT NOT NULL,
            log_date TEXT NOT NULL,
            FOREIGN KEY (habit_id) REFERENCES habits(id) ON DELETE CASCADE
        )
    """)

    # 9. Website Price & Content Monitors
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_monitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            url TEXT NOT NULL,
            title TEXT NOT NULL,
            target_price REAL,
            last_price REAL,
            last_content_hash TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 10. Long-Term Memory (Key-Value Facts)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, key)
        )
    """)

    # 11. Stored Files Registry
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 12. Authorized Telegram Users
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS authorized_users (
            user_id TEXT PRIMARY KEY,
            name TEXT DEFAULT '',
            added_by TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 13. User Preferences (Timezone & Settings)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id TEXT PRIMARY KEY,
            timezone TEXT DEFAULT 'Asia/Kolkata',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Safe Schema Migrations
    try:
        cursor.execute("ALTER TABLE reminders ADD COLUMN timezone_name TEXT DEFAULT 'Asia/Kolkata'")
    except Exception:
        pass  # Column already exists

    conn.commit()
    conn.close()
    logger.info("Database initialized successfully.")



# Initialize tables on module load
init_db()


# -------------------------------------------------------------
# Notes CRUD
# -------------------------------------------------------------
def add_note(user_id: str, title: str, content: str, tags: str = "") -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO notes (user_id, title, content, tags) VALUES (?, ?, ?, ?)",
        (str(user_id), title, content, tags)
    )
    note_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return note_id


def get_notes(user_id: str, query: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    if query:
        search = f"%{query}%"
        cursor.execute(
            "SELECT * FROM notes WHERE user_id = ? AND (title LIKE ? OR content LIKE ? OR tags LIKE ?) ORDER BY updated_at DESC",
            (str(user_id), search, search, search)
        )
    else:
        cursor.execute(
            "SELECT * FROM notes WHERE user_id = ? ORDER BY updated_at DESC LIMIT 20",
            (str(user_id),)
        )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def delete_note(user_id: str, note_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM notes WHERE user_id = ? AND id = ?", (str(user_id), note_id))
    affected = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return affected


# -------------------------------------------------------------
# To-Do Tasks CRUD
# -------------------------------------------------------------
def add_todo(user_id: str, title: str, priority: str = "medium", due_date: Optional[str] = None) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO todos (user_id, title, priority, due_date, status) VALUES (?, ?, ?, ?, 'pending')",
        (str(user_id), title, priority, due_date)
    )
    todo_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return todo_id


def get_todos(user_id: str, status: Optional[str] = "pending") -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    if status:
        cursor.execute(
            "SELECT * FROM todos WHERE user_id = ? AND status = ? ORDER BY created_at DESC",
            (str(user_id), status)
        )
    else:
        cursor.execute(
            "SELECT * FROM todos WHERE user_id = ? ORDER BY created_at DESC LIMIT 25",
            (str(user_id),)
        )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def complete_todo(user_id: str, todo_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE todos SET status = 'completed' WHERE user_id = ? AND id = ?", (str(user_id), todo_id))
    affected = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return affected


def delete_todo(user_id: str, todo_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM todos WHERE user_id = ? AND id = ?", (str(user_id), todo_id))
    affected = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return affected


# -------------------------------------------------------------
# Expenses CRUD
# -------------------------------------------------------------
def add_expense(user_id: str, amount: float, category: str, description: str, expense_date: Optional[str] = None) -> int:
    if not expense_date:
        expense_date = date.today().isoformat()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO expenses (user_id, amount, category, description, expense_date) VALUES (?, ?, ?, ?, ?)",
        (str(user_id), float(amount), category.lower(), description, expense_date)
    )
    expense_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return expense_id


def get_expense_summary(user_id: str, month: Optional[str] = None) -> Dict[str, Any]:
    """Returns monthly total and category-wise breakdown."""
    if not month:
        month = datetime.now().strftime("%Y-%m")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT SUM(amount) as total FROM expenses WHERE user_id = ? AND expense_date LIKE ?",
        (str(user_id), f"{month}%")
    )
    total_row = cursor.fetchone()
    total = total_row["total"] or 0.0

    cursor.execute(
        "SELECT category, SUM(amount) as cat_total, COUNT(*) as count FROM expenses WHERE user_id = ? AND expense_date LIKE ? GROUP BY category ORDER BY cat_total DESC",
        (str(user_id), f"{month}%")
    )
    categories = [dict(row) for row in cursor.fetchall()]

    cursor.execute(
        "SELECT * FROM expenses WHERE user_id = ? AND expense_date LIKE ? ORDER BY expense_date DESC, id DESC LIMIT 10",
        (str(user_id), f"{month}%")
    )
    recent = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return {
        "month": month,
        "total": round(total, 2),
        "categories": categories,
        "recent": recent
    }


# -------------------------------------------------------------
# User Preferences (Timezone) CRUD
# -------------------------------------------------------------
def set_user_timezone(user_id: str, tz_name: str) -> bool:
    """Sets or updates a user's preferred timezone (e.g. 'Asia/Kolkata', 'America/New_York')."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO user_preferences (user_id, timezone, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET
            timezone = excluded.timezone,
            updated_at = CURRENT_TIMESTAMP
        """,
        (str(user_id), tz_name.strip())
    )
    conn.commit()
    conn.close()
    return True


def get_user_timezone_str(user_id: str) -> str:
    """Gets user's configured timezone name, defaulting to 'Asia/Kolkata'."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT timezone FROM user_preferences WHERE user_id = ?", (str(user_id),))
    row = cursor.fetchone()
    conn.close()
    if row and row["timezone"]:
        return row["timezone"]
    return "Asia/Kolkata"


def get_user_timezone(user_id: str):
    """Gets user's zoneinfo.ZoneInfo object, defaulting to Asia/Kolkata."""
    import zoneinfo
    tz_str = get_user_timezone_str(user_id)
    try:
        from .timezone_utils import resolve_timezone
        return resolve_timezone(tz_str)
    except Exception:
        try:
            return zoneinfo.ZoneInfo(tz_str)
        except Exception:
            return zoneinfo.ZoneInfo("Asia/Kolkata")


# -------------------------------------------------------------
# Reminders CRUD
# -------------------------------------------------------------
def add_reminder(
    user_id: str,
    chat_id: str,
    text: str,
    due_time: str,
    reminder_type: str = "general",
    is_recurring: int = 0,
    recurrence_pattern: str = "",
    timezone_name: str = "Asia/Kolkata",
) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO reminders (
            user_id, chat_id, reminder_type, text, due_time,
            is_recurring, recurrence_pattern, timezone_name, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        """,
        (
            str(user_id),
            str(chat_id),
            reminder_type,
            text,
            due_time,
            is_recurring,
            recurrence_pattern,
            timezone_name,
        )
    )
    rem_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return rem_id


def get_active_reminders(user_id: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM reminders WHERE user_id = ? AND status = 'pending' ORDER BY due_time ASC",
        (str(user_id),)
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_due_reminders(now_utc_iso: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM reminders WHERE status = 'pending' AND due_time <= ? ORDER BY due_time ASC",
        (now_utc_iso,)
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def claim_due_reminders(now_utc_iso: str) -> List[Dict[str, Any]]:
    """
    Atomically claims due reminders by transitioning status from 'pending' to 'in_flight'.
    Uses BEGIN IMMEDIATE so concurrent threads/processes can never claim the same row,
    and only returns rows whose status was actually flipped (zero duplicate firing).
    """
    conn = get_db_connection()
    conn.execute("BEGIN IMMEDIATE")
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM reminders WHERE status = 'pending' AND due_time <= ? ORDER BY due_time ASC",
            (now_utc_iso,)
        )
        rows = [dict(row) for row in cursor.fetchall()]
        claimed: List[Dict[str, Any]] = []
        if rows:
            ids = [r["id"] for r in rows]
            placeholders = ",".join("?" for _ in ids)
            cursor.execute(
                f"UPDATE reminders SET status = 'in_flight' WHERE id IN ({placeholders}) AND status = 'pending'",
                ids
            )
            # Re-check which rows this transaction actually flipped to 'in_flight'
            q = ",".join("?" for _ in ids)
            cursor.execute(
                f"SELECT id FROM reminders WHERE id IN ({q}) AND status = 'in_flight'",
                ids
            )
            flipped_ids = {row["id"] for row in cursor.fetchall()}
            claimed = [r for r in rows if r["id"] in flipped_ids]
        conn.commit()
        return claimed
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def reset_stale_in_flight_reminders(older_than_minutes: int = 5) -> int:
    """
    Startup/crash recovery: re-queues reminders stuck in 'in_flight' (e.g. process died
    mid-dispatch) so they are never silently lost. Returns number of rows requeued.
    Rows older than 24h past due are marked 'failed' instead of re-firing forever.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=older_than_minutes)).isoformat()
    cursor.execute(
        "UPDATE reminders SET status = 'pending' WHERE status = 'in_flight' AND due_time <= ?",
        (cutoff,)
    )
    requeued = cursor.rowcount
    day_cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    cursor.execute(
        "UPDATE reminders SET status = 'failed' WHERE status IN ('pending','in_flight') AND due_time < ?",
        (day_cutoff,)
    )
    failed = cursor.rowcount
    conn.commit()
    conn.close()
    if requeued or failed:
        logger.info(f"Scheduler recovery: requeued {requeued} stale in-flight reminders, expired {failed} overdue >24h.")
    return requeued


def find_active_duplicate_reminder(user_id: str, text: str, due_time: str, reminder_type: str = "general") -> Optional[Dict[str, Any]]:
    """Returns an existing active (pending/in_flight) identical reminder, for dedup on creation."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM reminders WHERE user_id = ? AND text = ? AND due_time = ? AND reminder_type = ? "
        "AND status IN ('pending','in_flight') LIMIT 1",
        (str(user_id), text.strip(), due_time, reminder_type)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def update_reminder_next_run(reminder_id: int, next_due_utc_iso: str) -> None:
    """Advances a recurring reminder to its next scheduled UTC timestamp and resets status to 'pending'."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE reminders SET due_time = ?, status = 'pending' WHERE id = ?",
        (next_due_utc_iso, reminder_id)
    )
    conn.commit()
    conn.close()


def mark_reminder_fired(reminder_id: int) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE reminders SET status = 'fired' WHERE id = ?", (reminder_id,))
    conn.commit()
    conn.close()


def mark_reminder_failed(reminder_id: int, error_msg: str = "") -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE reminders SET status = 'failed' WHERE id = ?", (reminder_id,))
    conn.commit()
    conn.close()


def delete_reminder(user_id: str, reminder_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM reminders WHERE user_id = ? AND id = ?", (str(user_id), reminder_id))
    affected = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return affected



# -------------------------------------------------------------
# Medicine Schedule CRUD
# -------------------------------------------------------------
def add_medicine(user_id: str, name: str, dosage: str, schedule_time: str, instructions: str = "") -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO medicines (user_id, name, dosage, schedule_time, instructions, status) VALUES (?, ?, ?, ?, ?, 'active')",
        (str(user_id), name, dosage, schedule_time, instructions)
    )
    med_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return med_id


def get_medicines(user_id: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM medicines WHERE user_id = ? AND status = 'active' ORDER BY schedule_time ASC",
        (str(user_id),)
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def delete_medicine(user_id: str, med_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM medicines WHERE user_id = ? AND id = ?", (str(user_id), med_id))
    affected = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return affected


# -------------------------------------------------------------
# Bills & Utilities CRUD
# -------------------------------------------------------------
def add_bill(user_id: str, title: str, amount: float, due_date: str) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO bills (user_id, title, amount, due_date, status) VALUES (?, ?, ?, ?, 'unpaid')",
        (str(user_id), title, float(amount), due_date)
    )
    bill_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return bill_id


def get_bills(user_id: str, status: Optional[str] = "unpaid") -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    if status:
        cursor.execute(
            "SELECT * FROM bills WHERE user_id = ? AND status = ? ORDER BY due_date ASC",
            (str(user_id), status)
        )
    else:
        cursor.execute(
            "SELECT * FROM bills WHERE user_id = ? ORDER BY due_date ASC",
            (str(user_id),)
        )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def mark_bill_paid(user_id: str, bill_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE bills SET status = 'paid' WHERE user_id = ? AND id = ?", (str(user_id), bill_id))
    affected = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return affected


# -------------------------------------------------------------
# Habits Tracker CRUD
# -------------------------------------------------------------
def add_habit(user_id: str, habit_name: str) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO habits (user_id, habit_name, current_streak, best_streak) VALUES (?, ?, 0, 0)",
        (str(user_id), habit_name)
    )
    habit_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return habit_id


def log_habit_done(user_id: str, habit_name_or_id: str) -> Dict[str, Any]:
    today_str = date.today().isoformat()
    conn = get_db_connection()
    cursor = conn.cursor()

    # Find habit
    if habit_name_or_id.isdigit():
        cursor.execute("SELECT * FROM habits WHERE user_id = ? AND id = ?", (str(user_id), int(habit_name_or_id)))
    else:
        cursor.execute("SELECT * FROM habits WHERE user_id = ? AND LOWER(habit_name) = LOWER(?)", (str(user_id), habit_name_or_id.strip()))
    
    habit = cursor.fetchone()
    if not habit:
        conn.close()
        return {"success": False, "message": "Habit not found"}

    habit_dict = dict(habit)
    habit_id = habit_dict["id"]
    last_date = habit_dict["last_completed_date"]
    current_streak = habit_dict["current_streak"]
    best_streak = habit_dict["best_streak"]

    if last_date == today_str:
        conn.close()
        return {"success": True, "already_done": True, "habit": habit_dict}

    # Check streak continuation
    yesterday_str = (date.today().fromordinal(date.today().toordinal() - 1)).isoformat()
    if last_date == yesterday_str:
        new_streak = current_streak + 1
    else:
        new_streak = 1

    new_best = max(best_streak, new_streak)

    cursor.execute(
        "UPDATE habits SET current_streak = ?, best_streak = ?, last_completed_date = ? WHERE id = ?",
        (new_streak, new_best, today_str, habit_id)
    )
    cursor.execute(
        "INSERT OR IGNORE INTO habit_logs (habit_id, user_id, log_date) VALUES (?, ?, ?)",
        (habit_id, str(user_id), today_str)
    )
    conn.commit()
    conn.close()

    return {
        "success": True,
        "already_done": False,
        "habit_name": habit_dict["habit_name"],
        "streak": new_streak,
        "best_streak": new_best
    }


def get_habits(user_id: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM habits WHERE user_id = ? ORDER BY current_streak DESC", (str(user_id),))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


# -------------------------------------------------------------
# Price & Content Monitor CRUD
# -------------------------------------------------------------
def add_price_monitor(user_id: str, url: str, title: str, target_price: Optional[float] = None) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO price_monitors (user_id, url, title, target_price, status) VALUES (?, ?, ?, ?, 'active')",
        (str(user_id), url, title, target_price)
    )
    mon_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return mon_id


def get_active_monitors() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM price_monitors WHERE status = 'active'")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def update_monitor_status(monitor_id: int, last_price: Optional[float], content_hash: Optional[str]) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE price_monitors SET last_price = ?, last_content_hash = ? WHERE id = ?",
        (last_price, content_hash, monitor_id)
    )
    conn.commit()
    conn.close()


# -------------------------------------------------------------
# Long-Term Memory CRUD
# -------------------------------------------------------------
def save_memory(user_id: str, key: str, value: str, category: str = "general") -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO memories (user_id, key, value, category, created_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP) "
        "ON CONFLICT(user_id, key) DO UPDATE SET value = excluded.value, category = excluded.category, created_at = CURRENT_TIMESTAMP",
        (str(user_id), key.strip().lower(), value.strip(), category.lower())
    )
    conn.commit()
    conn.close()


def get_all_memories(user_id: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM memories WHERE user_id = ? ORDER BY category, key", (str(user_id),))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def delete_memory(user_id: str, key: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM memories WHERE user_id = ? AND key = ?", (str(user_id), key.strip().lower()))
    affected = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return affected


# -------------------------------------------------------------
# Stored Files CRUD
# -------------------------------------------------------------
def save_file_record(user_id: str, file_name: str, file_type: str, file_path: str, file_size: int = 0) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO files (user_id, file_name, file_type, file_path, file_size) VALUES (?, ?, ?, ?, ?)",
        (str(user_id), file_name, file_type, file_path, file_size)
    )
    file_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return file_id


def get_user_files(user_id: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM files WHERE user_id = ? ORDER BY created_at DESC LIMIT 20", (str(user_id),))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


# -------------------------------------------------------------
# User Authorization & Access Control
# -------------------------------------------------------------
def add_authorized_user(user_id: str, name: str = "", added_by: str = "") -> bool:
    """Grants bot usage permission to a Telegram user ID."""
    clean_uid = str(user_id).strip()
    if not clean_uid or not clean_uid.isdigit():
        return False

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO authorized_users (user_id, name, added_by, created_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (clean_uid, name.strip(), str(added_by).strip())
    )
    conn.commit()
    conn.close()
    logger.info(f"Authorized user {clean_uid} ({name}) added by {added_by}")
    return True


def remove_authorized_user(user_id: str) -> bool:
    """Revokes bot usage permission for a Telegram user ID."""
    clean_uid = str(user_id).strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM authorized_users WHERE user_id = ?", (clean_uid,))
    affected = cursor.rowcount > 0
    conn.commit()
    conn.close()
    if affected:
        logger.info(f"Authorized user {clean_uid} removed from database.")
    return affected


def get_authorized_users() -> List[Dict[str, Any]]:
    """Returns list of all dynamically authorized users."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM authorized_users ORDER BY created_at ASC")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_admin_user_ids() -> List[str]:
    """Returns primary owner/admin user IDs from environment."""
    env_admins = os.getenv("ALLOWED_TELEGRAM_USER_ID", "") or os.getenv("ADMIN_TELEGRAM_USER_ID", "")
    return [uid.strip() for uid in env_admins.split(",") if uid.strip()]


def is_admin_user(user_id: str) -> bool:
    """Verifies if the requester is an authorized administrator."""
    clean_uid = str(user_id).strip()
    admins = get_admin_user_ids()
    if not admins:
        return True  # If no admin configured, grant access
    return clean_uid in admins


def is_user_authorized(user_id: str) -> bool:
    """
    Checks if a user has access to interact with the bot:
    1. If no ALLOWED_TELEGRAM_USER_ID is set, all users allowed.
    2. If user_id is in ALLOWED_TELEGRAM_USER_ID / admin list -> Authorized.
    3. If user_id is in SQLite authorized_users table -> Authorized.
    """
    clean_uid = str(user_id).strip()
    admins = get_admin_user_ids()

    # If no restrictions are configured in .env and no DB users, open access
    if not admins:
        return True

    # 1. Superadmin check
    if clean_uid in admins:
        return True

    # 2. Database whitelist check
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM authorized_users WHERE user_id = ?", (clean_uid,))
    found = cursor.fetchone() is not None
    conn.close()
    return found


