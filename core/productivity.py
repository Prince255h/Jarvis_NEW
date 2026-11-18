"""SQLite persistence & helpers for Personal Productivity (Tasks, Reminders, Notes, Calendar, Study Progress, Daily Summary)."""

from datetime import datetime, date
from core.memory import get_connection


def initialize_productivity():
    with get_connection() as conn:
        # 4.1 & 4.7 Daily tasks / To-do list
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                priority TEXT NOT NULL DEFAULT 'Medium',
                category TEXT NOT NULL DEFAULT 'General',
                due_date TEXT DEFAULT '',
                completed INTEGER NOT NULL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 4.2 Reminders and alarms
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                remind_at TEXT NOT NULL,
                notified INTEGER NOT NULL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 4.3 Notes and quick capture
        conn.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT DEFAULT '',
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 4.4 Calendar events
        conn.execute("""
            CREATE TABLE IF NOT EXISTS calendar_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_date TEXT NOT NULL,
                event_time TEXT DEFAULT '',
                title TEXT NOT NULL,
                notes TEXT DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 4.5 & 4.6 Study / Pomodoro logs
        conn.execute("""
            CREATE TABLE IF NOT EXISTS study_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                duration_minutes INTEGER NOT NULL,
                session_date TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)


# ==========================================
# TASKS / TO-DO (4.1, 4.7)
# ==========================================

def add_task(title, priority="Medium", category="General", due_date=""):
    title = (title or "").strip()
    if not title:
        raise ValueError("Task title cannot be empty.")
    if not due_date:
        due_date = date.today().isoformat()
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO tasks (title, priority, category, due_date) VALUES (?, ?, ?, ?)",
            (title, priority, category, due_date)
        )
        return cur.lastrowid


def list_tasks(filter_mode="all"):
    today_str = date.today().isoformat()
    with get_connection() as conn:
        if filter_mode == "pending":
            sql = "SELECT id, title, priority, category, due_date, completed FROM tasks WHERE completed = 0 ORDER BY due_date ASC, id DESC"
            return conn.execute(sql).fetchall()
        elif filter_mode == "completed":
            sql = "SELECT id, title, priority, category, due_date, completed FROM tasks WHERE completed = 1 ORDER BY id DESC"
            return conn.execute(sql).fetchall()
        elif filter_mode == "today":
            sql = "SELECT id, title, priority, category, due_date, completed FROM tasks WHERE due_date = ? ORDER BY completed ASC, id DESC"
            return conn.execute(sql, (today_str,)).fetchall()
        else:
            sql = "SELECT id, title, priority, category, due_date, completed FROM tasks ORDER BY completed ASC, due_date ASC, id DESC"
            return conn.execute(sql).fetchall()


def toggle_task(task_id, completed):
    with get_connection() as conn:
        conn.execute(
            "UPDATE tasks SET completed = ? WHERE id = ?",
            (1 if completed else 0, task_id)
        )


def delete_task(task_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))


# ==========================================
# REMINDERS & ALARMS (2.6, 4.2)
# ==========================================

def add_reminder(title, remind_at):
    title = (title or "").strip()
    remind_at = (remind_at or "").strip()
    if not title or not remind_at:
        raise ValueError("Reminder title and date/time are required.")
    # Validate format YYYY-MM-DD HH:MM
    datetime.strptime(remind_at, "%Y-%m-%d %H:%M")
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO reminders (title, remind_at) VALUES (?, ?)",
            (title, remind_at)
        )
        return cur.lastrowid


def list_reminders(include_notified=True):
    with get_connection() as conn:
        if include_notified:
            return conn.execute(
                "SELECT id, title, remind_at, notified FROM reminders ORDER BY notified ASC, remind_at ASC"
            ).fetchall()
        return conn.execute(
            "SELECT id, title, remind_at, notified FROM reminders WHERE notified = 0 ORDER BY remind_at ASC"
        ).fetchall()


def get_due_reminders():
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    with get_connection() as conn:
        due = conn.execute(
            "SELECT id, title, remind_at FROM reminders WHERE notified = 0 AND remind_at <= ?",
            (now_str,)
        ).fetchall()
        for rem_id, _, _ in due:
            conn.execute("UPDATE reminders SET notified = 1 WHERE id = ?", (rem_id,))
    return due


def delete_reminder(reminder_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))


# ==========================================
# NOTES & QUICK CAPTURE (4.3)
# ==========================================

def save_note(title, content, tags="", note_id=None):
    title = (title or "").strip() or "Untitled Note"
    content = (content or "").strip()
    tags = (tags or "").strip()
    with get_connection() as conn:
        if note_id:
            conn.execute(
                "UPDATE notes SET title = ?, content = ?, tags = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (title, content, tags, note_id)
            )
            return note_id
        cur = conn.execute(
            "INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)",
            (title, content, tags)
        )
        return cur.lastrowid


def list_notes(search_text=""):
    with get_connection() as conn:
        if search_text:
            q = f"%{search_text}%"
            return conn.execute(
                "SELECT id, title, content, tags, updated_at FROM notes WHERE title LIKE ? OR content LIKE ? OR tags LIKE ? ORDER BY updated_at DESC",
                (q, q, q)
            ).fetchall()
        return conn.execute(
            "SELECT id, title, content, tags, updated_at FROM notes ORDER BY updated_at DESC"
        ).fetchall()


def delete_note(note_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))


