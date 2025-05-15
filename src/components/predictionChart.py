import logging
import os
import pandas as pd
from PyQt5.QtWidgets import QWidget, QComboBox, QVBoxLayout, QLabel, QSizePolicy
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class PredictionChart(QWidget):
    def __init__(self, controller=None):
        super().__init__(controller)
        self.controller = controller
        self.canvas = FigureCanvas(Figure(figsize=(5, 2), tight_layout=True))
        self.ax = self.canvas.figure.add_subplot(111)

        self.symbol_selector = QComboBox()
        self.symbol_selector.addItems(
            [
                "EURUSD","AUDUSD"
            ]
        )

        self.symbol_selector.currentTextChanged.connect(self.update_chart)

        self.init_ui( )

    def init_ui(self):
        """Initialize the UI layout."""
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Filter by Symbol:"))
        layout.addWidget(self.symbol_selector)

        layout.setStretchFactor(self.canvas, 1)
        layout.setStretchFactor(self.symbol_selector, 0)
        layout.setStretchFactor(QLabel("Filter by Symbol:"), 0)
        self.setLayout(layout)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Pass the path of the prediction CSV from the controller
        prediction_csv_path = "../data/prediction_history.csv"
        self.load_prediction_data(prediction_csv_path)
        self.populate_symbols()
        self.update_chart()

    def load_prediction_data(self, prediction_csv=None):
        """Load prediction data from the CSV file."""
        if prediction_csv and os.path.exists(prediction_csv):
            try:
                return pd.read_csv(prediction_csv)
            except Exception as e:
                logging.error(f"Error reading prediction data from {prediction_csv}: {e}")
        return None

    def populate_symbols(self):
        """Populate the symbol selector with available symbols."""
        self.symbol_selector.clear()
        df = self.load_prediction_data()
        if df is not None and "symbol" in df.columns:
            symbols = sorted(df["symbol"].dropna().unique())
            self.symbol_selector.addItem("All")
            self.symbol_selector.addItems(symbols)

    def update_chart(self):
        """Update the chart based on the selected symbol.

        """
        self.ax.clear()
        df = self.load_prediction_data()
        if df is not None and {"timestamp", "confidence", "symbol"}.issubset(df.columns):
            symbol = self.symbol_selector.currentText()
            if symbol != "All":
                df = df[df["symbol"] == symbol]
            df = df.tail(100)  # Take the last 100 entries
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            self.ax.plot(df["timestamp"], df["confidence"], label=f"{symbol} Confidence")
            self.ax.set_title(f"Prediction Confidence Over Time - {symbol}")
            self.ax.set_xlabel("Time")
            self.ax.set_ylabel("Confidence")
            self.ax.legend()
            self.canvas.figure.autofmt_xdate()
        else:
            self.ax.text(0.5, 0.5, "No prediction data available", ha='center', va='center')

        self.canvas.draw()
