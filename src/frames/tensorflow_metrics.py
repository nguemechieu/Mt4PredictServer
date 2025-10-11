import logging
import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton, QSizePolicy, QMessageBox, QScrollArea
)
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas


class TensorFlowMetricsTab(QWidget):
    """TensorFlow training metrics viewer with TensorBoard event reader."""

    def __init__(self):
        super().__init__()

        # --- Paths ---
        self.SUMMARY_PATH = Path("src/logs/metric_summary.log")
        self.TENSORBOARD_LOG_DIR = Path("src/logs")
        self.TENSORBOARD_LOG_DIR.mkdir(parents=True, exist_ok=True)

        # --- Base Layout ---
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # --- Scroll Area for content ---
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        content_widget = QWidget()
        self.layout = QVBoxLayout(content_widget)
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)

        # --- Header ---
        header = QLabel("<h2>📊 TensorFlow Training Metrics</h2>")
        header.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(header)

        # --- Training Summary Section ---
        self.summary_label = QLabel("📄 Training Summary:")
        self.summary_label.setFont(QFont("Segoe UI", 11))
        self.layout.addWidget(self.summary_label)

        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setFont(QFont("Consolas", 10))
        self.summary_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.layout.addWidget(self.summary_text)

        self.load_training_summary()

        # --- Metrics Button ---
        self.show_metrics_button = QPushButton("📈 Load TensorBoard Metrics")
        self.show_metrics_button.clicked.connect(self.show_tensorboard_metrics)
        self.layout.addWidget(self.show_metrics_button)

        # --- Placeholder for metrics chart ---
        self.metrics_tab = None

    # ============================================================
    # Training Summary Loader
    # ============================================================
    def load_training_summary(self):
        """Load training summary from log file or show fallback message."""
        try:
            if self.SUMMARY_PATH.exists():
                summary = self.SUMMARY_PATH.read_text(encoding="utf-8")
                self.summary_text.setText(summary)
            else:
                self.summary_text.setText("⚠️ No training summary found. Run a training session first.")
        except Exception as e:
            logging.error(f"❌ Failed to read summary file: {e}")
            self.summary_text.setText(f"❌ Error reading summary file: {e}")

    # ============================================================
    # TensorBoard Metrics Loader
    # ============================================================
    def show_tensorboard_metrics(self, tensorboard_log_dir=None):
        """Load and plot metrics from the latest TensorBoard run."""
        self._clear_metrics_tab()

        # --- Determine latest log directory ---
        log_dir = Path(tensorboard_log_dir or self.TENSORBOARD_LOG_DIR)
        if not log_dir.exists():
            return self._show_error(f"⚠️ TensorBoard log directory not found: {log_dir}")

        # Get the most recent subfolder
        subdirs = sorted(log_dir.glob("*/"), key=os.path.getmtime, reverse=True)
        target_dir = subdirs[0] if subdirs else log_dir

        # --- Check event files ---
        event_files = list(target_dir.glob("events.*"))
        if not event_files:
            return self._show_error(f"⚠️ No TensorBoard event files found in: {target_dir}")

        try:
            ea = EventAccumulator(str(target_dir))
            ea.Reload()

            scalar_tags = ea.Tags().get("scalars", [])
            if not scalar_tags:
                return self._show_error("ℹ️ No scalar metrics found in TensorBoard logs.")

            # --- Prepare data ---
            metrics = {}
            for tag in scalar_tags:
                events = ea.Scalars(tag)
                metrics[tag] = [(e.step, e.value) for e in events]

            # --- Plot metrics ---
            self.metrics_tab = self._plot_metrics(metrics)
            self.layout.addWidget(self.metrics_tab)

        except Exception as e:
            logging.error(f"❌ Failed to read TensorBoard logs: {e}")
            self._show_error(f"❌ Error reading TensorBoard logs: {e}")

    # ============================================================
    # Chart / UI Helpers
    # ============================================================
    def _plot_metrics(self, metrics_dict):
        """Generate matplotlib chart for scalar metrics."""
        try:
            fig, ax = plt.subplots(figsize=(8, 5))
            for tag, points in metrics_dict.items():
                steps, values = zip(*points)
                ax.plot(steps, values, label=tag)

            ax.set_title("📉 TensorBoard Metrics", fontsize=12)
            ax.set_xlabel("Epoch / Step")
            ax.set_ylabel("Metric Value")
            ax.legend()
            ax.grid(True)

            canvas = FigureCanvas(fig)
            canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            return canvas
        except Exception as e:
            return self._make_textbox(f"❌ Plot error: {e}")

    def _make_textbox(self, text):
        """Create read-only textbox widget."""
        box = QTextEdit()
        box.setReadOnly(True)
        box.setText(text)
        box.setFont(QFont("Consolas", 10))
        box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        return box

    def _show_error(self, message):
        """Display an inline error message box and log it."""
        logging.warning(message)
        QMessageBox.warning(self, "TensorBoard Metrics", message)
        self.metrics_tab = self._make_textbox(message)
        self.layout.addWidget(self.metrics_tab)

    def _clear_metrics_tab(self):
        """Remove any previous metrics view."""
        if self.metrics_tab:
            self.layout.removeWidget(self.metrics_tab)
            self.metrics_tab.deleteLater()
            self.metrics_tab = None
