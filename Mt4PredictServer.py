import io
import json
import logging
import os
import socket
import subprocess
import sys
import uuid

import keras
from PySide6.QtCore import Signal, QThread, QTimer, Qt, QObject
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QTextEdit, QPushButton,
    QMessageBox, QHBoxLayout, QTabWidget
)
from src.server.server import PredictServer

from src.components.AccountInfo import AccountInfo
from src.components.AccountMetrics import AccountMetrics
from src.components.ExecuteCommand import ExecuteCommand
from src.components.GPUMonitor import GPUMonitor
from src.components.GPUMonitorChart import GPUMonitorChart
from src.components.PositionHistory import PositionHistory
from src.components.TrafficMonitor import TrafficMonitor
from src.components.predictionChart import PredictionChart
from src.components.tensorflow_metrics import TensorFlowMetricsTab

HOST = "127.0.0.1"
PORT = 50052
LOG_PATH = "src/logs/predict_server.log"


# --- Force UTF-8 encoding ---
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


class OutputReaderThread(QThread):
    output_signal = Signal(str)

    def __init__(self, process):
        super().__init__()
        self.process = process
        self.running = True

    def run(self):
        while self.running and self.process.poll() is None:
            try:
                line = self.process.stdout.readline()
                if line:
                    self.output_signal.emit(line.strip())
            except Exception as e:
                self.output_signal.emit(f"[Reader Error] {e}")

    def stop(self):
        self.running = False
        self.quit()
        self.wait()


def dark_theme_stylesheet():
    return """
    QWidget { background-color: #1e1e1e; color: #dcdcdc; }
    QPushButton { background-color: #3c3c3c; border: 1px solid #555;
                  padding: 10px; font-size: 14px; color: white; }
    QPushButton:hover { background-color: #505050; }
    QTextEdit { background-color: #262626; border: 1px solid #444; color: #c8c8c8; }
    QLabel { color: #cccccc; }
    """


