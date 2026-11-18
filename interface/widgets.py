"""Custom Animated JARVIS Widgets: AI Core (3.1), Live Audio Waveform (3.2), Typing/Speaking Indicator (3.7)."""

import math
from PySide6.QtWidgets import QWidget, QLabel
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QRadialGradient, QBrush


class AICoreWidget(QWidget):
    """Holographic animated JARVIS Arc-Reactor / AI Core (3.1)."""

    def __init__(self, accent="#00d9ff", parent=None):
        super().__init__(parent)
        self.setMinimumSize(130, 130)
        self.setMaximumSize(160, 160)

        self._accent = QColor(accent)
        self._state = "idle"  # idle | thinking | speaking | error
        self._angle_outer = 0.0
        self._angle_inner = 0.0
        self._phase = 0.0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)  # ~30 FPS smooth animation

    def set_accent(self, hex_color: str):
        self._accent = QColor(hex_color)
        self.update()

    def set_state(self, state: str):
        self._state = state
        self.update()

    def _tick(self):
        speed = {
            "idle": 0.9,
            "thinking": 3.8,
            "speaking": 2.4,
            "error": 1.6,
        }.get(self._state, 1.0)

        self._angle_outer = (self._angle_outer + speed) % 360.0
        self._angle_inner = (self._angle_inner - speed * 1.6) % 360.0
        self._phase = (self._phase + 0.12 * speed) % (math.tau)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0
        radius = min(w, h) * 0.44

        base_color = QColor("#ff4455") if self._state == "error" else QColor(self._accent)
        pulse = 0.5 + 0.5 * math.sin(self._phase)

        # Ambient glow
        glow = QRadialGradient(QPointF(cx, cy), radius * 1.15)
        c_center = QColor(base_color)
        c_center.setAlpha(int(85 + 75 * pulse))
        c_edge = QColor(base_color)
        c_edge.setAlpha(0)
        glow.setColorAt(0.0, c_center)
        glow.setColorAt(0.65, QColor(base_color.red(), base_color.green(), base_color.blue(), 28))
        glow.setColorAt(1.0, c_edge)
        painter.setBrush(QBrush(glow))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), radius * 1.12, radius * 1.12)

        # Outer segmented rotating ring
        outer_rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
        pen_outer = QPen(base_color, 3.0)
        pen_outer.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_outer)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for i in range(4):
            start_deg = self._angle_outer + i * 90.0
            painter.drawArc(outer_rect, int(start_deg * 16), int(58 * 16))

        # Middle dashed tech ring
        mid_r = radius * 0.74
        mid_rect = QRectF(cx - mid_r, cy - mid_r, mid_r * 2, mid_r * 2)
        mid_color = QColor(base_color)
        mid_color.setAlpha(190)
        pen_mid = QPen(mid_color, 2.2)
        painter.setPen(pen_mid)
        for i in range(6):
            start_deg = self._angle_inner + i * 60.0
            painter.drawArc(mid_rect, int(start_deg * 16), int(34 * 16))

        # Inner pulsing energy ring
        inner_r = radius * (0.42 + 0.08 * pulse)
        inner_color = QColor(base_color)
        inner_color.setAlpha(int(170 + 80 * pulse))
        painter.setPen(QPen(inner_color, 2.5))
        painter.drawEllipse(QPointF(cx, cy), inner_r, inner_r)

        # Core orb
        core_r = radius * (0.20 + 0.05 * pulse)
        core_grad = QRadialGradient(QPointF(cx, cy), core_r)
        core_grad.setColorAt(0.0, QColor("#ffffff"))
        core_grad.setColorAt(0.55, base_color)
        core_grad.setColorAt(1.0, QColor(base_color.red(), base_color.green(), base_color.blue(), 40))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(core_grad))
        painter.drawEllipse(QPointF(cx, cy), core_r, core_r)

        # Orbiting energy nodes
        node_r = radius * 0.87
        painter.setBrush(QBrush(QColor("#ffffff")))
        for k in range(3):
            rad = math.radians(self._angle_outer * 1.4 + k * 120.0)
            nx = cx + math.cos(rad) * node_r
            ny = cy + math.sin(rad) * node_r
            painter.drawEllipse(QPointF(nx, ny), 2.5, 2.5)

        painter.end()

    def stop_animation(self):
        self._timer.stop()


class AudioWaveformWidget(QWidget):
    """Live animated audio equalizer / waveform synced to TTS speaking state (3.2)."""

    def __init__(self, accent="#00d9ff", bar_count=22, parent=None):
        super().__init__(parent)
        self.setFixedHeight(34)
        self.setMinimumWidth(140)
        self._accent = QColor(accent)
        self._bar_count = bar_count
        self._active = False
        self._phase = 0.0
        self._levels = [0.15] * bar_count

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(45)

    def set_accent(self, hex_color: str):
        self._accent = QColor(hex_color)
        self.update()

    def set_active(self, active: bool):
        self._active = bool(active)

    def _tick(self):
        self._phase += 0.35 if self._active else 0.08
        for i in range(self._bar_count):
            center_weight = 1.0 - abs((i - (self._bar_count - 1) / 2.0) / (self._bar_count / 2.0)) * 0.55
            if self._active:
                wave = (
                    0.45 * math.sin(self._phase + i * 0.55)
                    + 0.35 * math.cos(self._phase * 1.7 - i * 0.9)
                    + 0.20 * math.sin(self._phase * 2.5 + i * 1.3)
                )
                target = max(0.18, min(1.0, (0.55 + 0.45 * wave) * center_weight))
            else:
                wave = 0.5 + 0.5 * math.sin(self._phase + i * 0.35)
                target = 0.10 + 0.10 * wave * center_weight
            self._levels[i] = self._levels[i] * 0.55 + target * 0.45
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        gap = 3.0
        bar_w = max(2.5, (w - gap * (self._bar_count + 1)) / self._bar_count)
        mid_y = h / 2.0

        painter.setPen(Qt.PenStyle.NoPen)
        for i, level in enumerate(self._levels):
            bar_h = max(3.0, level * (h - 6))
            x = gap + i * (bar_w + gap)
            y = mid_y - bar_h / 2.0
            color = QColor(self._accent)
            color.setAlpha(235 if self._active else 110)
            painter.setBrush(QBrush(color))
            painter.drawRoundedRect(QRectF(x, y, bar_w, bar_h), bar_w / 2.0, bar_w / 2.0)

        painter.end()

    def stop_animation(self):
        self._timer.stop()


class StatusPulseLabel(QLabel):
    """Animated Typing / Thinking / Speaking status pill (3.7)."""

    def __init__(self, parent=None):
        super().__init__("READY", parent)
        self.setObjectName("status_pill")
        self._base_text = "READY"
        self._animate = False
        self._dots = 0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(350)

    def set_status(self, text: str, animate: bool = False):
        self._base_text = text
        self._animate = animate
        if not animate:
            self.setText(text)
        else:
            self._dots = 1
            self.setText(f"{text}.")

    def _tick(self):
        if not self._animate:
            return
        self._dots = (self._dots % 3) + 1
        self.setText(f"{self._base_text}{'.' * self._dots}")

    def stop_animation(self):
        self._timer.stop()

