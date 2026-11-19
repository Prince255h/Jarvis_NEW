"""Movie-Grade J.A.R.V.I.S & ULTRON Custom HUD Widgets (Deep Obsidian, Metallic Depth, Volumetric Core)."""

import math
from collections import deque
from PySide6.QtWidgets import QWidget, QLabel
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF
from PySide6.QtGui import (
    QPainter,
    QColor,
    QPen,
    QRadialGradient,
    QLinearGradient,
    QBrush,
    QPolygonF,
    QFont,
    QPainterPath,
)


class HUDCanvasWidget(QWidget):
    """Deep matte obsidian carbon backdrop with subtle metallic hairline grid and precision corner marks."""

    def __init__(self, theme_mode="dark", accent="#d99b38", parent=None):
        super().__init__(parent)
        self._theme = theme_mode
        self._accent = QColor(accent)
        self._scan_y = 0.0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(80)

    def set_theme_accent(self, theme_mode: str, accent_hex: str):
        self._theme = theme_mode
        self._accent = QColor(accent_hex)
        self.update()

    def _tick(self):
        self._scan_y = (self._scan_y + 0.0025) % 1.0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        w, h = self.width(), self.height()
        is_light = self._theme == "light"

        # Deep cinema carbon vignette (no bright neon wash)
        bg_grad = QRadialGradient(QPointF(w * 0.5, h * 0.4), max(w, h) * 0.85)
        if is_light:
            bg_grad.setColorAt(0.0, QColor("#eef2f6"))
            bg_grad.setColorAt(1.0, QColor("#dce3ec"))
        else:
            bg_grad.setColorAt(0.0, QColor("#0c1017"))
            bg_grad.setColorAt(0.65, QColor("#06080c"))
            bg_grad.setColorAt(1.0, QColor("#030406"))
        painter.fillRect(0, 0, w, h, QBrush(bg_grad))

        # Ultra-subtle hairline architectural grid (barely perceptible, like real cinema HUD)
        grid_color = QColor("#ffffff" if not is_light else "#0f172a")
        grid_color.setAlpha(7 if not is_light else 12)
        painter.setPen(QPen(grid_color, 1))
        step = 56
        for x in range(0, w, step):
            painter.drawLine(x, 0, x, h)
        for y in range(0, h, step):
            painter.drawLine(0, y, w, y)

        # Very restrained subtle scan shimmer
        sy = int(self._scan_y * h)
        scan_grad = QLinearGradient(0, sy - 10, 0, sy + 10)
        c_mid = QColor(self._accent)
        c_mid.setAlpha(10)
        c_zero = QColor(self._accent)
        c_zero.setAlpha(0)
        scan_grad.setColorAt(0.0, c_zero)
        scan_grad.setColorAt(0.5, c_mid)
        scan_grad.setColorAt(1.0, c_zero)
        painter.fillRect(0, sy - 10, w, 20, QBrush(scan_grad))

        # Subtle metallic corner brackets
        bracket = QColor(self._accent)
        bracket.setAlpha(80)
        painter.setPen(QPen(bracket, 1.5))
        m, L = 7, 14
        painter.drawLine(m, m, m + L, m)
        painter.drawLine(m, m, m, m + L)
        painter.drawLine(w - m, m, w - m - L, m)
        painter.drawLine(w - m, m, w - m, m + L)
        painter.drawLine(m, h - m, m + L, h - m)
        painter.drawLine(m, h - m, m, h - m - L)
        painter.drawLine(w - m, h - m, w - m - L, h - m)
        painter.drawLine(w - m, h - m, w - m, h - m - L)

        painter.end()

    def stop_animation(self):
        self._timer.stop()


