import os
from datetime import datetime

import matplotlib.pyplot as plt
import pandas as pd
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QTextEdit
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas



class AccountMetrics(QWidget):
    def __init__(self,controller):
        super().__init__(controller)
        self.setWindowTitle("📊 Account Metrics & AI Analysis")
        self.resize(1000, 700)
        self.controller=controller

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
        if os.path.exists(self.prediction_file):
            df = self.controller.predict_server.safe_read_csv(self.prediction_file)
            df.columns = ["s1", "s2", "s3", "s4", "symbol", "time", "open", "close", "high", "low", "volume", "predicted"]
            df["predicted"] = pd.to_numeric(df["predicted"], errors="coerce")
            df = df.dropna(subset=["predicted"])
            df["direction"] = df["predicted"].apply(lambda p: "up" if p >= 0.55 else "down" if p <= 0.45 else "neutral")

            total = len(df)
            ups =+ (df["direction"] == "up")
            downs = +(df["direction"] == "down")
            neutrals = +(df["direction"] == "neutral")

            self.summary_label.setText(
                f"<b>Total:</b> {total} | <b>Up:</b> {ups} | <b>Down:</b> {downs} | <b>Neutral:</b> {neutrals}"
            )

            # Plot histogram
            ax = self.confidence_canvas.figure.subplots()
            ax.clear()
            df["predicted"].hist(bins=30, ax=ax)
            ax.set_title("Confidence Score Histogram")
            ax.set_xlabel("Confidence")
            ax.set_ylabel("Frequency")
            self.confidence_canvas.draw()

            # Last predictions table
            self.load_table(df.tail(10))
        else:
            self.summary_label.setText("⚠️ No prediction data found.")

        if os.path.exists(self.training_log):
            with open(self.training_log, "r") as f:
                self.training_log_text.setText(f.read())
        else:
            self.training_log_text.setText("⚠️ No training log found.")

    def load_table(self, df):
        df = df.copy()
        df["datetime"] = df["time"].apply(lambda t: datetime.fromtimestamp(int(t)).strftime('%Y-%m-%d %H:%M:%S'))
        cols = ["datetime", "symbol", "direction", "predicted"]

        self.table_widget.setRowCount(len(df))
        self.table_widget.setColumnCount(len(cols))
        self.table_widget.setHorizontalHeaderLabels(cols)

        for row in range(len(df)):
            for col in range(len(cols)):
                val = str(df.iloc[row][cols[col]])
                self.table_widget.setItem(row, col, QTableWidgetItem(val))

        self.table_widget.resizeColumnsToContents()
