import os
import subprocess
import time
import socket
import shutil
from PySide6.QtCore import QTimer, QUrl
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QMessageBox
)
from PySide6.QtWebEngineWidgets import QWebEngineView


class TensorBoardViewer(QWidget):
    """📊 Embedded TensorBoard dashboard inside PySide6 GUI."""

    def __init__(self, logdir="./src/logs", port=6006, parent=None):
        super().__init__(parent)
        self.logdir = logdir
        self.port = port
        self.process = None  # FIX: do not overwrite subprocess module

        # --- UI setup ---
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        title = QLabel("📊 TensorBoard Live Dashboard")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        # --- Browser frame ---
        self.browser = QWebEngineView()
        layout.addWidget(self.browser)

        # --- Control buttons ---
        btn_start = QPushButton("🚀 Start TensorBoard")
        btn_stop = QPushButton("🛑 Stop TensorBoard")

        btn_start.clicked.connect(self.start_tensorboard)
        btn_stop.clicked.connect(self.stop_tensorboard)

        layout.addWidget(btn_start)
        layout.addWidget(btn_stop)

        # --- Auto-refresh (every 8s) ---
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_if_needed)
        self.timer.start(8000)

    # --------------------------------------------------------------
    def _find_tensorboard_executable(self):
        """Try to find the TensorBoard executable."""
        tb_path = shutil.which("tensorboard")
        if tb_path:
            return tb_path

        # Manual fallbacks for common Windows installs
        possible_paths = [
            r"C:\Users\nguem\AppData\Local\Programs\Python\Python313\Scripts\tensorboard.exe",
            r"C:\Users\nguem\AppData\Local\Programs\Python\Python312\Scripts\tensorboard.exe",
            r"C:\Python313\Scripts\tensorboard.exe",
            r"C:\Python312\Scripts\tensorboard.exe",
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None

    # --------------------------------------------------------------
    def _wait_for_port(self, host, port, timeout=10):
        """Wait for the TensorBoard port to be available."""
        start = time.time()
        while time.time() - start < timeout:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex((host, port)) == 0:
                    return True
            time.sleep(0.5)
        return False

    # --------------------------------------------------------------
    # def start_tensorboard(self):
    #     """Launch TensorBoard as a background process and embed it."""
    #     try:
    #         if self.process and getattr(self.process, "poll", None):
    #             if self.process.poll() is None:
    #                 QMessageBox.information(self, "Info", "TensorBoard is already running.")
    #                 return
    #
    #         exe_path = self._find_tensorboard_executable()
    #         if not exe_path:
    #             QMessageBox.critical(
    #                 self, "Error",
    #                 "❌ TensorBoard executable not found.\n"
    #                 "Please install it with:\n\npip install tensorboard"
    #             )
    #             return
    #
    #         # Ensure log directory exists
    #         os.makedirs(self.logdir, exist_ok=True)
    #
    #         # Launch TensorBoard
    #         self.process = subprocess.Popen(
    #             [exe_path, "--logdir", self.logdir, "--port", str(self.port)],
    #             stdout=subprocess.PIPE,
    #             stderr=subprocess.PIPE,
    #             creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    #         )
    #
    #         # Wait for port to be ready
    #         if not self._wait_for_port("127.0.0.1", self.port, timeout=15):
    #             # Read stderr if available
    #             if self.process.poll() is not None:
    #                 err_output = self.process.stderr.read().decode(errors="ignore")
    #                 if "Address already in use" in err_output:
    #                     QMessageBox.warning(
    #                         self, "Warning",
    #                         f"Port {self.port} already in use — please choose another port."
    #                     )
    #                 else:
    #                     QMessageBox.critical(
    #                         self, "Error",
    #                         f"TensorBoard failed to start:\n{err_output or 'Unknown error.'}"
    #                     )
    #             else:
    #                 QMessageBox.critical(
    #                     self, "Error",
    #                     f"TensorBoard failed to start on port {self.port} (connection refused)."
    #                 )
    #             return
    #
    #         # Successfully running
    #         url = f"http://127.0.0.1:{self.port}"
    #         self.browser.setUrl(QUrl(url))
    #         QMessageBox.information(self, "Success", f"✅ TensorBoard is running at {url}")
    #
    #     except Exception as e:
    #         QMessageBox.critical(self, "Error", f"Failed to start TensorBoard:\n{e}")

    # --------------------------------------------------------------
    def stop_tensorboard(self):
        """Stop TensorBoard process safely."""
        try:
            if self.process and getattr(self.process, "poll", None):
                if self.process.poll() is None:
                    self.process.terminate()
                    QMessageBox.information(self, "TensorBoard", "🛑 TensorBoard stopped.")
                    return
            QMessageBox.warning(self, "Warning", "No TensorBoard process running.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to stop TensorBoard:\n{e}")

    # --------------------------------------------------------------
    def refresh_if_needed(self):
        """Auto-refresh browser if disconnected."""
        try:
            expected_url = f"http://127.0.0.1:{self.port}"
            if self.browser.url().toString() != expected_url:
                self.browser.setUrl(QUrl(expected_url))
        except Exception as e:
            print(f"[TensorBoardViewer] Refresh error: {e}")

    # --------------------------------------------------------------
    def closeEvent(self, event):
        """Ensure TensorBoard terminates with the app."""
        self.stop_tensorboard()
        event.accept()
    def start_tensorboard(self):
     logdir = str(self.logdir) if isinstance(self.logdir, (str, bytes, os.PathLike)) else "./src/logs"
     self.process = subprocess.Popen(
        ["tensorboard", "--logdir", logdir, "--port", str(self.port)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
