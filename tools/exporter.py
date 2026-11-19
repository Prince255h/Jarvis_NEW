"""Export JARVIS Conversations and Reports to Formatted Markdown (.md) and Native PDF (.pdf)."""

import html as html_lib
from datetime import datetime
from pathlib import Path

from core.memory import get_recent_messages, get_active_session_id


def build_session_markdown(session_id=None, title="J.A.R.V.I.S Conversation Export") -> str:
    sid = session_id or get_active_session_id()
    rows = get_recent_messages(limit=500, session_id=sid)
    lines = [
        f"# {title}",
        f"- **Exported:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- **Session ID:** `{sid}`",
        f"- **Messages:** {len(rows)}",
        "",
        "---",
        "",
    ]
    for _, role, msg, ts in rows:
        speaker = "YOU" if role == "user" else "J.A.R.V.I.S"
        lines.append(f"### {speaker}  *({ts})*")
        lines.append("")
        lines.append(msg or "")
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


def export_markdown(content: str, output_path: str) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content or "", encoding="utf-8")
    return path


def export_text_to_pdf(content: str, output_path: str, title: str = "J.A.R.V.I.S Export") -> Path:
    """Render Markdown/plain text cleanly into a multi-page PDF via PySide6 QTextDocument + QPdfWriter."""
    from PySide6.QtGui import QTextDocument, QPdfWriter, QPageSize

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    doc = QTextDocument()
    # QTextDocument supports Markdown natively in Qt6!
    doc.setMarkdown(content or "")
    doc.setDefaultStyleSheet(
        "body { font-family: 'Segoe UI', Arial, sans-serif; font-size: 10pt; color: #111827; } "
        "h1, h2, h3 { color: #0f172a; } "
        "pre, code { font-family: Consolas, monospace; background-color: #f1f5f9; }"
    )

    writer = QPdfWriter(str(path))
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setTitle(title)
    writer.setCreator("J.A.R.V.I.S AI Assistant")
    doc.print_(writer)
    return path

