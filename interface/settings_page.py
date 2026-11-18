"""Appearance, Personality, Response Style & Multilingual Settings Page (1.4, 3.5, 3.6, 7.6)."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QGroupBox,
    QColorDialog,
    QGridLayout,
)
from PySide6.QtCore import Signal

from core.personality import PERSONALITIES, RESPONSE_STYLES, LANGUAGES
from core.brain import (
    get_personality,
    set_personality,
    get_response_style,
    set_response_style,
    get_language,
    set_language,
)
from interface.themes import ACCENT_PRESETS


class SettingsPage(QWidget):
    """Settings page for Dark/Light Themes, Accent Colors, AI Personality, Style, and Language."""

    theme_changed = Signal(str, str)  # (theme_mode, accent_hex)
    brain_settings_changed = Signal()

    def __init__(self, current_theme="dark", current_accent="#00d9ff", parent=None):
        super().__init__(parent)
        self._theme = current_theme
        self._accent = current_accent

        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        title = QLabel("JARVIS SETTINGS & CUSTOMIZATION")
        title.setObjectName("page_title")
        layout.addWidget(title)

        # 3.5 Light & Dark Theme + 3.6 Customizable Accent Colors
        theme_box = QGroupBox("Appearance: Theme & Accent Colors (3.5 - 3.6)")
        tb = QVBoxLayout(theme_box)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Theme Mode:"))
        self.dark_btn = QPushButton("DARK MODE")
        self.dark_btn.clicked.connect(lambda: self._set_theme("dark"))
        self.light_btn = QPushButton("LIGHT MODE")
        self.light_btn.clicked.connect(lambda: self._set_theme("light"))
        mode_row.addWidget(self.dark_btn)
        mode_row.addWidget(self.light_btn)
        mode_row.addStretch()
        tb.addLayout(mode_row)

        accent_grid = QGridLayout()
        for idx, (label, hex_code) in enumerate(ACCENT_PRESETS.items()):
            btn = QPushButton(f"●  {label}")
            btn.setStyleSheet(f"color: {hex_code}; border-color: {hex_code};")
            btn.clicked.connect(lambda checked=False, h=hex_code: self._set_accent(h))
            accent_grid.addWidget(btn, idx // 3, idx % 3)

        pick_btn = QPushButton("CUSTOM COLOR PICKER...")
        pick_btn.clicked.connect(self._pick_custom_color)
        tb.addLayout(accent_grid)
        tb.addWidget(pick_btn)
        layout.addWidget(theme_box)

        # 1.4 Personalities & Response Styles + 7.6 Multilingual
        brain_box = QGroupBox("AI Brain Personality, Style & Language (1.4, 7.6)")
        bb = QGridLayout(brain_box)

        bb.addWidget(QLabel("Personality Mode:"), 0, 0)
        self.personality_combo = QComboBox()
        for key, meta in PERSONALITIES.items():
            self.personality_combo.addItem(meta["label"], key)
        idx = self.personality_combo.findData(get_personality())
        if idx >= 0:
            self.personality_combo.setCurrentIndex(idx)
        self.personality_combo.currentIndexChanged.connect(self._on_personality_changed)
        bb.addWidget(self.personality_combo, 0, 1)

        bb.addWidget(QLabel("Response Style:"), 1, 0)
        self.style_combo = QComboBox()
        self.style_combo.addItems(list(RESPONSE_STYLES.keys()))
        self.style_combo.setCurrentText(get_response_style())
        self.style_combo.currentTextChanged.connect(self._on_style_changed)
        bb.addWidget(self.style_combo, 1, 1)

        bb.addWidget(QLabel("Response Language:"), 2, 0)
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(LANGUAGES)
        self.lang_combo.setCurrentText(get_language())
        self.lang_combo.currentTextChanged.connect(self._on_language_changed)
        bb.addWidget(self.lang_combo, 2, 1)

        layout.addWidget(brain_box)
        layout.addStretch()

    def _set_theme(self, mode):
        self._theme = mode
        self.theme_changed.emit(self._theme, self._accent)

    def _set_accent(self, hex_code):
        self._accent = hex_code
        self.theme_changed.emit(self._theme, self._accent)

    def _pick_custom_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self._set_accent(color.name())

    def _on_personality_changed(self):
        key = self.personality_combo.currentData()
        if key:
            set_personality(key)
            self.brain_settings_changed.emit()

    def _on_style_changed(self, style):
        set_response_style(style)
        self.brain_settings_changed.emit()

    def _on_language_changed(self, lang):
        set_language(lang)
        self.brain_settings_changed.emit()

