from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLabel
from PyQt5.QtGui import QFont
from PyQt5.QtCore import QTimer
import os

class TrafficMonitor(QWidget):
    LOG_PATH = "predict_server.log"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📡 MT4 <-> DLL Traffic Monitor")
        self.setMinimumSize(700, 400)

        layout = QVBoxLayout()
        self.label = QLabel("Real-Time Traffic Log (DLL <-> Python)")
        self.label.setFont(QFont("Segoe UI", 14))
        layout.addWidget(self.label)

        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setFont(QFont("Courier New", 10))
        layout.addWidget(self.text_area)

        self.setLayout(layout)
        self.last_log_size = 0

        # Auto-refresh every second
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_log)
        self.timer.start(1000)

    def update_log(self):
        try:
            if not os.path.exists(self.LOG_PATH):
                return

            with open(self.LOG_PATH, "r", encoding="utf-8") as f:
                f.seek(self.last_log_size)
                new_data = f.read()
                self.last_log_size = f.tell()

            if new_data:
                self.text_area.append(new_data.strip())
                self.text_area.verticalScrollBar().setValue(self.text_area.verticalScrollBar().maximum())

        except Exception as e:
            self.text_area.append(f"❌ Log read error: {e}")
