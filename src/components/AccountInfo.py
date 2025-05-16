from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QMessageBox, QHBoxLayout
)


class AccountInfo(QWidget):
    """Widget to display account information and open positions."""
    def __init__(self, controller):
        super().__init__()
        self.setWindowTitle("💼 Account Info & Positions")
        self.resize(900, 600)
        self.controller = controller

        # === Layout ===
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.header_label = QLabel("📊 Account Overview")
        self.layout.addWidget(self.header_label)

        self.status_label = QLabel("🕒 Waiting for data...")
        self.layout.addWidget(self.status_label)

        self.account_info_label = QLabel()
        self.layout.addWidget(self.account_info_label)

        self.layout.addWidget(QLabel("📄 Open Positions:"))
        self.table = QTableWidget()
        self.layout.addWidget(self.table)

        # Buttons
        button_layout = QHBoxLayout()
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.load_data)
        button_layout.addWidget(refresh_btn)
        self.layout.addLayout(button_layout)

        # Auto-refresh every 15 seconds
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.load_data)
        self.timer.start(15000)

        self.load_data()

    def load_data(self):
        """Load both account info and open positions."""
        self.load_account_info()
        self.load_open_positions()

    def load_account_info(self):
        """Fetch and display account information."""
        try:
            info = self.controller.predict_server.get_account_info()

            if not info or not isinstance(info, dict):
                self.account_info_label.setText("⚠️ Invalid account info received.")
                self.status_label.setText("⚠️ Account info not available.")
                return

            balance = info.get("balance", 0.0)
            equity = info.get("equity", 0.0)
            margin = info.get("margin", 0.0)
            leverage = info.get("leverage", 0)

            info_text = (
                f"<b>Balance:</b> ${balance:.2f} | "
                f"<b>Equity:</b> ${equity:.2f} | "
                f"<b>Margin:</b> ${margin:.2f} | "
                f"<b>Leverage:</b> {leverage}x"
            )
            self.account_info_label.setText(info_text)
            self.status_label.setText("🟢 Account info loaded.")

        except Exception as e:
            self.status_label.setText("❌ Failed to load account info.")
            QMessageBox.critical(self, "Error", f"Failed to load account info:\n{e}")

    def load_open_positions(self):
        """Fetch and display open positions."""
        try:
            positions = self.controller.predict_server.get_open_positions()

            if not positions or not isinstance(positions, list):
                self.table.setRowCount(0)
                self.status_label.setText("⚠️ No open positions available.")
                return

            columns = ["Ticket", "Symbol", "Type", "Lots", "OpenPrice", "SL", "TP", "Profit"]
            self.table.setRowCount(len(positions))
            self.table.setColumnCount(len(columns))
            self.table.setHorizontalHeaderLabels(columns)

            for row, pos in enumerate(positions):
                for col, name in enumerate(columns):
                    value = str(pos.get(name, ""))
                    item = QTableWidgetItem(value)

                    if name.lower() == "profit":
                        try:
                            pval = float(value)
                            if pval < 0:
                                item.setForeground(Qt.red)
                            elif pval > 0:
                                item.setForeground(Qt.darkGreen)
                        except Exception:
                            pass

                    self.table.setItem(row, col, item)

            self.table.resizeColumnsToContents()
            self.status_label.setText("🟢 Open positions loaded.")

        except Exception as e:
            self.table.setRowCount(0)
            self.status_label.setText("❌ Failed to load open positions.")
            QMessageBox.critical(self, "Error", f"Failed to load open positions:\n{e}")