# ==========================================
# CALENDAR INTEGRATION (4.4)
# ==========================================

def add_calendar_event(event_date, title, event_time="", notes=""):
    title = (title or "").strip()
    if not title:
        raise ValueError("Event title cannot be empty.")
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO calendar_events (event_date, event_time, title, notes) VALUES (?, ?, ?, ?)",
            (event_date, event_time.strip(), title, notes.strip())
        )
        return cur.lastrowid


def list_calendar_events(event_date=None):
    with get_connection() as conn:
        if event_date:
            return conn.execute(
                "SELECT id, event_date, event_time, title, notes FROM calendar_events WHERE event_date = ? ORDER BY event_time ASC, id ASC",
                (event_date,)
            ).fetchall()
        return conn.execute(
            "SELECT id, event_date, event_time, title, notes FROM calendar_events ORDER BY event_date ASC, event_time ASC"
        ).fetchall()


def delete_calendar_event(event_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM calendar_events WHERE id = ?", (event_id,))


def export_calendar_ics(output_path):
    """Export all calendar events to a standard .ics iCalendar file."""
    events = list_calendar_events()
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//JARVIS AI Assistant//Calendar//EN",
    ]
    for ev_id, ev_date, ev_time, title, notes in events:
        dt_clean = ev_date.replace("-", "")
        if ev_time and ":" in ev_time:
            tm_clean = ev_time.replace(":", "")[:4] + "00"
            dtstart = f"{dt_clean}T{tm_clean}"
        else:
            dtstart = dt_clean
        safe_title = title.replace("\n", " ")
        safe_notes = (notes or "").replace("\n", "\\n")
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:jarvis-event-{ev_id}@local",
            f"DTSTART:{dtstart}",
            f"SUMMARY:{safe_title}",
            f"DESCRIPTION:{safe_notes}",
            "END:VEVENT",
        ])
    lines.append("END:VCALENDAR")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\r\n".join(lines) + "\r\n")
    return len(events)


# ==========================================
# STUDY TIMER / POMODORO PROGRESS (4.5, 4.6)
# ==========================================

def log_study_session(topic, duration_minutes):
    topic = (topic or "Focused Study").strip()
    today_str = date.today().isoformat()
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO study_sessions (topic, duration_minutes, session_date) VALUES (?, ?, ?)",
            (topic, int(duration_minutes), today_str)
        )
        return cur.lastrowid


def get_study_progress(target_date=None):
    if not target_date:
        target_date = date.today().isoformat()
    with get_connection() as conn:
        total_min = conn.execute(
            "SELECT COALESCE(SUM(duration_minutes), 0) FROM study_sessions WHERE session_date = ?",
            (target_date,)
        ).fetchone()[0]
        sessions = conn.execute(
            "SELECT id, topic, duration_minutes, session_date, created_at FROM study_sessions WHERE session_date = ? ORDER BY id DESC",
            (target_date,)
        ).fetchall()
        total_all_time = conn.execute(
            "SELECT COALESCE(SUM(duration_minutes), 0) FROM study_sessions"
        ).fetchone()[0]
    return {
        "date": target_date,
        "today_minutes": total_min,
        "today_sessions": sessions,
        "all_time_minutes": total_all_time,
    }


# ==========================================
# DAILY SUMMARY (4.8)
# ==========================================

def build_daily_summary_text():
    today_str = date.today().isoformat()
    all_tasks = list_tasks("all")
    today_tasks = [t for t in all_tasks if t[4] == today_str]
    pending_tasks = [t for t in all_tasks if not t[5]]
    completed_today = [t for t in today_tasks if t[5]]

    reminders = list_reminders(include_notified=False)
    today_events = list_calendar_events(today_str)
    study = get_study_progress(today_str)
    notes = list_notes()[:5]

    lines = [
        f"=== JARVIS DAILY SUMMARY ({today_str}) ===",
        "",
        f"TASKS: {len(completed_today)}/{len(today_tasks)} completed today | {len(pending_tasks)} total pending",
    ]
    for _, title, priority, cat, due, done in pending_tasks[:8]:
        mark = "[x]" if done else "[ ]"
        lines.append(f"  {mark} ({priority}) {title} [due: {due}]")

    lines.append("")
    lines.append(f"UPCOMING REMINDERS ({len(reminders)}):")
    if reminders:
        for _, title, remind_at, _ in reminders[:6]:
            lines.append(f"  - {remind_at}: {title}")
    else:
        lines.append("  - No pending reminders.")

    lines.append("")
    lines.append(f"TODAY'S CALENDAR EVENTS ({len(today_events)}):")
    if today_events:
        for _, _, ev_time, title, _ in today_events:
            t_label = f"{ev_time} - " if ev_time else ""
            lines.append(f"  - {t_label}{title}")
    else:
        lines.append("  - No events scheduled today.")

    lines.append("")
    lines.append(
        f"STUDY PROGRESS: {study['today_minutes']} minutes today "
        f"({len(study['today_sessions'])} sessions) | All-time: {study['all_time_minutes']} min"
    )

    lines.append("")
    lines.append(f"RECENT NOTES ({len(notes)}):")
    if notes:
        for _, title, _, tags, _ in notes:
            tag_str = f" [{tags}]" if tags else ""
            lines.append(f"  - {title}{tag_str}")
    else:
        lines.append("  - No saved notes yet.")

    return "\n".join(lines)


initialize_productivity()

