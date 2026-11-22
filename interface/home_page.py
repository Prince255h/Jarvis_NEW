"""Cybernetic Hero Dashboard (Home Page) for J.A.R.V.I.S — Inspired by Movie-Grade Sci-Fi HUD."""

import time
import psutil
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QLineEdit,
    QPushButton,
    QMessageBox,
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QColor

from interface.cyber_widgets import (
    CyberRobotAvatar,
    SymmetricalAudioWaveform,
    CyberWaveformWing,
    CyberMicButton,
    CyberGlowProgressBar,
    CyberQuickActionButton,
)


class HomePage(QWidget):
    """Futuristic Cybernetic Hero Dashboard with Robot Avatar, Waveform Mic, Quick Actions, and System Info."""

    command_submitted = Signal(str)
    voice_toggled = Signal()
    open_youtube_signal = Signal()
    search_google_signal = Signal()
    play_music_signal = Signal()
    check_time_signal = Signal()
    shutdown_pc_signal = Signal()

    def __init__(self, accent="#00d2ff", parent=None):
        super().__init__(parent)
        self._accent = accent
        self._is_listening = False

        # Motivational quotes rotation
        self._quotes = [
            ("⭐ You've got this!", "Keep going! 😊"),
            ("🚀 All Systems Nominal", "JARVIS ready for directive."),
            ("⚡ High Efficiency Mode", "Neural pipelines online."),
            ("🛡️ Defense & Core Active", "Mark IX cybernetic link stable."),
            ("💡 Ready to Build", "Ask anything, execute tasks."),
        ]
        self._quote_index = 0

        self._setup_ui()

        # Telemetry & Clock update timer (1000ms)
        self._telemetry_timer = QTimer(self)
        self._telemetry_timer.timeout.connect(self._update_telemetry)
        self._telemetry_timer.start(1000)
        self._update_telemetry()

        # Motivational quote cycler (12 seconds)
        self._quote_timer = QTimer(self)
        self._quote_timer.timeout.connect(self._cycle_quote)
        self._quote_timer.start(12000)

    def set_accent(self, hex_color: str):
        self._accent = hex_color
        self.avatar.set_accent(hex_color)
        self.left_waveform.set_accent(hex_color)
        self.right_waveform.set_accent(hex_color)
        self.mic_btn.set_accent(hex_color)
        self.cpu_bar.set_accent(hex_color)
        self.ram_bar.set_accent(hex_color)
        if hasattr(self, "greeting_lbl"):
            self.greeting_lbl.setText(
                "<span style='color: #ffffff; font-size: 28px; font-weight: 700;'>Hello! 👋</span><br>"
                f"<span style='color: #ffffff; font-size: 34px; font-weight: 800;'>I'm </span>"
                f"<span style='color: {self._accent}; font-size: 34px; font-weight: 800; letter-spacing: 1px;'>JARVIS.</span><br>"
                "<span style='color: #8da4be; font-size: 15px; font-weight: 500;'>How can I help you today?</span>"
            )
        self.update()

    def set_speaking(self, is_speaking: bool):
        state = "speaking" if is_speaking else ("listening" if self._is_listening else "idle")
        self.avatar.set_state(state)
        active = is_speaking or self._is_listening
        self.left_waveform.set_active(active)
        self.right_waveform.set_active(active)
        if is_speaking:
            self.mic_btn.set_active(False, "Speaking...")
        elif self._is_listening:
            self.mic_btn.set_active(True, "Listening...")
        else:
            self.mic_btn.set_active(False, "Ready")

    def set_listening(self, is_listening: bool):
        self._is_listening = bool(is_listening)
        state = "listening" if self._is_listening else "idle"
        self.avatar.set_state(state)
        self.left_waveform.set_active(self._is_listening)
        self.right_waveform.set_active(self._is_listening)
        self.mic_btn.set_active(self._is_listening, "Listening..." if self._is_listening else "Ready")

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(18, 14, 18, 14)
        main_layout.setSpacing(20)

        # =====================================================
        # LEFT / CENTER HERO COLUMN (Avatar, Waveform, Input)
        # =====================================================
        center_col = QVBoxLayout()
        center_col.setSpacing(16)

        # 1. Top Hero Greeting Banner
        hero_banner = QFrame()
        hero_banner.setObjectName("cyber_card")
        hero_layout = QHBoxLayout(hero_banner)
        hero_layout.setContentsMargins(24, 20, 24, 20)
        hero_layout.setSpacing(24)

        # Animated Cybernetic Robot Avatar
        self.avatar = CyberRobotAvatar(accent=self._accent, size=150)
        self.avatar.clicked.connect(self._on_avatar_clicked)
        hero_layout.addWidget(self.avatar)

        # Greeting Typography
        text_layout = QVBoxLayout()
        text_layout.setSpacing(6)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.greeting_lbl = QLabel(
            "<span style='color: #ffffff; font-size: 28px; font-weight: 700;'>Hello! 👋</span><br>"
            f"<span style='color: #ffffff; font-size: 34px; font-weight: 800;'>I'm </span>"
            f"<span style='color: {self._accent}; font-size: 34px; font-weight: 800; letter-spacing: 1px;'>JARVIS.</span><br>"
            "<span style='color: #8da4be; font-size: 15px; font-weight: 500;'>How can I help you today?</span>"
        )
        self.greeting_lbl.setTextFormat(Qt.TextFormat.RichText)
        self.greeting_lbl.setStyleSheet("background: transparent;")
        text_layout.addWidget(self.greeting_lbl)
        hero_layout.addLayout(text_layout)
        hero_layout.addStretch()

        center_col.addWidget(hero_banner)

        # 2. Middle Voice & Waveform Equalizer Card
        voice_card = QFrame()
        voice_card.setObjectName("cyber_card")
        voice_layout = QVBoxLayout(voice_card)
        voice_layout.setContentsMargins(20, 24, 20, 24)
        voice_layout.setSpacing(8)

        # Flanked Waveform & Center Mic container (Left Wing - Center Mic Button - Right Wing)
        wf_container = QWidget()
        wf_layout = QHBoxLayout(wf_container)
        wf_layout.setContentsMargins(10, 8, 10, 8)
        wf_layout.setSpacing(16)
        wf_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.left_waveform = CyberWaveformWing(accent=self._accent, side="left", bar_count=22, height=68)
        self.mic_btn = CyberMicButton(accent=self._accent, size=76)
        self.mic_btn.clicked.connect(self._on_mic_clicked)
        self.right_waveform = CyberWaveformWing(accent=self._accent, side="right", bar_count=22, height=68)

        wf_layout.addWidget(self.left_waveform, 1)
        wf_layout.addWidget(self.mic_btn, 0, Qt.AlignmentFlag.AlignCenter)
        wf_layout.addWidget(self.right_waveform, 1)

        voice_layout.addWidget(wf_container)
        center_col.addWidget(voice_card, 1)

        # 3. Bottom Floating Command Input Capsule
        input_capsule = QFrame()
        input_capsule.setObjectName("cyber_input_capsule")
        input_layout = QHBoxLayout(input_capsule)
        input_layout.setContentsMargins(14, 8, 10, 8)
        input_layout.setSpacing(12)

        cmd_icon = QLabel("💬")
        cmd_icon.setFont(QFont("Segoe UI Emoji", 15))
        cmd_icon.setStyleSheet("background: transparent; color: #8da4be;")

        self.command_input = QLineEdit()
        self.command_input.setObjectName("cyber_text_input")
        self.command_input.setPlaceholderText("Type your command...")
        self.command_input.setFont(QFont("Segoe UI", 12))
        self.command_input.returnPressed.connect(self._on_transmit_clicked)

        self.send_btn = QPushButton("➔")
        self.send_btn.setObjectName("cyber_send_btn")
        self.send_btn.setFixedSize(40, 40)
        self.send_btn.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.clicked.connect(self._on_transmit_clicked)

        input_layout.addWidget(cmd_icon)
        input_layout.addWidget(self.command_input, 1)
        input_layout.addWidget(self.send_btn)

        center_col.addWidget(input_capsule)
        main_layout.addLayout(center_col, 1)

        # =====================================================
        # RIGHT WIDGETS COLUMN (Quick Actions, System Info, Quote)
        # =====================================================
        right_container = QWidget()
        right_container.setFixedWidth(280)
        right_col = QVBoxLayout(right_container)
        right_col.setContentsMargins(0, 0, 0, 0)
        right_col.setSpacing(14)

        # 1. Quick Actions Card
        qa_card = QFrame()
        qa_card.setObjectName("cyber_card")
        qa_layout = QVBoxLayout(qa_card)
        qa_layout.setContentsMargins(14, 12, 14, 14)
        qa_layout.setSpacing(8)

        qa_hdr = QHBoxLayout()
        qa_hdr.setSpacing(6)
        qa_icon = QLabel("⚡")
        qa_icon.setFont(QFont("Segoe UI Emoji", 13))
        qa_icon.setStyleSheet("color: #00d2ff; background: transparent;")
        qa_title = QLabel("Quick Actions")
        qa_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        qa_title.setStyleSheet("color: #ffffff; background: transparent;")
        qa_hdr.addWidget(qa_icon)
        qa_hdr.addWidget(qa_title)
        qa_hdr.addStretch()
        qa_layout.addLayout(qa_hdr)

        btn_yt = CyberQuickActionButton("Open YouTube", "▶", icon_color="#ff334b")
        btn_yt.clicked.connect(self._action_open_youtube)
        qa_layout.addWidget(btn_yt)

        btn_search = CyberQuickActionButton("Search Google", "G", icon_color="#4285f4")
        btn_search.clicked.connect(self._action_search_google)
        qa_layout.addWidget(btn_search)

        btn_music = CyberQuickActionButton("Play Music", "🎵", icon_color="#a855f7")
        btn_music.clicked.connect(self._action_play_music)
        qa_layout.addWidget(btn_music)

        btn_time = CyberQuickActionButton("Check Time", "🕒", icon_color="#00d2ff")
        btn_time.clicked.connect(self._action_check_time)
        qa_layout.addWidget(btn_time)

        btn_shutdown = CyberQuickActionButton("Shutdown PC", "⏻", icon_color="#ef4444")
        btn_shutdown.clicked.connect(self._action_shutdown_pc)
        qa_layout.addWidget(btn_shutdown)

        right_col.addWidget(qa_card)

        # 2. System Info Card
        sys_card = QFrame()
        sys_card.setObjectName("cyber_card")
        sys_layout = QVBoxLayout(sys_card)
        sys_layout.setContentsMargins(14, 12, 14, 14)
        sys_layout.setSpacing(10)

        sys_hdr = QHBoxLayout()
        sys_hdr.setSpacing(6)
        sys_icon = QLabel("💻")
        sys_icon.setFont(QFont("Segoe UI Emoji", 13))
        sys_icon.setStyleSheet("color: #00d2ff; background: transparent;")
        sys_title = QLabel("System Info")
        sys_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        sys_title.setStyleSheet("color: #ffffff; background: transparent;")
        sys_hdr.addWidget(sys_icon)
        sys_hdr.addWidget(sys_title)
        sys_hdr.addStretch()
        sys_layout.addLayout(sys_hdr)

        self.cpu_bar = CyberGlowProgressBar("CPU Usage", accent=self._accent)
        self.ram_bar = CyberGlowProgressBar("RAM Usage", accent=self._accent, is_gradient=True)
        sys_layout.addWidget(self.cpu_bar)
        sys_layout.addWidget(self.ram_bar)

        # Live Clock Row
        clock_row = QHBoxLayout()
        clock_icon = QLabel("🕒")
        clock_icon.setFont(QFont("Segoe UI Emoji", 11))
        clock_icon.setStyleSheet("color: #00d2ff; background: transparent;")
        clock_lbl = QLabel("Time")
        clock_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        clock_lbl.setStyleSheet("color: #8da4be; background: transparent;")
        self.live_time_lbl = QLabel("12:00 PM")
        self.live_time_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.live_time_lbl.setStyleSheet("color: #ffffff; background: transparent;")

        clock_row.addWidget(clock_icon)
        clock_row.addWidget(clock_lbl)
        clock_row.addStretch()
        clock_row.addWidget(self.live_time_lbl)
        sys_layout.addLayout(clock_row)

        right_col.addWidget(sys_card)

        # 3. Motivational / Status Quote Card
        self.quote_card = QFrame()
        self.quote_card.setObjectName("cyber_card")
        qc_layout = QVBoxLayout(self.quote_card)
        qc_layout.setContentsMargins(14, 12, 14, 12)
        qc_layout.setSpacing(3)
        qc_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.quote_title = QLabel("⭐ You've got this!")
        self.quote_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.quote_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.quote_title.setStyleSheet("color: #ffd166; background: transparent;")

        self.quote_sub = QLabel("Keep going! 😊")
        self.quote_sub.setFont(QFont("Segoe UI", 9))
        self.quote_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.quote_sub.setStyleSheet("color: #c5d4e8; background: transparent;")

        qc_layout.addWidget(self.quote_title)
        qc_layout.addWidget(self.quote_sub)
        right_col.addWidget(self.quote_card)

        right_col.addStretch()
        main_layout.addWidget(right_container)

    # =====================================================
    # EVENTS & ACTIONS
    # =====================================================

    def _on_avatar_clicked(self):
        self.voice_toggled.emit()

    def _on_mic_clicked(self):
        self.voice_toggled.emit()

    def _on_transmit_clicked(self):
        text = self.command_input.text().strip()
        if not text:
            return
        self.command_input.clear()
        self.command_submitted.emit(text)

    def _action_open_youtube(self):
        self.open_youtube_signal.emit()

    def _action_search_google(self):
        self.search_google_signal.emit()

    def _action_play_music(self):
        self.play_music_signal.emit()

    def _action_check_time(self):
        self.check_time_signal.emit()

    def _action_shutdown_pc(self):
        self.shutdown_pc_signal.emit()

    def _update_telemetry(self):
        try:
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent
            self.cpu_bar.set_value(cpu)
            self.ram_bar.set_value(ram)
        except Exception:
            pass

        # 12-hour AM/PM format (e.g. 12:00 PM)
        now_str = time.strftime("%I:%M %p")
        self.live_time_lbl.setText(now_str)

    def _cycle_quote(self):
        self._quote_index = (self._quote_index + 1) % len(self._quotes)
        title, sub = self._quotes[self._quote_index]
        self.quote_title.setText(title)
        self.quote_sub.setText(sub)

    def shutdown(self):
        self._telemetry_timer.stop()
        self._quote_timer.stop()
        self.avatar.stop_animation()
        self.left_waveform.stop_animation()
        self.right_waveform.stop_animation()
        self.mic_btn.stop_animation()
        self.cpu_bar.stop_animation()
        self.ram_bar.stop_animation()
