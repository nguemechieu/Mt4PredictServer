# frames/GPTChat.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel
)
from PySide6.QtGui import QColor, QTextCursor, QFont, QKeyEvent
from PySide6.QtCore import Qt
import os


class GPTChatFrame(QWidget):
    def __init__(self, controller=None):
        super().__init__()
        self.controller = controller
        self.gpt = getattr(controller, "gpt", None)
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)

        # --- Header ---
        self.header = QLabel("🤖 GPT Assistant Chat")
        self.header.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(self.header)

        # --- Chat Display ---
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont("Consolas", 10))
        layout.addWidget(self.chat_display, stretch=3)

        # --- Input Area (multiline) ---
        input_box_layout = QHBoxLayout()
        self.input_box = QTextEdit()
        self.input_box.setFont(QFont("Segoe UI", 11))
        self.input_box.setPlaceholderText(
            "Ask me about trading signals, account info, or paste logs here..."
        )
        self.input_box.setFixedHeight(80)  # Larger typing area
        self.input_box.installEventFilter(self)  # capture Enter press
        self.send_button = QPushButton("Send")
        self.send_button.setFixedHeight(60)
        self.send_button.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.send_button.clicked.connect(self._on_send_clicked)

        input_box_layout.addWidget(self.input_box, stretch=4)
        input_box_layout.addWidget(self.send_button, stretch=1)

        layout.addLayout(input_box_layout)
        self.setLayout(layout)

    # --- Capture Enter Press ---
    def eventFilter(self, source, event):
        if source == self.input_box and event.type() == QKeyEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if event.modifiers() & Qt.ShiftModifier:
                    # Shift+Enter for newline
                    self.input_box.insertPlainText("\n")
                else:
                    # Enter alone sends message
                    self._on_send_clicked()
                return True
        return super().eventFilter(source, event)

    def _connect_signals(self):
        if self.gpt:
            self.gpt.stream_signal.connect(self._append_stream)
            self.gpt.done_signal.connect(self._on_stream_done)
            self.gpt.error_signal.connect(self._on_stream_error)

    def _on_send_clicked(self):
        user_text = self.input_box.toPlainText().strip()
        if not user_text:
            return

        self._append_message("You", user_text, QColor("#00ccff"))
        self.input_box.clear()

        # Include logs automatically if relevant
        if any(k in user_text.lower() for k in ["log", "error", "analyze"]):
            logs = self._get_recent_logs()
            payload = {"query": user_text, "logs": logs}
            self._append_message("System", "📊 Fetching recent logs for GPT analysis...", QColor("#ffaa00"))
        else:
            payload = {"query": user_text}

        if self.gpt:
            self._append_message("GPT", "⏳ Thinking...", QColor("#aaaaaa"))
            self.gpt.analyze_signal_stream(payload)
        else:
            self._append_message("System", "⚠️ GPT not initialized.", QColor("#ff4444"))

    def _get_recent_logs(self, max_lines=60):
        log_path = "src/logs/predict_server.log"
        if not os.path.exists(log_path):
            return "⚠️ No log file found."
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        return "".join(lines[-max_lines:])

    def _append_message(self, sender, text, color):
        self.chat_display.moveCursor(QTextCursor.End)
        fmt = self.chat_display.currentCharFormat()
        fmt.setForeground(color)
        self.chat_display.setCurrentCharFormat(fmt)
        self.chat_display.insertPlainText(f"\n{sender}: {text}\n")
        self.chat_display.verticalScrollBar().setValue(
            self.chat_display.verticalScrollBar().maximum()
        )

    def _append_stream(self, token):
        self.chat_display.moveCursor(QTextCursor.End)
        fmt = self.chat_display.currentCharFormat()
        fmt.setForeground(QColor("#00ff99"))
        self.chat_display.setCurrentCharFormat(fmt)
        self.chat_display.insertPlainText(token)
        self.chat_display.verticalScrollBar().setValue(
            self.chat_display.verticalScrollBar().maximum()
        )

    def _on_stream_done(self, _):
        self.chat_display.append("\n✅ Done.\n")

    def _on_stream_error(self, msg):
        self.chat_display.append(f"\n❌ {msg}\n")
