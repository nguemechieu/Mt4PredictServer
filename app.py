import sys
import subprocess
import logging
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QTextEdit,
    QMessageBox,
    QLabel,
    QHBoxLayout,
    QSizePolicy,
)
from PyQt5.QtCore import QTimer, Qt, QObject, pyqtSignal
from PyQt5.QtGui import QFont, QIcon

# Path to your Python server
SERVER_SCRIPT = "mt4PredictServer.py"


# --- Logging system that outputs to GUI ---
class QtSignalEmitter(QObject):
    log_signal = pyqtSignal(str)


class QtLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.emitter = QtSignalEmitter()

    def emit(self, record):
        msg = self.format(record)
        self.emitter.log_signal.emit(msg)

class ServerTerminal(QWidget):
    def __init__(self):
        super().__init__()
        self.process = None
        self.setWindowTitle("Mt4PredictServer       -----------------           Control Panel")
        self.setWindowIcon(QIcon("logo.png"))
        self.setGeometry(400, 200, 720, 500)
        self.setStyleSheet(self.dark_theme_stylesheet())
        self.init_ui()
        self.init_logger()

    def init_ui(self):
        layout = QVBoxLayout()

        self.status_label = QLabel(
            "🔌 Status: <b><span style='color: red;'>Stopped</span></b>"
        )
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Segoe UI", 11))

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Courier New", 10))
        self.output.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.start_btn = QPushButton("Start Server")
        self.stop_btn = QPushButton("Stop Server")
        self.stop_btn.setEnabled(False)

        self.start_btn.clicked.connect(self.start_server)
        self.stop_btn.clicked.connect(self.stop_server)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)

        layout.addWidget(self.status_label)
        layout.addWidget(self.output)
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.timer = QTimer()
        self.timer.timeout.connect(self.read_output)

    def init_logger(self):
        self.logger = logging.getLogger("Mt4Logger")
        self.logger.setLevel(logging.DEBUG)

        qt_handler = QtLogHandler()
        qt_handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
        qt_handler.emitter.log_signal.connect(self.append_log)

        self.logger.addHandler(qt_handler)

        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
        self.logger.addHandler(console)

        file = logging.FileHandler("predict_server.log")
        file.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
        self.logger.addHandler(file)

    def append_log(self, msg):
        self.output.append(msg)
        self.output.verticalScrollBar().setValue(
            self.output.verticalScrollBar().maximum()
        )

    def start_server(self):
        if self.process and self.process.poll() is None:
            QMessageBox.warning(
                self, "Already Running", "The server is already running."
            )
            return
        try:
            self.process = subprocess.Popen(
                [sys.executable, SERVER_SCRIPT],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            self.status_label.setText(
                "🟢 Status: <b><span style='color: green;'>Running</span></b>"
            )
            self.logger.info("✅ Server started.")
            self.timer.start(100)
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "Startup Error", str(e))
            self.logger.error(f"❌ Failed to start server: {e}")

    def stop_server(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.logger.info("🛑 Server stopped.")
        else:
            self.logger.warning("⚠️ Server is not running.")
        self.status_label.setText(
            "🔌 Status: <b><span style='color: red;'>Stopped</span></b>"
        )
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.timer.stop()

    def read_output(self):
        if self.process and self.process.stdout:
            line = self.process.stdout.readline()
            if line:
                self.logger.info(line.strip())

    def closeEvent(self, event):
        if self.process and self.process.poll() is None:
            self.process.terminate()
        self.logger.info("👋 GUI closed.")
        event.accept()

    def dark_theme_stylesheet(self):
        return """
        QWidget {
            background-color: #1e1e1e;
            color: #dcdcdc;
        }
        QPushButton {
            background-color: #3c3c3c;
            border: 1px solid #555;
            padding: 10px;
            font-size: 14px;
            color: white;
        }
        QPushButton:hover {
            background-color: #505050;
        }
        QTextEdit {
            background-color: #262626;
            border: 1px solid #444;
            color: #c8c8c8;
        }
        QLabel {
            color: #cccccc;
        }
        """
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ServerTerminal()
    window.show()
    sys.exit(app.exec_())
