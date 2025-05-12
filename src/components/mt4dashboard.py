import os

import subprocess

import pandas as pd
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QComboBox, QSizePolicy, QTextEdit
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

LOG_PATH = "src/logs/predict_server.log"
MODEL_PATH = "src/model/model.keras"
TENSORBOARD_CMD = ["tensorboard", "--logdir", "logs", "--port", "6006"]
PREDICTION_CSV = "src/data/prediction_history.csv"

class PredictionChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.canvas = FigureCanvas(Figure(figsize=(5, 2), tight_layout=True))
        self.ax = self.canvas.figure.add_subplot(111)

        self.symbol_selector = QComboBox()
        self.symbol_selector.currentTextChanged.connect(self.update_chart)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Filter by Symbol:"))
        layout.addWidget(self.symbol_selector)
        layout.addWidget(self.canvas)
        self.setLayout(layout)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.populate_symbols()
        self.update_chart()

    def populate_symbols(self):
        self.symbol_selector.clear()
        if os.path.exists(PREDICTION_CSV):
            try:
                df = pd.read_csv(PREDICTION_CSV)
                if "symbol" in df.columns:
                    symbols = sorted(df["symbol"].dropna().unique())
                    self.symbol_selector.addItems(symbols)
            except Exception:
                self.symbol_selector.addItem("Error loading symbols")

    def update_chart(self):
        self.ax.clear()
        if os.path.exists(PREDICTION_CSV):
            try:
                df = pd.read_csv(PREDICTION_CSV)
                if {"timestamp", "confidence", "symbol"}.issubset(df.columns):
                    symbol = self.symbol_selector.currentText()
                    df = df[df["symbol"] == symbol].tail(100)
                    df["timestamp"] = pd.to_datetime(df["timestamp"])
                    self.ax.plot(df["timestamp"], df["confidence"], label=f"{symbol} Confidence")
                    self.ax.set_title(f"Prediction Confidence Over Time - {symbol}")
                    self.ax.set_xlabel("Time")
                    self.ax.set_ylabel("Confidence")
                    self.ax.legend()
                    self.canvas.figure.autofmt_xdate()
            except Exception as e:
                self.ax.text(0.5, 0.5, str(e), ha='center')
        else:
            self.ax.text(0.5, 0.5, "No prediction data yet", ha='center')
        self.canvas.draw()

class MT4Dashboard(QWidget):
    def __init__(self):
        super().__init__()

        self.command_output = None
        self.timer = None
        self.chart = None
        self.output_area = None
        self.gpu_status = None
        self.setWindowTitle("📊 MT4 AI Command Dashboard")
        self.setGeometry(200, 200, 900, 900)
        self.tensorboard_proc = None
        self.init_ui()
        self.init_timer()
    def init_ui(self):
     layout = QVBoxLayout()

    # Output area for logs
     self.output_area = QTextEdit()
     self.output_area.setReadOnly(True)
     self.output_area.setFont(QFont("Courier New", 10))
     self.output_area.setStyleSheet("background-color: #2E2E2E; color: #FFFFFF;")
     self.output_area.setText("Loading...")
     layout.addWidget(QLabel("🧾 Log Output:"))
     layout.addWidget(self.output_area)

    # Prediction chart
     self.chart = PredictionChart(self)
     self.chart.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
     self.chart.setMinimumHeight(200)
     self.chart.setMaximumHeight(400)
     layout.addWidget(QLabel("📈 Prediction Confidence Chart:"))
     layout.addWidget(self.chart)

    # GPU status area
     self.gpu_status = QTextEdit()
     self.gpu_status.setReadOnly(True)
     self.gpu_status.setFont(QFont("Courier New", 10))
     self.gpu_status.setStyleSheet("background-color: #1E1E1E; color: #00FF00;")
     layout.addWidget(QLabel("🖥 GPU Status:"))
     layout.addWidget(self.gpu_status)

     self.setLayout(layout)


    def refresh_log_output(self):
        if os.path.exists(LOG_PATH):
            with open(LOG_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()[-25:]
                self.output_area.setPlainText("".join(lines))

        try:
            result = subprocess.run(["nvidia-smi"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode == 0:
                self.gpu_status.setPlainText(result.stdout)
            else:
                self.gpu_status.setPlainText("nvidia-smi not available or failed.")
        except Exception as e:
            self.gpu_status.setPlainText(f"Error fetching GPU status: {e}")

        self.chart.update_chart()

    def init_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_log_output)
        self.timer.start(3000)
    def run_command(self):
        try:
            command = self.command_input.toPlainText().strip()
            if not command:
                self.command_output.setPlainText("⚠️ No command provided.")
                return
            result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output = result.stdout.strip() + ("\n" + result.stderr.strip() if result.stderr else "")
            self.command_output.setPlainText(output if output else "✅ Command executed successfully with no output.")
        except Exception as e:
            self.command_output.setPlainText(f"❌ Command error: {e}")



if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    dashboard = MT4Dashboard()
    dashboard.show()
    sys.exit(app.exec_())