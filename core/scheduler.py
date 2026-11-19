"""Custom Scheduled Task & Automation Engine for J.A.R.V.I.S (One-Time & Recurring)."""

from datetime import datetime, timedelta
from core.memory import get_connection


ACTION_TYPES = {
    "ai_prompt": {
        "label": "AI Prompt (Ask JARVIS)",
        "placeholder": "Enter prompt (e.g. Give me a concise morning briefing on Python best practices)",
    },
    "agent_goal": {
        "label": "Autonomous Agent Goal (Multi-Step)",
        "placeholder": "Enter multi-step goal (e.g. Search AI news and save a summary note)",
    },
    "open_app": {
        "label": "Open Desktop Application",
        "placeholder": "App name or path (e.g. vscode, chrome, notepad, calc)",
    },
    "open_website": {
        "label": "Open Website URL",
        "placeholder": "Website URL or shortcut (e.g. https://github.com, youtube)",
    },
    "web_search": {
        "label": "Run Web Search",
        "placeholder": "Search query (e.g. latest CVE security advisories)",
    },
    "organize_folder": {
        "label": "Organize Folder by Category",
        "placeholder": "Full folder path to auto-organize (e.g. C:\\Users\\admin\\Downloads)",
    },
    "plugin": {
        "label": "Run Plugin Tool",
        "placeholder": "Format: <plugin_name> <args> (e.g. calc 25 * 4)",
    },
    "terminal_command": {
        "label": "Run Pre-Approved Terminal Command",
        "placeholder": "PowerShell/shell command (requires explicit approval when scheduling)",
    },
    "daily_summary": {
        "label": "Daily Productivity Summary",
        "placeholder": "Optional extra note (leave blank for standard daily summary)",
    },
    "whatsapp_msg": {
        "label": "Send WhatsApp Message (Chrome)",
        "placeholder": "Format: Contact Name or Phone | Your message here",
    },
    "whatsapp_call": {
        "label": "WhatsApp Call Contact (Chrome)",
        "placeholder": "Contact Name or Phone number to call",
    },
    "notify": {
        "label": "Voice & HUD Notification",
        "placeholder": "Message to announce & display at scheduled time",
    },
}

SCHEDULE_TYPES = {
    "once": "Once",
    "daily": "Daily",
    "weekly": "Weekly",
    "interval": "Every N Minutes",
}


