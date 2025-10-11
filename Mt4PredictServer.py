import io
import json
import logging
import os
import shutil
import socket
import subprocess
import sys
import uuid

from PySide6.QtCore import Signal, QTimer, QObject, QThread
from PySide6.QtGui import QIcon, QColor, QTextCharFormat, QTextCursor, QFont, QFontDatabase
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QTabWidget, QLabel, QTextEdit, QPushButton
)
from tensorflow.keras.models import load_model

# --- Frame imports ---
from src.components.GPTAdvisor import GPTAdvisor
from src.components.mt4_predictor import MT4Predictor
from src.frames.AccountInfo import AccountInfo

from src.frames.tensorboadviewer import TensorBoardViewer

from src.frames.ExecuteCommand import ExecuteCommand
from src.frames.GPTChat import GPTChatFrame
from src.frames.LivePredictionsFrame import LivePredictionsFrame
from src.frames.PositionHistory import PositionHistory
from src.frames.ResourceMonitorFrame import ResourceMonitorFrame
from src.frames.ServerControlFrame import ServerControlFrame

from src.frames.tensorflow_metrics import TensorFlowMetricsTab
from src.server.server import PredictServer

# =====================================================
# CONSTANTS
# =====================================================
HOST = "127.0.0.1"
PORT = 9999  # Unified with PredictServer
LOG_PATH = "src/logs/predict_server.log"
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)


# =====================================================
# Dark theme stylesheet
# =====================================================
def dark_theme_stylesheet():
    return """
    QWidget { background-color: #1e1e1e; color: #dcdcdc; }
    QPushButton {
        background-color: #3c3c3c;
        border: 1px solid #555;
        padding: 10px; font-size: 14px; color: white;
    }
    QPushButton:hover { background-color: #505050; }
    QTextEdit { background-color: #262626; border: 1px solid #444; color: #c8c8c8; }
    QLabel { color: #cccccc; }
    """


# =====================================================
# THREAD: Background Reader
# =====================================================
class OutputReaderThread(QThread):
    output_signal = Signal(str)

    def __init__(self,  controller=None):
        super().__init__()
        self.process = controller
        self.controller = controller
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setStyleSheet(dark_theme_stylesheet())
        self.running = True
        self.server = PredictServer(controller)


    def run(self):
        """Read process output and emit lines to GUI."""
        try:
            self.server.start()
            if not self.process:
                return

            while self.running and self.process.poll() is None:
                line = self.process.stdout.readline()
                if line:
                    self.output_signal.emit(line.strip())
        except Exception as e:
            self.output_signal.emit(f"[Reader Error] {e}")

    def stop(self):
        """Stop thread and close server cleanly."""
        self.running = False
        try:
            self.server.stop()
        except Exception as e:
            self.output_signal.emit(f"[Server Stop Error] {e}")
        self.quit()
        self.wait()
