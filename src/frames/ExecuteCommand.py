from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QComboBox, QMessageBox, QGroupBox, QGridLayout
)


class ExecuteCommand(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.tp_input = None
        self.theme_button = None
        self.lot_input = None
        self.symbol_input = None
        self.sl_input = None
        self.controller = controller
        self.dark_mode = False  # default light mode
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("MT4 Command Center")
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignTop)

        # === Header with Title + Theme Toggle ===
        header = QHBoxLayout()
        title = QLabel("🧭 Execute MT4 Command")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setAlignment(Qt.AlignLeft)
        header.addWidget(title)

        self.theme_button = QPushButton("🌙 Dark Mode")
        self.theme_button.setFixedHeight(30)
        self.theme_button.clicked.connect(self.toggle_theme)
        self.theme_button.setStyleSheet("""
            QPushButton {
                background-color: #0078d7;
                color: white;
                border-radius: 8px;
                font-weight: 600;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #005ea6;
            }
        """)
        header.addWidget(self.theme_button, alignment=Qt.AlignRight)

        layout.addLayout(header)
        layout.addLayout(self.build_form())
        layout.addWidget(self.build_button_palette())
        layout.addWidget(self.build_send_box())

        self.apply_light_theme()
        self.update_visibility()

    # ========================== UI SECTIONS ==========================
    def build_form(self):
        form_layout = QVBoxLayout()

        # === Command Dropdown ===
        cmd_layout = QHBoxLayout()
        cmd_layout.addWidget(QLabel("Command:"))
        self.command_combo = QComboBox()
        self.command_combo.addItems([
            "buy", "sell", "buylimit", "selllimit", "buystop", "sellstop",
            "pause", "shutdown", "close_all", "account_info", "open_positions"
        ])
        self.command_combo.currentTextChanged.connect(self.update_visibility)
        cmd_layout.addWidget(self.command_combo)
        form_layout.addLayout(cmd_layout)

        # === Input fields ===
        for label, attr, default in [
            ("Symbol:", "symbol_input", "EURUSD"),
            ("Lot Size:", "lot_input", "0.1"),
            ("Stop Loss (pips):", "sl_input", "50"),
            ("Take Profit (pips):", "tp_input", "40"),
        ]:
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            field = QLineEdit(default)
            setattr(self, attr, field)
            row.addWidget(field)
            form_layout.addLayout(row)

        return form_layout

    def build_button_palette(self):
        """Creates calculator-like palette of trade commands"""
        box = QGroupBox("🎛️ Command Palette")
        grid = QGridLayout()

        palette_buttons = [
            ("BUY", "#28a745"), ("SELL", "#dc3545"),
            ("BUY LIMIT", "#218838"), ("SELL LIMIT", "#c82333"),
            ("BUY STOP", "#1e7e34"), ("SELL STOP", "#a71d2a"),
            ("CLOSE ALL", "#6f42c1"), ("PAUSE", "#ffc107"),
            ("SHUTDOWN", "#343a40")
        ]

        for i, (label, color) in enumerate(palette_buttons):
            btn = QPushButton(label)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    border-radius: 8px;
                    font-weight: bold;
                    padding: 10px;
                    min-width: 90px;
                }}
                QPushButton:hover {{
                    opacity: 0.85;
                }}
            """)
            btn.clicked.connect(lambda _, l=label: self.quick_send(l.lower().replace(" ", "")))
            grid.addWidget(btn, i // 3, i % 3)

        box.setLayout(grid)
        return box

    def build_send_box(self):
        box = QGroupBox("📤 Command Controls")
        box_layout = QHBoxLayout()
        self.send_button = QPushButton("🚀 Send Command to MT4")
        self.send_button.setFixedHeight(45)
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #0078d7;
                color: white;
                border-radius: 10px;
                font-weight: bold;
                font-size: 15px;
            }
            QPushButton:hover {
                background-color: #005ea6;
            }
        """)
        self.send_button.clicked.connect(self.send_command)
        box_layout.addStretch()
        box_layout.addWidget(self.send_button)
        box_layout.addStretch()
        box.setLayout(box_layout)
        return box

    # ========================== THEME TOGGLE ==========================
    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        if self.dark_mode:
            self.apply_dark_theme()
            self.theme_button.setText("☀️ Light Mode")
        else:
            self.apply_light_theme()
            self.theme_button.setText("🌙 Dark Mode")

    def apply_light_theme(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                color: #222;
            }
            QLabel {
                font-size: 13px;
            }
            QLineEdit {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 6px;
                padding: 6px;
            }
            QLineEdit:focus {
                border: 1px solid #0078d7;
            }
            QGroupBox {
                border: 1px solid #ddd;
                border-radius: 8px;
                background-color: #ffffff;
                padding: 8px;
                margin-top: 10px;
            }
        """)

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #121212;
                color: #e0e0e0;
            }
            QLabel {
                font-size: 13px;
                color: #ddd;
            }
            QLineEdit {
                background-color: #1e1e1e;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 6px;
                color: white;
            }
            QLineEdit:focus {
                border: 1px solid #00b4d8;
            }
            QGroupBox {
                border: 1px solid #333;
                border-radius: 8px;
                background-color: #1a1a1a;
                padding: 8px;
                margin-top: 10px;
            }
            QPushButton {
                color: white;
            }
        """)

    # ========================== LOGIC ==========================
    def update_visibility(self):
        trade_cmds = ["buy", "sell", "buylimit", "selllimit", "buystop", "sellstop"]
        show_fields = self.command_combo.currentText() in trade_cmds

        self.symbol_input.setVisible(show_fields)
        self.lot_input.setVisible(show_fields)
        self.sl_input.setVisible(show_fields)
        self.tp_input.setVisible(show_fields)

    def quick_send(self, cmd):
        self.command_combo.setCurrentText(cmd)
        self.send_command()

    def send_command(self):
        cmd = self.command_combo.currentText()
        try:
            payload = {"action": cmd}

            if cmd in ["buy", "sell", "buylimit", "selllimit", "buystop", "sellstop"]:
                payload["symbol"] = self.symbol_input.text().strip().upper()
                payload["lot"] = float(self.lot_input.text())
                payload["sl"] = int(self.sl_input.text())
                payload["tp"] = int(self.tp_input.text())

            if  self.controller.server is not None:
                self.controller.send_command(payload)
                QMessageBox.information(self, "Success", f"✅ '{cmd}' command sent successfully.")
            else:
                QMessageBox.warning(self, "Not Connected", "⚠️ MT4 Predictor not connected.")
        except ValueError:
            QMessageBox.critical(self, "Input Error", "❌ Invalid numeric value in SL, TP, or Lot size.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"❌ Failed to send command: {e}")
