import os
import time
from datetime import datetime

import matplotlib.pyplot as plt
import pandas as pd
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QTextEdit
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas


def safe_read_csv(filepath, retries=5, delay=0.1):
    """Safely read CSV with retry on file lock errors (Windows/MT4 writes)."""
    for attempt in range(retries):
        try:
            return pd.read_csv(filepath)
        except PermissionError:
            if attempt == retries - 1:
                raise
            time.sleep(delay)
    return None


class AccountMetrics(QWidget):
    def __init__(self, controller=None):
        super().__init__()
        self.setWindowTitle("📊 Account Metrics & AI Analysis")
        self.resize(1000, 700)
        self.controller = controller

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.prediction_file = "src/data/prediction_history.csv"
        self.training_log = "src/logs/training_summary.log"

        self.summary_label = QLabel()
        self.layout.addWidget(self.summary_label)

        self.confidence_canvas = FigureCanvas(plt.figure(figsize=(5, 3)))
        self.layout.addWidget(self.confidence_canvas)

        self.table_widget = QTableWidget()
        self.layout.addWidget(self.table_widget)

        self.training_log_text = QTextEdit()
        self.training_log_text.setReadOnly(True)
        self.layout.addWidget(QLabel("📚 Last Training Summary:"))
        self.layout.addWidget(self.training_log_text)

        self.load_metrics()

    def load_metrics(self):
        # === Load Predictions ===
        if os.path.exists(self.prediction_file):
            df = safe_read_csv(filepath=self.prediction_file)
            if df is not None and not df.empty:
                df.columns = [
                    "s1", "s2", "s3", "s4", "symbol", "time",
                    "open", "close", "high", "low", "volume", "predicted"
                ]
                df["predicted"] = pd.to_numeric(df["predicted"], errors="coerce")
                df = df.dropna(subset=["predicted"])

                # Direction classification
                df["direction"] = df["predicted"].apply(
                    lambda p: "up" if p >= 0.55 else "down" if p <= 0.45 else "neutral"
                )

                total = len(df)
                ups = (df["direction"] == "up").sum()
                downs = (df["direction"] == "down").sum()
                neutrals = (df["direction"] == "neutral").sum()

                self.summary_label.setText(
                    f"<b>Total:</b> {total} | <b>Up:</b> {ups} | "
                    f"<b>Down:</b> {downs} | <b>Neutral:</b> {neutrals}"
                )

                # Plot histogram
                self.confidence_canvas.figure.clf()
                ax = self.confidence_canvas.figure.add_subplot(111)
                df["predicted"].hist(bins=30, ax=ax, color="#3c8dbc", alpha=0.8)
                ax.set_title("Confidence Score Histogram")
                ax.set_xlabel("Confidence")
                ax.set_ylabel("Frequency")
                self.confidence_canvas.draw()

                # Last predictions table
                self.load_table(df.tail(10))
            else:
                self.summary_label.setText("⚠️ Prediction file empty.")
        else:
            self.summary_label.setText("⚠️ No prediction data found.")

        # === Load Training Log ===
        if os.path.exists(self.training_log):
            with open(self.training_log, "r") as f:
                lines = f.readlines()
                last_lines = "".join(lines[-30:])  # show only last 30 lines
                self.training_log_text.setText(last_lines)
        else:
            self.training_log_text.setText("⚠️ No training log found.")

    def load_table(self, df):
        df = df.copy()
        df["datetime"] = df["time"].apply(
            lambda t: datetime.fromtimestamp(int(float(t))).strftime('%Y-%m-%d %H:%M:%S')
        )
        cols = ["datetime", "symbol", "direction", "predicted"]

        self.table_widget.setRowCount(len(df))
        self.table_widget.setColumnCount(len(cols))
        self.table_widget.setHorizontalHeaderLabels(cols)

        for row in range(len(df)):
            for col in range(len(cols)):
                val = str(df.iloc[row][cols[col]])
                self.table_widget.setItem(row, col, QTableWidgetItem(val))

        self.table_widget.resizeColumnsToContents()