class AICoreWidget(QWidget):
    """Volumetric Movie-Style J.A.R.V.I.S / ULTRON Neural Sphere Core (3.1)."""

    def __init__(self, accent="#d99b38", parent=None):
        super().__init__(parent)
        self.setMinimumSize(156, 156)
        self.setMaximumSize(176, 176)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Neural Core — Click to pulse")

        self._accent = QColor(accent)
        self._state = "idle"  # idle | thinking | speaking | error
        self._angle_outer = 0.0
        self._angle_mid = 0.0
        self._angle_inner = 0.0
        self._phase = 0.0
        self._ripple = 0.0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(30)

    def set_accent(self, hex_color: str):
        self._accent = QColor(hex_color)
        self.update()

    def set_state(self, state: str):
        self._state = state
        self.update()

    def trigger_pulse(self):
        self._ripple = 0.01

    def mousePressEvent(self, event):
        self.trigger_pulse()
        super().mousePressEvent(event)

    def _tick(self):
        speed = {
            "idle": 0.75,
            "thinking": 3.5,
            "speaking": 2.2,
            "error": 1.8,
        }.get(self._state, 1.0)

        self._angle_outer = (self._angle_outer + speed * 0.75) % 360.0
        self._angle_mid = (self._angle_mid - speed * 1.45) % 360.0
        self._angle_inner = (self._angle_inner + speed * 2.1) % 360.0
        self._phase = (self._phase + 0.10 * speed) % math.tau

        if self._ripple > 0.0:
            self._ripple += 0.045
            if self._ripple >= 1.0:
                self._ripple = 0.0

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0
        radius = min(w, h) * 0.45

        base = QColor("#cf2538") if self._state == "error" else QColor(self._accent)
        pulse = 0.5 + 0.5 * math.sin(self._phase)

        # 1. Dark forged titanium outer housing shadow
        housing = QRadialGradient(QPointF(cx, cy), radius * 1.08)
        housing.setColorAt(0.0, QColor(base.red(), base.green(), base.blue(), int(75 + 55 * pulse)))
        housing.setColorAt(0.55, QColor(base.red(), base.green(), base.blue(), 22))
        housing.setColorAt(0.88, QColor(10, 13, 18, 160))
        housing.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(housing))
        painter.drawEllipse(QPointF(cx, cy), radius * 1.08, radius * 1.08)

        # 2. Outer metallic calibration ticks (48 fine marks)
        tick_r1 = radius * 0.94
        tick_r2 = radius * 1.01
        tick_col = QColor(base)
        tick_col.setAlpha(95)
        painter.setPen(QPen(tick_col, 1.0))
        for i in range(48):
            ang = math.radians(i * 7.5 + self._angle_outer * 0.25)
            extra = 3.0 if (i % 4 == 0) else 0.0
            painter.drawLine(
                QPointF(cx + math.cos(ang) * (tick_r1 - extra), cy + math.sin(ang) * (tick_r1 - extra)),
                QPointF(cx + math.cos(ang) * tick_r2, cy + math.sin(ang) * tick_r2),
            )

        # 3. Heavy machined segmented outer arcs (metallic depth)
        outer_r = radius * 0.84
        outer_rect = QRectF(cx - outer_r, cy - outer_r, outer_r * 2, outer_r * 2)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        pen_outer = QPen(base, 2.8)
        pen_outer.setCapStyle(Qt.PenCapStyle.FlatCap)
        painter.setPen(pen_outer)
        for i in range(3):
            painter.drawArc(outer_rect, int((self._angle_outer + i * 120.0) * 16), int(82 * 16))

        # 4. Counter-rotating neural filaments (Age of Ultron / JARVIS matrix look)
        mid_r = radius * 0.67
        mid_rect = QRectF(cx - mid_r, cy - mid_r, mid_r * 2, mid_r * 2)
        mid_col = QColor(base)
        mid_col.setAlpha(165)
        painter.setPen(QPen(mid_col, 1.6))
        for i in range(6):
            painter.drawArc(mid_rect, int((self._angle_mid + i * 60.0) * 16), int(38 * 16))

        # 5. Volumetric neural web spokes & polygon lattice
        web_r = radius * (0.50 + 0.03 * pulse)
        poly = QPolygonF()
        nodes = []
        for k in range(8):
            ang = math.radians(self._angle_inner + k * 45.0)
            pt = QPointF(cx + math.cos(ang) * web_r, cy + math.sin(ang) * web_r)
            poly.append(pt)
            nodes.append(pt)
        web_col = QColor(base)
        web_col.setAlpha(int(120 + 65 * pulse))
        painter.setPen(QPen(web_col, 1.2))
        painter.drawPolygon(poly)

        # Subtle synaptic cross-chords (real Jarvis/Ultron hologram sphere effect)
        chord_col = QColor(base)
        chord_col.setAlpha(55)
        painter.setPen(QPen(chord_col, 0.9))
        for k in range(4):
            painter.drawLine(nodes[k], nodes[k + 4])

        # 6. Incandescent volumetric molten core
        core_r = radius * (0.28 + 0.04 * pulse)
        core_grad = QRadialGradient(QPointF(cx, cy), core_r)
        core_grad.setColorAt(0.0, QColor("#fff7e6"))
        core_grad.setColorAt(0.38, base)
        core_grad.setColorAt(0.75, QColor(base.red(), base.green(), base.blue(), 75))
        core_grad.setColorAt(1.0, QColor(base.red(), base.green(), base.blue(), 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(core_grad))
        painter.drawEllipse(QPointF(cx, cy), core_r, core_r)

        # Crisp orbital nodes
        painter.setBrush(QBrush(QColor("#f8fafc")))
        for pt in nodes[::2]:
            painter.drawEllipse(pt, 1.8, 1.8)

        # Click shockwave ripple
        if self._ripple > 0.0:
            rip_r = radius * (0.25 + self._ripple * 0.95)
            rip_col = QColor(base)
            rip_col.setAlpha(int((1.0 - self._ripple) * 190))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(rip_col, 1.8))
            painter.drawEllipse(QPointF(cx, cy), rip_r, rip_r)

        painter.end()

    def stop_animation(self):
        self._timer.stop()


