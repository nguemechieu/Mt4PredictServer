import os
import time
import pandas as pd
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QTimer
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableView,
    QPushButton, QHBoxLayout, QSizePolicy, QMessageBox
)


# ==========================================================
# Model for Live Predictions
# ==========================================================
class PredictionsModel(QAbstractTableModel):
    """Model to store and render live predictions (with GPT analysis)."""

    def __init__(self):
        super().__init__()
        self.headers = ["Symbol", "Direction", "Confidence", "Timestamp", "Analysis"]
        self.data_list = []

    def rowCount(self, parent=QModelIndex()):
        return len(self.data_list)

    def columnCount(self, parent=QModelIndex()):
        return len(self.headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        row, col = index.row(), index.column()
        value = self.data_list[row][col]

        if role == Qt.DisplayRole:
            if col == 2:  # Confidence
                try:
                    return f"{float(value) * 100:.2f}%"
                except Exception:
                    return str(value)
            elif col == 3:  # Timestamp
                try:
                    return time.strftime("%H:%M:%S", time.localtime(float(value)))
                except Exception:
                    return str(value)
            elif col == 4:  # Analysis
                text = str(value)
                return text[:80] + ("..." if len(text) > 80 else "")
            return str(value)

        elif role == Qt.TextAlignmentRole:
            return Qt.AlignCenter

        elif role == Qt.ForegroundRole and col == 1:
            val = str(value).upper()
            if val in ["UP", "BUY"]:
                return QColor("#00ff66")
            elif val in ["DOWN", "SELL"]:
                return QColor("#ff4444")

        elif role == Qt.ToolTipRole and col == 4:
            return str(value)  # Full GPT explanation tooltip

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.headers[section]
        return None

    def load_from_dataframe(self, df: pd.DataFrame = None):
        """Safely load predictions including GPT analysis."""
        self.beginResetModel()
        if df is None or df.empty:
            self.data_list = []
        else:
            # Normalize column names (case-insensitive)
            df.columns = [c.strip().capitalize() for c in df.columns]
            for col in self.headers:
                if col not in df.columns:
                    df[col] = ""
            self.data_list = df[self.headers].values.tolist()
        self.endResetModel()

    def clear(self):
        """Clear all rows."""
        self.beginResetModel()
        self.data_list = []
        self.endResetModel()


# ==========================================================
# Live Predictions UI Frame
# ==========================================================
class LivePredictionsFrame(QWidget):
    """UI frame to display live predictions and GPT explanations."""

    def __init__(self, controller=None):
        super().__init__()
        self.controller = controller
        self.model = PredictionsModel()

        # File path for saved predictions
        self.predictions_path = "./src/data/predictions.csv"

        # --- UI Layout ---
        layout = QVBoxLayout(self)
        title = QLabel("🤖 Live Predictions (with AI Analysis)")
        title.setFont(QFont("Segoe UI Emoji", 13, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # --- Table setup ---
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setAlternatingRowColors(True)
        self.table.setFont(QFont("Consolas", 10))
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        self.table.verticalHeader().hide()
        layout.addWidget(self.table)

        # --- No Data Label ---
        self.no_data_label = QLabel("⚠️ No predictions available.")
        self.no_data_label.setFont(QFont("Segoe UI", 11))
        self.no_data_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.no_data_label)
        self.no_data_label.hide()

        # --- Buttons ---
        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton("🔄 Refresh Data")
        refresh_btn.clicked.connect(self.refresh_data)
        clear_btn = QPushButton("🧹 Clear Predictions")
        clear_btn.clicked.connect(self.clear_predictions)
        btn_layout.addWidget(refresh_btn)
        btn_layout.addWidget(clear_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        # Initial data load
        self.refresh_data()

        # Auto-refresh every 10s
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_data)
        self.timer.start(10000)

    # ======================================================
    # Data Handling
    # ======================================================
    def _load_predictions_csv(self):
        """Helper: safely load CSV file to DataFrame."""
        if not os.path.exists(self.predictions_path):
            return pd.DataFrame(columns=self.model.headers)

        try:
            df = pd.read_csv(self.predictions_path)
            return df
        except Exception as e:
            QMessageBox.warning(self, "Read Error", f"Failed to read predictions:\n{e}")
            return pd.DataFrame(columns=self.model.headers)

    def refresh_data(self):
        """Reload predictions from CSV every few seconds."""
        df = self._load_predictions_csv()
        self.model.load_from_dataframe(df)

        has_data = df is not None and not df.empty
        self.no_data_label.setVisible(not has_data)
        self.table.setVisible(has_data)

        if has_data:
            self.table.scrollToBottom()

    def clear_predictions(self):
        """Clear table + delete CSV file."""
        self.model.clear()
        self.no_data_label.show()
        self.table.hide()

        try:
            if os.path.exists(self.predictions_path):
                os.remove(self.predictions_path)
        except Exception as e:
            QMessageBox.warning(self, "Delete Error", f"Failed to delete predictions file:\n{e}")
