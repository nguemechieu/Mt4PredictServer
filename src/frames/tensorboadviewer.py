import os
import subprocess
import time
from PySide6.QtCore import QTimer, QUrl
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QMessageBox
from PySide6.QtWebEngineWidgets import QWebEngineView


class TensorBoardViewer(QWidget):
    """Embed a live TensorBoard dashboard into the PySide6 GUI."""

    def __init__(self,controller =None):

        super().__init__()
        self.logdir="src/logs"
        self.port=6006,
        self.process = None
        # --- Layout ---
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        title = QLabel("📊 TensorBoard Live Dashboard")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        # --- WebView for TensorBoard UI ---
        self.browser = QWebEngineView()
        layout.addWidget(self.browser)

        # --- Control buttons ---
        btn_start = QPushButton("🚀 Start TensorBoard")
        btn_stop = QPushButton("🛑 Stop TensorBoard")

        btn_start.clicked.connect(self.start_tensorboard)
        btn_stop.clicked.connect(self.stop_tensorboard)

        layout.addWidget(btn_start)
        layout.addWidget(btn_stop)

        # --- Auto-refresh ---
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_if_needed)
        self.timer.start(5000)

    # --------------------------------------------------------------
    def start_tensorboard(self):
        """Launch TensorBoard as a background process."""
        try:
            if self.process and self.process.poll() is None:
                QMessageBox.information(self, "Info", "TensorBoard is already running.")
                return

            if not os.path.exists(self.logdir):
                os.makedirs(self.logdir, exist_ok=True)

            # --- Launch TensorBoard subprocess ---
            self.process = subprocess.Popen(
                [
                    os.path.expanduser("./AppData/Local/Programs/Python/Python313/Scripts/tensorboard.exe"),
                    "--logdir", self.logdir,
                    "--port", str(self.port),
                    "--reload_interval", "10"
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            # Give TensorBoard a moment to start
            time.sleep(3)
            self.browser.setUrl(QUrl(f"http://localhost:{self.port}"))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start TensorBoard:\n{e}")

    # --------------------------------------------------------------
    def stop_tensorboard(self):
        """Stop TensorBoard process."""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            QMessageBox.information(self, "TensorBoard", "TensorBoard stopped.")
        else:
            QMessageBox.warning(self, "Warning", "No TensorBoard process running.")

    # --------------------------------------------------------------
    def refresh_if_needed(self):
        """Refresh dashboard if TensorBoard restarted."""
        try:
            url = f"http://localhost:{self.port}"
            if self.browser.url().toString() != url:
                self.browser.setUrl(QUrl(url))
        except Exception:
            pass

    # --------------------------------------------------------------
    def closeEvent(self, event):
        """Clean up process when closing the window."""
        self.stop_tensorboard()
        event.accept()
