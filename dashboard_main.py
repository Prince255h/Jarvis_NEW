
import sys

from PySide6.QtWidgets import QApplication
from interface.dashboard import Dashboard


app = QApplication(sys.argv)

dashboard = Dashboard()
dashboard.resize(750, 350)
dashboard.show()

sys.exit(app.exec())
