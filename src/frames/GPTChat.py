import os
import json
import threading
import time
import pyttsx3
import speech_recognition as sr  # ✅ Google Speech Recognition

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QTextCursor, QFont, QKeyEvent
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QLabel, QComboBox
)

SETTINGS_FILE = "src/config/tts_settings.json"


def _get_recent_logs(max_lines=60):
    log_path = "src/logs/predict_server.log"
    if not os.path.exists(log_path):
        return "⚠️ No log file found."
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    return "".join(lines[-max_lines:])


class GPTChatFrame(QWidget):
    """
    🤖 GPT Assistant Chat Frame
    Interactive Voice & Text Dialog
    ---------------------------------
    Features:
    - Online speech-to-text (Google)
    - Text-to-speech (pyttsx3 + eSpeak)
    - Continuous dialog loop
    - Voice selector (drop-down)
    - Visual listening indicator
    - GPT stream integration
    """

    def __init__(self, controller=None):
        super().__init__()
        self.controller = controller
        self.gpt = getattr(controller, "gpt", None)

        # --- Runtime state ---
        self.chat_display = None
        self.input_box = None
        self._last_gpt_response = ""
        self.auto_read = True
        self.is_listening = False
        self.dialog_active = False
        self._blinking = False

        # --- Voice & TTS ---
        self.tts_engine = pyttsx3.init()
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.voices = self.tts_engine.getProperty("voices")

        # --- UI ---
        self._init_ui()
        self._connect_signals()
        self._load_last_voice()

    # ==========================================================
    # UI SETUP
    # ==========================================================
    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)

        self.header = QLabel("🤖 GPT Assistant Chat")
        self.header.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(self.header)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont("Consolas", 10))
        layout.addWidget(self.chat_display, stretch=3)

        # --- Voice Selector ---
        self.voice_selector = QComboBox()
        for v in self.voices:
            self.voice_selector.addItem(v.name, v.id)
        self.voice_selector.setFixedHeight(40)
        self.voice_selector.currentIndexChanged.connect(self._on_voice_changed)
        layout.addWidget(self.voice_selector)

        # --- Input + Buttons ---
        input_layout = QHBoxLayout()
        self.input_box = QTextEdit()
        self.input_box.setFont(QFont("Segoe UI", 11))
        self.input_box.setPlaceholderText("Ask me about trading signals or speak to me...")
        self.input_box.setFixedHeight(80)
        self.input_box.installEventFilter(self)

        self.send_button = QPushButton("Send")
        self.read_button = QPushButton("🔊 Read")
        self.talk_button = QPushButton("🎤 Talk")
        self.stop_button = QPushButton("🛑 Stop")

        for btn in [self.send_button, self.read_button, self.talk_button, self.stop_button]:
            btn.setFixedHeight(60)

        input_layout.addWidget(self.input_box, stretch=4)
        input_layout.addWidget(self.send_button)
        input_layout.addWidget(self.read_button)
        input_layout.addWidget(self.talk_button)
        input_layout.addWidget(self.stop_button)
        layout.addLayout(input_layout)
        self.setLayout(layout)

        # Button connections
        self.send_button.clicked.connect(self._on_send_clicked)
        self.read_button.clicked.connect(self._on_read_clicked)
        self.talk_button.clicked.connect(self._on_talk_clicked)
        self.stop_button.clicked.connect(self._on_stop_clicked)

    # ==========================================================
    # EVENT FILTER (Enter Key)
    # ==========================================================
    def eventFilter(self, source, event):
        if source == self.input_box and event.type() == QKeyEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if event.modifiers() & Qt.ShiftModifier:
                    self.input_box.insertPlainText("\n")
                else:
                    self._on_send_clicked()
                return True
        return super().eventFilter(source, event)

    # ==========================================================
    # SIGNAL CONNECTIONS
    # ==========================================================
    def _connect_signals(self):
        if self.gpt:
            self.gpt.stream_signal.connect(self._append_stream)
            self.gpt.done_signal.connect(self._on_stream_done)
            self.gpt.error_signal.connect(self._on_stream_error)

    # ==========================================================
    # MESSAGE SENDING
    # ==========================================================
    def _on_send_clicked(self):
        try:
            user_text = self.input_box.toPlainText().strip()
            if not user_text:
                return
            self._append_message("You", user_text, QColor("#00ccff"))
            self.input_box.clear()
            self._last_gpt_response = ""
            self._clear_gpt_messages()

            payload = {"query": user_text}
            if any(k in user_text.lower() for k in ["log", "error", "analyze"]):
                payload["logs"] = _get_recent_logs()
                self._append_message("System", "📊 Fetching recent logs...", QColor("#ffaa00"))

            if self.gpt:
                self._append_message("GPT", "⏳ Thinking...", QColor("#aaaaaa"))
                self.gpt.analyze_signal_stream(payload)
            else:
                self._append_message("System", "⚠️ GPT not initialized.", QColor("#ff4444"))
        except Exception as e:
            self._append_message("System", str(e), QColor("#ff4444"))

    # ==========================================================
    # INTERACTIVE DIALOG LOOP
    # ==========================================================
    def _on_talk_clicked(self):
        if self.dialog_active:
            self.dialog_active = False
            self._append_message("System", "🛑 Conversation stopped.", QColor("#ffaa00"))
            return
        self.dialog_active = True
        self._append_message("System", "🎙️ Starting interactive conversation...", QColor("#00ff99"))
        threading.Thread(target=self._interactive_dialog_loop, daemon=True).start()

    def _interactive_dialog_loop(self):
        while self.dialog_active:
            user_text = self._listen_google()
            if not user_text:
                continue
            if any(word in user_text.lower() for word in ["stop", "exit", "cancel", "goodbye"]):
                self.dialog_active = False
                self._append_message("System", "🛑 Conversation ended by user.", QColor("#ffaa00"))
                break
            self._append_message("You (voice)", user_text, QColor("#00ccff"))
            payload = {"query": user_text}
            if "log" in user_text.lower():
                payload["logs"] = _get_recent_logs()

            if self.gpt:
                self._append_message("GPT", "⏳ Thinking...", QColor("#aaaaaa"))
                self.gpt.analyze_signal_stream(payload)
            else:
                self._append_message("System", "⚠️ GPT not initialized.", QColor("#ff4444"))
                break

            while self.auto_read and self.tts_engine.isBusy():
                time.sleep(0.5)
            time.sleep(0.3)

    def _listen_google(self):
        try:
            with self.microphone as source:
                self.is_listening = True
                self._start_blinking_indicator()
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                self._append_message("System", "🎧 Listening...", QColor("#ffaa00"))
                audio = self.recognizer.listen(source, timeout=8, phrase_time_limit=15)
            text = self.recognizer.recognize_google(audio)
            self._stop_blinking_indicator()
            self.is_listening = False
            if text:
                return text
        except sr.UnknownValueError:
            self._append_message("System", "😕 Didn't catch that. Try again.", QColor("#ffaa00"))
        except sr.RequestError as e:
            self._append_message("System", f"⚠️ Google API error: {e}", QColor("#ffaa00"))
            self.dialog_active = False
        except Exception as e:
            self._append_message("System", f"⚠️ Voice capture error: {e}", QColor("#ffaa00"))
        finally:
            self._stop_blinking_indicator()
            self.is_listening = False
        return None


    def _speak_text(self, text=''):
        try:
            self.tts_engine.stop()
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
        except Exception as e:
            self._append_message("System", f"❌ TTS Error: {e}", QColor("#ff4444"))

    # ==========================================================
    # VOICE SELECTION
    # ==========================================================
    def _on_voice_changed(self, index):
        try:
            selected_voice = self.voice_selector.itemData(index)
            self.tts_engine.setProperty("voice", selected_voice)
            self._save_last_voice(selected_voice)
            voice_name = self.voices[index].name
            self._append_message("System", f"🎤 Voice changed to {voice_name}", QColor("#00ff99"))
        except Exception as e:
            self._append_message("System", f"⚠️ Could not change voice: {e}", QColor("#ffaa00"))

    def _save_last_voice(self, voice_id):
        try:
            os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump({"voice_id": voice_id}, f)
        except Exception as e:
            print("Could not save voice:", e)

    def _load_last_voice(self):
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    voice_id = data.get("voice_id")
                    if voice_id:
                        self.tts_engine.setProperty("voice", voice_id)
                        for i in range(self.voice_selector.count()):
                            if self.voice_selector.itemData(i) == voice_id:
                                self.voice_selector.setCurrentIndex(i)
                                break
            self._append_message("System", "🔊 Voice loaded successfully.", QColor("#00ff99"))
        except Exception as e:
            self._append_message("System", f"⚠️ Could not load voice: {e}", QColor("#ffaa00"))



    # ==========================================================
    # HELPERS
    # ==========================================================
    def _append_message(self, sender: str, text: str, color: QColor):
        self.chat_display.moveCursor(QTextCursor.End)
        fmt = self.chat_display.currentCharFormat()
        fmt.setForeground(color)
        self.chat_display.setCurrentCharFormat(fmt)
        self.chat_display.insertPlainText(f"\n{sender}: {text}\n")
        self.chat_display.verticalScrollBar().setValue(self.chat_display.verticalScrollBar().maximum())

    def _clear_gpt_messages(self):
        self.chat_display.append("\n--- New Question ---\n")
        self._last_gpt_response = ""

    def _on_stop_clicked(self):
        self.dialog_active = False
        self.is_listening = False
        if self.chat_display:
            self.chat_display.clear()

        self.tts_engine.stop()
        self._stop_blinking_indicator()
        self._append_message("System", "🛑 Conversation stopped manually.", QColor("#ffaa00"))

    # ==========================================================
    # LISTENING INDICATOR (Blinking 🎙️)
    # ==========================================================
    def _start_blinking_indicator(self):
        if self._blinking:
            return
        self._blinking = True
        self._blink_timer = QTimer(self)
        self._blink_state = False
        self._blink_timer.timeout.connect(self._update_header_blink)
        self._blink_timer.start(500)

    def _stop_blinking_indicator(self):
        self._blinking = False
        if hasattr(self, "_blink_timer"):
            self._blink_timer.stop()
        self.header.setText("🤖 GPT Assistant Chat")

    def _update_header_blink(self):
        if not self._blinking:
            return
        self._blink_state = not self._blink_state
        self.header.setText("🎙️ Listening..." if self._blink_state else "🤖 GPT Assistant Chat")
    # ==========================================================
    # GPT STREAM EVENTS (AUTO READ FIXED)
    # ==========================================================
    def _append_stream(self, token):
        """Append live GPT token stream and collect response."""
        self.chat_display.moveCursor(QTextCursor.End)
        fmt = self.chat_display.currentCharFormat()
        fmt.setForeground(QColor("#00ff99"))
        self.chat_display.setCurrentCharFormat(fmt)
        self.chat_display.insertPlainText(token)
        self.chat_display.verticalScrollBar().setValue(
            self.chat_display.verticalScrollBar().maximum()
        )
        self._last_gpt_response += token

    def _on_stream_done(self, _):
        """When GPT finishes streaming, finalize and auto-read."""
        self._last_gpt_response = self._last_gpt_response.strip()
        if not self._last_gpt_response:
            return

        # Append the 'Done' marker
        self.chat_display.append("\n\n")


        # ✅ Ensure auto-reading of every GPT answer
        if self.auto_read:
            self._read_or_speak(self._last_gpt_response)

    def _on_stream_error(self, msg):
        self.chat_display.append(f"\n❌Error: {msg}\n")

    # ==========================================================
    # SMART READ FUNCTION (ALWAYS READ OR READ SELECTED TEXT)
    # ==========================================================
    def _on_read_clicked(self):
        """Read the last GPT response or any selected text."""
        cursor = self.chat_display.textCursor()
        selected_text = cursor.selectedText().strip()

        if selected_text:
            # ✅ Read selected text first
            self._append_message("System", "🔊 Reading selected text...", QColor("#00ff99"))
            self._read_or_speak(selected_text)
        elif self._last_gpt_response:
            # ✅ Read last GPT answer automatically
            self._append_message("System", "🔊 Reading last response...", QColor("#00ff99"))
            self._read_or_speak(self._last_gpt_response)
        else:
            self._append_message("System", "⚠️ Nothing to read yet.", QColor("#ffaa00"))

    def _read_or_speak(self, text: str):
        """Thread-safe wrapper to trigger TTS on any text."""
        if not text:
            return
        threading.Thread(target=self._speak_text, args=(text,), daemon=True).start()


    def _auto_read_selection(self):
     cursor = self.chat_display.textCursor()
     if cursor.hasSelection():
        text = cursor.selectedText().strip()
        if text:
            self._read_or_speak(text)
