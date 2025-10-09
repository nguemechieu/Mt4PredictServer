import os
import pandas as pd
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QMessageBox, QHBoxLayout
)


class AccountInfo(QWidget):
    """Widget to display live account information and open positions."""

    def __init__(self, controller=None):
        super().__init__()
        self.setWindowTitle("💼 Account Info & Positions")
        self.resize(950, 600)
        self.controller = controller

        # === File paths ===
        self.account_info_path = "./src/data/account_info.csv"
        self.open_orders_path = "./src/data/open_orders.csv"

        # === Layout ===
        layout = QVBoxLayout()
        self.setLayout(layout)

        # --- Header ---
        self.header_label = QLabel("📊 Account Overview")
        layout.addWidget(self.header_label)

        self.status_label = QLabel("🕒 Waiting for data...")
        layout.addWidget(self.status_label)

        self.account_info_label = QLabel()
        self.account_info_label.setTextFormat(Qt.RichText)
        layout.addWidget(self.account_info_label)

        # --- Table for open positions ---
        layout.addWidget(QLabel("📄 Open Positions:"))
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        # --- Buttons ---
        button_layout = QHBoxLayout()
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.load_data)
        clear_btn = QPushButton("🧹 Clear Data")
        clear_btn.clicked.connect(self.clear_data)
        button_layout.addWidget(refresh_btn)
        button_layout.addWidget(clear_btn)
        layout.addLayout(button_layout)

        # --- Auto refresh every 15 seconds ---
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.load_data)
        self.timer.start(15000)

        # --- Initial load ---
        self.load_data()

    # ---------------------------------------------------------------------
    def load_data(self):
        """Load both account info and open positions."""
        self.load_account_info()
        self.load_open_positions()

    # ---------------------------------------------------------------------
    def load_account_info(self):
        """Fetch and display account information from CSV."""
        if not os.path.exists(self.account_info_path):
            self.account_info_label.setText("⚠️ No account info file found.")
            self.status_label.setText("⚠️ Waiting for account data...")
            return

        try:
            df = pd.read_csv(self.account_info_path)

            if df.empty:
                self.account_info_label.setText("⚠️ Account info is empty.")
                return

            # Take latest record
            info = df.iloc[-1].to_dict()

            balance = info.get("balance", 0.0)
            equity = info.get("equity", 0.0)
            margin = info.get("margin", 0.0)
            free = info.get("free_margin", 0.0)
            leverage = info.get("leverage", 0)
            acc_num = info.get("account_number", "N/A")
            acc_name = info.get("account_name", "N/A")

            info_text = (
                f"<b>Account:</b> {acc_num} ({acc_name})<br>"
                f"<b>Balance:</b> ${balance:,.2f} | "
                f"<b>Equity:</b> ${equity:,.2f} | "
                f"<b>Margin:</b> ${margin:,.2f} | "
                f"<b>Free Margin:</b> ${free:,.2f} | "
                f"<b>Leverage:</b> {leverage}x"
            )

            self.account_info_label.setText(info_text)
            self.status_label.setText("🟢 Account info loaded.")
        except Exception as e:
            self.status_label.setText("❌ Failed to load account info.")
            QMessageBox.critical(self, "Error", f"Failed to load account info:\n{e}")

    # ---------------------------------------------------------------------
    def load_open_positions(self):
        """Load and display open positions from CSV."""
        if not os.path.exists(self.open_orders_path):
            self.table.setRowCount(0)
            self.status_label.setText("⚠️ No open orders file found.")
            return

        try:
            df = pd.read_csv(self.open_orders_path)

            if df.empty:
                self.table.setRowCount(0)
                self.status_label.setText("⚠️ No open positions available.")
                return

            # --- Define expected columns ---
            columns = ["ticket", "symbol", "type", "lots", "open_price",
                       "sl", "tp", "profit", "comment"]

            # Normalize and fill missing columns
            df.columns = [c.strip().lower() for c in df.columns]
            for col in columns:
                if col not in df.columns:
                    df[col] = ""

            # --- Populate table ---
            self.table.setColumnCount(len(columns))
            self.table.setHorizontalHeaderLabels(columns)
            self.table.setRowCount(len(df))

            for row_idx, row in df.iterrows():
                for col_idx, col in enumerate(columns):
                    value = str(row[col])
                    item = QTableWidgetItem(value)

                    # Profit color
                    if col == "profit":
                        try:
                            pval = float(value)
                            if pval < 0:
                                item.setForeground(Qt.red)
                            elif pval > 0:
                                item.setForeground(Qt.darkGreen)
                        except ValueError:
                            pass

                    self.table.setItem(row_idx, col_idx, item)

            self.table.resizeColumnsToContents()
            self.status_label.setText("🟢 Open positions loaded.")

        except Exception as e:
            self.table.setRowCount(0)
            self.status_label.setText("❌ Failed to load open positions.")
            QMessageBox.critical(self, "Error", f"Failed to load open positions:\n{e}")

    # ---------------------------------------------------------------------
    def clear_data(self):
        """Clear account info and open positions."""
        try:
            if os.path.exists(self.account_info_path):
                os.remove(self.account_info_path)
            if os.path.exists(self.open_orders_path):
                os.remove(self.open_orders_path)
            self.table.setRowCount(0)
            self.account_info_label.setText("⚠️ Cleared account data.")
            self.status_label.setText("🧹 Data cleared.")
        except Exception as e:
            QMessageBox.warning(self, "Clear Error", f"Failed to clear data:\n{e}")
