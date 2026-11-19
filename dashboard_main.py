"""Standalone launcher for the J.A.R.V.I.S System Telemetry Dashboard."""

import sys
from PySide6.QtWidgets import QApplication
from interface.dashboard import Dashboard


def main():
    app = QApplication(sys.argv)
    dashboard = Dashboard()
    dashboard.resize(820, 420)
    dashboard.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
