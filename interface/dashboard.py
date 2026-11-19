"""Holographic System Resource Telemetry Dashboard for JARVIS (3.8)."""

import os
import psutil

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QComboBox,
)
from PySide6.QtCore import QTimer, Qt

from interface.widgets import ArcGaugeWidget, TelemetryGraphWidget


class Dashboard(QWidget):
    """Iron Man HUD System Resource Monitor with circular Arc Gauges and live oscilloscope."""

    def __init__(self, accent="#00e5ff", parent=None):
        super().__init__(parent)
        self.setWindowTitle("J.A.R.V.I.S System Telemetry")
        self._accent = accent

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        title = QLabel("SYSTEM TELEMETRY // REAL-TIME DIAGNOSTICS")
        title.setObjectName("page_title")
        self.net_label = QLabel("NET: INIT...")
        self.net_label.setObjectName("hud_metric")
        self.net_label.setFixedHeight(26)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.net_label, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(header)

        # Row of 4 Circular Arc Gauges
        gauge_card = QFrame()
        gauge_card.setObjectName("hud_panel")
        gauge_row = QHBoxLayout(gauge_card)
        gauge_row.setSpacing(12)

        self.cpu_gauge = ArcGaugeWidget("CPU", accent=accent, size=116)
        self.ram_gauge = ArcGaugeWidget("RAM", accent=accent, size=116)
        self.disk_gauge = ArcGaugeWidget("STORAGE", accent=accent, size=116)
        self.bat_gauge = ArcGaugeWidget("POWER", accent=accent, size=116)

        for g in (self.cpu_gauge, self.ram_gauge, self.disk_gauge, self.bat_gauge):
            gauge_row.addWidget(g, 1, Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(gauge_card)

        # Live scrolling oscilloscope graph
        graph_card = QFrame()
        graph_card.setObjectName("card")
        gl = QVBoxLayout(graph_card)
        gl.setContentsMargins(10, 8, 10, 8)
        self.graph = TelemetryGraphWidget(accent=accent)
        gl.addWidget(self.graph)
        layout.addWidget(graph_card)

        # Top Processes Monitor
        proc_card = QFrame()
        proc_card.setObjectName("card")
        pl = QVBoxLayout(proc_card)
        pl.setContentsMargins(10, 8, 10, 8)
        pl.setSpacing(6)

        phdr = QHBoxLayout()
        ptitle = QLabel("TOP ACTIVE PROCESSES")
        ptitle.setObjectName("section_header")
        self.proc_sort = QComboBox()
        self.proc_sort.addItems(["Sort: RAM", "Sort: CPU"])
        self.proc_sort.setFixedWidth(120)
        self.proc_sort.currentTextChanged.connect(self._update_top_processes)
        phdr.addWidget(ptitle)
        phdr.addStretch()
        phdr.addWidget(self.proc_sort)
        pl.addLayout(phdr)

        self.proc_table = QTableWidget(0, 4)
        self.proc_table.setHorizontalHeaderLabels(["PID", "PROCESS", "CPU %", "RAM (MB)"])
        self.proc_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.proc_table.verticalHeader().setVisible(False)
        self.proc_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.proc_table.setMaximumHeight(145)
        pl.addWidget(self.proc_table)
        layout.addWidget(proc_card)

        self._tick_count = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(1000)

        self.update_stats()

    def set_accent(self, hex_color: str):
        self._accent = hex_color
        for g in (self.cpu_gauge, self.ram_gauge, self.disk_gauge, self.bat_gauge):
            g.set_accent(hex_color)
        self.graph.set_accent(hex_color)

    def update_stats(self):
        cpu = psutil.cpu_percent(interval=None)
        self.cpu_gauge.set_value(cpu, f"{psutil.cpu_count(logical=True)} CORES")

        ram = psutil.virtual_memory()
        self.ram_gauge.set_value(ram.percent, f"{ram.used / (1024**3):.1f}/{ram.total / (1024**3):.0f}G")

        disk_path = (
            os.environ.get("SystemDrive", "C:") + "\\"
            if os.name == "nt"
            else "/"
        )
        disk = psutil.disk_usage(disk_path)
        self.disk_gauge.set_value(disk.percent, f"{disk.free / (1024**3):.0f}G FREE")

        battery = psutil.sensors_battery()
        if battery:
            pwr = "CHG" if battery.power_plugged else "BAT"
            self.bat_gauge.set_value(battery.percent, pwr)
        else:
            self.bat_gauge.set_value(100, "AC PWR")

        self.graph.push_sample(cpu, ram.percent)

        io = psutil.net_io_counters()
        if io:
            self.net_label.setText(
                f"NET ↑ {io.bytes_sent / (1024**2):.0f}MB  ↓ {io.bytes_recv / (1024**2):.0f}MB"
            )

        self._tick_count += 1
        if self._tick_count % 2 == 1:
            self._update_top_processes()

    def _update_top_processes(self):
        try:
            procs = []
            for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]):
                info = p.info
                if not info or not info.get("name"):
                    continue
                mem_mb = (info["memory_info"].rss / (1024**2)) if info.get("memory_info") else 0.0
                cpu_pct = info.get("cpu_percent") or 0.0
                procs.append((info["pid"], info["name"], cpu_pct, mem_mb))
            sort_idx = 2 if "CPU" in self.proc_sort.currentText() else 3
            procs.sort(key=lambda x: x[sort_idx], reverse=True)
            top = procs[:6]
            self.proc_table.setRowCount(len(top))
            for r, (pid, name, cpu_p, ram_m) in enumerate(top):
                self.proc_table.setItem(r, 0, QTableWidgetItem(str(pid)))
                self.proc_table.setItem(r, 1, QTableWidgetItem(str(name)))
                self.proc_table.setItem(r, 2, QTableWidgetItem(f"{cpu_p:.1f}%"))
                self.proc_table.setItem(r, 3, QTableWidgetItem(f"{ram_m:.0f}"))
        except Exception:
            pass

    def shutdown(self):
        self.timer.stop()
        for g in (self.cpu_gauge, self.ram_gauge, self.disk_gauge, self.bat_gauge):
            g.stop_animation()


SystemDashboard = Dashboard
