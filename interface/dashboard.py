"""System Resource Monitor Dashboard for JARVIS (3.8)."""

import os
import psutil

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QGridLayout,
    QLabel,
    QProgressBar,
    QFrame,
)
from PySide6.QtCore import QTimer


class Dashboard(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("JARVIS System Monitor")

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("SYSTEM RESOURCE MONITOR")
        title.setObjectName("page_title")
        layout.addWidget(title)

        card = QFrame()
        card.setObjectName("card")
        grid = QGridLayout(card)
        grid.setSpacing(12)
        layout.addWidget(card)

        # CPU
        self.cpu_label = QLabel("CPU: 0%")
        self.cpu_bar = QProgressBar()

        # RAM
        self.ram_label = QLabel("RAM: 0%")
        self.ram_bar = QProgressBar()

        # Storage
        self.disk_label = QLabel("STORAGE: 0%")
        self.disk_bar = QProgressBar()

        # Battery & Network
        self.battery_label = QLabel("BATTERY: Checking...")
        self.net_label = QLabel("NETWORK: Checking...")

        grid.addWidget(self.cpu_label, 0, 0)
        grid.addWidget(self.cpu_bar, 0, 1)

        grid.addWidget(self.ram_label, 1, 0)
        grid.addWidget(self.ram_bar, 1, 1)

        grid.addWidget(self.disk_label, 2, 0)
        grid.addWidget(self.disk_bar, 2, 1)

        grid.addWidget(self.battery_label, 3, 0, 1, 2)
        grid.addWidget(self.net_label, 4, 0, 1, 2)
        layout.addStretch()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(1000)

        self.update_stats()

    def update_stats(self):
        # CPU usage
        cpu = psutil.cpu_percent(interval=None)
        self.cpu_label.setText(f"CPU: {cpu:.1f}%")
        self.cpu_bar.setValue(int(cpu))

        # RAM usage
        ram = psutil.virtual_memory()
        self.ram_label.setText(
            f"RAM: {ram.percent}% ({ram.used / (1024**3):.2f} / {ram.total / (1024**3):.1f} GB)"
        )
        self.ram_bar.setValue(int(ram.percent))

        # Disk usage
        disk_path = (
            os.environ.get("SystemDrive", "C:") + "\\"
            if os.name == "nt"
            else "/"
        )
        disk = psutil.disk_usage(disk_path)
        self.disk_label.setText(
            f"STORAGE ({disk_path}): {disk.percent}% ({disk.free / (1024**3):.1f} GB free)"
        )
        self.disk_bar.setValue(int(disk.percent))

        # Battery information
        battery = psutil.sensors_battery()
        if battery:
            charging = "Charging" if battery.power_plugged else "On Battery"
            self.battery_label.setText(f"BATTERY: {battery.percent:.0f}% | {charging}")
        else:
            self.battery_label.setText("BATTERY: Desktop / AC Power")

        # Network I/O
        io = psutil.net_io_counters()
        if io:
            self.net_label.setText(
                f"NETWORK: ↑ {io.bytes_sent / (1024**2):.1f} MB sent   |   ↓ {io.bytes_recv / (1024**2):.1f} MB received"
            )


SystemDashboard = Dashboard
