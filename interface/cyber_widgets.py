"""Cybernetic Sci-Fi HUD Widgets for J.A.R.V.I.S (Arc Reactor, Avatar, Waveform, Telemetry)."""

import math
import random
from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QFrame, QHBoxLayout, QVBoxLayout
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF, Signal, Property
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


class CyberRobotAvatar(QWidget):
    """Futuristic Robot Avatar with rotating arc-reactor rings, glowing headphones, and blinking cyan eyes."""

    clicked = Signal()

    def __init__(self, accent="#00d2ff", size=154, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("J.A.R.V.I.S Neural Core — Click to pulse")

        self._accent = QColor(accent)
        self._state = "idle"  # idle | thinking | speaking | listening | error
        self._angle_outer = 0.0
        self._angle_mid = 0.0
        self._glow_phase = 0.0
        self._ripple = 0.0

        # Organic eye blink animation
        self._blink_counter = 0
        self._is_blinking = False
        self._blink_height_factor = 1.0  # 1.0 (open) to 0.08 (closed)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)  # ~30 FPS

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
        self.clicked.emit()
        super().mousePressEvent(event)

    def _tick(self):
        speed = {
            "idle": 0.85,
            "listening": 2.2,
            "thinking": 3.6,
            "speaking": 2.5,
            "error": 1.6,
        }.get(self._state, 1.0)

        self._angle_outer = (self._angle_outer + speed * 0.8) % 360.0
        self._angle_mid = (self._angle_mid - speed * 1.5) % 360.0
        self._glow_phase = (self._glow_phase + 0.08 * speed) % math.tau

        if self._ripple > 0.0:
            self._ripple += 0.05
            if self._ripple >= 1.0:
                self._ripple = 0.0

        # Organic blinking logic (every ~120-180 ticks = ~4-6 seconds)
        self._blink_counter += 1
        if not self._is_blinking:
            if self._blink_counter > random.randint(110, 170):
                self._is_blinking = True
                self._blink_counter = 0
        else:
            # Quick blink cycle: close in 2 frames, open in 3 frames
            if self._blink_counter <= 2:
                self._blink_height_factor = max(0.1, 1.0 - self._blink_counter * 0.45)
            elif self._blink_counter <= 5:
                self._blink_height_factor = min(1.0, 0.1 + (self._blink_counter - 2) * 0.3)
            else:
                self._is_blinking = False
                self._blink_height_factor = 1.0
                self._blink_counter = 0

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0
        r = min(w, h) * 0.46

        accent = QColor("#ff334b") if self._state == "error" else QColor(self._accent)
        pulse = 0.5 + 0.5 * math.sin(self._glow_phase)

        # 1. Deep radial ambient cyan glow behind avatar
        glow_rad = QRadialGradient(QPointF(cx, cy), r * 1.12)
        glow_alpha = int(45 + 35 * pulse) if self._state in ("speaking", "listening") else int(25 + 20 * pulse)
        glow_rad.setColorAt(0.0, QColor(accent.red(), accent.green(), accent.blue(), glow_alpha))
        glow_rad.setColorAt(0.65, QColor(accent.red(), accent.green(), accent.blue(), 10))
        glow_rad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(glow_rad))
        painter.drawEllipse(QPointF(cx, cy), r * 1.12, r * 1.12)

        # 2. Outer Calibration Ticks (Rotating Arc Reactor)
        tick_r1 = r * 0.94
        tick_r2 = r * 1.01
        tick_pen = QColor(accent)
        tick_pen.setAlpha(int(70 + 40 * pulse))
        painter.setPen(QPen(tick_pen, 1.2))
        for i in range(36):
            ang = math.radians(i * 10.0 + self._angle_outer * 0.35)
            is_major = (i % 3 == 0)
            extra = 3.0 if is_major else 0.0
            p1 = QPointF(cx + math.cos(ang) * (tick_r1 - extra), cy + math.sin(ang) * (tick_r1 - extra))
            p2 = QPointF(cx + math.cos(ang) * tick_r2, cy + math.sin(ang) * tick_r2)
            painter.drawLine(p1, p2)

        # 3. Concentric Arc Reactor segmented rings
        ring_rect = QRectF(cx - r * 0.88, cy - r * 0.88, r * 1.76, r * 1.76)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        arc_pen = QPen(accent, 2.4)
        arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(arc_pen)
        for i in range(3):
            painter.drawArc(ring_rect, int((self._angle_outer + i * 120.0) * 16), int(76 * 16))

        mid_rect = QRectF(cx - r * 0.74, cy - r * 0.74, r * 1.48, r * 1.48)
        mid_col = QColor(accent)
        mid_col.setAlpha(int(100 + 50 * pulse))
        painter.setPen(QPen(mid_col, 1.4))
        for i in range(4):
            painter.drawArc(mid_rect, int((self._angle_mid + i * 90.0) * 16), int(52 * 16))

        # 4. Avatar Base Plate (Dark Matte Cybernetic Circle)
        inner_r = r * 0.68
        base_grad = QLinearGradient(0, cy - inner_r, 0, cy + inner_r)
        base_grad.setColorAt(0.0, QColor("#111a2c"))
        base_grad.setColorAt(1.0, QColor("#080c14"))
        painter.setBrush(QBrush(base_grad))
        border_col = QColor(accent)
        border_col.setAlpha(160)
        painter.setPen(QPen(border_col, 1.6))
        painter.drawEllipse(QPointF(cx, cy), inner_r, inner_r)

        # 5. Draw the Cyber Robot Head & Headphones
        # Center offsets for head drawing
        head_cx = cx
        head_cy = cy + inner_r * 0.05
        head_scale = inner_r * 0.88

        # --- A. Neck & Chest Collar ---
        collar_path = QPainterPath()
        c_top = head_cy + head_scale * 0.52
        c_bot = cy + inner_r * 0.96
        c_w = head_scale * 0.62
        collar_path.moveTo(head_cx - c_w * 0.5, c_top)
        collar_path.lineTo(head_cx + c_w * 0.5, c_top)
        collar_path.lineTo(head_cx + c_w * 0.85, c_bot)
        collar_path.lineTo(head_cx - c_w * 0.85, c_bot)
        collar_path.closeSubpath()
        collar_grad = QLinearGradient(0, c_top, 0, c_bot)
        collar_grad.setColorAt(0.0, QColor("#141d2f"))
        collar_grad.setColorAt(1.0, QColor("#0a0f1a"))
        painter.setBrush(QBrush(collar_grad))
        painter.setPen(QPen(QColor(accent.red(), accent.green(), accent.blue(), 140), 1.2))
        painter.drawPath(collar_path)

        # Collar center tech line
        painter.setPen(QPen(accent, 1.5))
        painter.drawLine(QPointF(head_cx, c_top + 2), QPointF(head_cx, c_bot - 4))

        # --- B. Headphone Arch (Behind Head) ---
        arch_r = head_scale * 0.68
        arch_rect = QRectF(head_cx - arch_r, head_cy - arch_r * 0.95, arch_r * 2, arch_r * 1.5)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor("#1e293b"), 4.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawArc(arch_rect, 35 * 16, 110 * 16)
        painter.setPen(QPen(accent, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawArc(arch_rect, 45 * 16, 90 * 16)

        # --- C. Robot Helmet / Skull Base ---
        head_path = QPainterPath()
        hw = head_scale * 0.54
        hh = head_scale * 0.62
        head_rect = QRectF(head_cx - hw, head_cy - hh * 0.68, hw * 2, hh * 1.22)
        head_path.addRoundedRect(head_rect, hw * 0.52, hh * 0.54)

        head_grad = QLinearGradient(0, head_cy - hh * 0.68, 0, head_cy + hh * 0.6)
        head_grad.setColorAt(0.0, QColor("#1c2538"))
        head_grad.setColorAt(0.5, QColor("#131a28"))
        head_grad.setColorAt(1.0, QColor("#0c111c"))
        painter.setBrush(QBrush(head_grad))
        painter.setPen(QPen(QColor("#2d3b55"), 1.4))
        painter.drawPath(head_path)

        # Visor glass faceplate (dark glossy curved shield)
        visor_path = QPainterPath()
        vw = hw * 0.78
        vh = hh * 0.44
        visor_rect = QRectF(head_cx - vw, head_cy - vh * 0.48, vw * 2, vh * 1.1)
        visor_path.addRoundedRect(visor_rect, 8.0, 8.0)
        v_grad = QLinearGradient(0, head_cy - vh * 0.5, 0, head_cy + vh * 0.6)
        v_grad.setColorAt(0.0, QColor("#080c14"))
        v_grad.setColorAt(0.7, QColor("#04060a"))
        v_grad.setColorAt(1.0, QColor("#0a0f1c"))
        painter.setBrush(QBrush(v_grad))
        painter.setPen(QPen(QColor(accent.red(), accent.green(), accent.blue(), 110), 1.0))
        painter.drawPath(visor_path)

        # --- D. Glowing Cybernetic Visor Eyes (with Organic Blink!) ---
        eye_w = vw * 0.38
        eye_h = max(1.2, vh * 0.28 * self._blink_height_factor)
        eye_y = head_cy - eye_h * 0.5 - 2
        eye_spacing = vw * 0.22

        # Outer Eye Glow
        eye_glow_col = QColor(accent)
        eye_glow_col.setAlpha(int(200 + 55 * pulse))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(eye_glow_col))

        # Left Eye
        left_eye_rect = QRectF(head_cx - eye_spacing - eye_w, eye_y, eye_w, eye_h)
        painter.drawRoundedRect(left_eye_rect, eye_h * 0.45, eye_h * 0.45)
        # Right Eye
        right_eye_rect = QRectF(head_cx + eye_spacing, eye_y, eye_w, eye_h)
        painter.drawRoundedRect(right_eye_rect, eye_h * 0.45, eye_h * 0.45)

        # White Core Eye Hotspot (Crisp Cinema Bloom)
        core_col = QColor("#ffffff")
        core_col.setAlpha(int(220 * self._blink_height_factor))
        painter.setBrush(QBrush(core_col))
        core_h = max(0.8, eye_h * 0.45)
        core_w = eye_w * 0.55
        painter.drawRoundedRect(
            QRectF(head_cx - eye_spacing - eye_w * 0.78, eye_y + (eye_h - core_h) / 2.0, core_w, core_h),
            core_h * 0.4,
            core_h * 0.4,
        )
        painter.drawRoundedRect(
            QRectF(head_cx + eye_spacing + eye_w * 0.22, eye_y + (eye_h - core_h) / 2.0, core_w, core_h),
            core_h * 0.4,
            core_h * 0.4,
        )

        # --- E. Over-Ear Headphones (Left & Right) ---
        hp_w = head_scale * 0.20
        hp_h = head_scale * 0.46
        hp_y = head_cy - hp_h * 0.52

        for side_sign, hp_x in ((-1, head_cx - hw - hp_w * 0.72), (1, head_cx + hw - hp_w * 0.28)):
            # Ear cup body
            hp_rect = QRectF(hp_x, hp_y, hp_w, hp_h)
            hp_grad = QLinearGradient(hp_x, hp_y, hp_x + hp_w, hp_y + hp_h)
            hp_grad.setColorAt(0.0, QColor("#1e293b"))
            hp_grad.setColorAt(0.5, QColor("#0f172a"))
            hp_grad.setColorAt(1.0, QColor("#020617"))
            painter.setBrush(QBrush(hp_grad))
            painter.setPen(QPen(QColor(accent.red(), accent.green(), accent.blue(), 130), 1.2))
            painter.drawRoundedRect(hp_rect, 6.0, 6.0)

            # Glowing status ring on ear cup
            center_y = hp_y + hp_h * 0.5
            ring_cx = hp_x + hp_w * 0.5
            ring_r = hp_w * 0.36
            ring_col = QColor(accent)
            ring_col.setAlpha(int(160 + 95 * pulse))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(ring_col, 1.8))
            painter.drawEllipse(QPointF(ring_cx, center_y), ring_r, ring_r)
            # Center LED pip
            painter.setBrush(QBrush(ring_col))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(ring_cx, center_y), 1.8, 1.8)

        # 6. Click Shockwave Ripple
        if self._ripple > 0.0:
            rip_r = r * (0.35 + self._ripple * 0.85)
            rip_col = QColor(accent)
            rip_col.setAlpha(int((1.0 - self._ripple) * 210))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(rip_col, 2.2))
            painter.drawEllipse(QPointF(cx, cy), rip_r, rip_r)

        painter.end()

    def stop_animation(self):
        self._timer.stop()


