"""
src/database/db.py
==================
SQLite database to track sent items and prevent duplicate notifications.
"""

import sqlite3
import logging
from datetime import datetime
from pathlib import Path

DB_PATH = Path("data/pulseagent.db")
logger = logging.getLogger(__name__)


def get_connection():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables on first run."""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sent_items (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id     TEXT UNIQUE NOT NULL,   -- URL or GUID
                source_type TEXT NOT NULL,           -- 'youtube', 'rss', 'news'
                title       TEXT,
                sent_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_breaking INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS digest_queue (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id     TEXT UNIQUE NOT NULL,
                title       TEXT NOT NULL,
                summary     TEXT,
                category    TEXT,
                source_url  TEXT,
                source_type TEXT,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_sent     INTEGER DEFAULT 0
            );
        """)
        logger.info("✅ Database initialized.")


def is_already_sent(item_id: str) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM sent_items WHERE item_id = ?", (item_id,)
        ).fetchone()
        return row is not None


def mark_as_sent(item_id: str, source_type: str, title: str, is_breaking: bool = False):
    with get_connection() as conn:
        try:
            conn.execute(
                """INSERT INTO sent_items (item_id, source_type, title, is_breaking)
                   VALUES (?, ?, ?, ?)""",
                (item_id, source_type, title, int(is_breaking))
            )
        except sqlite3.IntegrityError:
            pass  # Already exists


def add_to_digest_queue(item_id: str, title: str, summary: str,
                         category: str, source_url: str, source_type: str):
    with get_connection() as conn:
        try:
            conn.execute(
                """INSERT INTO digest_queue
                   (item_id, title, summary, category, source_url, source_type)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (item_id, title, summary, category, source_url, source_type)
            )
        except sqlite3.IntegrityError:
            pass


def get_unsent_digest_items() -> list:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM digest_queue WHERE is_sent = 0 ORDER BY created_at ASC"
        ).fetchall()
        return [dict(r) for r in rows]


def mark_digest_items_sent(item_ids: list):
    with get_connection() as conn:
        placeholders = ",".join("?" * len(item_ids))
        conn.execute(
            f"UPDATE digest_queue SET is_sent = 1 WHERE item_id IN ({placeholders})",
            item_ids
        )


def clear_old_digest(days: int = 2):
    """Keep database clean by removing old sent digest items."""
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM digest_queue WHERE is_sent = 1 AND created_at < datetime('now', ?)",
            (f"-{days} days",)
        )