# =====================================================
# FILE MAINTENANCE UTILITIES
# =====================================================
def cleanup_large_files(base_dir: str = "./src", max_size_mb: int = 50):
    """
    Automatically delete or rotate large .csv and .log files exceeding size limit.
    - base_dir: root directory to scan (default ./src)
    - max_size_mb: threshold in MB (default 50 MB)
    """
    deleted_files = []
    size_limit = max_size_mb * 1024 * 1024  # convert to bytes

    try:
        for root, _, files in os.walk(base_dir):
            for file in files:
                if file.endswith((".csv", ".log")):
                    path = os.path.join(root, file)
                    if os.path.exists(path) and os.path.getsize(path) > size_limit:
                        backup = path + ".bak"
                        shutil.move(path, backup)  # move instead of immediate delete
                        deleted_files.append((file, os.path.getsize(path)))
                        with open(path, "w", encoding="utf-8") as f:
                            f.write("")  # recreate empty file for continued logging

        if deleted_files:
            print(f"🧹 Cleaned {len(deleted_files)} large files (> {max_size_mb}MB):")
            for f, s in deleted_files:
                print(f"   - {f} ({round(s / (1024 * 1024), 2)} MB)")

    except Exception as e:
        print(f"❌ File cleanup error: {e}")

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
cleanup_large_files()
# =====================================================
# MAIN APPLICATION WINDOW
# =====================================================
class Mt4PredictServer(QWidget):
    def __init__(self):
        super().__init__()

        # Load emoji-capable font
        self.controller = self
        self.predictions = None
        self.process=None
        self.account_info={}
        self.open_orders={}
        self.order_history={}

        self.server_tab=None
        QFontDatabase.addApplicationFont("C:/Windows/Fonts/seguiemj.ttf")
        self.setFont(QFont("Segoe UI Emoji", 10))


        self.client_socket = None
        self.server = None
        self.output_thread = None
        self.logger = self._init_logger()

        # Load config and API key
        self.config = self._load_config()
        self.api_key = self.config.get("OPENAI_API_KEY", "not_set")

        # Core backend components
        self.gpt = GPTAdvisor(controller=self)
        self.predictor = MT4Predictor(controller=self)
        self.server = PredictServer(controller=self)

        # UI setup
        self.server_tab = ServerControlFrame(
            controller=self.controller,
            api_key=self.api_key,
            connect_fn=self.connect_to_server,
            send_cmd_fn=self.send_command
        )


        self.logger.info("🧠 Initializing Mt4PredictServer GUI...")

        self.setWindowTitle("Mt4PredictServer — Live Trading")
        self.setWindowIcon(QIcon("logo.png"))
        self.setGeometry(400, 200, 1200, 800)
        self.setStyleSheet(dark_theme_stylesheet())

        self._init_ui()
        self._init_gpu_monitor()

        # Auto-connect socket
        QTimer.singleShot(1500, self.connect_to_server)

        # Start PredictServer in background


        self.logger.info("🚀 PredictServer launched successfully.")

    # =====================================================
    # CONFIG
    # =====================================================
    def _load_config(self):
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                cfg = json.load(f)
            self.logger.info("✅ Config loaded successfully.")
            return cfg
        except Exception as e:
            self.logger.warning(f"⚠️ config.json missing or invalid: {e}")
            return {}

    # =====================================================
    # UI SETUP
    # =====================================================
    def _init_ui(self):
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()

        # --- Model Tab ---
        model_tab = QWidget()
        model_layout = QVBoxLayout()
        self.model_info = QTextEdit(readOnly=True)
        self.model_info.setFont(QFont("Courier New", 10))

        reload_btn = QPushButton("🔄 Reload Model")
        reload_btn.clicked.connect(lambda: QTimer.singleShot(100, self._reload_model_summary))

        model_layout.addWidget(QLabel("🧠 TensorFlow Model Info:"))
        model_layout.addWidget(reload_btn)
        model_layout.addWidget(self.model_info)
        model_tab.setLayout(model_layout)

        # --- Add all tabs ---
        self.tabs.addTab(self.server_tab, "Server")
        self.tabs.addTab(ResourceMonitorFrame(self.controller), "Monitor")
        self.tabs.addTab( LivePredictionsFrame(self.controller), "Predictor")
        self.tabs.addTab(GPTChatFrame(self.controller), "AI Advisor")
        self.tabs.addTab(AccountInfo(self.controller), "Account - Open orders")
        self.tabs.addTab(PositionHistory(self.controller), "Position History")
        self.tabs.addTab(TensorFlowMetricsTab(), "Metrics")
        self.tabs.addTab(ExecuteCommand(self.controller), "Commands")
        self.tabs.addTab(TensorBoardViewer(self.controller), "TensorBoard Viewer")
        self.tabs.addTab(model_tab, "Tensorflow Model")
        layout.addWidget(self.tabs)
        self.setLayout(layout)
        self._reload_model_summary()

    # =====================================================
    # SOCKET CONNECTION
    # =====================================================
    def connect_to_server(self):
        """Connect GUI socket client to PredictServer."""
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(2)
            self.client_socket.connect((HOST, PORT))
            self.logger.info("✅ Connected to PredictServer.")
        except Exception as e:
            self.logger.warning(f"🔁 Retrying connection: {e}")
            QTimer.singleShot(2000, self.connect_to_server)

    def send_command(self, command: dict) -> dict:
        """Send JSON command to PredictServer."""
        if not self.client_socket:
            self.connect_to_server()
            return {"status": "error", "reason": "Server not connected"}

        try:
            command["message_id"] = str(uuid.uuid4())
            self.client_socket.sendall((json.dumps(command) + "\n").encode("utf-8"))
            self.client_socket.settimeout(1.5)
            try:
                data = self.client_socket.recv(4096).decode().strip()
                return json.loads(data)
            except socket.timeout:
                return {"status": "pending", "reason": "No response yet"}
        except Exception as e:
            self.logger.error(f"❌ Send error: {e}")
            return {"status": "error", "reason": str(e)}

    # =====================================================
    # MODEL SUMMARY
    # =====================================================
    def _reload_model_summary(self):
        """Reload and display TensorFlow model summary."""
        try:
            path = "model/model.keras"
            if not os.path.exists(path):
                self.model_info.setPlainText("⚠️ No model file found.")
                return

            self.model_info.setPlainText("🔄 Loading model, please wait...")
            model = load_model(path)
            buf = io.StringIO()
            model.summary(print_fn=lambda x: buf.write(x + "\n"))
            summary = f"Model Summary:\n{buf.getvalue()}\nParameters: {model.count_params()}"
            self.model_info.setPlainText(summary)
            self.logger.info("✅ Model summary reloaded successfully.")
        except Exception as e:
            self.model_info.setPlainText(f"❌ Failed to load model: {e}")
            self.logger.error(f"❌ Model load error: {e}")

    # =====================================================
    # LOGGER SETUP
    # =====================================================
    def _init_logger(self):
        """Set up Qt-integrated logging."""
        logger = logging.getLogger("Mt4PredictServer")
        logger.setLevel(logging.DEBUG)
        logger.handlers.clear()

        class QtSignalEmitter(QObject):
            log_signal = Signal(str, str)

        class QtLogHandler(logging.Handler):
            def __init__(self, emitter_):
                super().__init__()
                self.emitter = emitter_
            def emit(self, record):
                msg = self.format(record)
                self.emitter.log_signal.emit(msg, record.levelname)

        emitter = QtSignalEmitter()
        qt_handler = QtLogHandler(emitter)
        qt_handler.setFormatter(logging.Formatter("%(asctime)s — %(message)s", "%H:%M:%S"))
        emitter.log_signal.connect(self._append_log)

        file_handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter("%(asctime)s — %(levelname)s — %(message)s"))

        logger.addHandler(qt_handler)
        logger.addHandler(file_handler)
        return logger

    # =====================================================
    # GPU MONITOR
    # =====================================================
    def _init_gpu_monitor(self):
        """Set up periodic GPU status checks."""
        self.gpu_timer = QTimer()
        self.gpu_timer.timeout.connect(self._refresh_gpu_status)
        self.gpu_timer.start(6000)

    def _refresh_gpu_status(self):
        """Refresh NVIDIA GPU status."""
        try:
            if shutil.which("nvidia-smi") is None:
                raise FileNotFoundError
            res = subprocess.run(["nvidia-smi"], capture_output=True, text=True, timeout=5)
            gpu_status = res.stdout if res.returncode == 0 else res.stderr
        except FileNotFoundError:
            gpu_status = "⚠️ No NVIDIA GPU detected."
        except subprocess.TimeoutExpired:
            gpu_status = "⚠️ GPU check timed out."
        except Exception as e:
            gpu_status = f"❌ GPU monitor error: {e}"

        if self.server_tab:
            self.server_tab.gpu_status_display.setPlainText(gpu_status)

    # =====================================================
    # GUI LOG APPENDER
    # =====================================================
    def _append_log(self, msg, level="INFO"):

     if self.server_tab is not None:
        self.server_tab.gpu_status_display.setPlainText(msg)
        """Append logs to visible GUI output."""
        target_output = getattr(self.server_tab, "output", None)
        if not target_output:
             return

        cursor = target_output.textCursor()
        cursor.movePosition(QTextCursor.End)
        fmt = QTextCharFormat()
        colors = {
            "INFO": "#00ff66",
            "WARNING": "#ffcc00",
            "ERROR": "#ff4444",
            "CRITICAL": "#ff0000"
        }
        fmt.setForeground(QColor(colors.get(level, "#ffffff")))
        cursor.insertText(f"{msg}\n", fmt)
        target_output.setTextCursor(cursor)
        target_output.ensureCursorVisible()

    # =====================================================
    # CLEANUP
    # =====================================================
    def closeEvent(self, event):
        """Gracefully stop threads and sockets."""
        self.logger.info("🧹 Closing application...")
        try:
            self.server.stop()
        except Exception as e:
            self.logger.error(f"Server stop error: {e}")
        if self.client_socket:
            self.client_socket.close()
        if self.output_thread:
            self.output_thread.stop()
        event.accept()


# =====================================================
# MAIN ENTRYPOINT
# =====================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Mt4PredictServer()
    window.resize(1200, 750)
    window.setMinimumSize(900, 600)
    app.setStyle("Fusion")
    window.show()
    sys.exit(app.exec())
