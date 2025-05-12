import logging
import os

from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton, QSizePolicy
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator

from components.predictionChart import PredictionChart


class TensorFlowMetricsTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.SUMMARY_PATH = os.path.join("src", "logs", "training_summary.txt")
        self.TENSORBOARD_LOG_DIR = os.path.join("src", "logs")
        self.metrics_tab = None
        self.layout = QVBoxLayout()
        # Show training summary
        self.summary_label = QLabel("📄 Training Summary:")
        self.layout.addWidget(self.summary_label)
        self.summary_label.setFont(QFont("Arial", 12))

        if not os.path.exists(self.SUMMARY_PATH):
            logging.error(f"Training summary file not found: {self.SUMMARY_PATH}")
            self.summary_label.setText("❌ Training summary file not found.")

            #Then Create a dummy summary
            self.summary_text = QTextEdit()
            self.summary_text.setReadOnly(True)
            self.summary_text.setText("⚠️ training_summary.txt not found.")
            self.layout.addWidget(self.summary_text)
            self.setLayout(self.layout)
            return
        # Show training summary if available
        if os.path.exists(self.SUMMARY_PATH):
            with open(self.SUMMARY_PATH, "r", encoding="utf-8") as f:
                summary = f.read()
                self.summary_text = QTextEdit()
                self.summary_text.setReadOnly(True)
                self.summary_text.setText(summary)
                self.layout.addWidget(self.summary_text)
        else:
            self.summary_text = QTextEdit()
            self.summary_text.setReadOnly(True)
            self.summary_text.setText("⚠️ training_summary.txt not found.")
            self.layout.addWidget(self.summary_text)

        # Add button to show TensorBoard metrics
        self.show_metrics_button = QPushButton("📊 Show TensorBoard Metrics")
        self.show_metrics_button.clicked.connect(self.show_tensorboard_metrics)
        self.layout.addWidget(self.show_metrics_button)

        self.setLayout(self.layout)

    def show_tensorboard_metrics(self, TENSORBOARD_LOG_DIR=None):
        try:
            # Load scalar metrics from TensorBoard logs
            ea = EventAccumulator(TENSORBOARD_LOG_DIR)
            ea.Reload()
            scalar_tags = ea.Tags().get("scalars", [])

            if scalar_tags:
                self.metrics_tab = PredictionChart(self)
                self.metrics_tab.update_chart(scalar_tags)
                self.layout.addWidget(self.metrics_tab)
            else:
                self.metrics_tab = QTextEdit()
                self.metrics_tab.setReadOnly(True)
                self.metrics_tab.setText("ℹ️ No scalar metrics found in TensorBoard logs.")
                self.layout.addWidget(self.metrics_tab)

        except Exception as e:
            logging.error(f"Failed to read TensorBoard logs: {e}")
            self.metrics_tab = QTextEdit()
            self.metrics_tab.setReadOnly(True)
            self.metrics_tab.setText(f"❌ Failed to read TensorBoard logs: {e}")
            self.layout.addWidget(self.metrics_tab)