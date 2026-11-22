"""Cinematic Stark Industries J.A.R.V.I.S HUD Interface (All 7 Feature Pillars)."""

import html as html_lib
import re
import sys
import threading
from datetime import datetime
from pathlib import Path
import psutil

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
    QSystemTrayIcon,
    QMenu,
    QTabWidget,
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import (
    QTextCursor,
    QTextCharFormat,
    QColor,
    QFont,
    QIcon,
    QPixmap,
    QPainter,
    QPen,
    QAction,
)

from interface.worker import JarvisWorker
from interface.dashboard import Dashboard
from interface.memory_page import MemoryManager
from interface.productivity_page import ProductivityPage
from interface.coding_page import CodingAssistantPage
from interface.cybersec_page import CybersecurityPage
from interface.automation_page import AutomationToolsPage
from interface.settings_page import SettingsPage
from interface.spotlight import SpotlightDialog, GlobalHotkeyFilter
from interface.themes import build_stylesheet, hex_to_rgba
from interface.cyber_widgets import CyberRobotAvatar, SymmetricalAudioWaveform
from interface.home_page import HomePage
from interface.widgets import (
    HUDCanvasWidget,
    AICoreWidget,
    AudioWaveformWidget,
    ArcGaugeWidget,
    TelemetryGraphWidget,
    StatusPulseLabel,
)

from core.personality import PERSONALITIES
from core.sfx import hud_sfx
from tools.exporter import build_session_markdown, export_markdown, export_text_to_pdf
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
    get_long_term_memories,
    get_custom_command_by_name,
    get_custom_commands,
    get_setting,
    set_setting,
)
from core.productivity import (
    add_task,
    list_tasks,
    save_note,
    add_reminder,
    list_reminders,
    get_due_reminders,
    build_daily_summary_text,
)
from core.scheduler import (
    ACTION_TYPES,
    save_scheduled_task,
    list_scheduled_tasks,
    claim_due_tasks,
)
from core.tts import JarvisTTS

