from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QComboBox, QMessageBox, QGroupBox, QFrame
)
from PyQt5.QtGui import QFont


class ExecuteCommand(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.symbol_input = None
        self.sl_input = None
        self.send_button = None
        self.command_combo = None
        self.controller = controller
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # === Title ===
        title = QLabel("🧭 Execute MT4 Command")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(title)

        # === Command Input Section ===
        layout.addLayout(self.build_form())

        # === Send Button Box ===
        button_box = self.build_button_box()
        layout.addWidget(button_box)

        self.update_visibility()

    def build_form(self):
        form_layout = QVBoxLayout()

        # === Command Dropdown ===
        cmd_layout = QHBoxLayout()
        cmd_layout.addWidget(QLabel("Command:"))
        self.command_combo = QComboBox()
        self.command_combo.addItems([
            "buy", "sell","buylimit","selllimit","buystop","sellstop", "pause", "shutdown", "close_all",
            "account_info", "open_positions"
        ])
        self.command_combo.currentTextChanged.connect(self.update_visibility)
        cmd_layout.addWidget(self.command_combo)
        form_layout.addLayout(cmd_layout)

        # === Symbol Input ===
        symbol_layout = QHBoxLayout()
        symbol_layout.addWidget(QLabel("Symbol:"))
        self.symbol_input = QLineEdit("EURUSD")
        symbol_layout.addWidget(self.symbol_input)
        form_layout.addLayout(symbol_layout)

        # === Lot Size ===
        lot_layout = QHBoxLayout()
        lot_layout.addWidget(QLabel("Lot Size:"))
        self.lot_input = QLineEdit("0.1")
        lot_layout.addWidget(self.lot_input)
        form_layout.addLayout(lot_layout)

        # === Stop Loss ===
        sl_layout = QHBoxLayout()
        sl_layout.addWidget(QLabel("Stop Loss (pips):"))
        self.sl_input = QLineEdit("50")
        sl_layout.addWidget(self.sl_input)
        form_layout.addLayout(sl_layout)

        # === Take Profit ===
        tp_layout = QHBoxLayout()
        tp_layout.addWidget(QLabel("Take Profit (pips):"))
        self.tp_input = QLineEdit("40")
        tp_layout.addWidget(self.tp_input)
        form_layout.addLayout(tp_layout)

        return form_layout

    def build_button_box(self):
        box = QGroupBox("📤 Command Controls")
        box.setStyleSheet("QGroupBox { font-weight: bold; margin-top: 10px; }")
        box_layout = QHBoxLayout()
        self.send_button = QPushButton("🚀 Send Command to MT4")
        self.send_button.setFixedHeight(40)
        self.send_button.setStyleSheet("font-size: 14px;")
        self.send_button.clicked.connect(self.send_command)

        box_layout.addStretch()
        box_layout.addWidget(self.send_button)
        box_layout.addStretch()

        box.setLayout(box_layout)
        return box

    def update_visibility(self):
        trade_cmds = ["buy", "sell"]
        show_fields = self.command_combo.currentText() in trade_cmds

        self.symbol_input.setVisible(show_fields)
        self.lot_input.setVisible(show_fields)
        self.sl_input.setVisible(show_fields)
        self.tp_input.setVisible(show_fields)

    def send_command(self):
        cmd = self.command_combo.currentText()
        try:
            payload = {"action": cmd}

            if cmd in ["buy", "sell"]:
                payload["symbol"] = self.symbol_input.text().strip().upper()
                payload["lot"] = float(self.lot_input.text())
                payload["sl"] = int(self.sl_input.text())
                payload["tp"] = int(self.tp_input.text())

            self.controller.predict_server.send_command(payload)
            QMessageBox.information(self, "Success", f"✅ '{cmd}' command sent successfully.")

        except ValueError:
            QMessageBox.critical(self, "Input Error", "❌ Invalid numeric value in SL, TP, or Lot size.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"❌ Failed to send command: {e}")
