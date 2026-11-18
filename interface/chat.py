"""Main Modern JARVIS AI Assistant Interface (All 7 Feature Pillars)."""

import re
import sys
from pathlib import Path

PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QTextBrowser,
    QStackedWidget,
    QMessageBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QFileDialog,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import (
    QTextCursor,
    QTextCharFormat,
    QColor,
    QFont,
)

from interface.worker import JarvisWorker
from interface.dashboard import Dashboard
from interface.memory_page import MemoryManager
from interface.productivity_page import ProductivityPage
from interface.coding_page import CodingAssistantPage
from interface.cybersec_page import CybersecurityPage
from interface.automation_page import AutomationToolsPage
from interface.settings_page import SettingsPage
from interface.themes import build_stylesheet
from interface.widgets import AICoreWidget, AudioWaveformWidget, StatusPulseLabel

from core.personality import PERSONALITIES
from core.brain import (
    start_new_chat,
    set_provider_mode,
    get_provider_mode,
    get_personality,
    set_personality,
    GEMINI_MODEL,
    GROQ_MODEL,
    OLLAMA_MODEL,
)
from core.memory import (
    create_new_conversation,
    set_active_session_id,
    get_recent_messages,
    add_long_term_memory,
    get_custom_command_by_name,
    get_custom_commands,
    get_setting,
    set_setting,
)
from core.productivity import (
    add_task,
    save_note,
    add_reminder,
    get_due_reminders,
)
from core.tts import JarvisTTS

from tools.computer import (
    open_application,
    open_website,
    search_google,
    search_youtube,
    volume_up,
    volume_down,
    volume_mute_toggle,
    set_volume_percent,
    capture_screenshot_qapp,
    is_potentially_dangerous_command,
    run_approved_command,
)
from tools.documents import extract_document_text
from tools.plugins import plugin_manager


class JarvisWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("J.A.R.V.I.S — Intelligent AI Assistant")
        self.resize(1280, 820)

        # Persisted theme & accent (3.5, 3.6)
        self.theme_mode = get_setting("theme_mode", "dark") or "dark"
        self.accent_color = get_setting("accent_color", "#00d9ff") or "#00d9ff"

        # Worker & streaming state
        self.worker = None
        self.tts = JarvisTTS()
        self.speech_buffer = ""

        # Chat attachments (7.1 Image, 7.2/7.3 PDF/Doc)
        self.attached_image_path = None
        self.attached_doc_meta = None

        self.stream_cursor = None
        self.stream_start_position = None
        self.stream_text_format = QTextCharFormat()

        # Provider health workers
        self.health_workers = {}
        self.provider_status_labels = {}
        self.provider_detail_labels = {}
        self.provider_check_buttons = {}
        self.check_all_pending = set()
        self.nav_buttons = {}

        # Setup UI & Styles
        self.setup_ui()
        self.apply_theme(self.theme_mode, self.accent_color)
        self.load_active_session_to_chat()

        # Live UI sync timer (waveform, AI core state, speaking indicator)
        self.ui_sync_timer = QTimer(self)
        self.ui_sync_timer.timeout.connect(self._sync_live_indicators)
        self.ui_sync_timer.start(150)

        # Live Reminder / Alarm polling timer (4.2)
        self.reminder_timer = QTimer(self)
        self.reminder_timer.timeout.connect(self._check_due_reminders)
        self.reminder_timer.start(15000)

    # =========================================
    # STOP SPEAKING
    # =========================================

    def stop_speaking(self):
        self.tts.clear()
        self.speech_buffer = ""

    # =========================================
    # MAIN UI & MODERN SIDEBAR (3.1 - 3.7)
    # =========================================

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # -----------------------------------------
        # MODERN SIDEBAR (3.4)
        # -----------------------------------------
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(230)
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(14, 14, 14, 14)
        sb_layout.setSpacing(8)

        # Animated AI Core (3.1)
        core_wrap = QHBoxLayout()
        core_wrap.addStretch()
        self.ai_core = AICoreWidget(accent=self.accent_color)
        core_wrap.addWidget(self.ai_core)
        core_wrap.addStretch()
        sb_layout.addLayout(core_wrap)

        logo = QLabel("J.A.R.V.I.S")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setObjectName("logo")
        sb_layout.addWidget(logo)

        # Live Audio Waveform (3.2) & Status Pill (3.7)
        self.waveform = AudioWaveformWidget(accent=self.accent_color)
        sb_layout.addWidget(self.waveform)

        status_wrap = QHBoxLayout()
        status_wrap.addStretch()
        self.status_pill = StatusPulseLabel()
        status_wrap.addWidget(self.status_pill)
        status_wrap.addStretch()
        sb_layout.addLayout(status_wrap)

        sb_layout.addSpacing(8)

        # Navigation items
        nav_specs = [
            ("chat", "💬  AI Chat"),
            ("productivity", "📋  Productivity"),
            ("coding", "💻  Coding Studio"),
            ("cybersec", "🛡️  Cybersecurity"),
            ("automation", "⚙️  Automation & Tools"),
            ("memory", "🧠  Memory & History"),
            ("dashboard", "📊  System & Providers"),
            ("settings", "🎨  Themes & Settings"),
        ]

        for key, label in nav_specs:
            btn = QPushButton(label)
            btn.setObjectName("nav_button")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, k=key: self.switch_page(k))
            sb_layout.addWidget(btn)
            self.nav_buttons[key] = btn

        sb_layout.addStretch()

        # Quick Theme Toggle Button (3.5)
        self.quick_theme_btn = QPushButton("☀  LIGHT / DARK")
        self.quick_theme_btn.clicked.connect(self._toggle_theme_quick)
        sb_layout.addWidget(self.quick_theme_btn)

        # -----------------------------------------
        # MAIN PAGE STACK
        # -----------------------------------------
        content_wrap = QWidget()
        content_layout = QVBoxLayout(content_wrap)
        content_layout.setContentsMargins(14, 12, 14, 12)

        self.pages = QStackedWidget()

        self.chat_page = self.create_chat_page()
        self.productivity_page = ProductivityPage()
        self.productivity_page.announce_signal.connect(self.tts.speak)

        self.coding_page = CodingAssistantPage()
        self.cybersec_page = CybersecurityPage()
        self.automation_page = AutomationToolsPage()

        self.memory_page = MemoryManager()
        self.memory_page.session_selected.connect(self._open_session_from_history)

        self.dashboard_page = Dashboard()
        self.providers_page = self.create_provider_page()
        self.system_providers_page = self._create_system_and_providers_page()

        self.settings_page = SettingsPage(self.theme_mode, self.accent_color)
        self.settings_page.theme_changed.connect(self.apply_theme)
        self.settings_page.brain_settings_changed.connect(self._sync_brain_controls)

        self.page_map = {
            "chat": self.chat_page,
            "productivity": self.productivity_page,
            "coding": self.coding_page,
            "cybersec": self.cybersec_page,
            "automation": self.automation_page,
            "memory": self.memory_page,
            "dashboard": self.system_providers_page,
            "settings": self.settings_page,
        }

        for widget in self.page_map.values():
            self.pages.addWidget(widget)

        content_layout.addWidget(self.pages)

        main_layout.addWidget(sidebar)
        main_layout.addWidget(content_wrap, 1)

        self.switch_page("chat")

    def _create_system_and_providers_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)
        layout.addWidget(self.dashboard_page, 1)
        layout.addWidget(self.providers_page, 2)
        return page

    # =========================================
    # CHAT PAGE (1.1 - 1.8, 3.3, 3.7, 7.1 - 7.8)
    # =========================================

    def create_chat_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)

        # Header controls
        header = QHBoxLayout()

        title = QLabel("JARVIS AI CHAT")
        title.setObjectName("page_title")
        header.addWidget(title)
        header.addStretch()

        header.addWidget(QLabel("MODE:"))
        self.personality_selector = QComboBox()
        for key, meta in PERSONALITIES.items():
            self.personality_selector.addItem(key, key)
        self.personality_selector.setCurrentText(get_personality())
        self.personality_selector.currentTextChanged.connect(self._change_personality_quick)
        header.addWidget(self.personality_selector)

        header.addWidget(QLabel("PROVIDER:"))
        self.provider_selector = QComboBox()
        self.provider_selector.addItems(["AUTO", "GEMINI", "GROQ", "OLLAMA"])
        self.provider_selector.setCurrentText(get_provider_mode().upper())
        self.provider_selector.currentTextChanged.connect(self.change_provider)
        header.addWidget(self.provider_selector)

        self.summarize_button = QPushButton("SUMMARIZE")
        self.summarize_button.clicked.connect(self.summarize_current_chat)
        header.addWidget(self.summarize_button)

        self.new_chat_button = QPushButton("NEW CHAT")
        self.new_chat_button.clicked.connect(self.new_conversation)
        header.addWidget(self.new_chat_button)

        # Status & attachment bar
        sub_bar = QHBoxLayout()
        self.provider_status = QLabel("Smart Routing: Auto | Tip: type /help for commands")
        self.provider_status.setObjectName("provider_status")

        self.attachment_label = QLabel("")
        self.attachment_label.setObjectName("subtitle")

        self.clear_attach_btn = QPushButton("✕")
        self.clear_attach_btn.setFixedWidth(30)
        self.clear_attach_btn.setVisible(False)
        self.clear_attach_btn.clicked.connect(self._clear_attachments)

        sub_bar.addWidget(self.provider_status, 1)
        sub_bar.addWidget(self.attachment_label)
        sub_bar.addWidget(self.clear_attach_btn)

        # Chat display
        self.chat_display = QTextBrowser()
        self.chat_display.setOpenExternalLinks(True)
        self.chat_display.setPlaceholderText(
            "Ask JARVIS anything, attach an image or PDF/document, or try /help, /search, /yt, /remember, /todo..."
        )

        # Input bar + Attachment buttons
        input_layout = QHBoxLayout()

        self.attach_img_btn = QPushButton("IMG")
        self.attach_img_btn.setToolTip("Attach an image for Vision analysis (7.1)")
        self.attach_img_btn.clicked.connect(self._attach_image)

        self.attach_doc_btn = QPushButton("DOC/PDF")
        self.attach_doc_btn.setToolTip("Attach a PDF, DOCX, or text document (7.2 - 7.3)")
        self.attach_doc_btn.clicked.connect(self._attach_document)

        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Ask JARVIS anything or type /help for slash commands...")
        self.message_input.returnPressed.connect(self.send_message)

        self.send_button = QPushButton("SEND")
        self.send_button.clicked.connect(self.send_message)

        self.stop_speaking_button = QPushButton("MUTE TTS")
        self.stop_speaking_button.clicked.connect(self.stop_speaking)

        input_layout.addWidget(self.attach_img_btn)
        input_layout.addWidget(self.attach_doc_btn)
        input_layout.addWidget(self.message_input, 5)
        input_layout.addWidget(self.send_button, 1)
        input_layout.addWidget(self.stop_speaking_button)

        layout.addLayout(header)
        layout.addLayout(sub_bar)
        layout.addWidget(self.chat_display, 1)
        layout.addLayout(input_layout)

        return page

    # =========================================
    # ATTACHMENTS (7.1 IMAGE, 7.2 PDF, 7.3 DOCS)
    # =========================================

    def _attach_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Attach Image for Vision Analysis", "", "Images (*.png *.jpg *.jpeg *.webp *.gif *.bmp)"
        )
        if not path:
            return
        self.attached_image_path = path
        self._update_attachment_banner()

    def _attach_document(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Attach PDF or Document", "", "Documents (*.pdf *.docx *.txt *.md *.csv *.json *.py *.log);;All Files (*)"
        )
        if not path:
            return
        try:
            self.attached_doc_meta = extract_document_text(path)
            self._update_attachment_banner()
        except Exception as err:
            QMessageBox.warning(self, "Document Load Error", str(err))

    def _clear_attachments(self):
        self.attached_image_path = None
        self.attached_doc_meta = None
        self._update_attachment_banner()

    def _update_attachment_banner(self):
        parts = []
        if self.attached_image_path:
            parts.append(f"Image: {Path(self.attached_image_path).name}")
        if self.attached_doc_meta:
            parts.append(f"Doc: {self.attached_doc_meta['name']} ({self.attached_doc_meta['word_count']} words)")
        text = "  |  ".join(parts)
        self.attachment_label.setText(text)
        self.clear_attach_btn.setVisible(bool(parts))

    # =========================================
    # PROVIDER & PERSONALITY CONTROLS
    # =========================================

    def change_provider(self, selected_provider):
        provider = selected_provider.lower().strip()
        try:
            set_provider_mode(provider)
            desc = "Smart Auto-Routing & Fallback enabled" if provider == "auto" else f"Locked to {selected_provider}"
            self.provider_status.setText(desc)
        except Exception as error:
            QMessageBox.warning(self, "Provider Error", str(error))

    def _change_personality_quick(self, selected_key):
        if selected_key in PERSONALITIES:
            set_personality(selected_key)
            self.provider_status.setText(f"Personality: {PERSONALITIES[selected_key]['label']}")
            idx = self.settings_page.personality_combo.findData(selected_key)
            if idx >= 0:
                self.settings_page.personality_combo.blockSignals(True)
                self.settings_page.personality_combo.setCurrentIndex(idx)
                self.settings_page.personality_combo.blockSignals(False)

    def _sync_brain_controls(self):
        p = get_personality()
        self.personality_selector.blockSignals(True)
        self.personality_selector.setCurrentText(p)
        self.personality_selector.blockSignals(False)
        self.provider_status.setText(f"Personality: {p} | Ready")

    # =========================================
    # AI PROVIDER HEALTH PANEL
    # =========================================

    def create_provider_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)

        top = QHBoxLayout()
        title = QLabel("AI PROVIDER HEALTH")
        title.setObjectName("page_title")
        self.check_all_button = QPushButton("CHECK ALL PROVIDERS")
        self.check_all_button.clicked.connect(self.check_all_providers)
        top.addWidget(title)
        top.addStretch()
        top.addWidget(self.check_all_button)
        layout.addLayout(top)

        grid = QGridLayout()
        grid.setSpacing(12)

        providers = [
            ("gemini", "Gemini", GEMINI_MODEL),
            ("groq", "Groq", GROQ_MODEL),
            ("ollama", "Ollama", OLLAMA_MODEL),
        ]

        for index, (provider, name, model) in enumerate(providers):
            card = QFrame()
            card.setObjectName("provider_card")
            card_layout = QVBoxLayout(card)

            name_label = QLabel(name)
            name_label.setStyleSheet("font-size: 17px; font-weight: bold;")
            model_label = QLabel(f"Model: {model}")
            model_label.setObjectName("subtitle")
            status_label = QLabel("NOT CHECKED")
            status_label.setStyleSheet("color: #ffaa00; font-weight: bold;")
            detail_label = QLabel("Waiting for health check...")
            detail_label.setWordWrap(True)

            check_button = QPushButton("CHECK CONNECTION")
            check_button.clicked.connect(lambda checked=False, p=provider: self.check_provider(p))

            card_layout.addWidget(name_label)
            card_layout.addWidget(model_label)
            card_layout.addWidget(status_label)
            card_layout.addWidget(detail_label)
            card_layout.addWidget(check_button)

            grid.addWidget(card, 0, index)

            self.provider_status_labels[provider] = status_label
            self.provider_detail_labels[provider] = detail_label
            self.provider_check_buttons[provider] = check_button

        layout.addLayout(grid)
        return page

    def check_provider(self, provider):
        provider = provider.lower().strip()
        if provider not in self.provider_status_labels or provider in self.health_workers:
            return

        self.provider_status_labels[provider].setText("CHECKING...")
        self.provider_status_labels[provider].setStyleSheet("color: #ffaa00; font-weight: bold;")
        self.provider_detail_labels[provider].setText("Testing provider connection...")
        self.provider_check_buttons[provider].setEnabled(False)

        worker = JarvisWorker(task="health_check", provider=provider)
        worker.health_check_completed.connect(self.show_provider_health)
        worker.error_occurred.connect(lambda error, p=provider: self.show_health_error(p, error))
        worker.finished.connect(lambda p=provider: self.health_worker_finished(p))
        self.health_workers[provider] = worker
        worker.start()

    def check_all_providers(self):
        providers = ["gemini", "groq", "ollama"]
        self.check_all_button.setEnabled(False)
        self.check_all_pending = set(providers)
        for provider in providers:
            if provider not in self.health_workers:
                self.check_provider(provider)
        self.check_all_pending.intersection_update(self.health_workers.keys())
        if not self.check_all_pending:
            self.check_all_button.setEnabled(True)

    def show_provider_health(self, provider, is_healthy, details):
        provider = provider.lower()
        if provider not in self.provider_status_labels:
            return
        if is_healthy:
            self.provider_status_labels[provider].setText("HEALTHY")
            self.provider_status_labels[provider].setStyleSheet("color: #00e676; font-weight: bold;")
        else:
            self.provider_status_labels[provider].setText("UNAVAILABLE")
            self.provider_status_labels[provider].setStyleSheet("color: #ff5566; font-weight: bold;")
        self.provider_detail_labels[provider].setText(str(details))

    def show_health_error(self, provider, error):
        if provider not in self.provider_status_labels:
            return
        self.provider_status_labels[provider].setText("ERROR")
        self.provider_status_labels[provider].setStyleSheet("color: #ff5566; font-weight: bold;")
        self.provider_detail_labels[provider].setText(str(error))

    def health_worker_finished(self, provider):
        worker = self.health_workers.pop(provider, None)
        if worker is not None:
            worker.deleteLater()
        if provider in self.provider_check_buttons:
            self.provider_check_buttons[provider].setEnabled(True)
        if provider in self.check_all_pending:
            self.check_all_pending.discard(provider)
            if not self.check_all_pending:
                self.check_all_button.setEnabled(True)

    # =========================================
    # SLASH COMMANDS & CUSTOM COMMANDS (2.x, 4.x, 7.4 - 7.8)
    # =========================================

    def _try_handle_slash_command(self, raw_message: str) -> bool:
        """Handle built-in and custom /commands. Returns True if handled locally or dispatched."""
        if not raw_message.startswith("/"):
            return False

        parts = raw_message.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd == "/help":
            customs = get_custom_commands()
            custom_lines = "\n".join(f"  /{c[1]} — {c[4] or c[3]}" for c in customs) or "  (none yet — add in Automation > Plugins & Commands)"
            tools = ", ".join(t["name"] for t in plugin_manager.list_tools()) or "(none)"
            help_text = (
                "Built-in JARVIS Commands:\n"
                "  /search <query>         — Live web search + AI answer\n"
                "  /yt <youtube_url>       — Summarize a YouTube video\n"
                "  /remember <fact>        — Save fact to Long-Term Memory\n"
                "  /summarize              — Summarize this conversation\n"
                "  /open <app or url>      — Open desktop app or website\n"
                "  /google <query>         — Search Google in browser\n"
                "  /youtube <query>        — Search YouTube in browser\n"
                "  /vol <up|down|mute|0-100> — Control system volume\n"
                "  /screenshot             — Capture screenshot (with permission)\n"
                "  /run <command>          — Run terminal command (with approval)\n"
                "  /todo <task>            — Quick-add to-do task\n"
                "  /note <text>            — Quick-capture a note\n"
                "  /remind <YYYY-MM-DD HH:MM> <msg> — Set reminder alarm\n"
                f"  /plugin <name> [args]   — Run plugin tool ({tools})\n\n"
                f"Your Custom Commands:\n{custom_lines}"
            )
            self.add_message("SYSTEM", help_text)
            return True

        if cmd == "/remember":
            if not arg:
                self.add_message("SYSTEM", "Usage: /remember <fact to remember>")
                return True
            add_long_term_memory(arg, category="explicit")
            self.add_message("SYSTEM", f"Saved to Long-Term Memory: {arg}")
            return True

        if cmd == "/summarize":
            self.summarize_current_chat()
            return True

        if cmd == "/open":
            try:
                if "." in arg or arg.startswith(("http://", "https://")) or arg.lower() in ("google", "youtube", "github", "gmail", "wikipedia", "owasp"):
                    msg = open_website(arg)
                else:
                    msg = open_application(arg)
                self.add_message("SYSTEM", msg)
            except Exception as err:
                self.add_message("ERROR", str(err))
            return True

        if cmd == "/google":
            try:
                self.add_message("SYSTEM", search_google(arg))
            except Exception as err:
                self.add_message("ERROR", str(err))
            return True

        if cmd == "/youtube":
            try:
                self.add_message("SYSTEM", search_youtube(arg))
            except Exception as err:
                self.add_message("ERROR", str(err))
            return True

        if cmd == "/vol":
            try:
                a = arg.lower()
                if a == "up":
                    msg = volume_up()
                elif a == "down":
                    msg = volume_down()
                elif a == "mute":
                    msg = volume_mute_toggle()
                elif a.isdigit():
                    msg = set_volume_percent(int(a))
                else:
                    msg = "Usage: /vol up | down | mute | 0-100"
                self.add_message("SYSTEM", msg)
            except Exception as err:
                self.add_message("ERROR", str(err))
            return True

        if cmd == "/screenshot":
            ans = QMessageBox.question(
                self,
                "Screenshot Permission",
                "Allow JARVIS to capture your screen and save it to data/screenshots/?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if ans == QMessageBox.StandardButton.Yes:
                try:
                    p = capture_screenshot_qapp(QApplication.instance())
                    self.add_message("SYSTEM", f"Screenshot saved: {p}")
                except Exception as err:
                    self.add_message("ERROR", str(err))
            else:
                self.add_message("SYSTEM", "Screenshot permission declined.")
            return True

        if cmd == "/run":
            if not arg:
                self.add_message("SYSTEM", "Usage: /run <command>")
                return True
            warn = "\n\nWARNING: Potentially destructive pattern detected!" if is_potentially_dangerous_command(arg) else ""
            ans = QMessageBox.question(
                self,
                "Approve Terminal Command",
                f"Execute this command?\n\n{arg}{warn}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if ans != QMessageBox.StandardButton.Yes:
                self.add_message("SYSTEM", "Command execution cancelled.")
                return True
            try:
                res = run_approved_command(arg)
                out = res["stdout"] or res["stderr"] or "(no output)"
                self.add_message("SYSTEM", f"$ {arg} (exit {res['returncode']})\n{out}")
            except Exception as err:
                self.add_message("ERROR", str(err))
            return True

        if cmd == "/todo":
            if not arg:
                self.add_message("SYSTEM", "Usage: /todo <task description>")
                return True
            add_task(arg)
            self.productivity_page.refresh_all()
            self.add_message("SYSTEM", f"Task added: {arg}")
            return True

        if cmd == "/note":
            if not arg:
                self.add_message("SYSTEM", "Usage: /note <note text>")
                return True
            save_note(arg[:40], arg, tags="quick")
            self.productivity_page.refresh_all()
            self.add_message("SYSTEM", f"Quick note saved.")
            return True

        if cmd == "/remind":
            m = re.match(r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})\s+(.+)$", arg)
            if not m:
                self.add_message("SYSTEM", "Usage: /remind YYYY-MM-DD HH:MM <reminder message>")
                return True
            try:
                add_reminder(m.group(2), m.group(1))
                self.productivity_page.refresh_all()
                self.add_message("SYSTEM", f"Reminder set for {m.group(1)}: {m.group(2)}")
            except Exception as err:
                self.add_message("ERROR", str(err))
            return True

        if cmd == "/plugin":
            p_parts = arg.split(maxsplit=1)
            if not p_parts:
                names = ", ".join(t["name"] for t in plugin_manager.list_tools())
                self.add_message("SYSTEM", f"Available plugins: {names or '(none)'}")
                return True
            try:
                res = plugin_manager.run_tool(p_parts[0], p_parts[1] if len(p_parts) > 1 else "")
                self.add_message("SYSTEM", f"[Plugin: {p_parts[0]}]\n{res}")
            except Exception as err:
                self.add_message("ERROR", str(err))
            return True

        if cmd == "/search":
            if not arg:
                self.add_message("SYSTEM", "Usage: /search <web query>")
                return True
            self._start_worker_stream(
                display_user_msg=f"/search {arg}",
                worker=JarvisWorker(message=arg, task="web_search", extra={"synthesize": True}),
            )
            return True

        if cmd == "/yt":
            if not arg:
                self.add_message("SYSTEM", "Usage: /yt <YouTube URL>")
                return True
            self._start_worker_stream(
                display_user_msg=f"/yt {arg}",
                worker=JarvisWorker(message=arg, task="youtube_summary", extra={"stream_to_chat": True}),
            )
            return True

        # Check user-defined custom commands (7.8)
        custom = get_custom_command_by_name(cmd.lstrip("/"))
        if custom:
            _, name, action_type, payload, _ = custom
            if action_type == "url":
                try:
                    self.add_message("SYSTEM", open_website(payload.replace("{args}", arg)))
                except Exception as err:
                    self.add_message("ERROR", str(err))
                return True
            elif action_type == "app":
                try:
                    self.add_message("SYSTEM", open_application(payload))
                except Exception as err:
                    self.add_message("ERROR", str(err))
                return True
            else:
                expanded = payload.replace("{args}", arg) if "{args}" in payload else f"{payload} {arg}".strip()
                self._start_worker_stream(
                    display_user_msg=f"/{name} {arg}".strip(),
                    worker=JarvisWorker(message=expanded, task="chat"),
                )
                return True

        return False

    # =========================================
    # SEND MESSAGE & STREAMING
    # =========================================

    def send_message(self):
        message = self.message_input.text().strip()
        if not message and not self.attached_image_path and not self.attached_doc_meta:
            return
        if self.worker is not None:
            return

        self.message_input.clear()
        self.stop_speaking()

        if message.startswith("/") and not self.attached_image_path and not self.attached_doc_meta:
            if self._try_handle_slash_command(message):
                return

        if not message:
            if self.attached_image_path:
                message = "Analyze this image in detail."
            elif self.attached_doc_meta:
                message = f"Summarize and explain the key points of {self.attached_doc_meta['name']}."

        image_path = self.attached_image_path
        doc_text = self.attached_doc_meta["text"] if self.attached_doc_meta else None
        doc_name = self.attached_doc_meta["name"] if self.attached_doc_meta else None
        self._clear_attachments()

        display_msg = message
        if image_path:
            display_msg = f"[Image: {Path(image_path).name}]\n{display_msg}"
        if doc_name:
            display_msg = f"[Document: {doc_name}]\n{display_msg}"

        worker = JarvisWorker(
            message=message,
            task="chat",
            image_path=image_path,
            document_context=doc_text,
        )
        self._start_worker_stream(display_user_msg=display_msg, worker=worker)

    def _start_worker_stream(self, display_user_msg: str, worker: JarvisWorker):
        self.add_message("YOU", display_user_msg)

        self.send_button.setEnabled(False)
        self.new_chat_button.setEnabled(False)
        self.provider_selector.setEnabled(False)
        self.summarize_button.setEnabled(False)

        self.ai_core.set_state("thinking")
        self.status_pill.set_status("THINKING", animate=True)

        self.start_stream_display()

        self.worker = worker
        self.worker.chunk_received.connect(self.append_stream_chunk)
        self.worker.stream_reset.connect(self.reset_stream_display)
        self.worker.stream_finished.connect(self.stream_completed)
        self.worker.task_completed.connect(self._on_chat_task_completed)
        self.worker.error_occurred.connect(self.show_error)
        self.worker.finished.connect(self.worker_finished)
        self.worker.start()

    def _on_chat_task_completed(self, title, body):
        self.remove_stream_display()
        self.add_message(title, body)

    def summarize_current_chat(self):
        if self.worker is not None:
            return
        self.send_button.setEnabled(False)
        self.summarize_button.setEnabled(False)
        self.ai_core.set_state("thinking")
        self.status_pill.set_status("SUMMARIZING", animate=True)

        self.worker = JarvisWorker(task="summarize")
        self.worker.task_completed.connect(lambda t, b: self.add_message(t, b))
        self.worker.error_occurred.connect(self.show_error)
        self.worker.finished.connect(self.worker_finished)
        self.worker.start()

    def start_stream_display(self):
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.stream_start_position = cursor.position()
        cursor.insertBlock()

        label_format = QTextCharFormat()
        label_format.setForeground(QColor("#00e676"))
        label_format.setFontWeight(QFont.Weight.Bold)
        cursor.insertText("JARVIS: ", label_format)

        self.stream_cursor = cursor
        self.chat_display.setTextCursor(cursor)
        self.chat_display.ensureCursorVisible()

    def append_stream_chunk(self, chunk):
        if self.stream_cursor is None:
            return

        text_chunk = str(chunk)
        self.stream_cursor.insertText(text_chunk, self.stream_text_format)
        self.chat_display.setTextCursor(self.stream_cursor)
        self.chat_display.ensureCursorVisible()

        self.speech_buffer += text_chunk
        sentences = re.split(r"(?<=[.!?])\s+", self.speech_buffer)
        self.speech_buffer = sentences.pop()

        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                self.tts.speak(sentence)

    def remove_stream_display(self):
        if self.stream_start_position is None:
            return
        cursor = QTextCursor(self.chat_display.document())
        cursor.setPosition(self.stream_start_position)
        cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        self.chat_display.setTextCursor(cursor)
        self.stream_cursor = None
        self.stream_start_position = None

    def reset_stream_display(self):
        self.tts.clear()
        self.speech_buffer = ""
        self.remove_stream_display()
        self.start_stream_display()

    def stream_completed(self, provider_name, full_response):
        remaining_text = self.speech_buffer.strip()
        if remaining_text:
            self.tts.speak(remaining_text)
        self.speech_buffer = ""
        self.stream_cursor = None
        self.stream_start_position = None
        self.provider_status.setText(f"Last used: {provider_name}")

    def show_error(self, error):
        self.tts.clear()
        self.speech_buffer = ""
        self.remove_stream_display()
        self.ai_core.set_state("error")
        self.add_message("ERROR", str(error))

    def worker_finished(self):
        worker = self.sender()
        self.worker = None
        self.send_button.setEnabled(True)
        self.new_chat_button.setEnabled(True)
        self.provider_selector.setEnabled(True)
        self.summarize_button.setEnabled(True)
        if not self.tts.is_speaking:
            self.ai_core.set_state("idle")
            self.status_pill.set_status("READY", animate=False)
        if worker is not None:
            worker.deleteLater()

    # =========================================
    # CHAT MESSAGE FORMATTING & HISTORY LOADING
    # =========================================

    def add_message(self, sender, message):
        colors = {
            "YOU": self.accent_color,
            "JARVIS": "#00e676",
            "SYSTEM": "#ffab00",
            "CONVERSATION SUMMARY": "#a855f7",
            "ERROR": "#ff5566",
        }
        color = colors.get(sender, self.accent_color)
        text_color = "#0f172a" if self.theme_mode == "light" else "#f1f5f9"

        safe_message = (
            str(message)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br>")
        )

        html = f"""
        <div style="margin: 10px 4px;">
            <span style="color: {color}; font-weight: bold; font-size: 14px;">{sender}:</span>
            <span style="color: {text_color}; font-size: 14px;"> {safe_message}</span>
        </div>
        """
        self.chat_display.append(html)
        self.chat_display.verticalScrollBar().setValue(self.chat_display.verticalScrollBar().maximum())

    def load_active_session_to_chat(self):
        self.chat_display.clear()
        rows = get_recent_messages(limit=40)
        if not rows:
            self.add_message("JARVIS", "Systems online. How may I assist you today? Type /help for slash commands.")
            return
        for _, role, msg, _ in rows:
            sender = "YOU" if role == "user" else "JARVIS"
            self.add_message(sender, msg)

    def _open_session_from_history(self, session_id: str):
        if self.worker is not None:
            QMessageBox.information(self, "Please wait", "Wait for the active response to finish before switching sessions.")
            return
        set_active_session_id(session_id)
        self.load_active_session_to_chat()
        self.switch_page("chat")

    def new_conversation(self):
        if self.worker is not None:
            QMessageBox.information(self, "Please wait", "JARVIS is still processing your message.")
            return

        answer = QMessageBox.question(
            self,
            "New conversation",
            "Start a new conversation? Your previous conversation will remain saved in History.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            self.stop_speaking()
            create_new_conversation()
            start_new_chat()
            self.chat_display.clear()
            self.add_message("JARVIS", "New conversation started. How can I help?")
        except Exception as error:
            QMessageBox.critical(self, "Error", f"Could not start a new conversation:\n{error}")

    # =========================================
    # NAVIGATION & LIVE INDICATORS
    # =========================================

    def switch_page(self, key: str):
        if key not in self.page_map:
            return
        if key == "memory":
            self.memory_page.refresh()
        elif key == "productivity":
            self.productivity_page.refresh_all()

        self.pages.setCurrentWidget(self.page_map[key])

        for nav_key, btn in self.nav_buttons.items():
            btn.setProperty("active", nav_key == key)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    # Compatibility navigation helpers
    def open_chat(self):
        self.switch_page("chat")

    def open_dashboard(self):
        self.switch_page("dashboard")

    def open_memory(self):
        self.switch_page("memory")

    def open_providers(self):
        self.switch_page("dashboard")

    def _sync_live_indicators(self):
        speaking = self.tts.is_speaking
        self.waveform.set_active(speaking)
        if speaking:
            self.ai_core.set_state("speaking")
            self.status_pill.set_status("SPEAKING", animate=True)
        elif self.worker is not None:
            self.ai_core.set_state("thinking")
        else:
            self.ai_core.set_state("idle")
            if self.status_pill.text() != "READY":
                self.status_pill.set_status("READY", animate=False)

    def _check_due_reminders(self):
        try:
            due = get_due_reminders()
            for _, title, remind_at in due:
                self.tts.speak(f"Reminder alert: {title}")
                self.productivity_page.refresh_reminders()
                QMessageBox.information(self, "JARVIS Reminder Alarm", f"Time: {remind_at}\n\n{title}")
        except Exception:
            pass

    # =========================================
    # THEMES & ACCENT COLORS (3.5, 3.6)
    # =========================================

    def apply_theme(self, theme_mode: str, accent_hex: str):
        self.theme_mode = (theme_mode or "dark").lower()
        self.accent_color = accent_hex or "#00d9ff"
        set_setting("theme_mode", self.theme_mode)
        set_setting("accent_color", self.accent_color)

        self.setStyleSheet(build_stylesheet(self.theme_mode, self.accent_color))
        self.ai_core.set_accent(self.accent_color)
        self.waveform.set_accent(self.accent_color)

        stream_fg = QColor("#0f172a") if self.theme_mode == "light" else QColor("#f1f5f9")
        self.stream_text_format.setForeground(stream_fg)

        self.quick_theme_btn.setText("🌙  DARK MODE" if self.theme_mode == "light" else "☀  LIGHT MODE")

    def apply_styles(self):
        self.apply_theme(self.theme_mode, self.accent_color)

    def _toggle_theme_quick(self):
        next_mode = "light" if self.theme_mode == "dark" else "dark"
        self.apply_theme(next_mode, self.accent_color)

    # =========================================
    # CLEAN SHUTDOWN
    # =========================================

    def closeEvent(self, event):
        self.ui_sync_timer.stop()
        self.reminder_timer.stop()
        self.ai_core.stop_animation()
        self.waveform.stop_animation()
        self.status_pill.stop_animation()

        if hasattr(self, "dashboard_page") and hasattr(self.dashboard_page, "timer"):
            self.dashboard_page.timer.stop()

        for page in (self.productivity_page, self.coding_page, self.cybersec_page, self.automation_page, self.memory_page):
            if hasattr(page, "shutdown"):
                page.shutdown()

        if hasattr(self, "tts"):
            self.tts.shutdown()

        if self.worker is not None and self.worker.isRunning():
            self.worker.requestInterruption()
            self.worker.quit()
            self.worker.wait(2000)

        for worker in list(self.health_workers.values()):
            if worker is not None and worker.isRunning():
                worker.requestInterruption()
                worker.quit()
                worker.wait(1000)

        event.accept()


# =========================================
# APPLICATION ENTRY POINT
# =========================================

def main():
    app = QApplication(sys.argv)
    window = JarvisWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