class SymmetricalAudioWaveform(QWidget):
    """Symmetrical dual-wing audio frequency waveform equalizer flanking the center microphone."""

    def __init__(self, accent="#00d2ff", bar_count=18, bars=None, height=54, parent=None):
        super().__init__(parent)
        self.setFixedHeight(height)
        self.setMinimumWidth(260)
        self._accent = QColor(accent)
        self._bar_count = bars if bars is not None else bar_count
        self._active = False
        self._phase = 0.0
        self._levels = [0.12] * self._bar_count

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)

    def set_accent(self, hex_color: str):
        self._accent = QColor(hex_color)
        self.update()

    def set_active(self, active: bool):
        self._active = bool(active)

    def _tick(self):
        self._phase += 0.38 if self._active else 0.08
        for i in range(self._bar_count):
            # Outward tapering curve (highest near center, tapering gently outward)
            center_weight = 1.0 - (i / float(self._bar_count)) * 0.65
            if self._active:
                harmonic = (
                    0.45 * math.sin(self._phase + i * 0.5)
                    + 0.35 * math.cos(self._phase * 1.8 - i * 0.7)
                    + 0.20 * math.sin(self._phase * 2.6 + i * 1.2)
                )
                target = max(0.18, min(1.0, (0.55 + 0.45 * harmonic) * center_weight))
            else:
                harmonic = 0.5 + 0.5 * math.sin(self._phase + i * 0.32)
                target = 0.08 + 0.12 * harmonic * center_weight
            self._levels[i] = self._levels[i] * 0.45 + target * 0.55
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        mid_y = h / 2.0
        cx = w / 2.0

        # Leave gap in middle for center microphone button (~90px)
        center_gap = 48.0
        wing_w = (w - center_gap * 2) / 2.0
        bar_gap = 3.2
        bar_w = max(2.6, (wing_w - bar_gap * self._bar_count) / self._bar_count)

        # Subtle baseline
        base_line = QColor(self._accent)
        base_line.setAlpha(26)
        painter.setPen(QPen(base_line, 1))
        painter.drawLine(8, int(mid_y), int(cx - center_gap + 8), int(mid_y))
        painter.drawLine(int(cx + center_gap - 8), int(mid_y), w - 8, int(mid_y))

        painter.setPen(Qt.PenStyle.NoPen)
        for i, lvl in enumerate(self._levels):
            bar_h = max(3.0, lvl * (h - 8))
            # Left Wing (radiating outward from center gap towards left edge)
            lx = (cx - center_gap) - (i + 1) * (bar_w + bar_gap)
            ly = mid_y - bar_h / 2.0

            # Right Wing (radiating outward from center gap towards right edge)
            rx = (cx + center_gap) + i * (bar_w + bar_gap)
            ry = mid_y - bar_h / 2.0

            # Gradient bar color (white/cyan hotspot at center)
            alpha = int(240 if self._active else 90 + 60 * (1.0 - i / float(self._bar_count)))
            col = QColor(self._accent)
            col.setAlpha(min(255, alpha))
            painter.setBrush(QBrush(col))

            if lx >= 2:
                painter.drawRoundedRect(QRectF(lx, ly, bar_w, bar_h), bar_w * 0.5, bar_w * 0.5)
            if rx + bar_w <= w - 2:
                painter.drawRoundedRect(QRectF(rx, ry, bar_w, bar_h), bar_w * 0.5, bar_w * 0.5)

        painter.end()

    def stop_animation(self):
        self._timer.stop()


