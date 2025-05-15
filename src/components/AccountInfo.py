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
        self.account_info = {}

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
        refresh_btn.clicked.connect(self.load_data)  # Fixed lambda issue
        button_layout.addWidget(refresh_btn)
        self.layout.addLayout(button_layout)

        # Auto-refresh every 15 seconds
        self.timer = QTimer()
        self.timer.timeout.connect(self.load_data)  # Fixed lambda issue
        self.timer.start(15000)

        self.load_data()

    def load_data(self):
        """Load account info and open positions."""
        self.load_account_info()
        self.load_open_positions()

    def load_account_info(self):
        """Fetch and display account information."""
        try:
            account_info = self.controller.predict_server.get_account_info()

            if not account_info:
                self.status_label.setText("⚠️ Account info not available.")
                return

            info_text = (
                f"<b>Balance:</b> ${account_info['Balance']:.2f} | "
                f"<b>Equity:</b> ${account_info['Equity']:.2f} | "
                f"<b>Margin:</b> ${account_info['Margin']:.2f} | "
                f"<b>Free Margin:</b> ${account_info['FreeMargin']:.2f} | "
                f"<b>Leverage:</b> {account_info['Leverage']}x"
            )
            self.account_info_label.setText(info_text)
            self.status_label.setText("🟢 Account info loaded.")

        except Exception as e:  # Replaced bare `except`
            QMessageBox.critical(self, "Error", f"Failed to load account info:\n{e}")

    def load_open_positions(self):
        """Fetch and display open positions."""
        try:
            positions = self.controller.predict_server.get_open_position()

            if not positions:
                self.status_label.setText("⚠️ No open positions available.")
                self.table.setRowCount(0)
                return

            expected_cols = ["Ticket", "Symbol", "Type", "Lots", "OpenPrice", "SL", "TP", "Profit"]
            self.table.setRowCount(len(positions))
            self.table.setColumnCount(len(expected_cols))
            self.table.setHorizontalHeaderLabels(expected_cols)

            for row, position in enumerate(positions):
                for col, col_name in enumerate(expected_cols):
                    val = str(position.get(col_name, ""))
                    item = QTableWidgetItem(val)

                    if col_name == "Profit":
                        try:
                            profit_val = float(val)
                            if profit_val < 0:
                                item.setForeground(Qt.red)
                            elif profit_val > 0:
                                item.setForeground(Qt.darkGreen)
                        except Exception:  # Replaced bare `except`
                            pass

                    self.table.setItem(row, col, item)

            self.table.resizeColumnsToContents()
            self.status_label.setText("🟢 Open positions loaded.")

        except Exception as e:  # Replaced bare `except`
            QMessageBox.critical(self, "Error", f"Failed to load open positions:\n{e}")