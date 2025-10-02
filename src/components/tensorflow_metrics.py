import logging
from pathlib import Path

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton, QSizePolicy
)
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator

from src.components.predictionChart import PredictionChart


class TensorFlowMetricsTab(QWidget):
    def __init__(self):
        super().__init__()

        # Paths
        self.SUMMARY_PATH = Path("src/logs/training_summary.log")
        self.TENSORBOARD_LOG_DIR = Path("src/logs/tensorboard_metrics.log")

        # Layout
        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)

        # Training summary
        self.summary_label = QLabel("📄 Training Summary:")
        self.summary_label.setFont(QFont("Segoe UI", 12))
        self.layout.addWidget(self.summary_label)

        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.layout.addWidget(self.summary_text)

        self.load_training_summary()

        # Button for TensorBoard metrics
        self.show_metrics_button = QPushButton("📊 Show TensorBoard Metrics")
        self.show_metrics_button.clicked.connect(self.show_tensorboard_metrics)
        self.layout.addWidget(self.show_metrics_button)

        # Placeholder for metrics chart/text
        self.metrics_tab = None

    # -----------------------------
    # Helpers
    # -----------------------------
    def load_training_summary(self):
        """Load training summary from log file or show fallback message."""
        if self.SUMMARY_PATH.exists():
            try:
                summary = self.SUMMARY_PATH.read_text(encoding="utf-8")
                self.summary_text.setText(summary)
            except Exception as e:
                logging.error(f"❌ Failed to read summary file: {e}")
                self.summary_text.setText(f"❌ Error reading summary file: {e}")
        else:
            logging.warning(f"⚠️ Training summary file not found: {self.SUMMARY_PATH}")
            self.summary_text.setText("⚠️ Training summary not found.")

    def clear_metrics_tab(self):
        """Remove any previous metrics widget before adding new."""
        if self.metrics_tab:
            self.layout.removeWidget(self.metrics_tab)
            self.metrics_tab.deleteLater()
            self.metrics_tab = None

    # -----------------------------
    # TensorBoard Metrics
    # -----------------------------
    def show_tensorboard_metrics(self, tensorboard_log_dir=None):
        """Load scalar metrics from TensorBoard event logs."""
        self.clear_metrics_tab()

        log_dir = Path(tensorboard_log_dir or self.TENSORBOARD_LOG_DIR)
        if not log_dir.exists():
            msg = f"⚠️ TensorBoard log directory not found: {log_dir}"
            logging.error(msg)
            self.metrics_tab = self._make_textbox(msg)
            self.layout.addWidget(self.metrics_tab)
            return

        try:
            ea = EventAccumulator(str(log_dir))
            ea.Reload()
            scalar_tags = ea.Tags().get("scalars", [])

            if scalar_tags:
                self.metrics_tab = PredictionChart(self)
                self.metrics_tab.update_chart()
            else:
                self.metrics_tab = self._make_textbox("ℹ️ No scalar metrics found in TensorBoard logs.")
        except Exception as e:
            logging.error(f"❌ Failed to read TensorBoard logs: {e}")
            self.metrics_tab = self._make_textbox(f"❌ Error reading TensorBoard logs: {e}")

        self.layout.addWidget(self.metrics_tab)

    # -----------------------------
    # Utility
    # -----------------------------
    def _make_textbox(self, text: str) -> QTextEdit:
        """Helper to quickly make a readonly QTextEdit with text."""
        box = QTextEdit()
        box.setReadOnly(True)
        box.setText(text)
        box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        return box