def initialize_scheduler():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                action_type TEXT NOT NULL,
                payload TEXT NOT NULL DEFAULT '',
                schedule_type TEXT NOT NULL DEFAULT 'once',
                interval_minutes INTEGER NOT NULL DEFAULT 60,
                next_run_at TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                speak_result INTEGER NOT NULL DEFAULT 1,
                last_run_at TEXT DEFAULT '',
                last_status TEXT DEFAULT 'PENDING',
                last_output TEXT DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_task_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                task_name TEXT NOT NULL,
                ran_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL,
                output TEXT NOT NULL
            )
        """)


def _validate_datetime(dt_str: str) -> datetime:
    return datetime.strptime((dt_str or "").strip(), "%Y-%m-%d %H:%M")


def compute_next_run(current_dt_str: str, schedule_type: str, interval_minutes: int = 60, now: datetime = None):
    """Compute the next future run timestamp string, or None if a one-time task is finished."""
    now = now or datetime.now()
    stype = (schedule_type or "once").strip().lower()
    if stype == "once":
        return None

    try:
        dt = _validate_datetime(current_dt_str)
    except ValueError:
        dt = now

    if stype == "daily":
        step = timedelta(days=1)
    elif stype == "weekly":
        step = timedelta(weeks=1)
    elif stype == "interval":
        mins = max(1, int(interval_minutes or 60))
        step = timedelta(minutes=mins)
    else:
        return None

    while dt <= now:
        dt += step
    return dt.strftime("%Y-%m-%d %H:%M")


def save_scheduled_task(
    name: str,
    action_type: str,
    payload: str,
    next_run_at: str,
    schedule_type: str = "once",
    interval_minutes: int = 60,
    enabled: bool = True,
    speak_result: bool = True,
    task_id: int = None,
) -> int:
    name = (name or "").strip()
    action_type = (action_type or "").strip().lower()
    schedule_type = (schedule_type or "once").strip().lower()
    payload = (payload or "").strip()

    if not name:
        raise ValueError("Task name cannot be empty.")
    if action_type not in ACTION_TYPES:
        raise ValueError(f"Unsupported action type: {action_type}")
    if schedule_type not in SCHEDULE_TYPES:
        raise ValueError(f"Unsupported schedule type: {schedule_type}")
    if action_type != "daily_summary" and not payload:
        raise ValueError("Action payload cannot be empty.")

    _validate_datetime(next_run_at)
    interval_minutes = max(1, int(interval_minutes or 60))

    with get_connection() as conn:
        if task_id:
            conn.execute(
                """
                UPDATE scheduled_tasks
                SET name = ?, action_type = ?, payload = ?, schedule_type = ?,
                    interval_minutes = ?, next_run_at = ?, enabled = ?, speak_result = ?
                WHERE id = ?
                """,
                (
                    name,
                    action_type,
                    payload,
                    schedule_type,
                    interval_minutes,
                    next_run_at.strip(),
                    1 if enabled else 0,
                    1 if speak_result else 0,
                    int(task_id),
                ),
            )
            return int(task_id)

        cur = conn.execute(
            """
            INSERT INTO scheduled_tasks (
                name, action_type, payload, schedule_type, interval_minutes,
                next_run_at, enabled, speak_result
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                action_type,
                payload,
                schedule_type,
                interval_minutes,
                next_run_at.strip(),
                1 if enabled else 0,
                1 if speak_result else 0,
            ),
        )
        return cur.lastrowid


def list_scheduled_tasks() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, name, action_type, payload, schedule_type, interval_minutes,
                   next_run_at, enabled, speak_result, last_run_at, last_status, last_output
            FROM scheduled_tasks
            ORDER BY enabled DESC, next_run_at ASC, id DESC
            """
        ).fetchall()

    return [
        {
            "id": r[0],
            "name": r[1],
            "action_type": r[2],
            "payload": r[3],
            "schedule_type": r[4],
            "interval_minutes": r[5],
            "next_run_at": r[6],
            "enabled": bool(r[7]),
            "speak_result": bool(r[8]),
            "last_run_at": r[9] or "",
            "last_status": r[10] or "PENDING",
            "last_output": r[11] or "",
        }
        for r in rows
    ]


def get_scheduled_task(task_id: int) -> dict | None:
    for t in list_scheduled_tasks():
        if t["id"] == int(task_id):
            return t
    return None


def set_scheduled_task_enabled(task_id: int, enabled: bool):
    with get_connection() as conn:
        conn.execute(
            "UPDATE scheduled_tasks SET enabled = ? WHERE id = ?",
            (1 if enabled else 0, int(task_id)),
        )


def delete_scheduled_task(task_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM scheduled_tasks WHERE id = ?", (int(task_id),))
        conn.execute("DELETE FROM scheduled_task_logs WHERE task_id = ?", (int(task_id),))


def list_scheduled_logs(limit: int = 30) -> list[tuple]:
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT id, task_id, task_name, ran_at, status, output
            FROM scheduled_task_logs
            ORDER BY id DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()


def claim_due_tasks(now: datetime = None) -> list[dict]:
    """Atomically claim enabled tasks whose next_run_at <= now and advance their schedule."""
    now = now or datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M")
    claimed = []

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, name, action_type, payload, schedule_type, interval_minutes,
                   next_run_at, enabled, speak_result
            FROM scheduled_tasks
            WHERE enabled = 1 AND next_run_at <= ?
            ORDER BY next_run_at ASC
            """,
            (now_str,),
        ).fetchall()

        for r in rows:
            tid, name, action_type, payload, schedule_type, interval_min, next_run_at, _, speak = r
            next_dt = compute_next_run(next_run_at, schedule_type, interval_min, now=now)
            if next_dt is None:
                # One-time task: disable immediately so it never fires twice
                conn.execute(
                    "UPDATE scheduled_tasks SET enabled = 0, last_status = 'RUNNING' WHERE id = ?",
                    (tid,),
                )
            else:
                conn.execute(
                    "UPDATE scheduled_tasks SET next_run_at = ?, last_status = 'RUNNING' WHERE id = ?",
                    (next_dt, tid),
                )

            claimed.append({
                "id": tid,
                "name": name,
                "action_type": action_type,
                "payload": payload,
                "schedule_type": schedule_type,
                "interval_minutes": interval_min,
                "next_run_at": next_dt or next_run_at,
                "speak_result": bool(speak),
            })

    return claimed