class CyberWaveformWing(QWidget):
    """One symmetrical wing of audio frequency equalizer bars flanking the microphone."""

    def __init__(self, accent="#00d2ff", side="left", bar_count=18, height=64, parent=None):
        super().__init__(parent)
        self.setFixedHeight(height)
        self.setMinimumWidth(120)
        self._accent = QColor(accent)
        self._side = side  # "left" (radiates right-to-left) or "right" (radiates left-to-right)
        self._bar_count = bar_count
        self._active = False
        self._phase = 0.0
        self._levels = [0.12] * bar_count

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)

    def set_accent(self, hex_color: str):
        self._accent = QColor(hex_color)
        self.update()

    def set_active(self, active: bool):
        self._active = bool(active)

    def _tick(self):
        self._phase += 0.38 if self._active else 0.08
        for i in range(self._bar_count):
            center_weight = 1.0 - (i / float(self._bar_count)) * 0.72
            if self._active:
                harmonic = (
                    0.45 * math.sin(self._phase + i * 0.5)
                    + 0.35 * math.cos(self._phase * 1.8 - i * 0.7)
                    + 0.20 * math.sin(self._phase * 2.6 + i * 1.2)
                )
                target = max(0.18, min(1.0, (0.55 + 0.45 * harmonic) * center_weight))
            else:
                harmonic = 0.5 + 0.5 * math.sin(self._phase + i * 0.32)
                target = 0.08 + 0.14 * harmonic * center_weight
            self._levels[i] = self._levels[i] * 0.45 + target * 0.55
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        mid_y = h / 2.0

        bar_gap = 4.0
        bar_w = max(3.0, (w - bar_gap * (self._bar_count + 1)) / float(self._bar_count))

        # Baseline
        base_line = QColor(self._accent)
        base_line.setAlpha(28)
        painter.setPen(QPen(base_line, 1))
        painter.drawLine(0, int(mid_y), w, int(mid_y))

        painter.setPen(Qt.PenStyle.NoPen)
        for i, lvl in enumerate(self._levels):
            bar_h = max(3.5, lvl * (h - 10))
            if self._side == "left":
                x = (w - (i + 1) * (bar_w + bar_gap))
            else:
                x = (i * (bar_w + bar_gap))

            y = mid_y - bar_h / 2.0
            alpha = int(240 if self._active else 90 + 70 * (1.0 - i / float(self._bar_count)))
            col = QColor(self._accent)
            col.setAlpha(min(255, max(30, alpha)))
            painter.setBrush(QBrush(col))
            painter.drawRoundedRect(QRectF(x, y, bar_w, bar_h), bar_w * 0.5, bar_w * 0.5)

        painter.end()

    def stop_animation(self):
        self._timer.stop()