class AudioWaveformWidget(QWidget):
    """Precision metallic voice-modulation equalizer synced to live TTS speech (3.2)."""

    def __init__(self, accent="#d99b38", bar_count=28, parent=None):
        super().__init__(parent)
        self.setFixedHeight(34)
        self.setMinimumWidth(160)
        self._accent = QColor(accent)
        self._bar_count = bar_count
        self._active = False
        self._phase = 0.0
        self._levels = [0.10] * bar_count

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(36)

    def set_accent(self, hex_color: str):
        self._accent = QColor(hex_color)
        self.update()

    def set_active(self, active: bool):
        self._active = bool(active)

    def _tick(self):
        self._phase += 0.42 if self._active else 0.07
        for i in range(self._bar_count):
            center = 1.0 - abs((i - (self._bar_count - 1) / 2.0) / (self._bar_count / 2.0)) * 0.65
            if self._active:
                w = (
                    0.46 * math.sin(self._phase + i * 0.55)
                    + 0.34 * math.cos(self._phase * 1.9 - i * 0.85)
                    + 0.20 * math.sin(self._phase * 2.8 + i * 1.4)
                )
                target = max(0.16, min(1.0, (0.55 + 0.45 * w) * center))
            else:
                w = 0.5 + 0.5 * math.sin(self._phase + i * 0.35)
                target = 0.07 + 0.08 * w * center
            self._levels[i] = self._levels[i] * 0.48 + target * 0.52
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        gap = 2.4
        bar_w = max(2.2, (w - gap * (self._bar_count + 1)) / self._bar_count)
        mid_y = h / 2.0

        base_line = QColor(self._accent)
        base_line.setAlpha(35)
        painter.setPen(QPen(base_line, 1))
        painter.drawLine(4, int(mid_y), w - 4, int(mid_y))

        painter.setPen(Qt.PenStyle.NoPen)
        for i, level in enumerate(self._levels):
            bar_h = max(2.5, level * (h - 6))
            x = gap + i * (bar_w + gap)
            y = mid_y - bar_h / 2.0

            col = QColor(self._accent)
            col.setAlpha(225 if self._active else 85)
            painter.setBrush(QBrush(col))
            painter.drawRoundedRect(QRectF(x, y, bar_w, bar_h), 1.2, 1.2)

        painter.end()

    def stop_animation(self):
        self._timer.stop()