class Mt4PredictServer(QWidget):
    def __init__(self):
        super().__init__()
        self.status_label = None
        self.tabs = None
        self.logger = self.init_logger()
        # add this back
        self.predict_server = PredictServer(self)

        self.client_socket = None
        self.process = None
        self.reader_thread = None
        self.timer = None

        self.setWindowTitle("Mt4PredictServer - Unified Dashboard")
        self.setWindowIcon(QIcon("logo.png"))
        self.setGeometry(400, 200, 1200, 800)
        self.setStyleSheet(dark_theme_stylesheet())

        self.init_ui()
        self.init_timer()

    # -------------------------
    # UI
    # -------------------------
    def init_ui(self):
        layout = QVBoxLayout()
        self.tabs = QTabWidget()

        # === Server Tab ===
        self.status_label = QLabel("🔌 Status: <b><span style='color: red;'>Stopped</span></b>")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Segoe UI", 13))

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Courier New", 10))

        self.start_btn = QPushButton("Start Server")
        self.stop_btn = QPushButton("Stop Server")
        self.stop_btn.setEnabled(False)

        self.start_btn.clicked.connect(self.start_server)
        self.stop_btn.clicked.connect(self.stop_server)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)

        server_tab = QWidget()
        server_layout = QVBoxLayout()
        server_layout.addWidget(self.status_label)
        server_layout.addLayout(btn_layout)
        server_layout.addWidget(QLabel("🧾 Server Output Log:"))
        server_layout.addWidget(self.output)
        server_tab.setLayout(server_layout)

        # === Chart Tab ===
        chart_tab = QWidget()
        chart_layout = QVBoxLayout()
        self.chart = PredictionChart(self)
        chart_layout.addWidget(QLabel("📈 Prediction Chart:"))
        chart_layout.addWidget(self.chart)
        chart_tab.setLayout(chart_layout)

        # === GPU Tab ===
        gpu_tab = QWidget()
        gpu_layout = QVBoxLayout()
        self.gpu_status = QTextEdit()
        self.gpu_status.setReadOnly(True)
        self.gpu_status.setFont(QFont("Courier New", 10))
        self.gpu_status.setStyleSheet("background-color: #1E1E1E; color: #00FF00;")
        gpu_layout.addWidget(QLabel("🖥 GPU Status:"))
        gpu_layout.addWidget(self.gpu_status)
        gpu_tab.setLayout(gpu_layout)

        # === Model Info Tab ===
        model_tab = QWidget()
        model_layout = QVBoxLayout()
        self.model_info = QTextEdit()
        self.model_info.setReadOnly(True)
        reload_button = QPushButton("🔄 Reload Model")
        reload_button.clicked.connect(self.reload_model_summary)
        model_layout.addWidget(QLabel("🧠 TensorFlow Model Info:"))
        model_layout.addWidget(reload_button)
        model_layout.addWidget(self.model_info)
        model_tab.setLayout(model_layout)

        # === Tabs ===
        self.tabs.addTab(server_tab, "Server")
        self.tabs.addTab(TrafficMonitor(self), "Traffic Monitor")
        self.tabs.addTab(chart_tab, "Chart")
        self.tabs.addTab(GPUMonitor(self), "GPU")
        self.tabs.addTab(GPUMonitorChart(self), "GPU Monitor")
        self.tabs.addTab(model_tab, "Model")
        self.tensorflow_tab = TensorFlowMetricsTab()
        self.tabs.addTab(self.tensorflow_tab, "TensorFlow Metrics")
        self.tabs.addTab(ExecuteCommand(self), "Execute Command")
        self.tabs.addTab(AccountMetrics(self), "Account Metrics")
        self.tabs.addTab(AccountInfo(self), "Account Info")
        self.tabs.addTab(PositionHistory(self), "Positions History")

        layout.addWidget(self.tabs)
        self.setLayout(layout)
        self.reload_model_summary()

    # -------------------------
    # Networking (Client)
    # -------------------------
    def connect_to_server(self):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(3)
            self.client_socket.connect((HOST, PORT))
            self.logger.info("✅ Connected to MT4PredictServer.")
        except Exception as e:
            self.logger.error(f"❌ Could not connect: {e}")
            self.client_socket = None

    def send_command(self, command: dict) -> dict:
        if not self.client_socket:
            self.connect_to_server()
            if not self.client_socket:
                return {"status": "error", "reason": "No server connection"}

        try:
            command["message_id"] = str(uuid.uuid4())
            self.client_socket.sendall((json.dumps(command) + "\n").encode())
            data = self.client_socket.recv(4096).decode().strip()
            return json.loads(data)
        except Exception as e:
            self.logger.error(f"❌ Command send error: {e}")
            return {"status": "error", "reason": str(e)}

    # -------------------------
    # Model Info
    # -------------------------
    def reload_model_summary(self):
        try:
            model = keras.models.load_model("src/model/model.keras")
            self.model_info.clear()
            buf = io.StringIO()
            model.summary(print_fn=lambda x: buf.write(x + "\n"))
            self.model_info.append("Model Summary:")
            self.model_info.append(buf.getvalue())
            self.model_info.append(f"Total Parameters: {model.count_params()}")
        except FileNotFoundError:
            self.model_info.setPlainText("⚠️ No model file found at src/model/model.keras")
        except Exception as e:
            self.model_info.setPlainText(f"❌ Failed to load model: {e}")

    # -------------------------
    # Logging
    # -------------------------
    def init_logger(self):
        logger = logging.getLogger("PredictGUI")
        logger.setLevel(logging.DEBUG)

        class QtSignalEmitter(QObject):
            log_signal = Signal(str)

        class QtLogHandler(logging.Handler):
            def __init__(self):
                super().__init__()
                self.emitter = QtSignalEmitter()

            def emit(self, record):
                self.emitter.log_signal.emit(self.format(record))

        handler = QtLogHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
        handler.emitter.log_signal.connect(self.append_log)
        logger.addHandler(handler)

        file_handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
        logger.addHandler(file_handler)

        return logger

    def append_log(self, msg):
        self.output.append(msg)
        self.output.verticalScrollBar().setValue(self.output.verticalScrollBar().maximum())

    # -------------------------
    # Timer
    # -------------------------
    def init_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_log_output)
        self.timer.start(5000)

    def refresh_log_output(self):
        try:
            result = subprocess.run(["nvidia-smi"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode == 0:
                self.gpu_status.setPlainText(result.stdout)
            else:
                self.gpu_status.setPlainText("⚠️ nvidia-smi not available.")
        except Exception as e:
            self.logger.error(e)

    # -------------------------
    # Server Lifecycle
    # -------------------------
    def start_server(self):
        if self.process and self.process.poll() is None:
            QMessageBox.warning(self, "Already Running", "The server is already running.")
            return

        try:
            SERVER_SCRIPT = os.path.abspath("src/server/server.py")
            self.process = subprocess.Popen(
                [sys.executable, SERVER_SCRIPT],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                bufsize=1,
            )
            self.status_label.setText("🟢 Status: <b><span style='color: green;'>Running</span></b>")
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)

            self.reader_thread = OutputReaderThread(self.process)
            self.reader_thread.output_signal.connect(self.append_log)
            self.reader_thread.start()

            QTimer.singleShot(3000, self.connect_to_server)
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

        if self.reader_thread:
            self.reader_thread.stop()

        if self.client_socket:
            self.client_socket.close()
            self.client_socket = None

        self.status_label.setText("🔌 Status: <b><span style='color: red;'>Stopped</span></b>")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def closeEvent(self, event):
        self.stop_server()
        event.accept()


# ========================
# Run GUI
# ========================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Mt4PredictServer()
    window.resize(1200, 750)
    window.setMinimumSize(900, 600)
    window.show()
    app.setStyle("Fusion")
    sys.exit(app.exec())
