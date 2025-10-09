import json
import logging
import threading
from datetime import datetime
from PySide6.QtCore import QObject, Signal

import re

from components.GPTAdvisor import GPTAdvisor


def _parse_decision(text):
    text = text.upper()
    match = re.search(r"\b(DECISION\s*[:\-]?\s*)?(BUY|SELL|HOLD)\b", text)
    if match:
        return {"action": match.group(2)}
    return {"action": "HOLD"}


class AutoTradeManager(QObject):
    """
    Autonomous GPT-driven trade executor integrated with Mt4PredictServer.
    Monitors live signals, streams GPT reasoning, and issues trade commands.
    """
    stream_signal = Signal(str)  # Live reasoning output
    decision_signal = Signal(dict)  # Final structured trade decision

    def __init__(self, controller=None):
        super().__init__()

        self.controller = controller
        # reference to Mt4PredictServer
        self.logger = self.controller.logger or logging.getLogger("AutoTradeManager")
        self.client = None
        self.active = False
        self.thread = None

        # ----------------------------------------------------------------------

    def start(self):
        if self.active:
            self.log("⚙️ Auto-trade already running.")
            return
        self.active = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        self.log("🚀 Auto-trade loop started.")

    def stop(self):
        self.active = False
        self.log("🛑 Auto-trade stopped.")

    # ----------------------------------------------------------------------
    def _loop(self):
        """Continuously monitor predictions and analyze them with GPT."""
        while self.active:
            try:
                if not self.controller.server.predictor:
                    self.log("⚠️ Predictor not ready.")
                    break

                # Example simulated signal
                signal = {
                    "pair": "EURUSD",
                    "price": round(1.0950, 5),
                    "rsi": 33.2,
                    "macd": -0.0019,
                    "confidence": 0.87,
                    "model_signal": "BUY",
                    "timestamp": datetime.utcnow().isoformat(),
                }
                self._analyze_and_trade(signal)
            except Exception as e:
                self.log(f"[AutoTrade] Error: {e}")
            finally:
                import time;
                time.sleep(20)

    # ----------------------------------------------------------------------
    def _analyze_and_trade(self, signal):
        prompt = (
            f"Model prediction: {json.dumps(signal, indent=2)}\n"
            f"Based on this data, decide whether to BUY, SELL, or HOLD.\n"
            f"Return only one final decision line starting with Decision:"
        )

        self.client = GPTAdvisor(self.controller)
        stream = self.client.chat(
            messages=[
                {"role": "system", "content": "You are a professional algorithmic trader AI."},
                {"role": "user", "content": prompt},
            ])

        full_text = ""
        for chunk in stream:
            if chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                full_text += token
                self.stream_signal.emit(token)

        # Parse decision
        decision = _parse_decision(full_text)
        self.decision_signal.emit(decision)

        # Execute automatically
        if decision.get("action") in ["BUY", "SELL"]:
            cmd = {"action": decision["action"], "pair": signal["pair"], "price": signal["price"]}
            resp = self.controller.send_command(cmd)
            self.log(f"Sent order: {cmd} → {resp}")

    # ----------------------------------------------------------------------

    def log(self, msg):
        if self.logger:
            self.logger.info(msg)
        print(msg)