class ArcGaugeWidget(QWidget):
    """Machined Iron Man HUD Circular Telemetry Arc Gauge."""

    def __init__(self, label="CPU", accent="#d99b38", size=110, parent=None):
        super().__init__(parent)
        self._label = label
        self._value = 0.0
        self._display_value = 0.0
        self._subtext = ""
        self._accent = QColor(accent)
        self.setMinimumSize(size, size)
        self.setMaximumSize(size + 30, size + 30)

        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._smooth_step)
        self._anim_timer.start(40)

    def set_accent(self, hex_color: str):
        self._accent = QColor(hex_color)
        self.update()

    def set_value(self, value: float, subtext: str = ""):
        self._value = max(0.0, min(100.0, float(value)))
        self._subtext = subtext

    def _smooth_step(self):
        if abs(self._display_value - self._value) > 0.2:
            self._display_value += (self._value - self._display_value) * 0.22
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        side = min(w, h) - 14
        rect = QRectF((w - side) / 2.0, (h - side) / 2.0, side, side)

        arc_color = QColor("#cf2538") if self._display_value >= 88 else (
            QColor("#d99b38") if self._display_value >= 75 else QColor(self._accent)
        )

        # Machined dark track arc
        track_col = QColor(255, 255, 255, 24)
        pen_track = QPen(track_col, 6.0)
        pen_track.setCapStyle(Qt.PenCapStyle.FlatCap)
        painter.setPen(pen_track)
        painter.drawArc(rect, 210 * 16, -240 * 16)

        # Active precision arc
        span = -int((self._display_value / 100.0) * 240.0 * 16)
        pen_val = QPen(arc_color, 6.0)
        pen_val.setCapStyle(Qt.PenCapStyle.FlatCap)
        painter.setPen(pen_val)
        painter.drawArc(rect, 210 * 16, span)

        # Center percentage
        painter.setPen(QColor("#e2e8f0"))
        painter.setFont(QFont("Consolas", max(11, int(side * 0.17)), QFont.Weight.Bold))
        painter.drawText(rect.adjusted(0, -8, 0, -4), Qt.AlignmentFlag.AlignCenter, f"{int(round(self._display_value))}%")

        # Label
        painter.setFont(QFont("Consolas", max(7, int(side * 0.095)), QFont.Weight.Bold))
        painter.setPen(arc_color)
        painter.drawText(rect.adjusted(0, int(side * 0.25), 0, 0), Qt.AlignmentFlag.AlignCenter, self._label)

        if self._subtext:
            painter.setFont(QFont("Consolas", max(7, int(side * 0.08))))
            painter.setPen(QColor("#7a8699"))
            painter.drawText(rect.adjusted(0, int(side * 0.58), 0, 10), Qt.AlignmentFlag.AlignCenter, self._subtext)

        painter.end()

    def stop_animation(self):
        self._anim_timer.stop()


class TelemetryGraphWidget(QWidget):
    """Restrained dual-channel CPU / RAM oscilloscope graph."""

    def __init__(self, accent="#d99b38", secondary="#7a8ea8", max_points=60, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(110)
        self._accent = QColor(accent)
        self._secondary = QColor(secondary)
        self._cpu_hist = deque([0.0] * max_points, maxlen=max_points)
        self._ram_hist = deque([0.0] * max_points, maxlen=max_points)

    def set_accent(self, hex_color: str):
        self._accent = QColor(hex_color)
        self.update()

    def push_sample(self, cpu_pct: float, ram_pct: float):
        self._cpu_hist.append(max(0.0, min(100.0, float(cpu_pct))))
        self._ram_hist.append(max(0.0, min(100.0, float(ram_pct))))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        pad = 10

        painter.setPen(QPen(QColor(255, 255, 255, 18), 1, Qt.PenStyle.DotLine))
        for i in range(1, 4):
            y = pad + (h - 2 * pad) * (i / 4.0)
            painter.drawLine(pad, int(y), w - pad, int(y))

        def draw_series(data, color: QColor, fill_alpha: int):
            pts = list(data)
            if len(pts) < 2:
                return
            dx = (w - 2 * pad) / (len(pts) - 1)
            path = QPainterPath()
            fill_path = QPainterPath()
            for idx, val in enumerate(pts):
                x = pad + idx * dx
                y = (h - pad) - (val / 100.0) * (h - 2 * pad)
                if idx == 0:
                    path.moveTo(x, y)
                    fill_path.moveTo(x, h - pad)
                    fill_path.lineTo(x, y)
                else:
                    path.lineTo(x, y)
                    fill_path.lineTo(x, y)
            fill_path.lineTo(w - pad, h - pad)
            fill_path.closeSubpath()

            fc = QColor(color)
            fc.setAlpha(fill_alpha)
            painter.fillPath(fill_path, QBrush(fc))
            painter.setPen(QPen(color, 1.8))
            painter.drawPath(path)

        draw_series(self._ram_hist, self._secondary, 22)
        draw_series(self._cpu_hist, self._accent, 34)

        painter.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        painter.setPen(self._accent)
        painter.drawText(pad + 4, 15, f"● CPU {self._cpu_hist[-1]:.0f}%")
        painter.setPen(self._secondary)
        painter.drawText(pad + 86, 15, f"● RAM {self._ram_hist[-1]:.0f}%")

        painter.end()


class StatusPulseLabel(QLabel):
    """Animated HUD telemetry status pill (3.7)."""

    def __init__(self, parent=None):
        super().__init__("ONLINE // STANDBY", parent)
        self.setObjectName("status_pill")
        self._base_text = "ONLINE // STANDBY"
        self._animate = False
        self._dots = 0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(340)

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