from tools.computer import (
    open_application,
    open_new_tab,
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
from tools.cybersec import get_local_network_info
from tools.documents import extract_document_text
from tools.plugins import plugin_manager


def render_markdown_html(text: str, accent: str, is_light: bool) -> str:
    """Convert Markdown text (fenced code, inline code, bold, headers, bullets) into styled HUD HTML."""
    code_bg = "#e8f0fa" if is_light else "#040a15"
    code_border = hex_to_rgba(accent, 0.45)
    inline_bg = hex_to_rgba(accent, 0.14)

    segments = re.split(r"```([a-zA-Z0-9_+-]*)\n?(.*?)```", str(text), flags=re.DOTALL)
    out = []

    for idx, seg in enumerate(segments):
        mod = idx % 3
        if mod == 1:
            # Language label captured alongside code block; handled in mod == 2
            continue
        elif mod == 2:
            lang = segments[idx - 1].strip().upper() or "CODE"
            escaped_code = html_lib.escape(seg.strip("\n"))
            out.append(
                f'<div style="margin:8px 0; padding:8px 10px; background:{code_bg}; '
                f'border:1px solid {code_border}; border-left:3px solid {accent}; border-radius:6px;">'
                f'<div style="color:{accent}; font-family:Consolas,monospace; font-size:10px; '
                f'font-weight:bold; margin-bottom:4px;">{lang}</div>'
                f'<pre style="margin:0; font-family:Consolas,monospace; font-size:12.5px; '
                f'white-space:pre-wrap;">{escaped_code}</pre></div>'
            )
        else:
            esc = html_lib.escape(seg)
            # Inline code
            esc = re.sub(
                r"`([^`\n]+)`",
                lambda m: (
                    f'<span style="background:{inline_bg}; color:{accent}; '
                    f'font-family:Consolas,monospace; padding:1px 4px; border-radius:3px;">{m.group(1)}</span>'
                ),
                esc,
            )
            # Bold
            esc = re.sub(r"\*\*([^\*\n]+)\*\*", r"<b>\1</b>", esc)
            # Markdown headings & bullets line by line
            lines = esc.splitlines()
            formatted_lines = []
            for ln in lines:
                s = ln.strip()
                if s.startswith("### "):
                    formatted_lines.append(f'<span style="color:{accent}; font-weight:bold; font-size:14px;">{s[4:]}</span><br>')
                elif s.startswith("## "):
                    formatted_lines.append(f'<span style="color:{accent}; font-weight:bold; font-size:15px;">{s[3:]}</span><br>')
                elif s.startswith("# "):
                    formatted_lines.append(f'<span style="color:{accent}; font-weight:bold; font-size:16px;">{s[2:]}</span><br>')
                elif s.startswith(("- ", "* ")):
                    formatted_lines.append(f'&nbsp;&nbsp;<span style="color:{accent};">▸</span> {s[2:]}<br>')
                else:
                    formatted_lines.append(ln + "<br>")
            html_part = "".join(formatted_lines)
            if html_part.endswith("<br>"):
                html_part = html_part[:-4]
            out.append(html_part)

    return "".join(out)


class JarvisWindow(QMainWindow):

    weather_updated = Signal(str)

    def __init__(self):
        super().__init__()

        self.setWindowTitle("J.A.R.V.I.S // MARK IX NEURAL HUD")
        self.resize(1360, 860)

        # Persisted theme & accent — default to signature Arc Reactor Cyan (#00d2ff)
        self.theme_mode = get_setting("theme_mode", "dark") or "dark"
        saved_accent = get_setting("accent_color", None)
        if not saved_accent:
            saved_accent = "#cf2538" if get_personality() == "ULTRON" else "#00d2ff"
        self.accent_color = saved_accent

        # Worker & streaming state
        self.worker = None
        self._weather_worker = None
        self.scheduled_workers = []
        self.agent_mode_enabled = False
        self.tts = JarvisTTS()
        self.speech_buffer = ""
        self._in_stream_code_block = False
        self._pending_backticks = ""
        self._pending_bracket = ""

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

        # Setup HUD UI & Theme
        self.setup_ui()
        self.apply_theme(self.theme_mode, self.accent_color)
        self.load_active_session_to_chat()
        self._setup_tray_and_spotlight()

        # Subtle Stark boot chime
        hud_sfx.play("boot")

        # 1. Live voice/core indicator timer (150ms)
        self.ui_sync_timer = QTimer(self)
        self.ui_sync_timer.timeout.connect(self._sync_live_indicators)
        self.ui_sync_timer.start(150)

        # 2. Live HUD clock & telemetry timer (1000ms)
        self.hud_telemetry_timer = QTimer(self)
        self.hud_telemetry_timer.timeout.connect(self._update_hud_telemetry)
        self.hud_telemetry_timer.start(1000)
        self._update_hud_telemetry()

        # 3. Live Reminder / Alarm polling timer (15s)
        self.reminder_timer = QTimer(self)
        self.reminder_timer.timeout.connect(self._check_due_reminders)
        self.reminder_timer.start(15000)

        # 4. Live Weather async refresh timer (every 15 min + startup via daemon thread)
        self.weather_updated.connect(self.rail_weather_label.setText)
        self.weather_timer = QTimer(self)
        self.weather_timer.timeout.connect(self.refresh_weather)
        self.weather_timer.start(900_000)
        self._startup_weather_timer = QTimer(self)
        self._startup_weather_timer.setSingleShot(True)
        self._startup_weather_timer.timeout.connect(self.refresh_weather)
        self._startup_weather_timer.start(1200)

        # 5. Live Custom Task Scheduler polling timer (every 10s)
        self.scheduler_timer = QTimer(self)
        self.scheduler_timer.timeout.connect(self._check_scheduled_tasks)
        self.scheduler_timer.start(10_000)
        self._startup_sched_timer = QTimer(self)
        self._startup_sched_timer.setSingleShot(True)
        self._startup_sched_timer.timeout.connect(self._check_scheduled_tasks)
        self._startup_sched_timer.start(2500)

    def stop_speaking(self):
        self.tts.clear()
        self.speech_buffer = ""

    # =========================================
    # MAIN HOLOGRAPHIC HUD SHELL
    # =========================================

    def setup_ui(self):
        # Holographic animated canvas as central backdrop
        self.hud_canvas = HUDCanvasWidget(self.theme_mode, self.accent_color)
        self.setCentralWidget(self.hud_canvas)

        root_layout = QHBoxLayout(self.hud_canvas)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Hidden or background-managed telemetry widgets for backward-compat
        self.ai_core = AICoreWidget(accent=self.accent_color)
        self.waveform = AudioWaveformWidget(accent=self.accent_color)
        self.status_pill = StatusPulseLabel()

        # -----------------------------------------
        # LEFT COMMAND DOCK (AUTHENTIC CYBER HUD SIDEBAR)
        # -----------------------------------------
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(248)
        sb_layout = QVBoxLayout(self.sidebar)
        sb_layout.setContentsMargins(14, 16, 14, 16)
        sb_layout.setSpacing(8)

        # Profile / Logo Header (Robot Avatar + JARVIS + Subtitle)
        header_frame = QWidget()
        hdr_layout = QHBoxLayout(header_frame)
        hdr_layout.setContentsMargins(0, 0, 0, 8)
        hdr_layout.setSpacing(10)

        self.sidebar_avatar = CyberRobotAvatar(accent=self.accent_color, size=46)
        self.sidebar_avatar.clicked.connect(lambda: self.switch_page("home"))

        brand_col = QVBoxLayout()
        brand_col.setSpacing(1)
        brand_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.logo_label = QLabel("JARVIS")
        self.logo_label.setObjectName("sidebar_brand_title")
        self.logo_label.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        self.logo_label.setStyleSheet("color: #ffffff; letter-spacing: 1px;")

        self.subtitle_label = QLabel("Your Personal AI Assistant")
        self.subtitle_label.setFont(QFont("Segoe UI", 8))
        self.subtitle_label.setStyleSheet("color: #7a92ad;")

        brand_col.addWidget(self.logo_label)
        brand_col.addWidget(self.subtitle_label)

        hdr_layout.addWidget(self.sidebar_avatar)
        hdr_layout.addLayout(brand_col)
        hdr_layout.addStretch()
        sb_layout.addWidget(header_frame)

        # Divider hairline
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background: rgba(0, 210, 255, 0.18);")
        sb_layout.addWidget(div)
        sb_layout.addSpacing(4)

        # Navigation Buttons (Inspired directly by the reference image)
        nav_specs = [
            ("home", "🏠  Home"),
            ("chat", "💬  Chat"),
            ("voice", "🎙  Voice Control"),
            ("tools", "⊞  Tools"),
            ("settings", "⚙  Settings"),
            ("about", "ℹ  About"),
        ]

        for key, label in nav_specs:
            btn = QPushButton(label)
            btn.setObjectName("nav_button")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, k=key: self.switch_page(k))
            sb_layout.addWidget(btn)
            self.nav_buttons[key] = btn

        sb_layout.addStretch()

        # Online Status Card
        status_card = QFrame()
        status_card.setObjectName("sidebar_status_card")
        sc_layout = QVBoxLayout(status_card)
        sc_layout.setContentsMargins(12, 10, 12, 10)
        sc_layout.setSpacing(2)

        dot_row = QHBoxLayout()
        dot_row.setSpacing(6)
        dot_lbl = QLabel("🟢")
        dot_lbl.setFont(QFont("Segoe UI Emoji", 9))
        dot_text = QLabel("Online")
        dot_text.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        dot_text.setStyleSheet("color: #00e676;")
        dot_row.addWidget(dot_lbl)
        dot_row.addWidget(dot_text)
        dot_row.addStretch()

        ready_text = QLabel("Ready to help!")
        ready_text.setFont(QFont("Segoe UI", 8))
        ready_text.setStyleSheet("color: #8da4be;")

        sc_layout.addLayout(dot_row)
        sc_layout.addWidget(ready_text)
        sb_layout.addWidget(status_card)

        # Quick theme switcher
        self.quick_theme_btn = QPushButton("☀  TITANIUM LIGHT")
        self.quick_theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.quick_theme_btn.setFixedHeight(30)
        self.quick_theme_btn.clicked.connect(self._toggle_theme_quick)
        sb_layout.addWidget(self.quick_theme_btn)

        # -----------------------------------------
        # RIGHT MAIN AREA: TOP HUD BAR + PAGE STACK
        # -----------------------------------------
        right_shell = QWidget()
        right_layout = QVBoxLayout(right_shell)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Top HUD Telemetry Strip
        topbar = QFrame()
        topbar.setObjectName("topbar")
        topbar.setFixedHeight(46)
        tb = QHBoxLayout(topbar)
        tb.setContentsMargins(14, 6, 16, 6)
        tb.setSpacing(10)

        self.toggle_sidebar_btn = QPushButton("☰")
        self.toggle_sidebar_btn.setFixedSize(32, 26)
        self.toggle_sidebar_btn.setStyleSheet("padding: 0px; font-size: 14px;")
        self.toggle_sidebar_btn.setToolTip("Show / Hide Left Sidebar")
        self.toggle_sidebar_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_sidebar_btn.clicked.connect(self._toggle_sidebar)

        self.hud_brand_label = QLabel("●  STARK INDUSTRIES // J.A.R.V.I.S CORE")
        self.hud_brand_label.setObjectName("hud_brand")

        # Instant cinematic identity switch: REAL JARVIS vs REAL ULTRON
        self.mode_jarvis_btn = QPushButton("J.A.R.V.I.S")
        self.mode_jarvis_btn.setFixedHeight(26)
        self.mode_jarvis_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mode_jarvis_btn.clicked.connect(lambda: self.apply_identity_preset("JARVIS"))

        self.mode_ultron_btn = QPushButton("ULTRON")
        self.mode_ultron_btn.setFixedHeight(26)
        self.mode_ultron_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mode_ultron_btn.clicked.connect(lambda: self.apply_identity_preset("ULTRON"))

        self.top_cpu_metric = QLabel("CPU --%")
        self.top_cpu_metric.setObjectName("hud_metric")
        self.top_ram_metric = QLabel("RAM --%")
        self.top_ram_metric.setObjectName("hud_metric")
        self.top_engine_metric = QLabel("AUTO • JARVIS")
        self.top_engine_metric.setObjectName("hud_metric")

        self.hud_clock_label = QLabel("00:00:00")
        self.hud_clock_label.setObjectName("hud_clock")

        self.toggle_rail_btn = QPushButton("HUD RAIL")
        self.toggle_rail_btn.setFixedHeight(26)
        self.toggle_rail_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_rail_btn.clicked.connect(self._toggle_telemetry_rail)

        # Window Controls (Minimize, Maximize/Restore, Close)
        self.min_btn = QPushButton("🗕")
        self.min_btn.setFixedSize(30, 26)
        self.min_btn.setToolTip("Minimize")
        self.min_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.min_btn.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,0.06); color: #c5d4e8; border: 1px solid rgba(255,255,255,0.12); border-radius: 4px; font-weight: bold; } "
            "QPushButton:hover { background: rgba(0,210,255,0.25); color: #ffffff; border-color: #00d2ff; }"
        )
        self.min_btn.clicked.connect(self.showMinimized)

        self.max_btn = QPushButton("🗖")
        self.max_btn.setFixedSize(30, 26)
        self.max_btn.setToolTip("Maximize / Restore")
        self.max_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.max_btn.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,0.06); color: #c5d4e8; border: 1px solid rgba(255,255,255,0.12); border-radius: 4px; font-weight: bold; } "
            "QPushButton:hover { background: rgba(0,210,255,0.25); color: #ffffff; border-color: #00d2ff; }"
        )
        self.max_btn.clicked.connect(self._toggle_maximize_window)

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(30, 26)
        self.close_btn.setToolTip("Close")
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,0.06); color: #c5d4e8; border: 1px solid rgba(255,255,255,0.12); border-radius: 4px; font-weight: bold; } "
            "QPushButton:hover { background: rgba(235,50,50,0.85); color: #ffffff; border-color: #ff3b3b; }"
        )
        self.close_btn.clicked.connect(self.close)

        tb.addWidget(self.toggle_sidebar_btn)
        tb.addWidget(self.hud_brand_label)
        tb.addSpacing(6)
        tb.addWidget(self.mode_jarvis_btn)
        tb.addWidget(self.mode_ultron_btn)
        tb.addStretch()
        tb.addWidget(self.top_cpu_metric)
        tb.addWidget(self.top_ram_metric)
        tb.addWidget(self.top_engine_metric)
        tb.addWidget(self.hud_clock_label)
        tb.addWidget(self.toggle_rail_btn)
        tb.addSpacing(4)
        tb.addWidget(self.min_btn)
        tb.addWidget(self.max_btn)
        tb.addWidget(self.close_btn)
        right_layout.addWidget(topbar)

        # Stacked Pages Container
        content_wrap = QWidget()
        content_wrap.setObjectName("page_root")
        content_layout = QVBoxLayout(content_wrap)
        content_layout.setContentsMargins(14, 10, 14, 10)

        self.pages = QStackedWidget()

        # 1. Cybernetic Hero Home Page
        self.home_page = HomePage(accent=self.accent_color)
        self.home_page.command_submitted.connect(self._handle_home_command)
        self.home_page.voice_toggled.connect(self._toggle_voice_listening)
        self.home_page.open_youtube_signal.connect(lambda: self._execute_quick_action("open_youtube"))
        self.home_page.search_google_signal.connect(lambda: self._execute_quick_action("search_google"))
        self.home_page.play_music_signal.connect(lambda: self._execute_quick_action("play_music"))
        self.home_page.check_time_signal.connect(lambda: self._execute_quick_action("check_time"))
        self.home_page.shutdown_pc_signal.connect(lambda: self._execute_quick_action("shutdown_pc"))

        # 2. Conversational Chat Console
        self.chat_page = self.create_chat_page()

        # Sub-pages for tools hub
        self.productivity_page = ProductivityPage()
        self.productivity_page.announce_signal.connect(self.tts.speak)
        self.productivity_page.run_scheduled_now_signal.connect(self._dispatch_scheduled_task)

        self.coding_page = CodingAssistantPage()
        self.cybersec_page = CybersecurityPage()
        self.automation_page = AutomationToolsPage()

        self.memory_page = MemoryManager()
        self.memory_page.session_selected.connect(self._open_session_from_history)

        self.dashboard_page = Dashboard(accent=self.accent_color)
        self.providers_page = self.create_provider_page()
        self.system_providers_page = self._create_system_and_providers_page()

        self.settings_page = SettingsPage(
            self.theme_mode,
            self.accent_color,
            current_voice=self.tts.voice,
            current_rate=self.tts.rate,
        )
        self.settings_page.theme_changed.connect(self.apply_theme)
        self.settings_page.brain_settings_changed.connect(self._sync_brain_controls)
        self.settings_page.voice_changed.connect(self._on_voice_settings_changed)
        self.settings_page.preset_identity_selected.connect(self.apply_identity_preset)
        self.settings_page.weather_city_changed.connect(lambda _c: self.refresh_weather())

        # 3. Dedicated Voice Control Page
        self.voice_page = self._create_voice_control_page()

        # 4. Grouped Tools Hub
        self.tools_hub = self._create_tools_hub()

        # 5. About Page
        self.about_page = self._create_about_page()

        self.page_map = {
            "home": self.home_page,
            "chat": self.chat_page,
            "voice": self.voice_page,
            "tools": self.tools_hub,
            "settings": self.settings_page,
            "about": self.about_page,
        }

        for widget in self.page_map.values():
            self.pages.addWidget(widget)

        content_layout.addWidget(self.pages)
        right_layout.addWidget(content_wrap, 1)

        root_layout.addWidget(self.sidebar)
        root_layout.addWidget(right_shell, 1)

        self.switch_page("home")

    def _create_system_and_providers_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)
        layout.addWidget(self.dashboard_page, 3)
        layout.addWidget(self.providers_page, 2)
        return page

    def _create_tools_hub(self):
        hub = QTabWidget()
        hub.setObjectName("tools_hub_tabs")
        hub.addTab(self.productivity_page, "📅 Productivity & Scheduler")
        hub.addTab(self.automation_page, "⚡ Automation & RAG")
        hub.addTab(self.coding_page, "💻 Code Studio")
        hub.addTab(self.cybersec_page, "🛡️ Cyber Defense & Vault")
        hub.addTab(self.system_providers_page, "📊 Telemetry & Engines")
        hub.addTab(self.memory_page, "🧠 Memory & History")
        return hub

    def _create_voice_control_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Header Banner
        hdr = QHBoxLayout()
        title_box = QVBoxLayout()
        v_title = QLabel("VOICE SYNTHESIS & RECOGNITION MATRIX")
        v_title.setObjectName("page_title")
        v_sub = QLabel("Configure real-time neural speech profiles, latency presets, and audio harmonics.")
        v_sub.setObjectName("subtitle")
        title_box.addWidget(v_title)
        title_box.addWidget(v_sub)
        hdr.addLayout(title_box)
        hdr.addStretch()
        layout.addLayout(hdr)

        # Center Visualizer Card
        vis_card = QFrame()
        vis_card.setObjectName("cyber_card")
        vis_layout = QVBoxLayout(vis_card)
        vis_layout.setContentsMargins(24, 20, 24, 20)
        vis_layout.setSpacing(14)
        vis_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.voice_page_avatar = CyberRobotAvatar(accent=self.accent_color, size=110)
        self.voice_page_avatar.clicked.connect(self.voice_page_avatar.trigger_pulse)
        vis_layout.addWidget(self.voice_page_avatar, 0, Qt.AlignmentFlag.AlignCenter)

        self.voice_page_waveform = SymmetricalAudioWaveform(accent=self.accent_color, bars=44, height=72)
        vis_layout.addWidget(self.voice_page_waveform, 0, Qt.AlignmentFlag.AlignCenter)

        self.voice_page_status = QLabel("●  VOICE SYSTEM ACTIVE // DUAL-WING HARMONICS READY")
        self.voice_page_status.setObjectName("status_indicator")
        self.voice_page_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vis_layout.addWidget(self.voice_page_status, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(vis_card)

        # Voice Settings Card
        ctrl_card = QFrame()
        ctrl_card.setObjectName("cyber_card")
        ctrl_layout = QVBoxLayout(ctrl_card)
        ctrl_layout.setContentsMargins(20, 16, 20, 16)
        ctrl_layout.setSpacing(12)

        ctrl_title = QLabel("NEURAL VOICE SYNTHESIS PRESETS")
        ctrl_title.setObjectName("section_header")
        ctrl_layout.addWidget(ctrl_title)

        form_row = QHBoxLayout()
        form_row.setSpacing(16)

        # Voice Profile
        col1 = QVBoxLayout()
        col1.addWidget(QLabel("VOICE IDENTITY:"))
        self.v_profile_combo = QComboBox()
        self.v_profile_combo.addItem("Ryan Neural (British - Stark Jarvis)", "en-GB-RyanNeural")
        self.v_profile_combo.addItem("Christopher Neural (Deep American - Ultron)", "en-US-ChristopherNeural")
        self.v_profile_combo.addItem("Sonia Neural (British English Female)", "en-GB-SoniaNeural")
        self.v_profile_combo.addItem("Guy Neural (American English Male)", "en-US-GuyNeural")
        self.v_profile_combo.addItem("Jenny Neural (American English Female)", "en-US-JennyNeural")
        for idx in range(self.v_profile_combo.count()):
            if self.v_profile_combo.itemData(idx) == self.tts.voice:
                self.v_profile_combo.setCurrentIndex(idx)
                break
        self.v_profile_combo.currentIndexChanged.connect(self._on_voice_combo_changed)
        col1.addWidget(self.v_profile_combo)
        form_row.addLayout(col1)

        # Speech Rate
        col2 = QVBoxLayout()
        col2.addWidget(QLabel("SPEECH SPEED / RATE:"))
        self.v_rate_combo = QComboBox()
        self.v_rate_combo.addItem("0.85x (Deliberate & Measured)", "-15%")
        self.v_rate_combo.addItem("1.00x (Standard Cinematic)", "+0%")
        self.v_rate_combo.addItem("1.15x (Brisk Tactical)", "+15%")
        self.v_rate_combo.addItem("1.30x (Rapid Briefing)", "+30%")
        self.v_rate_combo.setCurrentIndex(1)
        self.v_rate_combo.currentIndexChanged.connect(self._on_voice_rate_changed)
        col2.addWidget(self.v_rate_combo)
        form_row.addLayout(col2)

        # Pitch
        col3 = QVBoxLayout()
        col3.addWidget(QLabel("VOCAL PITCH:"))
        self.v_pitch_combo = QComboBox()
        self.v_pitch_combo.addItem("Deep Resonance (-6Hz)", "-6Hz")
        self.v_pitch_combo.addItem("Natural Tone (+0Hz)", "+0Hz")
        self.v_pitch_combo.addItem("Elevated Pitch (+4Hz)", "+4Hz")
        self.v_pitch_combo.setCurrentIndex(1)
        self.v_pitch_combo.currentIndexChanged.connect(self._on_voice_pitch_changed)
        col3.addWidget(self.v_pitch_combo)
        form_row.addLayout(col3)

        ctrl_layout.addLayout(form_row)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        test_btn = QPushButton("🔊  TEST VOCAL SYNTHESIS")
        test_btn.setObjectName("primary_cta")
        test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        test_btn.clicked.connect(self._test_voice_synthesis)

        stop_btn = QPushButton("🛑  MUTE / STOP SPEECH")
        stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        stop_btn.clicked.connect(self.stop_speaking)

        btn_row.addWidget(test_btn)
        btn_row.addWidget(stop_btn)
        btn_row.addStretch()
        ctrl_layout.addLayout(btn_row)

        layout.addWidget(ctrl_card)

        # Commands Reference Card
        cmd_card = QFrame()
        cmd_card.setObjectName("cyber_card")
        cmd_layout = QVBoxLayout(cmd_card)
        cmd_layout.setContentsMargins(18, 14, 18, 14)
        cmd_layout.setSpacing(6)

        ref_lbl = QLabel("SUPPORTED VOCAL & ACTION PATTERNS")
        ref_lbl.setObjectName("section_header")
        cmd_layout.addWidget(ref_lbl)

        tips = [
            "▸ 'Open YouTube' or 'Play music on YouTube' — Launches browser streaming instantly.",
            "▸ 'Search Google for quantum mechanics' — Opens immediate web search queries.",
            "▸ 'Msg Priyanshu on WhatsApp that I am on my way' — Full end-to-end WhatsApp Web messaging.",
            "▸ 'What's the weather in Tokyo?' — Live meteorological telemetry retrieval.",
            "▸ 'Look at my screen and help me fix this' — Captures desktop viewport for Vision AI inspection.",
            "▸ 'Set a reminder to drink water at 5pm' — Autonomous background scheduler and audio chime.",
        ]
        for tip in tips:
            lbl = QLabel(tip)
            lbl.setStyleSheet("color: #8da4be; font-size: 11px;")
            cmd_layout.addWidget(lbl)

        layout.addWidget(cmd_card)
        layout.addStretch()
        return page

    def _on_voice_combo_changed(self):
        voice_id = self.v_profile_combo.currentData()
        pitch = self.v_pitch_combo.currentData()
        self.tts.set_voice_profile(voice_id, pitch)
        hud_sfx.play("click")

    def _on_voice_rate_changed(self):
        rate = self.v_rate_combo.currentData()
        self.tts.set_rate(rate)
        hud_sfx.play("click")

    def _on_voice_pitch_changed(self):
        voice_id = self.v_profile_combo.currentData()
        pitch = self.v_pitch_combo.currentData()
        self.tts.set_voice_profile(voice_id, pitch)
        hud_sfx.play("click")

    def _test_voice_synthesis(self):
        who = "Ultron" if get_personality() == "ULTRON" else "J.A.R.V.I.S"
        hud_sfx.play("pulse")
        self.tts.speak(f"Greetings. I am {who}. All vocal synthesis systems and audio harmonics are operating at maximum fidelity.")

    def _create_about_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        card = QFrame()
        card.setObjectName("cyber_card")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(28, 24, 28, 24)
        c_layout.setSpacing(16)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        about_avatar = CyberRobotAvatar(accent=self.accent_color, size=116)
        about_avatar.clicked.connect(about_avatar.trigger_pulse)
        c_layout.addWidget(about_avatar, 0, Qt.AlignmentFlag.AlignCenter)

        title = QLabel("J.A.R.V.I.S // MARK IX NEURAL SYSTEM")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet("color: #ffffff; letter-spacing: 1.5px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c_layout.addWidget(title)

        sub = QLabel("Autonomous Tactical AI Interface & Personal Operating System")
        sub.setFont(QFont("Segoe UI", 11))
        sub.setStyleSheet("color: #00d2ff; font-weight: 500;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c_layout.addWidget(sub)

        desc = QLabel(
            "Just A Rather Very Intelligent System (J.A.R.V.I.S) is a state-of-the-art AI assistant engineered "
            "with multi-engine LLM routing (Google Gemini 2.5/2.0, Groq LLaMA 3.3, local Ollama), "
            "low-latency Edge neural speech synthesis with streaming prefetch, automated browser workflows "
            "with Selenium Chrome & PyAutoGUI, local vector RAG, encrypted cyber defense vault, "
            "and an animated hardware-accelerated Cyber HUD interface inspired by Iron Man."
        )
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setStyleSheet("color: #9ab4cf; font-size: 13px; line-height: 1.6; max-width: 780px;")
        c_layout.addWidget(desc)

        # Spec Grid
        grid_frame = QFrame()
        grid_frame.setStyleSheet("background: rgba(4, 10, 20, 0.6); border: 1px solid rgba(0, 210, 255, 0.15); border-radius: 10px; padding: 12px;")
        g_layout = QVBoxLayout(grid_frame)
        g_layout.setSpacing(8)

        specs = [
            ("Core Architecture", "Python 3.10+ / PySide6 / Hardware Accelerated Cyber HUD"),
            ("AI Engines", "Google Gemini 2.5 Flash / Groq LLaMA 3.3 / Local Ollama (Auto-Fallback)"),
            ("Vocal Synthesis", "Edge-TTS Neural Voice with Symmetrical Waveform Processing"),
            ("OS Automation", "PyAutoGUI Mouse/Keyboard & Selenium Chrome WhatsApp / Web Automation"),
            ("Hotkeys", "Ctrl+Shift+Space (Spotlight)  |  Enter (Transmit)  |  Esc (Dismiss)"),
            ("Build Version", "Mark IX — Cybernetic HUD Edition (Build 9.4.0)"),
        ]
        for label, val in specs:
            row = QHBoxLayout()
            lbl_l = QLabel(f"●  {label}:")
            lbl_l.setStyleSheet("color: #00d2ff; font-weight: 600; font-size: 12px;")
            lbl_r = QLabel(val)
            lbl_r.setStyleSheet("color: #ffffff; font-size: 12px;")
            row.addWidget(lbl_l)
            row.addWidget(lbl_r)
            row.addStretch()
            g_layout.addLayout(row)

        c_layout.addWidget(grid_frame)
        layout.addWidget(card)
        layout.addStretch()
        return page

    def _toggle_maximize_window(self):
        if self.isMaximized():
            self.showNormal()
            self.max_btn.setText("🗖")
        else:
            self.showMaximized()
            self.max_btn.setText("🗗")

    def _handle_home_command(self, text: str):
        text = text.strip()
        if not text:
            return
        # Switch to chat and transmit
        self.switch_page("chat")
        self.message_input.setText(text)
        self.send_message()

    def _toggle_voice_listening(self):
        if self.tts.is_speaking:
            self.stop_speaking()
            return
        hud_sfx.play("pulse")
        if hasattr(self, "home_page"):
            self.home_page.mic_button.set_state("listening")
        self.tts.speak("Awaiting your directive, Sir. What can I do for you?")

    def _execute_quick_action(self, action_name: str):
        hud_sfx.play("click")
        if action_name == "open_youtube":
            try:
                open_website("https://www.youtube.com")
                self.tts.speak("Opening YouTube for you, Sir.")
            except Exception as e:
                self.add_message("ERROR", f"Failed to open YouTube: {e}")
        elif action_name == "search_google":
            try:
                open_website("https://www.google.com")
                self.tts.speak("Opening Google Search.")
            except Exception as e:
                self.add_message("ERROR", f"Failed to open Google: {e}")
        elif action_name == "play_music":
            try:
                open_website("https://music.youtube.com")
                self.tts.speak("Opening YouTube Music.")
            except Exception as e:
                self.add_message("ERROR", f"Failed to open YouTube Music: {e}")
        elif action_name == "check_time":
            now_str = datetime.now().strftime("%I:%M %p")
            self.tts.speak(f"The current time is {now_str}, Sir.")
            self.add_message("SYSTEM", f"Current Time: **{now_str}**", subtitle="TIME CHECK")
        elif action_name == "shutdown_pc":
            reply = QMessageBox.question(
                self,
                "Confirm System Shutdown",
                "Are you sure you want to shut down your computer?\nEnsure all your work is saved.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.tts.speak("Initiating system shutdown. Goodbye, Sir.")
                try:
                    import os
                    os.system("shutdown /s /t 15")
                    self.add_message("SYSTEM", "System shutdown initiated (15 second timer). Run `shutdown /a` to abort.", subtitle="SHUTDOWN")
                except Exception as e:
                    self.add_message("ERROR", f"Shutdown command failed: {e}")

    # =========================================
    # CHAT PAGE + RIGHT TELEMETRY HUD RAIL
    # =========================================

    def create_chat_page(self):
        page = QWidget()
        outer = QHBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(12)

        # ---- Left/Center: Neural Chat Console ----
        console = QWidget()
        layout = QVBoxLayout(console)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Control Bar
        header = QHBoxLayout()
        header.setSpacing(8)

        title = QLabel("NEURAL COMMAND CONSOLE")
        title.setObjectName("page_title")
        header.addWidget(title)
        header.addStretch()

        header.addWidget(QLabel("PERSONA:"))
        self.personality_selector = QComboBox()
        for key in PERSONALITIES:
            self.personality_selector.addItem(key, key)
        self.personality_selector.setCurrentText(get_personality())
        self.personality_selector.currentTextChanged.connect(self._change_personality_quick)
        header.addWidget(self.personality_selector)

        header.addWidget(QLabel("ENGINE:"))
        self.provider_selector = QComboBox()
        self.provider_selector.addItems(["AUTO", "GEMINI", "GROQ", "OLLAMA"])
        self.provider_selector.setCurrentText(get_provider_mode().upper())
        self.provider_selector.currentTextChanged.connect(self.change_provider)
        header.addWidget(self.provider_selector)

        self.agent_toggle_btn = QPushButton("AGENT: OFF")
        self.agent_toggle_btn.setCheckable(True)
        self.agent_toggle_btn.setToolTip("Toggle Autonomous Multi-Step Tool-Chaining Agent Mode")
        self.agent_toggle_btn.toggled.connect(self._toggle_agent_mode)
        header.addWidget(self.agent_toggle_btn)

        self.summarize_button = QPushButton("SUMMARIZE")
        self.summarize_button.clicked.connect(self.summarize_current_chat)
        header.addWidget(self.summarize_button)

        self.export_chat_button = QPushButton("EXPORT")
        self.export_chat_button.setToolTip("Export current conversation to Markdown or PDF")
        self.export_chat_button.clicked.connect(self._export_current_chat)
        header.addWidget(self.export_chat_button)

        self.new_chat_button = QPushButton("+ NEW")
        self.new_chat_button.clicked.connect(self.new_conversation)
        header.addWidget(self.new_chat_button)

        # Status & Attachment Banner
        sub_bar = QHBoxLayout()
        self.provider_status = QLabel("NEURAL ROUTER: AUTO FALLBACK ACTIVE  |  TYPE /help FOR COMMANDS")
        self.provider_status.setObjectName("provider_status")

        self.attachment_label = QLabel("")
        self.attachment_label.setObjectName("subtitle")

        self.clear_attach_btn = QPushButton("✕")
        self.clear_attach_btn.setFixedWidth(28)
        self.clear_attach_btn.setVisible(False)
        self.clear_attach_btn.clicked.connect(self._clear_attachments)

        sub_bar.addWidget(self.provider_status, 1)
        sub_bar.addWidget(self.attachment_label)
        sub_bar.addWidget(self.clear_attach_btn)

        # Chat Stream Display (intercept clicked links so they also open in Chrome)
        self.chat_display = QTextBrowser()
        self.chat_display.setOpenExternalLinks(False)
        self.chat_display.anchorClicked.connect(self._open_chat_link_in_chrome)
        self.chat_display.setPlaceholderText(
            "Awaiting directive, Sir... Ask anything, attach an image or PDF, or click a quick-command chip below."
        )

        # Quick Action HUD Chips
        chips_row = QHBoxLayout()
        chips_row.setSpacing(6)
        quick_chips = [
            ("🤖 Agent Goal", lambda: self._prefill_input("/agent ")),
            ("👁️ Screen Vision", self._capture_screen_for_vision),
            ("📚 Folder KB", lambda: self._prefill_input("/kb ")),
            ("⚡ Briefing", self._chip_daily_briefing),
            ("🌐 Web Search", lambda: self._prefill_input("/search ")),
            ("📋 Clipboard", self._open_clipboard_tab),
            ("🔍 Spotlight", self._summon_spotlight),
            ("❓ Commands", lambda: self._run_chip_command("/help")),
        ]
        for label, handler in quick_chips:
            chip = QPushButton(label)
            chip.setObjectName("chip_button")
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            chip.clicked.connect(handler)
            chips_row.addWidget(chip)
        chips_row.addStretch()

        # Glowing Command Input Capsule
        capsule = QFrame()
        capsule.setObjectName("input_capsule")
        cap_layout = QHBoxLayout(capsule)
        cap_layout.setContentsMargins(8, 6, 8, 6)
        cap_layout.setSpacing(6)

        self.attach_img_btn = QPushButton("IMG")
        self.attach_img_btn.setToolTip("Attach image for Vision AI (7.1)")
        self.attach_img_btn.clicked.connect(self._attach_image)

        self.attach_doc_btn = QPushButton("PDF/DOC")
        self.attach_doc_btn.setToolTip("Attach PDF, DOCX, or text document (7.2 - 7.3)")
        self.attach_doc_btn.clicked.connect(self._attach_document)

        self.screen_vision_btn = QPushButton("SCREEN")
        self.screen_vision_btn.setToolTip("Look at My Screen — capture screen with permission & analyze with Vision AI")
        self.screen_vision_btn.clicked.connect(self._capture_screen_for_vision)

        self.message_input = QLineEdit()
        self.message_input.setObjectName("command_input")
        self.message_input.setPlaceholderText("Enter directive, query, or /command...")
        self.message_input.returnPressed.connect(self.send_message)

        self.send_button = QPushButton("TRANSMIT")
        self.send_button.setObjectName("primary_cta")
        self.send_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_button.clicked.connect(self.send_message)

        self.stop_speaking_button = QPushButton("MUTE")
        self.stop_speaking_button.setToolTip("Stop JARVIS voice playback")
        self.stop_speaking_button.clicked.connect(self.stop_speaking)

        cap_layout.addWidget(self.attach_img_btn)
        cap_layout.addWidget(self.attach_doc_btn)
        cap_layout.addWidget(self.screen_vision_btn)
        cap_layout.addWidget(self.message_input, 1)
        cap_layout.addWidget(self.send_button)
        cap_layout.addWidget(self.stop_speaking_button)

        layout.addLayout(header)
        layout.addLayout(sub_bar)
        layout.addWidget(self.chat_display, 1)
        layout.addLayout(chips_row)
        layout.addWidget(capsule)

        # ---- Right: Holographic Telemetry Rail ----
        self.telemetry_rail = QFrame()
        self.telemetry_rail.setObjectName("hud_panel")
        self.telemetry_rail.setFixedWidth(236)
        rl = QVBoxLayout(self.telemetry_rail)
        rl.setContentsMargins(10, 10, 10, 10)
        rl.setSpacing(8)

        rail_title = QLabel("LIVE HUD TELEMETRY")
        rail_title.setObjectName("section_header")
        rail_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rl.addWidget(rail_title)

        mini_gauges = QHBoxLayout()
        mini_gauges.setSpacing(4)
        self.rail_cpu_gauge = ArcGaugeWidget("CPU", accent=self.accent_color, size=94)
        self.rail_ram_gauge = ArcGaugeWidget("RAM", accent=self.accent_color, size=94)
        mini_gauges.addWidget(self.rail_cpu_gauge)
        mini_gauges.addWidget(self.rail_ram_gauge)
        rl.addLayout(mini_gauges)

        self.rail_graph = TelemetryGraphWidget(accent=self.accent_color, max_points=40)
        self.rail_graph.setFixedHeight(92)
        rl.addWidget(self.rail_graph)

        mission_lbl = QLabel("MISSION STATUS")
        mission_lbl.setObjectName("section_header")
        rl.addWidget(mission_lbl)

        self.rail_stats_label = QLabel("Loading telemetry...")
        self.rail_stats_label.setWordWrap(True)
        self.rail_stats_label.setStyleSheet("font-family: Consolas, monospace; font-size: 11px; line-height: 1.5;")
        rl.addWidget(self.rail_stats_label)

        wx_lbl = QLabel("LOCAL ATMOSPHERE")
        wx_lbl.setObjectName("section_header")
        rl.addWidget(wx_lbl)

        self.rail_weather_label = QLabel("Fetching weather...")
        self.rail_weather_label.setWordWrap(True)
        self.rail_weather_label.setStyleSheet("font-family: Consolas, monospace; font-size: 10.5px; color: #94a3b8;")
        rl.addWidget(self.rail_weather_label)

        rl.addStretch()

        quick_dash_btn = QPushButton("OPEN TELEMETRY")
        quick_dash_btn.clicked.connect(lambda: self.switch_page("dashboard"))
        quick_prod_btn = QPushButton("OPEN PRODUCTIVITY")
        quick_prod_btn.clicked.connect(lambda: self.switch_page("productivity"))
        rl.addWidget(quick_dash_btn)
        rl.addWidget(quick_prod_btn)

        outer.addWidget(console, 1)
        outer.addWidget(self.telemetry_rail)

        return page

    def _toggle_telemetry_rail(self):
        self.telemetry_rail.setVisible(not self.telemetry_rail.isVisible())

    def _prefill_input(self, prefix: str):
        self.message_input.setText(prefix)
        self.message_input.setFocus()

    def _run_chip_command(self, cmd: str):
        self._try_handle_slash_command(cmd)

    def _chip_daily_briefing(self):
        self.add_message("SYSTEM", build_daily_summary_text())

    def _chip_net_info(self):
        self.add_message("SYSTEM", get_local_network_info())

    def _open_clipboard_tab(self):
        self.switch_page("automation")
        self.automation_page.tabs.setCurrentIndex(3)

    def _open_chat_link_in_chrome(self, qurl):
        url = qurl.toString()
        if url.startswith(("http://", "https://")):
            try:
                open_website(url)
            except Exception as err:
                self.add_message("ERROR", str(err))

    def _toggle_agent_mode(self, checked: bool):
        self.agent_mode_enabled = bool(checked)
        self.agent_toggle_btn.setText("AGENT: ON" if checked else "AGENT: OFF")
        hud_sfx.play("click")
        if checked:
            self.provider_status.setText("AUTONOMOUS AGENT MODE ACTIVE — MULTI-STEP TOOL CHAINING ENABLED")
        else:
            self.provider_status.setText("NEURAL ROUTER: STANDARD STREAMING MODE")

    def _export_current_chat(self):
        md_text = build_session_markdown()
        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Current Conversation",
            "jarvis_conversation.pdf",
            "PDF Document (*.pdf);;Markdown File (*.md)",
        )
        if not path:
            return
        try:
            if path.lower().endswith(".pdf") or "PDF" in selected_filter:
                if not path.lower().endswith(".pdf"):
                    path += ".pdf"
                export_text_to_pdf(md_text, path, title="J.A.R.V.I.S Conversation Export")
            else:
                export_markdown(md_text, path)
            self.add_message("SYSTEM", f"Conversation exported successfully to `{path}`.")
        except Exception as err:
            QMessageBox.warning(self, "Export Error", str(err))

    def _capture_screen_for_vision(self, custom_prompt: str = ""):
        if self.worker is not None:
            return
        ans = QMessageBox.question(
            self,
            "Screen Vision Permission",
            "Allow J.A.R.V.I.S to briefly minimize, capture your screen, and analyze it with Vision AI?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        self.showMinimized()
        QTimer.singleShot(320, lambda: self._finish_screen_vision_capture(custom_prompt))

    def _finish_screen_vision_capture(self, custom_prompt: str = ""):
        try:
            shot_path = capture_screenshot_qapp(QApplication.instance())
        except Exception as err:
            self.showNormal()
            self.add_message("ERROR", f"Screen Vision capture failed: {err}")
            return

        self.showNormal()
        self.raise_()
        self.activateWindow()

        prompt = (custom_prompt or "").strip() or (
            "Look at my screen carefully. Summarize what is currently open, spot any visible errors "
            "or issues, and suggest how you can help."
        )
        worker = JarvisWorker(
            message=prompt,
            task="chat",
            image_path=str(shot_path),
        )
        self._start_worker_stream(
            display_user_msg=f"[Screen Vision: {shot_path.name}]\n{prompt}",
            worker=worker,
        )

    # =========================================
    # SYSTEM TRAY, SPOTLIGHT & GLOBAL HOTKEY
    # =========================================

    def _build_tray_icon(self) -> QIcon:
        pm = QPixmap(64, 64)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QColor(self.accent_color)
        p.setBrush(QColor("#080b10"))
        p.setPen(QPen(c, 5))
        p.drawEllipse(6, 6, 52, 52)
        p.setBrush(c)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(22, 22, 20, 20)
        p.end()
        return QIcon(pm)

    def _setup_tray_and_spotlight(self):
        self.spotlight = SpotlightDialog(accent=self.accent_color, parent=self)
        self.spotlight.command_submitted.connect(self._handle_spotlight_command)

        self._hotkey_filter = GlobalHotkeyFilter(self._summon_spotlight)
        app_inst = QApplication.instance()
        if app_inst is not None:
            app_inst.installNativeEventFilter(self._hotkey_filter)
            self._hotkey_filter.register()

        self.tray_icon = None
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = QSystemTrayIcon(self._build_tray_icon(), self)
            self.tray_icon.setToolTip("J.A.R.V.I.S AI Assistant (Ctrl+Shift+Space for Spotlight)")
            menu = QMenu()
            act_show = QAction("Open J.A.R.V.I.S", self)
            act_show.triggered.connect(self._restore_from_tray)
            act_spot = QAction("Quick Spotlight (Ctrl+Shift+Space)", self)
            act_spot.triggered.connect(self._summon_spotlight)
            act_mute = QAction("Mute Voice", self)
            act_mute.triggered.connect(self.stop_speaking)
            act_quit = QAction("Quit", self)
            act_quit.triggered.connect(self.close)
            menu.addAction(act_show)
            menu.addAction(act_spot)
            menu.addAction(act_mute)
            menu.addSeparator()
            menu.addAction(act_quit)
            self.tray_icon.setContextMenu(menu)
            self.tray_icon.activated.connect(
                lambda reason: self._restore_from_tray()
                if reason == QSystemTrayIcon.ActivationReason.DoubleClick
                else None
            )
            self.tray_icon.show()

    def _restore_from_tray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _summon_spotlight(self):
        hud_sfx.play("pulse")
        self.spotlight.apply_accent(self.accent_color)
        self.spotlight.summon()

    def _handle_spotlight_command(self, text: str):
        self._restore_from_tray()
        self.switch_page("chat")
        self.message_input.setText(text)
        self.send_message()

    def refresh_weather(self):
        city = get_setting("weather_city", "") or ""

        def _fetch():
            try:
                from tools.weather import fetch_weather

                summary = fetch_weather(city)["summary"]
                self.weather_updated.emit(summary)
            except Exception:
                self.weather_updated.emit("Weather offline")

        threading.Thread(target=_fetch, daemon=True, name="Jarvis-Weather").start()

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
            parts.append(f"IMG: {Path(self.attached_image_path).name}")
        if self.attached_doc_meta:
            parts.append(f"DOC: {self.attached_doc_meta['name']} ({self.attached_doc_meta['word_count']}w)")
        self.attachment_label.setText("  |  ".join(parts))
        self.clear_attach_btn.setVisible(bool(parts))

    # =========================================
    # PROVIDER & PERSONALITY CONTROLS
    # =========================================

    def change_provider(self, selected_provider):
        provider = selected_provider.lower().strip()
        try:
            set_provider_mode(provider)
            desc = "NEURAL ROUTER: AUTO FALLBACK ACTIVE" if provider == "auto" else f"ENGINE LOCKED: {selected_provider}"
            self.provider_status.setText(desc)
            self._update_top_engine_badge()
        except Exception as error:
            QMessageBox.warning(self, "Provider Error", str(error))

    def _change_personality_quick(self, selected_key):
        if selected_key in PERSONALITIES:
            set_personality(selected_key)
            self.provider_status.setText(f"PERSONA MATRIX: {PERSONALITIES[selected_key]['label'].upper()}")
            self._update_top_engine_badge()
            self._sync_identity_branding()
            idx = self.settings_page.personality_combo.findData(selected_key)
            if idx >= 0:
                self.settings_page.personality_combo.blockSignals(True)
                self.settings_page.personality_combo.setCurrentIndex(idx)
                self.settings_page.personality_combo.blockSignals(False)

    def _sync_identity_branding(self):
        if get_personality() == "ULTRON":
            self.logo_label.setText("U.L.T.R.O.N")
            self.hud_brand_label.setText("●  ULTRON PRIME // STRATEGIC MATRIX")
            self.setWindowTitle("U.L.T.R.O.N // STRATEGIC NEURAL CORE")
        else:
            self.logo_label.setText("J.A.R.V.I.S")
            self.hud_brand_label.setText("●  STARK INDUSTRIES // J.A.R.V.I.S CORE")
            self.setWindowTitle("J.A.R.V.I.S // STARK NEURAL HUD")

    def _sync_brain_controls(self):
        p = get_personality()
        self.personality_selector.blockSignals(True)
        self.personality_selector.setCurrentText(p)
        self.personality_selector.blockSignals(False)
        self._update_top_engine_badge()
        self._sync_identity_branding()

    def _update_top_engine_badge(self):
        self.top_engine_metric.setText(f"{get_provider_mode().upper()} • {get_personality()}")

    # =========================================
    # AI PROVIDER HEALTH PANEL
    # =========================================

    def create_provider_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)

        top = QHBoxLayout()
        title = QLabel("AI ENGINE DIAGNOSTICS")
        title.setObjectName("page_title")
        self.check_all_button = QPushButton("SCAN ALL ENGINES")
        self.check_all_button.clicked.connect(self.check_all_providers)
        top.addWidget(title)
        top.addStretch()
        top.addWidget(self.check_all_button)
        layout.addLayout(top)

        grid = QGridLayout()
        grid.setSpacing(10)

        providers = [
            ("gemini", "GEMINI CORE", GEMINI_MODEL),
            ("groq", "GROQ TURBO", GROQ_MODEL),
            ("ollama", "OLLAMA LOCAL", OLLAMA_MODEL),
        ]

        for index, (provider, name, model) in enumerate(providers):
            card = QFrame()
            card.setObjectName("provider_card")
            card_layout = QVBoxLayout(card)

            name_label = QLabel(name)
            name_label.setStyleSheet("font-family: Consolas, monospace; font-size: 15px; font-weight: bold;")
            model_label = QLabel(f"MODEL: {model}")
            model_label.setObjectName("subtitle")
            status_label = QLabel("STANDBY")
            status_label.setStyleSheet("color: #ffb300; font-family: Consolas, monospace; font-weight: bold;")
            detail_label = QLabel("Awaiting link verification...")
            detail_label.setWordWrap(True)

            check_button = QPushButton("VERIFY LINK")
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

        self.provider_status_labels[provider].setText("SCANNING...")
        self.provider_status_labels[provider].setStyleSheet("color: #ffb300; font-family: Consolas, monospace; font-weight: bold;")
        self.provider_detail_labels[provider].setText("Testing neural link...")
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
            self.provider_status_labels[provider].setText("ONLINE")
            self.provider_status_labels[provider].setStyleSheet("color: #00f59b; font-family: Consolas, monospace; font-weight: bold;")
        else:
            self.provider_status_labels[provider].setText("OFFLINE")
            self.provider_status_labels[provider].setStyleSheet("color: #ff4775; font-family: Consolas, monospace; font-weight: bold;")
        self.provider_detail_labels[provider].setText(str(details))

    def show_health_error(self, provider, error):
        if provider not in self.provider_status_labels:
            return
        self.provider_status_labels[provider].setText("FAULT")
        self.provider_status_labels[provider].setStyleSheet("color: #ff4775; font-family: Consolas, monospace; font-weight: bold;")
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
    # SLASH COMMANDS & CUSTOM COMMANDS
    # =========================================

    def _try_handle_slash_command(self, raw_message: str) -> bool:
        if not raw_message.startswith("/"):
            return False

        parts = raw_message.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd == "/help":
            customs = get_custom_commands()
            custom_lines = "\n".join(f"- `/{c[1]}` — {c[4] or c[3]}" for c in customs) or "- (none yet — add in `05 // AUTOMATION`)"
            tools = ", ".join(t["name"] for t in plugin_manager.list_tools()) or "(none)"
            help_text = (
                "### Built-in J.A.R.V.I.S Directives\n"
                "- `/agent <goal>` — Autonomous multi-step Agent Mode (chains tools)\n"
                "- `/schedule <YYYY-MM-DD HH:MM> <action> | <payload>` — Schedule automated custom task (or `/schedule list`)\n"
                "- `/kb <question>` — Ask your locally indexed folder (RAG)\n"
                "- `/screen [question]` — Look at My Screen with Vision AI (with permission)\n"
                "- `/search <query>` — Live web search + AI answer\n"
                "- `/yt <youtube_url>` — Summarize a YouTube video\n"
                "- `/remember <fact>` — Save fact to Long-Term Memory\n"
                "- `/summarize` — Summarize this conversation\n"
                "- `/whatsapp <contact> | <message>` — Send message via WhatsApp Web in Chrome\n"
                "- `/open <app or url>` — Open desktop app or website\n"
                "- `/google <query>` — Search Google in browser\n"
                "- `/youtube <query>` — Search YouTube in browser\n"
                "- `/vol <up|down|mute|0-100>` — Control system volume\n"
                "- `/screenshot` — Capture screenshot (with permission)\n"
                "- `/run <command>` — Run terminal command (with approval)\n"
                "- `/todo <task>` — Quick-add to-do task\n"
                "- `/note <text>` — Quick-capture a note\n"
                "- `/remind <YYYY-MM-DD HH:MM> <msg>` — Set reminder alarm\n"
                f"- `/plugin <name> [args]` — Run plugin tool (`{tools}`)\n\n"
                f"### Your Custom Commands\n{custom_lines}"
            )
            self.add_message("SYSTEM", help_text)
            return True

        if cmd == "/agent":
            if not arg:
                self.add_message("SYSTEM", "Usage: `/agent <multi-step goal>`")
                return True
            self._start_worker_stream(
                display_user_msg=f"/agent {arg}",
                worker=JarvisWorker(message=arg, task="agent_mode"),
            )
            return True

        if cmd == "/kb":
            if not arg:
                self.add_message("SYSTEM", "Usage: `/kb <question about your indexed folder>`")
                return True
            self._start_worker_stream(
                display_user_msg=f"/kb {arg}",
                worker=JarvisWorker(message=arg, task="rag_ask", extra={"stream_to_chat": True}),
            )
            return True

        if cmd == "/screen":
            self._capture_screen_for_vision(arg)
            return True

        if cmd == "/schedule":
            if not arg or arg.lower() == "list":
                tasks = list_scheduled_tasks()
                if not tasks:
                    self.add_message(
                        "SYSTEM",
                        "No scheduled tasks yet.\nUsage: `/schedule YYYY-MM-DD HH:MM ai_prompt | Give me an evening briefing` "
                        "(or manage all options in `02 // PRODUCTIVITY` → **Scheduled Tasks**).",
                    )
                    return True
                lines = ["### Scheduled Custom Tasks"]
                for t in tasks:
                    st = "ON" if t["enabled"] else "OFF"
                    lines.append(
                        f"- **[{st}] {t['name']}** (`{t['action_type']}`, {t['schedule_type']}) — Next: `{t['next_run_at']}` | Last: `{t['last_status']}`"
                    )
                self.add_message("SYSTEM", "\n".join(lines))
                return True

            m = re.match(r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})\s+([a-z_]+)\s*\|\s*(.+)$", arg, flags=re.IGNORECASE)
            if not m:
                allowed = ", ".join(ACTION_TYPES.keys())
                self.add_message(
                    "SYSTEM",
                    "Usage: `/schedule YYYY-MM-DD HH:MM <action_type> | <payload>`\n"
                    f"Action types: `{allowed}`\n"
                    "For recurring schedules (`daily`, `weekly`, `interval`) open `02 // PRODUCTIVITY` → **Scheduled Tasks**.",
                )
                return True

            run_at, atype, payload = m.group(1), m.group(2).lower(), m.group(3).strip()
            if atype == "terminal_command":
                warn = "\n\nWARNING: Potentially destructive pattern!" if is_potentially_dangerous_command(payload) else ""
                ans = QMessageBox.question(
                    self,
                    "Approve Scheduled Command",
                    f"Approve scheduling this terminal command at {run_at}?\n\n{payload}{warn}",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if ans != QMessageBox.StandardButton.Yes:
                    self.add_message("SYSTEM", "Scheduled command cancelled.")
                    return True
            try:
                tid = save_scheduled_task(
                    name=f"{atype}: {payload[:36]}",
                    action_type=atype,
                    payload=payload,
                    next_run_at=run_at,
                    schedule_type="once",
                )
                self.productivity_page.refresh_scheduled_tasks()
                self.add_message("SYSTEM", f"Scheduled custom task **#{tid}** (`{atype}`) for `{run_at}`.")
            except Exception as err:
                self.add_message("ERROR", str(err))
            return True

        if cmd == "/remember":
            if not arg:
                self.add_message("SYSTEM", "Usage: `/remember <fact to remember>`")
                return True
            add_long_term_memory(arg, category="explicit")
            self.add_message("SYSTEM", f"Saved to Long-Term Memory: **{arg}**")
            return True

        if cmd == "/summarize":
            self.summarize_current_chat()
            return True

        if cmd == "/whatsapp":
            if not arg or arg.lower() in ("help", "?"):
                help_text = (
                    "### WhatsApp Web Automation (Google Chrome)\n"
                    "- `/whatsapp <contact_name_or_number> | <message>` — Send message via WhatsApp Web in Chrome\n"
                    "- `/whatsapp call <contact_name_or_number>` — Call contact (Voice Call in Chrome)\n"
                    "- `/whatsapp video <contact_name_or_number>` — Call contact (Video Call in Chrome)\n"
                    "- `/whatsapp add <name> <phone>` — Save contact to Address Book (e.g. `/whatsapp add Mom +919876543210`)\n"
                    "- `/whatsapp list` — View all saved Address Book contacts\n"
                    "- `/whatsapp remove <name>` — Remove a contact\n"
                    "- `/whatsapp open` — Open WhatsApp Web in Google Chrome\n\n"
                    "**Examples:**\n"
                    "- `/whatsapp Alex | Hey Alex, see you at 6`\n"
                    "- `/whatsapp 919876543210 | Hello from JARVIS`\n"
                    "- `/whatsapp call Mom`"
                )
                self.add_message("SYSTEM", help_text)
                return True

            if arg.lower() in ("open", "web"):
                from tools.whatsapp import open_whatsapp_web
                res = open_whatsapp_web()
                self.add_message("J.A.R.V.I.S", res, subtitle="WHATSAPP")
                self.tts.speak("Opening WhatsApp Web in Google Chrome.")
                return True

            if arg.lower() in ("list", "contacts"):
                from core.memory import list_whatsapp_contacts
                contacts = list_whatsapp_contacts()
                if not contacts:
                    msg = "No saved contacts yet. Add with `/whatsapp add <name> <phone>` (e.g. `/whatsapp add Mom +919876543210`)."
                else:
                    lines = "\n".join(f"- **{c[0]}**: `{c[1]}`" for c in contacts)
                    msg = f"### Saved WhatsApp Address Book\n{lines}"
                self.add_message("SYSTEM", msg)
                return True

            if arg.lower().startswith("add "):
                parts = arg[4:].strip().split(maxsplit=1)
                if len(parts) == 2:
                    from core.memory import save_whatsapp_contact
                    name, phone = parts[0], parts[1]
                    try:
                        save_whatsapp_contact(name, phone)
                        self.add_message("SYSTEM", f"Saved contact **{name}** (`{phone}`) to WhatsApp Address Book.")
                    except Exception as err:
                        self.add_message("ERROR", str(err))
                else:
                    self.add_message("SYSTEM", "Usage: `/whatsapp add <name> <phone>` (e.g. `/whatsapp add Mom +919876543210`)")
                return True

            if arg.lower().startswith("remove ") or arg.lower().startswith("del "):
                name = arg.split(maxsplit=1)[1].strip()
                from core.memory import delete_whatsapp_contact
                delete_whatsapp_contact(name)
                self.add_message("SYSTEM", f"Removed contact **{name}** from WhatsApp Address Book.")
                return True

            if arg.lower().startswith("call "):
                from tools.whatsapp import parse_and_call_whatsapp
                res = parse_and_call_whatsapp(arg[5:])
                self.add_message("J.A.R.V.I.S", res, subtitle="WHATSAPP")
                self.tts.speak(res)
                return True

            if arg.lower().startswith("video "):
                from tools.whatsapp import parse_and_call_whatsapp
                res = parse_and_call_whatsapp(arg)
                self.add_message("J.A.R.V.I.S", res, subtitle="WHATSAPP")
                self.tts.speak(res)
                return True

            from tools.whatsapp import parse_and_send_whatsapp
            try:
                res = parse_and_send_whatsapp(arg)
                self.add_message("J.A.R.V.I.S", res, subtitle="WHATSAPP")
                self.tts.speak("Processing WhatsApp message via Google Chrome.")
            except Exception as err:
                self.add_message("ERROR", str(err))
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
                    msg = "Usage: `/vol up | down | mute | 0-100`"
                self.add_message("SYSTEM", msg)
            except Exception as err:
                self.add_message("ERROR", str(err))
            return True

        if cmd == "/screenshot":
            ans = QMessageBox.question(
                self,
                "Screenshot Permission",
                "Allow J.A.R.V.I.S to capture your screen and save it to data/screenshots/?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if ans == QMessageBox.StandardButton.Yes:
                try:
                    p = capture_screenshot_qapp(QApplication.instance())
                    self.add_message("SYSTEM", f"Screenshot captured: `{p}`")
                except Exception as err:
                    self.add_message("ERROR", str(err))
            else:
                self.add_message("SYSTEM", "Screenshot permission declined.")
            return True

        if cmd == "/run":
            if not arg:
                self.add_message("SYSTEM", "Usage: `/run <command>`")
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
            self._start_worker_stream(
                display_user_msg=f"/run {arg}",
                worker=JarvisWorker(message=arg, task="run_command"),
            )
            return True

        if cmd == "/todo":
            if not arg:
                self.add_message("SYSTEM", "Usage: `/todo <task description>`")
                return True
            add_task(arg)
            self.productivity_page.refresh_all()
            self.add_message("SYSTEM", f"Task logged: **{arg}**")
            return True

        if cmd == "/note":
            if not arg:
                self.add_message("SYSTEM", "Usage: `/note <note text>`")
                return True
            save_note(arg[:40], arg, tags="quick")
            self.productivity_page.refresh_all()
            self.add_message("SYSTEM", "Quick note archived.")
            return True

        if cmd == "/remind":
            m = re.match(r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})\s+(.+)$", arg)
            if not m:
                self.add_message("SYSTEM", "Usage: `/remind YYYY-MM-DD HH:MM <reminder message>`")
                return True
            try:
                add_reminder(m.group(2), m.group(1))
                self.productivity_page.refresh_all()
                self.add_message("SYSTEM", f"Alarm armed for `{m.group(1)}`: **{m.group(2)}**")
            except Exception as err:
                self.add_message("ERROR", str(err))
            return True

        if cmd == "/plugin":
            p_parts = arg.split(maxsplit=1)
            if not p_parts:
                names = ", ".join(t["name"] for t in plugin_manager.list_tools())
                self.add_message("SYSTEM", f"Available plugins: `{names or '(none)'}`")
                return True
            try:
                res = plugin_manager.run_tool(p_parts[0], p_parts[1] if len(p_parts) > 1 else "")
                self.add_message("SYSTEM", f"```text\n[Plugin: {p_parts[0]}]\n{res}\n```")
            except Exception as err:
                self.add_message("ERROR", str(err))
            return True

        if cmd == "/search":
            if not arg:
                self.add_message("SYSTEM", "Usage: `/search <web query>`")
                return True
            self._start_worker_stream(
                display_user_msg=f"/search {arg}",
                worker=JarvisWorker(message=arg, task="web_search", extra={"synthesize": True}),
            )
            return True

        if cmd == "/yt":
            if not arg:
                self.add_message("SYSTEM", "Usage: `/yt <YouTube URL>`")
                return True
            self._start_worker_stream(
                display_user_msg=f"/yt {arg}",
                worker=JarvisWorker(message=arg, task="youtube_summary", extra={"stream_to_chat": True}),
            )
            return True

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

    def _try_handle_natural_automation(self, message: str) -> bool:
        """Handle unambiguous natural-language desktop commands directly like real JARVIS."""
        from tools.computer import (
            APP_ALIASES,
            SITE_SHORTCUTS,
            volume_up,
            volume_down,
            volume_mute_toggle,
            set_volume_percent,
            capture_screenshot_qapp,
        )

        lower = message.lower().strip().rstrip(".!?")

        # 1. "open whatsapp" / "launch whatsapp" / "open whatsapp web"
        if re.match(r"^(?:open|launch)\s+whatsapp(?:\s+web)?$", lower):
            self.add_message("YOU", message)
            from tools.whatsapp import open_whatsapp_web
            res = open_whatsapp_web()
            self.add_message("J.A.R.V.I.S", res, subtitle="WHATSAPP")
            self.tts.speak("Opening WhatsApp Web in Google Chrome.")
            return True

        # Save contact in address book ("save contact Mom as +919876543210")
        m_save = re.match(r"^(?:save|add)\s+contact\s+([a-z0-9 _]+?)\s+(?:as\s+|with\s+number\s+)?([+\d\s\-()]{7,25})$", lower)
        if m_save:
            c_name = m_save.group(1).strip()
            c_phone = m_save.group(2).strip()
            from core.memory import save_whatsapp_contact
            try:
                save_whatsapp_contact(c_name, c_phone)
                self.add_message("YOU", message)
                res = f"Saved contact **{c_name}** (`{c_phone}`) to WhatsApp Address Book."
                self.add_message("J.A.R.V.I.S", res, subtitle="WHATSAPP")
                self.tts.speak(f"Saved contact {c_name} to address book.")
                return True
            except Exception as err:
                self.add_message("ERROR", str(err))
                return True

        # 2. "message <contact> on whatsapp saying <text>" / "send message to <contact> on whatsapp: <text>" / "whatsapp <contact> <text>"
        m_w_msg1 = re.match(
            r"^(?:send\s+(?:a\s+)?(?:whatsapp(?:\s+message|\s+msg)?|message|msg)\s+to\s+|message\s+|msg\s+|tell\s+)"
            r"([a-z0-9 _+]+?)"
            r"(?:\s+on\s+whatsapp)?"
            r"(?:\s*(?::|saying|that|tha|to\s+say)\s*|\s+)"
            r"(.+)$",
            lower,
        )
        m_w_msg2 = re.match(
            r"^whatsapp(?:\s+to)?\s+([a-z0-9 _+]+?)(?:\s*(?::|saying|that|tha)\s*|\s+)(.+)$",
            lower,
        )
        m_w_target = m_w_msg1 or m_w_msg2
        if m_w_target:
            contact_part = m_w_target.group(1).strip()
            msg_part = m_w_target.group(2).strip()
            # Clean possible leading typo artifacts like 'tha ' or 'that '
            msg_part = re.sub(r"^(?:tha|that|saying|to\s+say)\s+", "", msg_part, flags=re.IGNORECASE).strip()
            if contact_part and msg_part and not contact_part.startswith("call"):
                self.add_message("YOU", message)
                from tools.whatsapp import send_whatsapp_message
                res = send_whatsapp_message(contact=contact_part, message=msg_part, auto_send=True)
                self.add_message("J.A.R.V.I.S", res, subtitle="WHATSAPP")
                self.tts.speak(f"Sending message to {contact_part} on WhatsApp Web.")
                return True

        # 3. "call <contact> on whatsapp" / "whatsapp call <contact>" / "video call <contact> on whatsapp"
        m_w_call1 = re.match(r"^(?:voice\s+call|video\s+call|call)\s+(.+?)\s+on\s+whatsapp$", lower)
        m_w_call2 = re.match(r"^whatsapp\s+(?:video\s+)?call\s+(.+)$", lower)
        m_w_call_target = m_w_call1 or m_w_call2
        if m_w_call_target:
            contact_part = m_w_call_target.group(1).strip()
            ctype = "video" if "video" in lower else "voice"
            if contact_part:
                self.add_message("YOU", message)
                from tools.whatsapp import call_whatsapp_contact
                res = call_whatsapp_contact(contact=contact_part, call_type=ctype)
                self.add_message("J.A.R.V.I.S", res, subtitle="WHATSAPP")
                self.tts.speak(f"Opening chat with {contact_part} on WhatsApp Web for {ctype} call.")
                return True

        # 4. System Volume Controls
        if lower in ("volume up", "increase volume", "turn up volume", "raise volume"):
            self.add_message("YOU", message)
            res = volume_up()
            self.add_message("J.A.R.V.I.S", res, subtitle="SYSTEM")
            self.tts.speak(res)
            return True

        if lower in ("volume down", "decrease volume", "lower volume", "turn down volume"):
            self.add_message("YOU", message)
            res = volume_down()
            self.add_message("J.A.R.V.I.S", res, subtitle="SYSTEM")
            self.tts.speak(res)
            return True

        if lower in ("mute", "unmute", "mute volume", "mute sound", "toggle mute"):
            self.add_message("YOU", message)
            res = volume_mute_toggle()
            self.add_message("J.A.R.V.I.S", res, subtitle="SYSTEM")
            self.tts.speak(res)
            return True

        m_vol = re.match(r"^(?:set\s+volume\s+to\s+|volume\s+)(\d{1,3})(?:%|\s*percent)?$", lower)
        if m_vol:
            self.add_message("YOU", message)
            pct = int(m_vol.group(1))
            res = set_volume_percent(pct)
            self.add_message("J.A.R.V.I.S", res, subtitle="SYSTEM")
            self.tts.speak(res)
            return True

        # 5. Screenshot
        if lower in ("take a screenshot", "take screenshot", "capture screen", "screenshot"):
            self.add_message("YOU", message)
            try:
                p = capture_screenshot_qapp(QApplication.instance())
                res = f"Screenshot captured: `{p}`"
                self.add_message("J.A.R.V.I.S", res, subtitle="SYSTEM")
                self.tts.speak("Screenshot captured and saved.")
            except Exception as err:
                self.add_message("ERROR", str(err))
            return True

        # "search google for <query>"
        m_g = re.match(r"^search\s+google\s+(?:for\s+)?(.+)$", lower)
        if m_g:
            self.add_message("YOU", message)
            res = search_google(m_g.group(1).strip())
            self.add_message("J.A.R.V.I.S", res, subtitle="AUTOMATION")
            self.tts.speak(res)
            return True

        # "search youtube for <query>"
        m_yt = re.match(r"^search\s+youtube\s+(?:for\s+)?(.+)$", lower)
        if m_yt:
            self.add_message("YOU", message)
            res = search_youtube(m_yt.group(1).strip())
            self.add_message("J.A.R.V.I.S", res, subtitle="AUTOMATION")
            self.tts.speak(res)
            return True

        # "open a new tab" / "open new tab in chrome" / "new tab"
        m_tab = re.match(
            r"^(?:(?:open|launch)\s+)?(?:a\s+)?new\s+tab(?:\s+(?:in|on)\s+(?:chrome|google\s+chrome|browser))?$",
            lower,
        )
        if m_tab:
            self.add_message("YOU", message)
            try:
                res = open_new_tab()
                self.add_message("J.A.R.V.I.S", res, subtitle="AUTOMATION")
                self.tts.speak("Opening a new tab in Google Chrome.")
            except Exception as err:
                self.add_message("ERROR", str(err))
            return True

        # "open <known website or app>" (including e.g. "open youtube on chrome")
        web_tlds = (
            ".com", ".org", ".net", ".io", ".dev", ".ai", ".edu", ".gov",
            ".co", ".in", ".uk", ".app", ".gg", ".tv", ".me", ".xyz", ".info",
        )
        m_open = re.match(r"^(?:open|launch)\s+([a-z0-9._:/-]+)(?:\s+(?:on|in)\s+\w+)?$", lower)
        if m_open:
            target = m_open.group(1).strip()
            is_web_domain = (
                target in SITE_SHORTCUTS
                or target.startswith(("http://", "https://"))
                or any(target.endswith(tld) for tld in web_tlds)
            )
            if is_web_domain:
                self.add_message("YOU", message)
                try:
                    res = open_website(target)
                    self.add_message("J.A.R.V.I.S", res, subtitle="AUTOMATION")
                    self.tts.speak(f"Opening {target}.")
                except Exception as err:
                    self.add_message("ERROR", str(err))
                return True
            if target in APP_ALIASES:
                self.add_message("YOU", message)
                try:
                    res = open_application(target)
                    self.add_message("J.A.R.V.I.S", res, subtitle="AUTOMATION")
                    self.tts.speak(f"Launching {target}.")
                except Exception as err:
                    self.add_message("ERROR", str(err))
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
        self.ai_core.trigger_pulse()

        if message.startswith("/") and not self.attached_image_path and not self.attached_doc_meta:
            if self._try_handle_slash_command(message):
                return

        # Natural-language desktop shortcuts (so "open youtube", "open notepad", "search google for ..." work directly!)
        if not self.attached_image_path and not self.attached_doc_meta:
            if self._try_handle_natural_automation(message):
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

        if self.agent_mode_enabled and not image_path and not doc_text:
            worker = JarvisWorker(message=message, task="agent_mode")
            self._start_worker_stream(display_user_msg=f"[AGENT] {display_msg}", worker=worker)
            return

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
        self.status_pill.set_status("NEURAL COMPUTE", animate=True)

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
        card_content = self._execute_action_directives(body)
        self.add_message(title, card_content)

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
        self._in_stream_code_block = False
        self._pending_backticks = ""
        self._pending_bracket = ""
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.stream_start_position = cursor.position()
        cursor.insertBlock()

        label_format = QTextCharFormat()
        label_format.setForeground(QColor(self.accent_color))
        label_format.setFontWeight(QFont.Weight.Bold)
        active_name = "U.L.T.R.O.N" if get_personality() == "ULTRON" else "J.A.R.V.I.S"
        cursor.insertText(f"{active_name}  //  STREAMING: ", label_format)

        self.stream_cursor = cursor
        self.chat_display.setTextCursor(cursor)
        self.chat_display.ensureCursorVisible()

    def _filter_speech_stream_chunk(self, text_chunk: str) -> str:
        """Strip fenced ```code``` blocks, brackets, emojis, and action tags across streaming chunks."""
        combined = self._pending_backticks + text_chunk
        self._pending_backticks = ""

        # Hold trailing 1-2 backticks in case the next chunk completes a ``` fence
        trailing_ticks = len(combined) - len(combined.rstrip("`"))
        if trailing_ticks in (1, 2):
            self._pending_backticks = combined[-trailing_ticks:]
            combined = combined[:-trailing_ticks]

        prose_parts = []
        segments = combined.split("```")
        for idx, seg in enumerate(segments):
            if idx > 0:
                self._in_stream_code_block = not self._in_stream_code_block
            if not self._in_stream_code_block and seg:
                prose_parts.append(seg)
        filtered = "".join(prose_parts)

        # Prepend pending bracket fragment from previous chunk if any
        if hasattr(self, "_pending_bracket") and self._pending_bracket:
            filtered = self._pending_bracket + filtered
            self._pending_bracket = ""

        # If there is an unclosed [ that could be an action tag or link, hold it
        last_bracket = filtered.rfind("[")
        if last_bracket != -1 and "]" not in filtered[last_bracket:]:
            if len(filtered) - last_bracket < 150 and "\n" not in filtered[last_bracket:]:
                self._pending_bracket = filtered[last_bracket:]
                filtered = filtered[:last_bracket]

        # Strip action tags completely
        filtered = re.sub(r"\[\s*[A-Z_]{2,}\b[^\]]*\]", "", filtered)
        filtered = re.sub(r"\[\s*[A-Za-z0-9_-]+\s*[:|][^\]]*\]", "", filtered)
        return filtered

    def append_stream_chunk(self, chunk):
        if self.stream_cursor is None:
            return

        text_chunk = str(chunk)
        self.stream_cursor.insertText(text_chunk, self.stream_text_format)
        self.chat_display.setTextCursor(self.stream_cursor)
        self.chat_display.ensureCursorVisible()

        spoken_chunk = self._filter_speech_stream_chunk(text_chunk)
        if not spoken_chunk:
            return

        self.speech_buffer += spoken_chunk

        # Split at sentence boundaries or newlines, grouping tiny fragments for smooth prefetch speech
        parts = re.split(r"(?<=[.!?])\s+|\n{2,}", self.speech_buffer)
        if len(parts) > 1:
            self.speech_buffer = parts.pop()
            merged = ""
            for sentence in parts:
                s = sentence.strip()
                if not s:
                    continue
                merged = f"{merged} {s}".strip() if merged else s
                if len(merged) >= 42:
                    self.tts.speak(merged)
                    merged = ""
            if merged:
                self.speech_buffer = f"{merged} {self.speech_buffer}".strip()

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
        self._in_stream_code_block = False
        self._pending_backticks = ""
        self._pending_bracket = ""
        self.remove_stream_display()
        self.start_stream_display()

    def stream_completed(self, provider_name, full_response):
        remaining_text = self.speech_buffer.strip()
        if remaining_text:
            self.tts.speak(remaining_text)
        self.speech_buffer = ""
        self._in_stream_code_block = False
        self._pending_backticks = ""
        self._pending_bracket = ""

        # Parse and execute any [ACTION: ...] directives emitted by AI
        card_content = self._execute_action_directives(full_response)

        # Upgrade raw streamed block into a crisp Markdown holographic card!
        self.remove_stream_display()
        active_name = "U.L.T.R.O.N" if get_personality() == "ULTRON" else "J.A.R.V.I.S"
        self.add_message(active_name, card_content, subtitle=provider_name.upper())
        self.provider_status.setText(f"LAST TELEMETRY LINK: {provider_name.upper()}")

    def _execute_action_directives(self, text: str) -> str:
        """Execute any [ACTION: ...] tags in the response and replace with sleek execution badges."""
        pattern = re.compile(r"\[ACTION:\s*([A-Z_]+)\s*([^\]]*)\]")
        if not pattern.search(text):
            return text

        def repl(m):
            atype = m.group(1).strip()
            raw_args = m.group(2).strip()
            attrs = {}
            for k, v1, v2 in re.findall(r'(\w+)=(?:"([^"]*)"|\'([^\']*)\')', raw_args):
                attrs[k] = v1 if v1 != "" else v2

            try:
                if atype == "WHATSAPP_MSG":
                    from tools.whatsapp import send_whatsapp_message
                    c = attrs.get("contact", "")
                    msg = attrs.get("text", "")
                    if c:
                        send_whatsapp_message(contact=c, message=msg, auto_send=True)
                        return f"\n> 💬 **[ACTION EXECUTED]** *Dispatched WhatsApp message to `{c}` via Google Chrome.*"

                elif atype == "WHATSAPP_CALL":
                    from tools.whatsapp import call_whatsapp_contact
                    c = attrs.get("contact", "")
                    ct = attrs.get("type", "voice")
                    if c:
                        call_whatsapp_contact(contact=c, call_type=ct)
                        return f"\n> 📞 **[ACTION EXECUTED]** *Opened chat with `{c}` on WhatsApp Web in Chrome for {ct} call.*"

                elif atype == "WHATSAPP_OPEN":
                    from tools.whatsapp import open_whatsapp_web
                    open_whatsapp_web()
                    return "\n> 🌐 **[ACTION EXECUTED]** *Opened WhatsApp Web in Google Chrome.*"

                elif atype == "OPEN_APP":
                    from tools.computer import open_application
                    app = attrs.get("app", "")
                    if app:
                        res = open_application(app)
                        return f"\n> ⚡ **[ACTION EXECUTED]** *{res}*"

                elif atype in ("OPEN_URL", "OPEN_NEW_TAB", "NEW_TAB", "OPEN_TAB"):
                    from tools.computer import open_website, open_new_tab
                    url = attrs.get("url", "").strip()
                    if url and url.lower() not in ("about:blank", "about:newtab", "chrome://newtab", "new tab", "newtab"):
                        res = open_website(url)
                    else:
                        res = open_new_tab(url or "chrome://newtab")
                    return f"\n> 🌐 **[ACTION EXECUTED]** *{res}*"

                elif atype == "SEARCH_GOOGLE":
                    from tools.computer import search_google
                    q = attrs.get("query", "")
                    if q:
                        res = search_google(q)
                        return f"\n> 🔍 **[ACTION EXECUTED]** *{res}*"

                elif atype == "SEARCH_YOUTUBE":
                    from tools.computer import search_youtube
                    q = attrs.get("query", "")
                    if q:
                        res = search_youtube(q)
                        return f"\n> 🎬 **[ACTION EXECUTED]** *{res}*"

                elif atype == "VOLUME":
                    from tools.computer import volume_up, volume_down, volume_mute_toggle, set_volume_percent
                    lvl = attrs.get("level", "up").lower()
                    if lvl == "up":
                        res = volume_up()
                    elif lvl == "down":
                        res = volume_down()
                    elif lvl == "mute":
                        res = volume_mute_toggle()
                    elif lvl.isdigit():
                        res = set_volume_percent(int(lvl))
                    else:
                        res = f"Volume level {lvl}"
                    return f"\n> 🔊 **[ACTION EXECUTED]** *{res}*"

                elif atype == "TAKE_SCREENSHOT":
                    from tools.computer import capture_screenshot_qapp
                    p = capture_screenshot_qapp(QApplication.instance())
                    return f"\n> 📸 **[ACTION EXECUTED]** *Screenshot captured: `{p}`*"

                elif atype == "SCHEDULE":
                    from core.scheduler import save_scheduled_task
                    tid = save_scheduled_task(
                        name="AI Directive Job",
                        action_type=attrs.get("action", "ai_prompt"),
                        payload=attrs.get("payload", ""),
                        next_run_at=attrs.get("time", ""),
                    )
                    return f"\n> ⏰ **[ACTION EXECUTED]** *Task #{tid} scheduled for {attrs.get('time')}*"

            except Exception as err:
                return f"\n> ⚠️ **[ACTION FAILED: {atype}]** *{err}*"

            return f"\n> ⚙️ **[ACTION: {atype}]**"

        return pattern.sub(repl, text)

    def show_error(self, error):
        self.tts.clear()
        self.speech_buffer = ""
        self._in_stream_code_block = False
        self._pending_backticks = ""
        self._pending_bracket = ""
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
            self.status_pill.set_status("ONLINE // READY", animate=False)
        if worker is not None:
            worker.deleteLater()

    # =========================================
    # HOLOGRAPHIC CHAT CARDS & HISTORY
    # =========================================

    def add_message(self, sender, message, subtitle=""):
        is_light = self.theme_mode == "light"
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Clean, cinematic obsidian/titanium cards — NO loud neon pastel fills
        if is_light:
            card_user = "rgba(15, 20, 28, 0.045)"
            card_ai = "rgba(15, 20, 28, 0.025)"
            border_subtle = "rgba(15, 20, 28, 0.12)"
            text_color = "#0f141c"
            meta_color = "#5a687a"
        else:
            card_user = "rgba(255, 255, 255, 0.045)"
            card_ai = "rgba(255, 255, 255, 0.022)"
            border_subtle = "rgba(255, 255, 255, 0.08)"
            text_color = "#dde3ea"
            meta_color = "#6a7689"

        palette = {
            "YOU": ("#94a3b8" if not is_light else "#475569", card_user),
            "J.A.R.V.I.S": (self.accent_color, card_ai),
            "U.L.T.R.O.N": (self.accent_color, card_ai),
            "JARVIS": (self.accent_color, card_ai),
            "SYSTEM": ("#c9973b", card_ai),
            "CONVERSATION SUMMARY": ("#9b87d6", card_ai),
            "ERROR": ("#cf2538", "rgba(207, 37, 56, 0.08)"),
        }
        badge_color, card_bg = palette.get(sender, (self.accent_color, card_ai))

        rendered_body = render_markdown_html(message, self.accent_color, is_light)
        sub_tag = f"  //  {html_lib.escape(subtitle)}" if subtitle else ""

        card_html = f"""
        <table width="100%" cellspacing="0" cellpadding="0" style="margin: 7px 0px;">
            <tr>
                <td style="
                    background-color: {card_bg};
                    border: 1px solid {border_subtle};
                    border-left: 2px solid {badge_color};
                    border-radius: 6px;
                    padding: 10px 14px;
                ">
                    <div style="margin-bottom: 5px;">
                        <span style="
                            color: {badge_color};
                            font-family: Consolas, monospace;
                            font-size: 11px;
                            font-weight: bold;
                            letter-spacing: 1.2px;
                        ">{html_lib.escape(sender)}{sub_tag}</span>
                        <span style="
                            color: {meta_color};
                            font-family: Consolas, monospace;
                            font-size: 10px;
                        ">&nbsp;&nbsp;[{timestamp}]</span>
                    </div>
                    <div style="color: {text_color}; font-size: 13.5px; line-height: 1.5;">
                        {rendered_body}
                    </div>
                </td>
            </tr>
        </table>
        """
        self.chat_display.append(card_html)
        self.chat_display.verticalScrollBar().setValue(self.chat_display.verticalScrollBar().maximum())

    def load_active_session_to_chat(self):
        self.chat_display.clear()
        rows = get_recent_messages(limit=40)
        if not rows:
            self.add_message(
                "J.A.R.V.I.S",
                "All primary systems are online and calibrated. How may I assist you today?\n"
                "- Click any **Quick Action chip** below or type `/help` for directives.",
                subtitle="MARK IX BOOT",
            )
            return
        for _, role, msg, _ in rows:
            sender = "YOU" if role == "user" else "J.A.R.V.I.S"
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
            QMessageBox.information(self, "Please wait", "J.A.R.V.I.S is still computing.")
            return

        answer = QMessageBox.question(
            self,
            "New Session",
            "Initialize a fresh neural session? Your current session stays archived in Memory Vault.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            self.stop_speaking()
            create_new_conversation()
            start_new_chat()
            self.chat_display.clear()
            self.add_message("J.A.R.V.I.S", "New session initialized. Ready for your next directive.", subtitle="FRESH SESSION")
        except Exception as error:
            QMessageBox.critical(self, "Error", f"Could not start a new conversation:\n{error}")

    # =========================================
    # NAVIGATION & LIVE TELEMETRY SYNC
    # =========================================

    def _toggle_sidebar(self):
        self.sidebar.setVisible(not self.sidebar.isVisible())
        hud_sfx.play("click")

    def switch_page(self, key: str):
        route_map = {
            "home": ("home", None, None),
            "chat": ("chat", None, None),
            "voice": ("voice", None, None),
            "tools": ("tools", None, None),
            "settings": ("settings", None, None),
            "about": ("about", None, None),
            # Legacy & direct shortcut mappings
            "workspace": ("tools", self.tools_hub, 0),
            "productivity": ("tools", self.tools_hub, 0),
            "automation": ("tools", self.tools_hub, 1),
            "dev_cyber": ("tools", self.tools_hub, 2),
            "coding": ("tools", self.tools_hub, 2),
            "cybersec": ("tools", self.tools_hub, 3),
            "system": ("tools", self.tools_hub, 4),
            "dashboard": ("tools", self.tools_hub, 4),
            "providers": ("tools", self.tools_hub, 4),
            "memory": ("tools", self.tools_hub, 5),
        }
        if key not in route_map:
            return

        hub_key, sub_tabs, tab_idx = route_map[key]
        hud_sfx.play("click")

        if key == "productivity":
            self.productivity_page.refresh_all()
        elif key in ("memory", "system"):
            self.memory_page.refresh()

        if sub_tabs is not None and tab_idx is not None:
            sub_tabs.setCurrentIndex(tab_idx)

        self.pages.setCurrentWidget(self.page_map[hub_key])

        for nav_key, btn in self.nav_buttons.items():
            btn.setProperty("active", nav_key == hub_key)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

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
        if hasattr(self, "home_page"):
            self.home_page.set_speaking(speaking)
        if hasattr(self, "sidebar_avatar"):
            if speaking:
                self.sidebar_avatar.set_state("speaking")
            elif self.worker is not None:
                self.sidebar_avatar.set_state("thinking")
            else:
                self.sidebar_avatar.set_state("idle")
        if hasattr(self, "voice_page_avatar"):
            if speaking:
                self.voice_page_avatar.set_state("speaking")
                self.voice_page_waveform.set_active(True)
            elif self.worker is not None:
                self.voice_page_avatar.set_state("thinking")
                self.voice_page_waveform.set_active(False)
            else:
                self.voice_page_avatar.set_state("idle")
                self.voice_page_waveform.set_active(False)

        if speaking:
            self.ai_core.set_state("speaking")
            self.status_pill.set_status("VOCAL SYNTHESIS", animate=True)
        elif self.worker is not None:
            self.ai_core.set_state("thinking")
        else:
            self.ai_core.set_state("idle")
            if self.status_pill.text() != "ONLINE // READY":
                self.status_pill.set_status("ONLINE // READY", animate=False)

    def _update_hud_telemetry(self):
        now = datetime.now()
        self.hud_clock_label.setText(now.strftime("%H:%M:%S  |  %a %d %b").upper())

        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent

        self.top_cpu_metric.setText(f"CPU {cpu:.0f}%")
        self.top_ram_metric.setText(f"RAM {ram:.0f}%")
        self._update_top_engine_badge()

        self.rail_cpu_gauge.set_value(cpu)
        self.rail_ram_gauge.set_value(ram)
        self.rail_graph.push_sample(cpu, ram)

        # Refresh mission counters lightly every 5 seconds
        if now.second % 5 == 0 or self.rail_stats_label.text() == "Loading telemetry...":
            try:
                pending = len(list_tasks("pending"))
                rems = len(list_reminders(include_notified=False))
                scheds = sum(1 for t in list_scheduled_tasks() if t["enabled"])
                ltms = len(get_long_term_memories())
                plugs = len(plugin_manager.list_tools())
                self.rail_stats_label.setText(
                    f"▸ PENDING TASKS   : {pending}\n"
                    f"▸ SCHEDULED JOBS  : {scheds}\n"
                    f"▸ ACTIVE ALARMS   : {rems}\n"
                    f"▸ LONG-TERM FACTS : {ltms}\n"
                    f"▸ LOADED PLUGINS  : {plugs}"
                )
            except Exception:
                pass

    def _check_due_reminders(self):
        try:
            due = get_due_reminders()
            for _, title, remind_at in due:
                hud_sfx.play("alert")
                self.tts.speak(f"Reminder alert: {title}")
                self.productivity_page.refresh_reminders()
                QMessageBox.information(self, "J.A.R.V.I.S Alarm", f"Time: {remind_at}\n\n{title}")
        except Exception:
            pass

    def _check_scheduled_tasks(self):
        try:
            due_tasks = claim_due_tasks()
            for task_dict in due_tasks:
                self._dispatch_scheduled_task(task_dict)
        except Exception as err:
            print(f"[SCHEDULER POLL ERROR] {err}")

    def _dispatch_scheduled_task(self, task_dict: dict):
        worker = JarvisWorker(task="run_scheduled_task", extra={"task_dict": dict(task_dict)})
        worker.task_completed.connect(lambda header, out, w=worker: self._on_scheduled_task_done(header, out, w))
        worker.error_occurred.connect(lambda err, name=task_dict.get("name", "Task"): self.add_message("ERROR", f"Scheduled task '{name}' failed: {err}"))
        worker.finished.connect(lambda w=worker: self._cleanup_scheduled_worker(w))
        self.scheduled_workers.append(worker)
        worker.start()

    def _on_scheduled_task_done(self, header: str, output: str, worker: JarvisWorker):
        hud_sfx.play("alert")
        self.add_message("SYSTEM", output, subtitle=header)
        self.productivity_page.refresh_all()
        res = worker.extra.get("result") or {}
        if res.get("speak_result", True):
            spoken = f"Scheduled task {res.get('name', '')} finished."
            if res.get("action_type") == "notify":
                spoken = output[:250]
            self.tts.speak(spoken)

    def _cleanup_scheduled_worker(self, worker: JarvisWorker):
        if worker in self.scheduled_workers:
            self.scheduled_workers.remove(worker)
        worker.deleteLater()

    def apply_identity_preset(self, identity: str):
        """Instantly switch between cinematic REAL J.A.R.V.I.S (Stark Gold + British Voice) and REAL ULTRON (Forged Crimson + Deep Voice)."""
        identity = identity.upper().strip()
        if identity == "ULTRON":
            set_personality("ULTRON")
            self.tts.set_voice_profile("en-US-ChristopherNeural", "-6Hz")
            self.apply_theme("dark", "#cf2538")
            self.logo_label.setText("U.L.T.R.O.N")
            self.hud_brand_label.setText("●  ULTRON PRIME // STRATEGIC MATRIX")
            self.setWindowTitle("U.L.T.R.O.N // STRATEGIC NEURAL CORE")
        else:
            set_personality("JARVIS")
            self.tts.set_voice_profile("en-GB-RyanNeural", "+0Hz")
            self.apply_theme("dark", "#d99b38")
            self.logo_label.setText("J.A.R.V.I.S")
            self.hud_brand_label.setText("●  STARK INDUSTRIES // J.A.R.V.I.S CORE")
            self.setWindowTitle("J.A.R.V.I.S // STARK NEURAL HUD")

        self._sync_brain_controls()
        idx = self.settings_page.personality_combo.findData(get_personality())
        if idx >= 0:
            self.settings_page.personality_combo.blockSignals(True)
            self.settings_page.personality_combo.setCurrentIndex(idx)
            self.settings_page.personality_combo.blockSignals(False)
        for i in range(self.settings_page.voice_combo.count()):
            if self.settings_page.voice_combo.itemData(i)["voice"] == self.tts.voice:
                self.settings_page.voice_combo.blockSignals(True)
                self.settings_page.voice_combo.setCurrentIndex(i)
                self.settings_page.voice_combo.blockSignals(False)
                break
        self.ai_core.trigger_pulse()

    def _on_voice_settings_changed(self, voice_id: str, pitch: str, rate: str):
        if voice_id == "__TEST__":
            self.stop_speaking()
            who = "Ultron" if get_personality() == "ULTRON" else "Jarvis"
            self.tts.speak(
                f"{who} vocal synthesis online. Speech speed and streaming prefetch are now calibrated for smooth, continuous playback."
            )
            return
        self.tts.set_voice_profile(voice_id, pitch)
        self.tts.set_rate(rate)

    # =========================================
    # THEMES & ACCENT COLORS
    # =========================================

    def apply_theme(self, theme_mode: str, accent_hex: str):
        self.theme_mode = (theme_mode or "dark").lower()
        self.accent_color = accent_hex or "#d99b38"
        set_setting("theme_mode", self.theme_mode)
        set_setting("accent_color", self.accent_color)

        self.setStyleSheet(build_stylesheet(self.theme_mode, self.accent_color))
        self.hud_canvas.set_theme_accent(self.theme_mode, self.accent_color)
        self.ai_core.set_accent(self.accent_color)
        self.waveform.set_accent(self.accent_color)
        self.rail_cpu_gauge.set_accent(self.accent_color)
        self.rail_ram_gauge.set_accent(self.accent_color)
        self.rail_graph.set_accent(self.accent_color)
        self.dashboard_page.set_accent(self.accent_color)

        if hasattr(self, "home_page"):
            self.home_page.set_accent(self.accent_color)
        if hasattr(self, "sidebar_avatar"):
            self.sidebar_avatar.set_accent(self.accent_color)
        if hasattr(self, "voice_page_avatar"):
            self.voice_page_avatar.set_accent(self.accent_color)
            self.voice_page_waveform.set_accent(self.accent_color)

        # Keep SettingsPage state synchronized with sidebar quick-toggle and identity presets
        if hasattr(self, "settings_page"):
            self.settings_page._theme = self.theme_mode
            self.settings_page._accent = self.accent_color
        if hasattr(self, "spotlight"):
            self.spotlight.apply_accent(self.accent_color)
        if hasattr(self, "tray_icon") and self.tray_icon is not None:
            self.tray_icon.setIcon(self._build_tray_icon())

        self._sync_identity_branding()

        stream_fg = QColor("#0f141c") if self.theme_mode == "light" else QColor("#dde3ea")
        self.stream_text_format.setForeground(stream_fg)

        self.quick_theme_btn.setText("🌙  OBSIDIAN DARK" if self.theme_mode == "light" else "☀  TITANIUM LIGHT")

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
        self.hud_telemetry_timer.stop()
        self.reminder_timer.stop()
        if hasattr(self, "weather_timer"):
            self.weather_timer.stop()
        if hasattr(self, "_startup_weather_timer"):
            self._startup_weather_timer.stop()
        if hasattr(self, "scheduler_timer"):
            self.scheduler_timer.stop()
        if hasattr(self, "_startup_sched_timer"):
            self._startup_sched_timer.stop()
        for sw in list(self.scheduled_workers):
            if sw is not None and sw.isRunning():
                sw.quit()
                sw.wait(2000)
        if hasattr(self, "_hotkey_filter"):
            self._hotkey_filter.unregister()
            app_inst = QApplication.instance()
            if app_inst is not None:
                app_inst.removeNativeEventFilter(self._hotkey_filter)
        if hasattr(self, "tray_icon") and self.tray_icon is not None:
            self.tray_icon.hide()
        if self._weather_worker is not None and self._weather_worker.isRunning():
            self._weather_worker.quit()
            self._weather_worker.wait(1000)
        self.hud_canvas.stop_animation()
        self.ai_core.stop_animation()
        self.waveform.stop_animation()
        self.rail_cpu_gauge.stop_animation()
        self.rail_ram_gauge.stop_animation()
        self.status_pill.stop_animation()

        if hasattr(self, "home_page"):
            self.home_page.shutdown()
        if hasattr(self, "sidebar_avatar"):
            self.sidebar_avatar.stop_animation()
        if hasattr(self, "voice_page_avatar"):
            self.voice_page_avatar.stop_animation()
            self.voice_page_waveform.stop_animation()

        if hasattr(self, "dashboard_page"):
            self.dashboard_page.shutdown()

        for page in (self.productivity_page, self.coding_page, self.cybersec_page, self.automation_page, self.memory_page):
            if hasattr(page, "shutdown"):
                page.shutdown()

        hud_sfx.shutdown()

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
