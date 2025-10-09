import logging
import os
import platform
import subprocess
import sys

from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QMessageBox
)

from src.server.server import PredictServer


# =====================================================
# Background Reader Thread
# =====================================================
class OutputReaderThread(QThread):
    """Continuously reads process output and emits it to the GUI."""
    output_signal = Signal(str)

    def __init__(self,controller=None) -> None:
        super().__init__()

        self.process = controller.process
        self.logger = logging.getLogger(self.__class__.__name__)
        self.running = True
        self.server = PredictServer(controller)

    def run(self):
        try:
            self.server.start()
            while self.running and self.process.poll() is None:
                line = self.process.stdout.readline()
                if line:
                    self.output_signal.emit(line.strip())
        except Exception as e:
            self.output_signal.emit(f"[Reader Error] {e}")

    def stop(self):
        self.running = False
        try:
            self.server.stop()
        except Exception as e:
            self.output_signal.emit(f"[Server Stop Error] {e}")
        self.quit()
        self.wait()


# =====================================================
# ServerControlFrame Widget
# =====================================================
class ServerControlFrame(QWidget):
    """GUI control panel for Mt4PredictServer."""

    def __init__(self, controller=None, api_key=None, connect_fn=None, send_cmd_fn=None):
        super().__init__()
        # Load emoji-safe font
        self.output= QTextEdit()
        self.gpu_status_display = self.output
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Segoe UI Emoji", 10))

        self.controller = controller
        self.logger =controller.logger
        self.api_key = api_key
        self.connect_fn = connect_fn
        self.send_cmd_fn = send_cmd_fn

        self.process = None
        self.reader_thread = None
      

        # Initialize components
        self._init_ui()
        self._init_timer()

    # =====================================================
    # UI Setup
    # =====================================================
    def _init_ui(self):
        layout = QVBoxLayout(self)
        self.process=None

        # --- Status Label ---
        self.status_label = QLabel("🔌 Status: <b><span style='color: red;'>Stopped</span></b>")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Segoe UI", 13))
        layout.addWidget(self.status_label)

        # --- Buttons ---
        self.start_btn = QPushButton("▶️ Start Server")
        self.stop_btn = QPushButton("⏹ Stop Server")
    
        self.stop_btn.setEnabled(False)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
  
        layout.addLayout(btn_layout)

        # --- Output Log ---
        layout.addWidget(QLabel("🧾 Server Output:"))
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Courier New", 10))
        layout.addWidget(self.output)

        # --- Event Bindings ---
        self.start_btn.clicked.connect(self.start_server)
        self.stop_btn.clicked.connect(self.stop_server)

        self.setLayout(layout)

    # =====================================================
    # AutoTrader
    # =====================================================
    def _init_autotrader(self):
        if not self.api_key:
            self.log("⚠️ Missing OpenAI API key — auto-trader disabled.")
            return
        self.auto_trader = AutoTradeManager(controller=self.controller)
        self.auto_trader.stream_signal.connect(self.append_log)
        self.auto_trader.decision_signal.connect(self._on_ai_decision)

    def _on_ai_decision(self, decision=None):
        self.log(f"🤖 AI Decision: {decision}")
        if decision.get("action") in ["BUY", "SELL"] and self.send_cmd_fn:
            self.send_cmd_fn(decision)

    # =====================================================
    # Logging
    # =====================================================
    def log(self, msg: str=None):
        """Log messages both to console and the GUI."""
        if self.logger:
            self.logger.info(msg)
        self.output.append(msg)
        self.output.moveCursor(QTextCursor.End)

    def append_log(self, msg: str=None):
        self.log(msg)

    # =====================================================
    # Server Control
    # =====================================================
    def start_server(self):
        """Start the PredictServer process."""
        if self.process and self.process.poll() is None:
            QMessageBox.warning(self, "Already Running", "The server is already running.")
            return

        try:
            self.process = subprocess.Popen(
                [sys.executable, os.path.abspath("src/server/server.py")],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                bufsize=1,
            )

            # Start reader thread
            self.reader_thread = OutputReaderThread(self.controller)
            self.reader_thread.output_signal.connect(self.append_log)
            self.reader_thread.start()

            # Update UI
            self.status_label.setText("🟢 Status: <b><span style='color: green;'>Running</span></b>")
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)

            QTimer.singleShot(3000, self.connect_fn or (lambda: self.log("✅ Ready to connect.")))

        except Exception as e:
            QMessageBox.critical(self, "Startup Error", str(e))
            self.log(f"❌ Failed to start server: {e}")

    def stop_server(self):
        """Stop the running server."""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.log("🛑 Server stopped.")

        if self.reader_thread:
            self.reader_thread.stop()
        # UI reset
        self.status_label.setText("🔌 Status: <b><span style='color: red;'>Stopped</span></b>")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)



    # =====================================================
    # GPU Monitor
    # =====================================================
    def _init_timer(self):
        """Initialize periodic GPU status refresh."""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh_gpu_status)
        self.timer.start(5000)

    def _refresh_gpu_status(self):
        """Check GPU status safely and log results."""
        try:
            if platform.system() in ("Windows", "Linux","MacOs"):
                result = subprocess.run(
                    ["nvidia-smi"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    gpu_status = result.stdout.strip()
                else:
                    gpu_status = f"NVIDIA-SMI error:\n{result.stderr.strip()}"
            else:
                gpu_status = "GPU check not supported on this OS."
        except FileNotFoundError:
            gpu_status = "⚠️ NVIDIA GPU not found or drivers not installed."
        except subprocess.TimeoutExpired:
            gpu_status = "⚠️ GPU check timed out."
        except Exception as e:
            gpu_status = f"❌ GPU check error: {e}"

        self.output.append(gpu_status + "\n")
        self.output.moveCursor(QTextCursor.End)
