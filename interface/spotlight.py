"""Floating Stark Quick-Summon Spotlight Command Bar & Windows Global Hotkey Filter (Ctrl+Shift+Space)."""

import ctypes
import sys
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton
from PySide6.QtCore import Qt, Signal, QAbstractNativeEventFilter


HOTKEY_ID = 0x4A52  # 'JR'
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
VK_SPACE = 0x20
WM_HOTKEY = 0x0312


class GlobalHotkeyFilter(QAbstractNativeEventFilter):
    """Native Windows event filter listening for WM_HOTKEY (Ctrl+Shift+Space)."""

    def __init__(self, callback):
        super().__init__()
        self._callback = callback
        self._registered = False

    def register(self) -> bool:
        if sys.platform != "win32":
            return False
        try:
            ok = ctypes.windll.user32.RegisterHotKey(None, HOTKEY_ID, MOD_CONTROL | MOD_SHIFT, VK_SPACE)
            self._registered = bool(ok)
            return self._registered
        except Exception:
            return False

    def unregister(self):
        if sys.platform == "win32" and self._registered:
            try:
                ctypes.windll.user32.UnregisterHotKey(None, HOTKEY_ID)
            except Exception:
                pass
            self._registered = False

    def nativeEventFilter(self, eventType, message):
        if sys.platform == "win32":
            try:
                msg = ctypes.wintypes.MSG.from_address(int(message))
                if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                    self._callback()
                    return True, 0
            except Exception:
                pass
        return False, 0


class SpotlightDialog(QDialog):
    """Sleek floating Stark Command Bar summoned globally via Ctrl+Shift+Space or System Tray."""

    command_submitted = Signal(str)

    def __init__(self, accent="#d99b38", parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFixedWidth(620)
        self._accent = accent

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        hdr = QHBoxLayout()
        self.title_lbl = QLabel("●  J.A.R.V.I.S  //  QUICK COMMAND SPOTLIGHT")
        self.title_lbl.setStyleSheet(f"color: {accent}; font-family: Consolas, monospace; font-size: 11px; font-weight: bold; letter-spacing: 2px;")
        hint_lbl = QLabel("ENTER to run  •  ESC to hide")
        hint_lbl.setStyleSheet("color: #7a8699; font-family: Consolas, monospace; font-size: 10px;")
        hdr.addWidget(self.title_lbl)
        hdr.addStretch()
        hdr.addWidget(hint_lbl)
        layout.addLayout(hdr)

        row = QHBoxLayout()
        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("Ask anything, /agent <goal>, /search <query>, /kb <doc query>, or open <app>...")
        self.input_box.returnPressed.connect(self._submit)
        go_btn = QPushButton("RUN")
        go_btn.setObjectName("primary_cta")
        go_btn.clicked.connect(self._submit)
        row.addWidget(self.input_box, 1)
        row.addWidget(go_btn)
        layout.addLayout(row)

        self.apply_accent(accent)

    def apply_accent(self, accent: str):
        self._accent = accent
        self.title_lbl.setStyleSheet(
            f"color: {accent}; font-family: Consolas, monospace; font-size: 11px; font-weight: bold; letter-spacing: 2px;"
        )
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #080b10;
                border: 1px solid {accent};
                border-radius: 10px;
            }}
            QLineEdit {{
                background-color: #0e131c;
                color: #e2e8f0;
                border: 1px solid #253042;
                border-radius: 7px;
                padding: 10px;
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border: 1px solid {accent};
            }}
            QPushButton#primary_cta {{
                background-color: {accent};
                color: #06080b;
                border: none;
                border-radius: 7px;
                padding: 10px 18px;
                font-family: Consolas, monospace;
                font-weight: bold;
            }}
        """)

    def summon(self):
        self.input_box.clear()
        self.show()
        self.raise_()
        self.activateWindow()
        self.input_box.setFocus()

    def _submit(self):
        text = self.input_box.text().strip()
        if not text:
            self.hide()
            return
        self.hide()
        self.command_submitted.emit(text)

