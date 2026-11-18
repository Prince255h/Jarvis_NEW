"""SQLite persistence layer for JARVIS conversations, sessions, long-term memory, settings, and custom commands."""

import sqlite3
import uuid
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "jarvis.db"


def get_connection():
    return sqlite3.connect(DB_PATH, timeout=10.0)


def initialize_memory():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                session_id TEXT
            )
        """)

        # Migrate older databases
        columns = [
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(conversations)"
            ).fetchall()
        ]

        if "session_id" not in columns:
            connection.execute(
                "ALTER TABLE conversations ADD COLUMN session_id TEXT"
            )

        connection.execute("""
            UPDATE conversations
            SET session_id = 'legacy'
            WHERE session_id IS NULL
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # Session metadata & summaries (1.6 & 3.9)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                title TEXT NOT NULL DEFAULT 'New Conversation',
                summary TEXT DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Long-term memory facts (1.7)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS long_term_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL DEFAULT 'general',
                fact TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Custom commands (7.8)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS custom_commands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                action_type TEXT NOT NULL DEFAULT 'prompt',
                payload TEXT NOT NULL,
                description TEXT DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        existing = connection.execute(
            "SELECT value FROM settings WHERE key = 'active_session_id'"
        ).fetchone()

        if not existing:
            old_messages = connection.execute(
                "SELECT COUNT(*) FROM conversations"
            ).fetchone()[0]

            initial_session = "legacy" if old_messages else str(uuid.uuid4())

            connection.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?)",
                ("active_session_id", initial_session)
            )
            connection.execute(
                "INSERT OR IGNORE INTO sessions (session_id, title) VALUES (?, ?)",
                (initial_session, "Previous Conversation" if old_messages else "New Conversation")
            )

        # Backfill sessions table for any session_id present in conversations
        connection.execute("""
            INSERT OR IGNORE INTO sessions (session_id, title)
            SELECT DISTINCT session_id, 'Saved Conversation'
            FROM conversations
            WHERE session_id IS NOT NULL
        """)


# ==========================================
# SETTINGS HELPERS
# ==========================================

def get_setting(key, default=None):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT value FROM settings WHERE key = ?",
            (key,)
        ).fetchone()
        return row[0] if row else default


def set_setting(key, value):
    with get_connection() as connection:
        connection.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, str(value))
        )


# ==========================================
# CONVERSATION SESSIONS (1.5, 1.6, 1.8, 3.9)
# ==========================================

def get_active_session_id():
    with get_connection() as connection:
        result = connection.execute(
            "SELECT value FROM settings WHERE key = 'active_session_id'"
        ).fetchone()

        if result:
            return result[0]

        new_id = str(uuid.uuid4())
        connection.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('active_session_id', ?)",
            (new_id,)
        )
        connection.execute(
            "INSERT OR IGNORE INTO sessions (session_id, title) VALUES (?, 'New Conversation')",
            (new_id,)
        )
        return new_id


def set_active_session_id(session_id):
    with get_connection() as connection:
        connection.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('active_session_id', ?)",
            (session_id,)
        )
        connection.execute(
            "INSERT OR IGNORE INTO sessions (session_id, title) VALUES (?, 'Saved Conversation')",
            (session_id,)
        )
    return session_id


def create_new_conversation(title="New Conversation"):
    new_id = str(uuid.uuid4())
    with get_connection() as connection:
        connection.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('active_session_id', ?)",
            (new_id,)
        )
        connection.execute(
            "INSERT INTO sessions (session_id, title) VALUES (?, ?)",
            (new_id, title)
        )
    return new_id


def save_message(role, message, session_id=None):
    if session_id is None:
        session_id = get_active_session_id()

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO conversations (role, message, session_id)
            VALUES (?, ?, ?)
            """,
            (role, message, session_id)
        )
        connection.execute(
            "INSERT OR IGNORE INTO sessions (session_id, title) VALUES (?, ?)",
            (session_id, "New Conversation")
        )
        # Auto-title session from first user message if still default
        if role == "user":
            row = connection.execute(
                "SELECT title FROM sessions WHERE session_id = ?",
                (session_id,)
            ).fetchone()
            if row and row[0] in ("New Conversation", "Saved Conversation"):
                auto_title = " ".join((message or "").split())[:55] or "Conversation"
                connection.execute(
                    "UPDATE sessions SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE session_id = ?",
                    (auto_title, session_id)
                )
            else:
                connection.execute(
                    "UPDATE sessions SET updated_at = CURRENT_TIMESTAMP WHERE session_id = ?",
                    (session_id,)
                )
        else:
            connection.execute(
                "UPDATE sessions SET updated_at = CURRENT_TIMESTAMP WHERE session_id = ?",
                (session_id,)
            )


def get_recent_messages(limit=50, session_id=None):
    if session_id is None:
        session_id = get_active_session_id()

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, role, message, timestamp
            FROM conversations
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (session_id, limit)
        ).fetchall()

    return list(reversed(rows))


def list_sessions(limit=50):
    """Return sessions ordered by most recently updated with message counts."""
    with get_connection() as connection:
        return connection.execute(
            """
            SELECT
                s.session_id,
                s.title,
                COALESCE(s.summary, ''),
                s.updated_at,
                COUNT(c.id) AS msg_count
            FROM sessions s
            LEFT JOIN conversations c ON c.session_id = s.session_id
            GROUP BY s.session_id
            HAVING msg_count > 0 OR s.session_id = (
                SELECT value FROM settings WHERE key = 'active_session_id'
            )
            ORDER BY s.updated_at DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()


