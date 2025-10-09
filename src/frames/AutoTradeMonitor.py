from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit, QHBoxLayout, QPushButton
from PySide6.QtGui import QFont, QColor, QTextCursor
from PySide6.QtCore import  QTimer

from components.GPTAdvisor import GPTAdvisor


class AutoTradeMonitor(QWidget):
    """GUI dashboard for the GPT AutoTradeManager."""

    def __init__(self, controller=None):
        super().__init__()
        self.controller = controller
        self.autotrader = getattr(controller, "autotrade_manager", None)
        self.client = GPTAdvisor(self.controller)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # --- Header ---
        title = QLabel("🤖 Auto-Trading Monitor")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        layout.addWidget(title)

        # --- Status line ---
        self.status_label = QLabel("Status: 💤 Idle")
        self.status_label.setFont(QFont("Consolas", 12))
        layout.addWidget(self.status_label)

        # --- Decision history ---
        self.history_box = QTextEdit()
        self.history_box.setReadOnly(True)
        self.history_box.setFont(QFont("Courier New", 10))
        layout.addWidget(self.history_box)

        # --- Live reasoning stream ---
        layout.addWidget(QLabel("🧠 GPT Reasoning Stream:"))
        self.stream_box = QTextEdit()
        self.stream_box.setReadOnly(True)
        self.stream_box.setFont(QFont("Courier New", 10))
        layout.addWidget(self.stream_box)

        # --- Control buttons ---
        btn_row = QHBoxLayout()
        self.start_btn = QPushButton("▶️ Start Auto-Trading")
        self.stop_btn = QPushButton("⏹ Stop")
        self.clear_btn = QPushButton("🧹 Clear History")
        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.stop_btn)
        btn_row.addWidget(self.clear_btn)
        layout.addLayout(btn_row)

        # --- Connections ---
        self.start_btn.clicked.connect(self._start_autotrade)
        self.stop_btn.clicked.connect(self._stop_autotrade)
        self.clear_btn.clicked.connect(self.history_box.clear)

        if self.autotrader:
            self.autotrader.stream_signal.connect(self._append_stream)
            self.autotrader.decision_signal.connect(self._on_decision)

        # --- Periodic refresh ---
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh_status)
        self.timer.start(3000)

    # ------------------------------------------------------------
    def _start_autotrade(self):
        if self.autotrader:
            self.autotrader.start()
            self.status_label.setText("Status: 🚀 Running")

    def _stop_autotrade(self):
        if self.autotrader:
            self.autotrader.stop()
            self.status_label.setText("Status: 🛑 Stopped")

    def _append_stream(self, token: str):
        self.stream_box.moveCursor(QTextCursor.End)
        self.stream_box.insertPlainText(token)
        self.stream_box.verticalScrollBar().setValue(
            self.stream_box.verticalScrollBar().maximum()
        )

    def _on_decision(self, decision: dict):
        color = {
            "BUY": "#00ff99",
            "SELL": "#ff6666",
            "HOLD": "#cccccc",
        }.get(decision.get("action", "HOLD"), "#cccccc")

        self.history_box.moveCursor(QTextCursor.End)
        self.history_box.setTextColor(QColor(color))
        self.history_box.insertPlainText(
            f"{decision.get('action')} @ {decision.get('timestamp', '')}\n"
        )
        self.history_box.verticalScrollBar().setValue(
            self.history_box.verticalScrollBar().maximum()
        )
        self.stream_box.append("\n✅ Decision received.\n")

    def _refresh_status(self):
        if self.autotrader and self.autotrader.active:
            self.status_label.setText("Status: 🚀 Running")
        else:
            self.status_label.setText("Status: 💤 Idle")