def execute_scheduled_task(task: dict) -> dict:
    """Execute a single scheduled task, record its run log, and return result metadata."""
    tid = task["id"]
    name = task["name"]
    atype = task["action_type"]
    payload = task.get("payload", "")
    ran_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = "SUCCESS"

    try:
        if atype == "ai_prompt":
            from core.brain import ask_jarvis

            output = ask_jarvis(payload, include_history=False, save_to_memory=True)

        elif atype == "agent_goal":
            from core.agent import run_agent_goal

            output = run_agent_goal(payload, max_steps=5)

        elif atype == "open_app":
            from tools.computer import open_application

            output = open_application(payload)

        elif atype == "open_website":
            from tools.computer import open_website

            output = open_website(payload)

        elif atype == "web_search":
            from tools.web_search import web_search, format_search_results

            results = web_search(payload, max_results=5)
            output = format_search_results(payload, results)

        elif atype == "organize_folder":
            from tools.computer import execute_folder_organization

            output = execute_folder_organization(payload)

        elif atype == "plugin":
            from tools.plugins import plugin_manager

            parts = payload.split(maxsplit=1)
            tool_name = parts[0] if parts else ""
            tool_args = parts[1] if len(parts) > 1 else ""
            output = plugin_manager.run_tool(tool_name, tool_args)

        elif atype == "terminal_command":
            from tools.computer import run_approved_command

            res = run_approved_command(payload)
            blocks = [f"$ {payload} (exit {res['returncode']})"]
            if res["stdout"]:
                blocks.append(res["stdout"])
            if res["stderr"]:
                blocks.append(f"[STDERR]\n{res['stderr']}")
            output = "\n".join(blocks)
            if res["returncode"] != 0:
                status = "ERROR"

        elif atype == "daily_summary":
            from core.productivity import build_daily_summary_text

            base_sum = build_daily_summary_text()
            output = f"{payload}\n\n{base_sum}".strip() if payload else base_sum

        elif atype == "whatsapp_msg":
            from tools.whatsapp import parse_and_send_whatsapp

            output = parse_and_send_whatsapp(payload)

        elif atype == "whatsapp_call":
            from tools.whatsapp import parse_and_call_whatsapp

            output = parse_and_call_whatsapp(payload)

        elif atype == "notify":
            output = payload

        else:
            raise ValueError(f"Unknown scheduled action type: {atype}")

    except Exception as err:
        status = "ERROR"
        output = f"[{type(err).__name__}] {err}"

    with get_connection() as conn:
        conn.execute(
            """
            UPDATE scheduled_tasks
            SET last_run_at = ?, last_status = ?, last_output = ?
            WHERE id = ?
            """,
            (ran_at, status, str(output)[:4000], tid),
        )
        conn.execute(
            """
            INSERT INTO scheduled_task_logs (task_id, task_name, ran_at, status, output)
            VALUES (?, ?, ?, ?, ?)
            """,
            (tid, name, ran_at, status, str(output)[:4000]),
        )

    return {
        "id": tid,
        "name": name,
        "action_type": atype,
        "status": status,
        "ran_at": ran_at,
        "output": str(output),
        "speak_result": bool(task.get("speak_result", True)),
    }


initialize_scheduler()