def get_session_summary(session_id=None):
    if session_id is None:
        session_id = get_active_session_id()
    with get_connection() as connection:
        row = connection.execute(
            "SELECT summary FROM sessions WHERE session_id = ?",
            (session_id,)
        ).fetchone()
        return row[0] if row and row[0] else ""


def save_session_summary(summary, session_id=None):
    if session_id is None:
        session_id = get_active_session_id()
    with get_connection() as connection:
        connection.execute(
            "INSERT OR IGNORE INTO sessions (session_id, title) VALUES (?, 'Conversation')",
            (session_id,)
        )
        connection.execute(
            "UPDATE sessions SET summary = ?, updated_at = CURRENT_TIMESTAMP WHERE session_id = ?",
            (summary, session_id)
        )


def delete_session(session_id):
    with get_connection() as connection:
        connection.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
        connection.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
    if get_active_session_id() == session_id:
        create_new_conversation()


def search_messages(search_text):
    with get_connection() as connection:
        return connection.execute(
            """
            SELECT id, role, message, timestamp
            FROM conversations
            WHERE message LIKE ?
            ORDER BY id DESC
            LIMIT 200
            """,
            (f"%{search_text}%",)
        ).fetchall()


def delete_message(message_id):
    with get_connection() as connection:
        connection.execute(
            "DELETE FROM conversations WHERE id = ?",
            (message_id,)
        )


def clear_all_memory():
    with get_connection() as connection:
        connection.execute("DELETE FROM conversations")
        connection.execute("DELETE FROM sessions")
    create_new_conversation()


# ==========================================
# LONG-TERM MEMORY (1.7)
# ==========================================

def add_long_term_memory(fact, category="general"):
    fact = (fact or "").strip()
    if not fact:
        return None
    category = (category or "general").strip().lower()
    with get_connection() as connection:
        existing = connection.execute(
            "SELECT id FROM long_term_memory WHERE LOWER(fact) = LOWER(?)",
            (fact,)
        ).fetchone()
        if existing:
            return existing[0]
        cur = connection.execute(
            "INSERT INTO long_term_memory (category, fact) VALUES (?, ?)",
            (category, fact)
        )
        return cur.lastrowid


def get_long_term_memories(search_text=""):
    with get_connection() as connection:
        if search_text:
            return connection.execute(
                """
                SELECT id, category, fact, created_at
                FROM long_term_memory
                WHERE fact LIKE ? OR category LIKE ?
                ORDER BY id DESC
                """,
                (f"%{search_text}%", f"%{search_text}%")
            ).fetchall()
        return connection.execute(
            """
            SELECT id, category, fact, created_at
            FROM long_term_memory
            ORDER BY id DESC
            """
        ).fetchall()


def delete_long_term_memory(memory_id):
    with get_connection() as connection:
        connection.execute(
            "DELETE FROM long_term_memory WHERE id = ?",
            (memory_id,)
        )


def clear_long_term_memory():
    with get_connection() as connection:
        connection.execute("DELETE FROM long_term_memory")


# ==========================================
# CUSTOM COMMANDS (7.8)
# ==========================================

def save_custom_command(name, action_type, payload, description=""):
    clean_name = name.strip().lstrip("/").lower()
    if not clean_name:
        raise ValueError("Command name cannot be empty.")
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO custom_commands (name, action_type, payload, description)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                action_type = excluded.action_type,
                payload = excluded.payload,
                description = excluded.description
            """,
            (clean_name, action_type.strip().lower(), payload.strip(), description.strip())
        )


def get_custom_commands():
    with get_connection() as connection:
        return connection.execute(
            """
            SELECT id, name, action_type, payload, description
            FROM custom_commands
            ORDER BY name ASC
            """
        ).fetchall()


def get_custom_command_by_name(name):
    clean_name = name.strip().lstrip("/").lower()
    with get_connection() as connection:
        return connection.execute(
            """
            SELECT id, name, action_type, payload, description
            FROM custom_commands
            WHERE name = ?
            """,
            (clean_name,)
        ).fetchone()


def delete_custom_command(command_id):
    with get_connection() as connection:
        connection.execute(
            "DELETE FROM custom_commands WHERE id = ?",
            (command_id,)
        )


initialize_memory()
