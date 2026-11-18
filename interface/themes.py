"""Dynamic Light & Dark Themes and Customizable Accent Colors for JARVIS (3.5, 3.6)."""

ACCENT_PRESETS = {
    "Arc Cyan": "#00d9ff",
    "Ultron Crimson": "#ff3366",
    "Emerald Matrix": "#00e676",
    "Stark Gold": "#ffab00",
    "Quantum Violet": "#a855f7",
    "Cobalt Blue": "#3b82f6",
}


def hex_to_rgba(hex_color: str, alpha: float) -> str:
    color = hex_color.lstrip("#")
    if len(color) != 6:
        return f"rgba(0, 217, 255, {alpha})"
    r = int(color[0:2], 16)
    g = int(color[2:4], 16)
    b = int(color[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


def build_stylesheet(theme_mode: str = "dark", accent: str = "#00d9ff") -> str:
    """Generate a unified modern Qt stylesheet for dark or light mode with custom accent color."""
    is_light = (theme_mode or "dark").lower() == "light"

    if is_light:
        bg_main = "#f3f6fb"
        bg_sidebar = "#e7eef8"
        bg_surface = "#ffffff"
        bg_surface_alt = "#eef3fa"
        text_primary = "#0f172a"
        text_secondary = "#475569"
        border_subtle = "#cbd5e1"
        btn_hover = hex_to_rgba(accent, 0.16)
        btn_active = hex_to_rgba(accent, 0.25)
    else:
        bg_main = "#070c17"
        bg_sidebar = "#0a1120"
        bg_surface = "#0e172a"
        bg_surface_alt = "#132038"
        text_primary = "#f1f5f9"
        text_secondary = "#94a3b8"
        border_subtle = "#1e3250"
        btn_hover = hex_to_rgba(accent, 0.18)
        btn_active = hex_to_rgba(accent, 0.28)

    accent_soft = hex_to_rgba(accent, 0.12)

    return f"""
        QMainWindow {{
            background-color: {bg_main};
        }}

        QWidget {{
            background-color: {bg_main};
            color: {text_primary};
            font-family: "Segoe UI", Arial, sans-serif;
            font-size: 13px;
        }}

        QFrame#sidebar {{
            background-color: {bg_sidebar};
            border-right: 1px solid {border_subtle};
        }}

        QLabel {{
            background-color: transparent;
            color: {text_primary};
        }}

        QLabel#logo {{
            color: {accent};
            font-size: 22px;
            font-weight: bold;
            letter-spacing: 3px;
            padding: 4px;
        }}

        QLabel#page_title {{
            color: {accent};
            font-size: 20px;
            font-weight: bold;
            padding: 4px 2px;
        }}

        QLabel#subtitle, QLabel#muted {{
            color: {text_secondary};
            font-size: 12px;
        }}

        QLabel#provider_status {{
            color: {accent};
            font-size: 12px;
            font-weight: 600;
            padding-left: 4px;
        }}

        QLabel#status_pill {{
            background-color: {accent_soft};
            color: {accent};
            border: 1px solid {accent};
            border-radius: 11px;
            padding: 3px 10px;
            font-size: 11px;
            font-weight: bold;
        }}

        QFrame#card, QFrame#provider_card {{
            background-color: {bg_surface};
            border: 1px solid {border_subtle};
            border-radius: 10px;
        }}

        QGroupBox {{
            background-color: {bg_surface};
            border: 1px solid {border_subtle};
            border-radius: 9px;
            margin-top: 10px;
            padding-top: 12px;
            font-weight: bold;
            color: {accent};
        }}

        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px;
        }}

        QPushButton {{
            background-color: {bg_surface_alt};
            color: {accent};
            border: 1px solid {accent};
            border-radius: 7px;
            padding: 8px 14px;
            font-weight: bold;
        }}

        QPushButton:hover {{
            background-color: {btn_hover};
        }}

        QPushButton:pressed {{
            background-color: {btn_active};
        }}

        QPushButton:disabled {{
            color: {text_secondary};
            border-color: {border_subtle};
            background-color: {bg_surface};
        }}

        QPushButton#nav_button {{
            background-color: transparent;
            color: {text_primary};
            border: 1px solid transparent;
            border-radius: 8px;
            padding: 9px 12px;
            text-align: left;
            font-size: 13px;
            font-weight: 600;
        }}

        QPushButton#nav_button:hover {{
            background-color: {btn_hover};
            color: {accent};
        }}

        QPushButton#nav_button[active="true"] {{
            background-color: {accent_soft};
            color: {accent};
            border: 1px solid {accent};
        }}

        QPushButton#danger_button {{
            background-color: transparent;
            color: #ff5566;
            border: 1px solid #ff5566;
        }}

        QPushButton#danger_button:hover {{
            background-color: rgba(255, 85, 102, 0.18);
        }}

        QComboBox {{
            background-color: {bg_surface};
            color: {text_primary};
            border: 1px solid {border_subtle};
            border-radius: 7px;
            padding: 6px 10px;
            min-width: 95px;
        }}

        QComboBox:hover {{
            border-color: {accent};
        }}

        QComboBox QAbstractItemView {{
            background-color: {bg_surface};
            color: {text_primary};
            selection-background-color: {btn_hover};
            selection-color: {accent};
            border: 1px solid {accent};
        }}

        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDateTimeEdit, QDateEdit {{
            background-color: {bg_surface};
            color: {text_primary};
            border: 1px solid {border_subtle};
            border-radius: 7px;
            padding: 8px;
            selection-background-color: {accent};
        }}

        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border: 1px solid {accent};
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
            padding: 6px 8px;
            border-radius: 5px;
        }}

        QListWidget::item:selected {{
            background-color: {accent_soft};
            color: {accent};
            border: 1px solid {accent};
        }}

        QTabWidget::pane {{
            border: 1px solid {border_subtle};
            border-radius: 8px;
            background-color: {bg_main};
            padding: 6px;
        }}

        QTabBar::tab {{
            background-color: {bg_surface};
            color: {text_secondary};
            border: 1px solid {border_subtle};
            border-bottom: none;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            padding: 8px 14px;
            margin-right: 3px;
            font-weight: 600;
        }}

        QTabBar::tab:selected {{
            background-color: {accent_soft};
            color: {accent};
            border-color: {accent};
        }}

        QProgressBar {{
            border: 1px solid {border_subtle};
            border-radius: 6px;
            background-color: {bg_surface};
            text-align: center;
            color: {text_primary};
            min-height: 20px;
        }}

        QProgressBar::chunk {{
            background-color: {accent};
            border-radius: 5px;
        }}

        QCalendarWidget QWidget {{
            background-color: {bg_surface};
            color: {text_primary};
        }}

        QCalendarWidget QAbstractItemView:enabled {{
            background-color: {bg_surface};
            color: {text_primary};
            selection-background-color: {accent};
            selection-color: #000000;
        }}

        QScrollBar:vertical {{
            background: {bg_main};
            width: 8px;
            margin: 0px;
        }}

        QScrollBar::handle:vertical {{
            background: {border_subtle};
            border-radius: 4px;
            min-height: 24px;
        }}

        QScrollBar::handle:vertical:hover {{
            background: {accent};
        }}

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
    """