class CyberMicButton(QWidget):
    """Glowing circular microphone button with expanding pulse ring and status caption."""

    clicked = Signal()

    def __init__(self, accent="#00d2ff", size=72, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size + 22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._accent = QColor(accent)
        self._active = False
        self._hovered = False
        self._phase = 0.0
        self._ripple = 0.0
        self._label = "Listening..."

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)

    def set_accent(self, hex_color: str):
        self._accent = QColor(hex_color)
        self.update()

    def set_active(self, active: bool, label: str = "Listening..."):
        self._active = bool(active)
        self._label = label
        if active:
            self._ripple = 0.05
        self.update()

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self._ripple = 0.05
        self.clicked.emit()
        super().mousePressEvent(event)

    def _tick(self):
        speed = 2.4 if self._active else (1.4 if self._hovered else 0.8)
        self._phase = (self._phase + 0.08 * speed) % math.tau
        if self._ripple > 0.0:
            self._ripple += 0.04
            if self._ripple >= 1.0:
                self._ripple = 0.05 if self._active else 0.0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        button_size = w
        cx = w / 2.0
        cy = button_size / 2.0
        r = button_size * 0.38

        pulse = 0.5 + 0.5 * math.sin(self._phase)
        accent = QColor(self._accent)

        # 1. Ripple pulse ring
        if self._ripple > 0.0 or self._active:
            rip_r = r * (1.0 + (self._ripple if self._ripple > 0 else pulse * 0.35) * 0.75)
            rip_alpha = int((1.0 - (self._ripple if self._ripple > 0 else pulse * 0.35)) * 180)
            rip_col = QColor(accent)
            rip_col.setAlpha(max(0, rip_alpha))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(rip_col, 2.0))
            painter.drawEllipse(QPointF(cx, cy), rip_r, rip_r)

        # 2. Outer ambient halo
        halo = QRadialGradient(QPointF(cx, cy), r * 1.35)
        halo_alpha = int(90 + 65 * pulse) if (self._active or self._hovered) else int(45 + 30 * pulse)
        halo.setColorAt(0.0, QColor(accent.red(), accent.green(), accent.blue(), halo_alpha))
        halo.setColorAt(0.65, QColor(accent.red(), accent.green(), accent.blue(), 20))
        halo.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(halo))
        painter.drawEllipse(QPointF(cx, cy), r * 1.35, r * 1.35)

        # 3. Main button disc (Gradient Dark Glass with Neon Border)
        disc_grad = QLinearGradient(0, cy - r, 0, cy + r)
        if self._active:
            disc_grad.setColorAt(0.0, QColor(accent.red(), accent.green(), accent.blue(), 180))
            disc_grad.setColorAt(1.0, QColor("#005288"))
        else:
            disc_grad.setColorAt(0.0, QColor("#121b2d"))
            disc_grad.setColorAt(1.0, QColor("#080c16"))
        painter.setBrush(QBrush(disc_grad))

        disc_border = QColor(accent)
        disc_border.setAlpha(255 if (self._active or self._hovered) else 180)
        painter.setPen(QPen(disc_border, 2.4))
        painter.drawEllipse(QPointF(cx, cy), r, r)

        # 4. Draw Vector Microphone Icon
        icon_col = QColor("#ffffff" if (self._active or self._hovered) else accent)
        painter.setPen(QPen(icon_col, 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.setBrush(QBrush(icon_col))

        # Mic capsule
        mw = r * 0.34
        mh = r * 0.62
        mic_rect = QRectF(cx - mw * 0.5, cy - mh * 0.65, mw, mh)
        painter.drawRoundedRect(mic_rect, mw * 0.5, mw * 0.5)

        # Mic outer crescent / stand
        painter.setBrush(Qt.BrushStyle.NoBrush)
        crescent_r = mw * 1.05
        crescent_rect = QRectF(cx - crescent_r, cy - mh * 0.35, crescent_r * 2, crescent_r * 1.8)
        painter.drawArc(crescent_rect, 0 * 16, -180 * 16)

        # Mic vertical stem & base bar
        stem_top = cy + crescent_r * 0.55
        stem_bot = stem_top + r * 0.22
        painter.drawLine(QPointF(cx, stem_top), QPointF(cx, stem_bot))
        painter.drawLine(QPointF(cx - mw * 0.6, stem_bot), QPointF(cx + mw * 0.6, stem_bot))

        # 5. Status Caption Underneath Button
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        text_col = QColor(accent if self._active else "#8ea3bf")
        painter.setPen(text_col)
        painter.drawText(QRectF(0, button_size + 2, w, 18), Qt.AlignmentFlag.AlignCenter, self._label)

        painter.end()

    def stop_animation(self):
        self._timer.stop()


class CyberGlowProgressBar(QWidget):
    """Sleek animated horizontal progress bar with smooth value glide and glowing gradient fill."""

    def __init__(self, label="CPU Usage", accent="#00d2ff", is_gradient=False, parent=None):
        super().__init__(parent)
        self.setFixedHeight(38)
        self._label = label
        self._accent = QColor(accent)
        self._is_gradient = is_gradient  # e.g. Purple -> Cyan gradient for RAM
        self._target_value = 0.0
        self._display_value = 0.0

        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._step)
        self._anim_timer.start(33)

    def set_value(self, value: float):
        self._target_value = max(0.0, min(100.0, float(value)))

    def set_accent(self, hex_color: str):
        self._accent = QColor(hex_color)
        self.update()

    def _step(self):
        if abs(self._display_value - self._target_value) > 0.15:
            self._display_value += (self._target_value - self._display_value) * 0.24
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()

        # Top label row: Label on left, percentage on right
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        painter.setPen(QColor("#c5d4e8"))
        painter.drawText(QRectF(0, 0, w * 0.6, 16), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self._label)

        pct_str = f"{int(round(self._display_value))}%"
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.setPen(QColor("#ffffff"))
        painter.drawText(QRectF(w * 0.5, 0, w * 0.5, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, pct_str)

        # Track bar (bottom)
        bar_y = 22.0
        bar_h = 7.0
        track_rect = QRectF(0, bar_y, w, bar_h)

        # Dark glass track background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#131a28")))
        painter.drawRoundedRect(track_rect, bar_h * 0.5, bar_h * 0.5)

        # Active glowing fill
        fill_w = max(bar_h, (self._display_value / 100.0) * w)
        fill_rect = QRectF(0, bar_y, fill_w, bar_h)

        fill_grad = QLinearGradient(0, bar_y, fill_w, bar_y)
        if self._is_gradient:
            fill_grad.setColorAt(0.0, QColor("#a855f7"))  # Neon Purple
            fill_grad.setColorAt(1.0, QColor("#00d2ff"))  # Neon Cyan
        else:
            fill_grad.setColorAt(0.0, QColor("#0088ff"))  # Electric Blue
            fill_grad.setColorAt(1.0, QColor(self._accent))  # Vibrant Cyan

        painter.setBrush(QBrush(fill_grad))
        painter.drawRoundedRect(fill_rect, bar_h * 0.5, bar_h * 0.5)

        # Glow pip at head of progress
        if self._display_value > 2:
            pip_col = QColor("#ffffff")
            painter.setBrush(QBrush(pip_col))
            painter.drawEllipse(QPointF(fill_w - bar_h * 0.5, bar_y + bar_h * 0.5), 1.8, 1.8)

        painter.end()

    def stop_animation(self):
        self._anim_timer.stop()


class CyberQuickActionButton(QPushButton):
    """Sleek rounded Quick Action button with vibrant colored icon, hover glow, and smooth elevation."""

    def __init__(self, title: str, icon_symbol: str, icon_color="#00d2ff", parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._title = title
        self._icon_symbol = icon_symbol
        self._icon_color = QColor(icon_color)
        self._hover = False

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        rect = QRectF(1, 1, w - 2, h - 2)

        # Card body
        bg_col = QColor("#141d2f" if self._hover else "#0d1422")
        border_col = QColor(self._icon_color if self._hover else QColor(255, 255, 255, 30))
        border_width = 1.6 if self._hover else 1.0

        painter.setBrush(QBrush(bg_col))
        painter.setPen(QPen(border_col, border_width))
        painter.drawRoundedRect(rect, 10.0, 10.0)

        # Icon pill on left
        icon_size = 28.0
        icon_rect = QRectF(10, (h - icon_size) / 2.0, icon_size, icon_size)
        icon_bg = QColor(self._icon_color)
        icon_bg.setAlpha(42 if self._hover else 24)
        painter.setBrush(QBrush(icon_bg))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(icon_rect, 7.0, 7.0)

        # Icon symbol
        painter.setFont(QFont("Segoe UI Emoji", 13))
        painter.setPen(self._icon_color)
        painter.drawText(icon_rect, Qt.AlignmentFlag.AlignCenter, self._icon_symbol)

        # Title text
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        text_col = QColor("#ffffff" if self._hover else "#d2deed")
        painter.setPen(text_col)
        text_rect = QRectF(48, 0, w - 56, h)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self._title)

        painter.end()
