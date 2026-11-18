# J.A.R.V.I.S — Intelligent AI Assistant

A modern desktop AI assistant built with Python and PySide6 featuring multi-provider AI routing, desktop automation, personal productivity, coding & cybersecurity studios, and advanced multimodal/document tools.

## Features
1. **Smart AI Brain**: Gemini, Groq, and Ollama support with automatic fallback, task-based routing, 6 personalities, 5 response styles, conversation summarization, long-term memory, and full conversation history search.
2. **Desktop Automation**: Launch apps & websites, Google/YouTube search, create files/folders, smart folder organizer, volume control, permission-gated screenshots, and approval-gated terminal execution.
3. **Modern JARVIS Interface**: Animated AI Core, live audio waveform, typing/speaking indicators, modern sidebar, Dark & Light themes, customizable accent colors, and system resource dashboard.
4. **Personal Productivity**: Daily tasks/to-do list, reminders & voice alarms, quick-capture notes, calendar with `.ics` export, Pomodoro study timer, daily study progress, and AI daily briefing.
5. **Coding Studio**: Explain, debug (with local Python syntax check), generate, review, terminal error analysis, Git/GitHub helper, Linux commands, and static + AI code security auditing.
6. **Cybersecurity Center**: OWASP Top 10 learning, vulnerability explanations, security log analyzer, HTTP header/request analyzer, local network info, security checklists, bug bounty report drafting, and legal lab-based study assistance.
7. **Advanced Intelligence**: Multimodal image understanding, native PDF/DOCX/text analysis, web search (`/search`), YouTube summarization (`/yt`), multilingual responses, plugin system (`plugins/`), and custom slash commands.

## Quick Start (Windows)
1. Double-click **`Run_JARVIS.bat`** — it automatically creates a virtual environment, installs all packages from `requirements.txt`, creates a starter `.env`, and launches JARVIS.
2. Open `.env` (or copy `.env.example` to `.env`) and add your `GEMINI_API_KEY` and/or `GROQ_API_KEY` (or run Ollama locally).
3. Inside chat, type `/help` to view all built-in, plugin, and custom slash commands.

