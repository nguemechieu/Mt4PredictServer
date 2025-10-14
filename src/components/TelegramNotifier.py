import os
import time
import json
import threading
import requests

class TelegramNotifier:
    """
    📢 Telegram Notifier for trading alerts and GPT Advisor interaction.
    -------------------------------------------------------------
    • Uses simple HTTPS API (no async coroutine issues)
    • Thread-safe (runs send() in background)
    • Supports GPT reflection / interaction summaries
    """

    def __init__(self, controller=None, chat_id=None, token="8053577939:AAHalquHGZj9ppYjJgZQp3NJBTzdYy7N84A"):
        self.controller = controller
        self.chat_id = chat_id
        self.token = token
        if not token or not chat_id:
            if controller and hasattr(controller, "logger"):
                controller.logger.warning("⚠️ Telegram notifier not fully configured (missing token or chat_id).")
        else:
            if controller and hasattr(controller, "logger"):
                controller.logger.info(f"🤖 Telegram Notifier ready for chat {chat_id}")

    # --------------------------------------------------------------
    def send(self, text: str):
        """Send a message asynchronously via background thread."""
        if not self.token or not self.chat_id:
            if self.controller and hasattr(self.controller, "logger"):
                self.controller.logger.warning("⚠️ Telegram send skipped — missing token or chat ID.")
            return
        threading.Thread(target=self._send_thread, args=(text,), daemon=True).start()

    def _send_thread(self, text: str):
        """Internal thread that sends message via Telegram HTTP API."""
        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "Markdown"
            }
            response = requests.post(url, data=payload, timeout=5)
            if response.status_code != 200:
                err_msg = response.text
                if self.controller and hasattr(self.controller, "logger"):
                    self.controller.logger.warning(f"⚠️ Telegram API error: {err_msg}")
        except Exception as e:
            if self.controller and hasattr(self.controller, "logger"):
                self.controller.logger.error(f"❌ Telegram send error: {e}")

    # --------------------------------------------------------------
    def send_signal(self, symbol: str, result: dict):
        """
        Send a concise trade signal notification.
        Includes GPT Advisor reflection if available.
        """
        try:
            direction = result.get("direction", "N/A")
            conf = float(result.get("confidence", 0)) * 100
            prob = float(result.get("probability", 0))
            reflection = ""

            # --- GPT Advisor contextual explanation ---
            if hasattr(self.controller, "gpt") and self.controller.gpt:
                try:
                    reflection = self.controller.gpt.short_reason(symbol, result)
                except Exception as e:
                    reflection = f"(GPT error: {e})"

            message = (
                f"📈 *{symbol}* Signal Update\n"
                f"Direction: *{direction}*\n"
                f"Confidence: {conf:.2f}%\n"
                f"Probability: {prob:.4f}\n"
                f"Time: {time.strftime('%H:%M:%S')}\n"
            )
            if reflection:
                message += f"\n🧠 GPT Insight:\n_{reflection}_"

            self.send(message)

        except Exception as e:
            if self.controller and hasattr(self.controller, "logger"):
                self.controller.logger.error(f"⚠️ Telegram send_signal error: {e}")

    # --------------------------------------------------------------
    def daily_summary(self, portfolio_state: dict, summary: dict, reflection: str = ""):
        """Compile and send an AI-generated daily trading summary."""
        try:
            balance = portfolio_state.get("balance", 0)
            equity = portfolio_state.get("equity", 0)
            drawdown = portfolio_state.get("drawdown_pct", 0)
            volatility = portfolio_state.get("volatility", 0)
            win_rate = summary.get("win_rate", 0)
            avg_profit = summary.get("avg_profit", 0)

            text = (
                f"📊 *Daily Trading Summary*\n\n"
                f"💰 Balance: ${balance:.2f}\n"
                f"📉 Equity: ${equity:.2f}\n"
                f"⚠️ Drawdown: {drawdown}%\n"
                f"📈 Volatility: {volatility}\n"
                f"🏆 Win Rate: {win_rate}%\n"
                f"💹 Avg Profit: {avg_profit} pips\n\n"
            )

            if reflection:
                text += f"🧠 Reflection:\n_{reflection[:600]}_"

            self.send(text)

        except Exception as e:
            if self.controller and hasattr(self.controller, "logger"):
                self.controller.logger.error(f"⚠️ Telegram daily_summary error: {e}")
