"""Movie-Grade J.A.R.V.I.S & ULTRON Themes — Deep Matte Obsidian, Forged Carbon & Precision Accents."""

# Cinematic, restrained movie-accurate accents (NO cheap neon glare)
ACCENT_PRESETS = {
    "Arc Reactor Cyan": "#00d2ff",
    "J.A.R.V.I.S Gold": "#d99b38",
    "ULTRON Crimson": "#cf2538",
    "Stark Holo Steel": "#3e96cc",
    "Titanium Silver": "#94a3b8",
    "Tactical Emerald": "#2da878",
    "Neon Purple": "#a855f7",
    "Obsidian Amber": "#c97a2b",
}


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    color = (hex_color or "#00d2ff").lstrip("#")
    if len(color) != 6:
        return (0, 210, 255)
    return int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)


def hex_to_rgba(hex_color: str, alpha: float) -> str:
    r, g, b = hex_to_rgb(hex_color)
    return f"rgba({r}, {g}, {b}, {alpha})"


def build_stylesheet(theme_mode: str = "dark", accent: str = "#00d2ff") -> str:
    """Build a heavy, cinematic movie-grade Stark/Ultron stylesheet (matte obsidian + hairline steel)."""
    is_light = (theme_mode or "dark").lower() == "light"

    if is_light:
        bg_main = "#e6ebf0"
        bg_sidebar = "#dce2e9"
        bg_topbar = "#eef2f6"
        bg_surface = "#f4f7fa"
        bg_surface_solid = "#ffffff"
        bg_surface_alt = "#e2e8f0"
        bg_input = "#ffffff"
        text_primary = "#0f141c"
        text_secondary = "#4d5a6b"
        border_subtle = "#c5ced9"
        border_med = "#aebbc9"
        btn_hover = "#d8e0e8"
        btn_active = hex_to_rgba(accent, 0.22)
        accent_soft = hex_to_rgba(accent, 0.13)
        accent_subtle = hex_to_rgba(accent, 0.06)
        primary_text = "#ffffff"
    else:
        # True cinema obsidian carbon & forged titanium (zero cheap neon wash)
        bg_main = "#05070a"
        bg_sidebar = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0a0d12, stop:1 #06080b)"
        bg_topbar = "rgba(10, 13, 18, 0.94)"
        bg_surface = "rgba(13, 17, 23, 0.90)"
        bg_surface_solid = "#0d1117"
        bg_surface_alt = "#141922"
        bg_input = "#0a0d13"
        text_primary = "#dde3ea"
        text_secondary = "#7a8699"
        border_subtle = "#1c232e"
        border_med = "#283242"
        btn_hover = "#1a212d"
        btn_active = hex_to_rgba(accent, 0.24)
        accent_soft = hex_to_rgba(accent, 0.14)
        accent_subtle = hex_to_rgba(accent, 0.06)
        primary_text = "#06080b"

    accent_line = hex_to_rgba(accent, 0.55)

    return f"""
        QMainWindow {{
            background-color: {bg_main};
        }}

        QWidget {{
            background-color: transparent;
            color: {text_primary};
            font-family: "Segoe UI", "Inter", Arial, sans-serif;
            font-size: 13px;
        }}

        QWidget#page_root {{
            background-color: transparent;
        }}

        QFrame#sidebar {{
            background: {bg_sidebar};
            border-right: 1px solid {border_subtle};
        }}

        QFrame#topbar {{
            background-color: {bg_topbar};
            border-bottom: 1px solid {border_subtle};
        }}

        QFrame#hud_panel {{
            background-color: {bg_surface};
            border: 1px solid {border_subtle};
            border-top: 2px solid {accent_line};
            border-radius: 8px;
        }}

        QFrame#input_capsule {{
            background-color: {bg_input};
            border: 1px solid {border_med};
            border-radius: 9px;
        }}

        QLabel {{
            background-color: transparent;
            color: {text_primary};
        }}

        QLabel#logo {{
            color: {text_primary};
            font-family: "Consolas", "Segoe UI", monospace;
            font-size: 19px;
            font-weight: bold;
            letter-spacing: 6px;
            padding: 2px;
        }}

        QLabel#hud_brand {{
            color: {accent};
            font-family: "Consolas", monospace;
            font-size: 11.5px;
            font-weight: bold;
            letter-spacing: 2.2px;
        }}

        QLabel#hud_clock {{
            color: {text_primary};
            font-family: "Consolas", monospace;
            font-size: 11.5px;
            font-weight: bold;
            letter-spacing: 1px;
        }}

        QLabel#hud_metric {{
            color: {text_secondary};
            font-family: "Consolas", monospace;
            font-size: 11px;
            padding: 2px 8px;
            background-color: {bg_surface_alt};
            border: 1px solid {border_subtle};
            border-radius: 5px;
        }}

        QLabel#section_header {{
            color: {text_secondary};
            font-family: "Consolas", monospace;
            font-size: 10px;
            font-weight: bold;
            letter-spacing: 2.2px;
            padding-top: 4px;
        }}

        QLabel#page_title {{
            color: {text_primary};
            font-family: "Consolas", "Segoe UI", monospace;
            font-size: 17px;
            font-weight: bold;
            letter-spacing: 2px;
            padding: 2px;
        }}

        QLabel#subtitle, QLabel#muted {{
            color: {text_secondary};
            font-size: 12px;
        }}

        QLabel#provider_status {{
            color: {text_secondary};
            font-family: "Consolas", monospace;
            font-size: 11px;
            letter-spacing: 0.6px;
        }}

        QLabel#status_pill {{
            background-color: {accent_soft};
            color: {accent};
            border: 1px solid {accent_line};
            border-radius: 9px;
            padding: 3px 12px;
            font-family: "Consolas", monospace;
            font-size: 10px;
            font-weight: bold;
            letter-spacing: 1.6px;
        }}

        QFrame#card, QFrame#provider_card {{
            background-color: {bg_surface};
            border: 1px solid {border_subtle};
            border-left: 2px solid {accent_line};
            border-radius: 8px;
        }}

        QGroupBox {{
            background-color: {bg_surface};
            border: 1px solid {border_subtle};
            border-radius: 8px;
            margin-top: 12px;
            padding: 14px 10px 10px 10px;
            font-family: "Consolas", "Segoe UI", monospace;
            font-size: 11.5px;
            font-weight: bold;
            color: {accent};
        }}

        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px;
        }}

        /* Matte forged metallic buttons — accent appears subtly on hover */
        QPushButton {{
            background-color: {bg_surface_alt};
            color: {text_primary};
            border: 1px solid {border_med};
            border-radius: 6px;
            padding: 7px 13px;
            font-family: "Consolas", "Segoe UI", monospace;
            font-size: 11.5px;
            font-weight: bold;
            letter-spacing: 0.6px;
        }}

        QPushButton:hover {{
            background-color: {btn_hover};
            color: {accent};
            border: 1px solid {accent_line};
        }}

        QPushButton:pressed {{
            background-color: {btn_active};
        }}

        QPushButton:disabled {{
            color: {text_secondary};
            border-color: {border_subtle};
            background-color: {bg_surface};
        }}

        QPushButton#primary_cta {{
            background-color: {accent};
            color: {primary_text};
            border: 1px solid {accent};
            border-radius: 6px;
            padding: 8px 18px;
            font-family: "Consolas", "Segoe UI", monospace;
            font-size: 11.5px;
            font-weight: bold;
            letter-spacing: 1.4px;
        }}

        QPushButton#primary_cta:hover {{
            background-color: {hex_to_rgba(accent, 0.85)};
            color: {primary_text};
        }}

        QPushButton#primary_cta:disabled {{
            background-color: {border_subtle};
            color: {text_secondary};
            border-color: {border_subtle};
        }}

        QPushButton#chip_button {{
            background-color: {bg_surface_alt};
            color: {text_secondary};
            border: 1px solid {border_subtle};
            border-radius: 6px;
            padding: 4px 10px;
            font-family: "Segoe UI", sans-serif;
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0px;
        }}

        QPushButton#chip_button:hover {{
            background-color: {accent_soft};
            color: {text_primary};
            border: 1px solid {accent_line};
        }}

        QPushButton#nav_button {{
            background-color: transparent;
            color: #8da4be;
            border: 1px solid transparent;
            border-radius: 12px;
            padding: 10px 14px;
            text-align: left;
            font-family: "Segoe UI", sans-serif;
            font-size: 13px;
            font-weight: 600;
            letter-spacing: 0.3px;
        }}

        QPushButton#nav_button:hover {{
            background-color: rgba(0, 210, 255, 0.10);
            color: #ffffff;
            border: 1px solid rgba(0, 210, 255, 0.25);
        }}

        QPushButton#nav_button[active="true"] {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #005ce6, stop:1 #00b4d8);
            color: #ffffff;
            border: 1px solid rgba(0, 210, 255, 0.65);
            border-radius: 12px;
            font-weight: bold;
        }}

        QFrame#cyber_card {{
            background-color: rgba(10, 16, 28, 0.82);
            border: 1px solid rgba(0, 210, 255, 0.24);
            border-radius: 16px;
        }}

        QFrame#cyber_card:hover {{
            border: 1px solid rgba(0, 210, 255, 0.45);
        }}

        QFrame#cyber_input_capsule {{
            background-color: rgba(8, 13, 22, 0.92);
            border: 1px solid rgba(0, 210, 255, 0.38);
            border-radius: 22px;
        }}

        QFrame#cyber_input_capsule:focus-within {{
            border: 1.5px solid #00d2ff;
        }}

        QLineEdit#cyber_text_input {{
            background: transparent;
            border: none;
            color: #ffffff;
            font-family: "Segoe UI", sans-serif;
            font-size: 13px;
            padding: 4px;
        }}

        QPushButton#cyber_send_btn {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #005ce6, stop:1 #00b4d8);
            color: #ffffff;
            border: none;
            border-radius: 12px;
            font-weight: bold;
        }}

        QPushButton#cyber_send_btn:hover {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0077ff, stop:1 #33d6ff);
        }}

        QPushButton#cyber_send_btn:pressed {{
            background: #0044bb;
        }}

        QFrame#sidebar_status_card {{
            background-color: rgba(10, 16, 26, 0.85);
            border: 1px solid rgba(0, 210, 255, 0.22);
            border-radius: 14px;
        }}

        QPushButton#danger_button {{
            background-color: rgba(207, 37, 56, 0.10);
            color: #e04f5f;
            border: 1px solid rgba(207, 37, 56, 0.45);
        }}

        QPushButton#danger_button:hover {{
            background-color: rgba(207, 37, 56, 0.24);
            color: #ff6b7a;
            border: 1px solid #e04f5f;
        }}

        QComboBox {{
            background-color: {bg_surface_solid};
            color: {text_primary};
            border: 1px solid {border_med};
            border-radius: 6px;
            padding: 5px 10px;
            min-width: 90px;
            font-family: "Consolas", "Segoe UI", monospace;
            font-size: 11.5px;
        }}

        QComboBox:hover {{
            border-color: {accent_line};
        }}

        QComboBox QAbstractItemView {{
            background-color: {bg_surface_solid};
            color: {text_primary};
            selection-background-color: {accent_soft};
            selection-color: {accent};
            border: 1px solid {border_med};
        }}

        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDateTimeEdit, QDateEdit {{
            background-color: {bg_input};
            color: {text_primary};
            border: 1px solid {border_subtle};
            border-radius: 7px;
            padding: 8px 10px;
            selection-background-color: {accent};
        }}

        QLineEdit#command_input {{
            background-color: transparent;
            border: none;
            padding: 8px 6px;
            font-size: 14px;
            color: {text_primary};
        }}

        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border: 1px solid {accent_line};
        }}

        QLineEdit#command_input:focus {{
            border: none;
        }}

        QTextBrowser {{
            background-color: {bg_surface};
            color: {text_primary};
            border: 1px solid {border_subtle};
            border-radius: 9px;
            padding: 12px;
            font-size: 14px;
        }}

        QListWidget, QTableWidget {{
            background-color: {bg_surface};
            color: {text_primary};
            border: 1px solid {border_subtle};
            border-radius: 8px;
            padding: 4px;
        }}

        QListWidget::item {{
            padding: 7px 9px;
            border-radius: 5px;
            margin: 1px 0px;
        }}

        QListWidget::item:hover {{
            background-color: {accent_subtle};
        }}

        QListWidget::item:selected {{
            background-color: {accent_soft};
            color: {accent};
            border-left: 2px solid {accent};
        }}

        QTabWidget::pane {{
            border: 1px solid {border_subtle};
            border-radius: 8px;
            background-color: {bg_surface};
            padding: 8px;
        }}

        QTabBar::tab {{
            background-color: {bg_surface_alt};
            color: {text_secondary};
            border: 1px solid {border_subtle};
            border-bottom: none;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            padding: 8px 14px;
            margin-right: 3px;
            font-family: "Consolas", "Segoe UI", monospace;
            font-size: 11px;
            font-weight: bold;
        }}

        QTabBar::tab:hover {{
            color: {text_primary};
        }}

        QTabBar::tab:selected {{
            background-color: {bg_surface};
            color: {accent};
            border-top: 2px solid {accent};
        }}

        QProgressBar {{
            border: 1px solid {border_subtle};
            border-radius: 5px;
            background-color: {bg_surface_solid};
            text-align: center;
            color: {text_primary};
            font-family: "Consolas", monospace;
            font-size: 11px;
            min-height: 20px;
        }}

        QProgressBar::chunk {{
            background-color: {accent};
            border-radius: 4px;
        }}

        QCalendarWidget QWidget {{
            background-color: {bg_surface_solid};
            color: {text_primary};
        }}

        QCalendarWidget QAbstractItemView:enabled {{
            background-color: {bg_surface_solid};
            color: {text_primary};
            selection-background-color: {accent};
            selection-color: #05070a;
        }}

        QSplitter::handle {{
            background-color: {border_subtle};
            height: 3px;
        }}

        QScrollBar:vertical {{
            background: transparent;
            width: 6px;
            margin: 2px;
        }}

        QScrollBar::handle:vertical {{
            background: {border_med};
            border-radius: 3px;
            min-height: 28px;
        }}

        QScrollBar::handle:vertical:hover {{
            background: {accent};
        }}

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
    """
