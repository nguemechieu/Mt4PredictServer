import os, time, json, threading
from telegram import Bot

class TelegramNotifier:
    """
    📢 Telegram Notifier for trading alerts and daily summaries.
    """

    def __init__(self, controller=None, chat_id=None, token_path="config/telegram_token.json"):
        self.controller = controller
        self.chat_id = chat_id
        self.bot = None
        token = "8053577939:AAHalquHGZj9ppYjJgZQp3NJBTzdYy7N84A"
        # if os.path.exists(token_path):
        #     data = json.load(open(token_path))
        #     token = "8053577939:AAHalquHGZj9ppYjJgZQp3NJBTzdYy7N84A"
        #     self.chat_id = data.get("CHAT_ID", self.chat_id)
        #     if token:
        self.bot = Bot(token=token)
        if not self.bot:
            self.controller.logger.error("⚠️ Telegram bot not initialized. Missing token.")

    # --------------------------------------------------------------
    def send(self, text):
        """Send message safely in background thread."""
        if not self.bot or not self.chat_id:
            return
        threading.Thread(target=self._send_thread, args=(text,), daemon=True).start()

    def _send_thread(self, text):
        try:
            self.bot.send_message(chat_id=self.chat_id, text=text)
        except Exception as e:
            self.controller.logger.error(f"⚠️ Telegram send error: {e}")

    # --------------------------------------------------------------
    def daily_summary(self, portfolio_state, summary, reflection):
        """Compile and send an AI-generated daily summary."""
        text = (
            f"📊 *Daily Trading Summary*\n\n"
            f"Balance: ${portfolio_state.get('balance', 0):.2f}\n"
            f"Equity: ${portfolio_state.get('equity', 0):.2f}\n"
            f"Drawdown: {portfolio_state.get('drawdown_pct', 0)}%\n"
            f"Volatility: {portfolio_state.get('volatility', 0)}\n"
            f"Win Rate: {summary.get('win_rate', 0)}%\n"
            f"Avg Profit: {summary.get('avg_profit', 0)} pips\n\n"
            f"🧠 Reflection:\n{reflection[:600]}..."
        )
        self.send(text)
