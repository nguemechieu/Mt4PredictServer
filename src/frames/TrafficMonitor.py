from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLabel
from PySide6.QtGui import QFont
from PySide6.QtCore import QTimer
import os
LOG_PATH = os.path.join("src", "logs", "predict_server.log")

class TrafficMonitor(QWidget):


    def __init__(self, controller=None):
        super().__init__()
        self.LOG_PATH = LOG_PATH
        self.setWindowTitle("📡 MT4 <-> Traffic Monitor")
        self.setMinimumSize(700, 400)
        self.controller = controller

        layout = QVBoxLayout()
        self.label = QLabel("Real-Time Traffic Log (MT4 <-> Python)")
        self.label.setFont(QFont("Segoe UI", 14))
        layout.addWidget(self.label)

        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setFont(QFont("Courier New", 10))
        layout.addWidget(self.text_area)

        self.setLayout(layout)
        self.last_log_size = 0
        self.last_inode = None

        # Auto-refresh every second
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_log)
        self.timer.start(1000)

    def update_log(self):
        try:
            if not os.path.exists(self.LOG_PATH):
                return

            # Reset if file rotated or truncated
            stat_info = os.stat(self.LOG_PATH)
            if self.last_inode is None or self.last_inode != stat_info.st_ino or stat_info.st_size < self.last_log_size:
                self.last_inode = stat_info.st_ino
                self.last_log_size = 0

            with open(self.LOG_PATH, "r") as f:
                f.seek(self.last_log_size)
                new_data = f.read()
                self.last_log_size = f.tell()

            if new_data:
                for line in new_data.strip().splitlines():
                    self.text_area.append(line)
                self.text_area.verticalScrollBar().setValue(
                    self.text_area.verticalScrollBar().maximum()
                )

        except Exception as e:
            self.text_area.append(f"❌ Log read error: {e.args.__str__()}")
