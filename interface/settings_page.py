"""Appearance, Voice Speed/Profile, Personality, Response Style & Multilingual Settings Page."""

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
    QCheckBox,
    QLineEdit,
)
from PySide6.QtCore import Signal

from core.personality import PERSONALITIES, RESPONSE_STYLES, LANGUAGES
from core.memory import get_setting, set_setting
from core.sfx import hud_sfx
from core.brain import (
    get_personality,
    set_personality,
    get_response_style,
    set_response_style,
    get_language,
    set_language,
)
from core.tts import VOICE_PRESETS, SPEED_PRESETS
from interface.themes import ACCENT_PRESETS


class SettingsPage(QWidget):
    """Settings for J.A.R.V.I.S / ULTRON Theme Presets, Accent Colors, Voice Speed/Profile, Personality & Language."""

    theme_changed = Signal(str, str)
    brain_settings_changed = Signal()
    voice_changed = Signal(str, str, str)  # (voice_id, pitch, rate)
    preset_identity_selected = Signal(str)  # "JARVIS" or "ULTRON"
    weather_city_changed = Signal(str)

    def __init__(self, current_theme="dark", current_accent="#d99b38", current_voice="en-GB-RyanNeural", current_rate="+18%", parent=None):
        super().__init__(parent)
        self._theme = current_theme
        self._accent = current_accent

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("HUD CONFIG // IDENTITY, VOICE & APPEARANCE")
        title.setObjectName("page_title")
        layout.addWidget(title)

        # Quick Movie Identity Presets (REAL JARVIS vs REAL ULTRON)
        id_box = QGroupBox("CINEMATIC IDENTITY PRESETS (THEME + VOICE + PERSONA)")
        id_row = QHBoxLayout(id_box)
        jarvis_btn = QPushButton("J.A.R.V.I.S  (STARK GOLD + BRITISH VOICE)")
        jarvis_btn.clicked.connect(lambda: self.preset_identity_selected.emit("JARVIS"))
        ultron_btn = QPushButton("U.L.T.R.O.N  (FORGED CRIMSON + DEEP VOICE)")
        ultron_btn.clicked.connect(lambda: self.preset_identity_selected.emit("ULTRON"))
        id_row.addWidget(jarvis_btn)
        id_row.addWidget(ultron_btn)
        layout.addWidget(id_box)

        # Theme & Accent Colors
        theme_box = QGroupBox("APPEARANCE: OBSIDIAN / TITANIUM THEME & ACCENT")
        tb = QVBoxLayout(theme_box)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Surface Mode:"))
        self.dark_btn = QPushButton("OBSIDIAN DARK")
        self.dark_btn.clicked.connect(lambda: self._set_theme("dark"))
        self.light_btn = QPushButton("TITANIUM LIGHT")
        self.light_btn.clicked.connect(lambda: self._set_theme("light"))
        mode_row.addWidget(self.dark_btn)
        mode_row.addWidget(self.light_btn)
        mode_row.addStretch()
        tb.addLayout(mode_row)

        accent_grid = QGridLayout()
        for idx, (label, hex_code) in enumerate(ACCENT_PRESETS.items()):
            btn = QPushButton(f"●  {label}")
            btn.setStyleSheet(f"color: {hex_code}; border-left: 3px solid {hex_code};")
            btn.clicked.connect(lambda checked=False, h=hex_code: self._set_accent(h))
            accent_grid.addWidget(btn, idx // 3, idx % 3)

        pick_btn = QPushButton("CUSTOM ACCENT COLOR...")
        pick_btn.clicked.connect(self._pick_custom_color)
        tb.addLayout(accent_grid)
        tb.addWidget(pick_btn)
        layout.addWidget(theme_box)

        # Voice Synthesis Engine (Speed & Voice Profile)
        voice_box = QGroupBox("VOCAL SYNTHESIS ENGINE (SPEED & VOICE)")
        vb = QGridLayout(voice_box)

        vb.addWidget(QLabel("Voice Profile:"), 0, 0)
        self.voice_combo = QComboBox()
        for label, meta in VOICE_PRESETS.items():
            self.voice_combo.addItem(label, meta)
        for i in range(self.voice_combo.count()):
            if self.voice_combo.itemData(i)["voice"] == current_voice:
                self.voice_combo.setCurrentIndex(i)
                break
        self.voice_combo.currentIndexChanged.connect(self._emit_voice_change)
        vb.addWidget(self.voice_combo, 0, 1)

        vb.addWidget(QLabel("Speech Speed:"), 1, 0)
        self.speed_combo = QComboBox()
        for label, rate_val in SPEED_PRESETS.items():
            self.speed_combo.addItem(label, rate_val)
        s_idx = self.speed_combo.findData(current_rate)
        if s_idx >= 0:
            self.speed_combo.setCurrentIndex(s_idx)
        self.speed_combo.currentIndexChanged.connect(self._emit_voice_change)
        vb.addWidget(self.speed_combo, 1, 1)

        test_voice_btn = QPushButton("TEST VOICE NOW")
        test_voice_btn.clicked.connect(self._emit_voice_test)
        vb.addWidget(test_voice_btn, 0, 2, 2, 1)
        layout.addWidget(voice_box)

        # AI Brain Personality, Style & Language
        brain_box = QGroupBox("AI BRAIN PERSONALITY, STYLE & LANGUAGE")
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

        # HUD Sound Effects & Weather City
        hud_box = QGroupBox("HUD TELEMETRY: SOUND EFFECTS & LIVE WEATHER")
        hb = QHBoxLayout(hud_box)
        self.sfx_checkbox = QCheckBox("Enable Stark HUD Sound Effects (boot chime & micro-clicks)")
        self.sfx_checkbox.setChecked(hud_sfx.enabled)
        self.sfx_checkbox.toggled.connect(self._on_sfx_toggled)

        self.weather_city_input = QLineEdit()
        self.weather_city_input.setPlaceholderText("Weather City (blank = auto-detect)")
        self.weather_city_input.setText(get_setting("weather_city", "") or "")
        save_city_btn = QPushButton("SAVE CITY")
        save_city_btn.clicked.connect(self._save_weather_city)

        hb.addWidget(self.sfx_checkbox, 2)
        hb.addWidget(self.weather_city_input, 1)
        hb.addWidget(save_city_btn)
        layout.addWidget(hud_box)

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

    def _emit_voice_change(self):
        meta = self.voice_combo.currentData() or {"voice": "en-GB-RyanNeural", "pitch": "+0Hz"}
        rate = self.speed_combo.currentData() or "+18%"
        self.voice_changed.emit(meta["voice"], meta["pitch"], rate)

    def _emit_voice_test(self):
        self._emit_voice_change()
        self.voice_changed.emit("__TEST__", "", "")

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

    def _on_sfx_toggled(self, checked: bool):
        hud_sfx.set_enabled(checked)
        if checked:
            hud_sfx.play("click")

    def _save_weather_city(self):
        city = self.weather_city_input.text().strip()
        set_setting("weather_city", city)
        self.weather_city_changed.emit(city)
