import logging
import threading
from typing import Iterable
from PySide6.QtCore import QObject, Signal
import pandas as pd
import os

try:
    from openai import OpenAI
    from openai.types.chat import (
        ChatCompletionAssistantMessageParam,
        ChatCompletionDeveloperMessageParam,
        ChatCompletionFunctionMessageParam,
        ChatCompletionSystemMessageParam,
        ChatCompletionToolMessageParam,
        ChatCompletionUserMessageParam,
    )
except ImportError:
    OpenAI = None


# ==========================================================
# 🧩 Helper: Account Context Loader
# ==========================================================
def build_context_from_account():
    """Safely load account info and orders from CSVs for contextual analysis."""
    try:
        context = []

        # Account Info
        if os.path.exists("./src/data/account_info.csv"):
            acc = pd.read_csv("./src/data/account_info.csv").to_dict(orient="records")[-1]
            context.append(
                f"Account Summary:\n"
                f"  • Balance: ${acc.get('balance', 0):,.2f}\n"
                f"  • Equity: ${acc.get('equity', 0):,.2f}\n"
                f"  • Free Margin: ${acc.get('free_margin', 0):,.2f}\n"
                f"  • Margin: ${acc.get('margin', 0):,.2f}\n"
            )

        # Open Orders
        if os.path.exists("./src/data/open_orders.csv"):
            open_orders = pd.read_csv("./src/data/open_orders.csv")
            context.append(f"Open Orders: {len(open_orders)} active positions.")
            if not open_orders.empty:
                top_orders = open_orders.head(3).to_dict(orient="records")
                for o in top_orders:
                    context.append(
                        f"  - {o.get('symbol', '?')} {o.get('type', '?')} "
                        f"@ {o.get('open_price', '?')} (lots {o.get('lots', '?')})"
                    )

        # Order History
        if os.path.exists("./src/data/order_history.csv"):
            history = pd.read_csv("./src/data/order_history.csv")
            context.append(f"Closed Trades: {len(history)} total.")
            if not history.empty:
                last_profit = history['profit'].iloc[-1] if 'profit' in history else 0
                total_pnl = history['profit'].sum() if 'profit' in history else 0
                context.append(f"Last trade PnL: {last_profit:.2f}, Total PnL: {total_pnl:.2f}")

        return "\n".join(context) if context else "No account context available."
    except Exception as e:
        return f"⚠️ Error building account context: {e}"


# ==========================================================
# 🤖 GPTAdvisor
# ==========================================================
class GPTAdvisor(QObject):
    """
    GPTAdvisor integrates GPT model (OpenAI or local) for trading-related insights.
    Supports streaming via Qt signals and offline fallback.
    """

    stream_signal = Signal(str)
    done_signal = Signal(str)
    error_signal = Signal(str)

    def __init__(self, controller=None):
        super().__init__()
        self.controller = controller
        self.logger = logging.getLogger("GPTAdvisor")
        self.model = "gpt-4o-mini"
        self.api_key = getattr(controller, "api_key", None)
        self._client = None

        if self.api_key and OpenAI:
            try:
                self._client = OpenAI(api_key=self.api_key)
                self.logger.info("🤖 GPTAdvisor connected to OpenAI successfully.")
            except Exception as e:
                self.logger.warning(f"⚠️ Failed to initialize OpenAI client: {e}")
        else:
            self.logger.info("⚙️ GPTAdvisor running in offline mode (no API key).")

    # ==========================================================
    # BASIC CHAT
    # ==========================================================
    def chat(self, prompt: str = None, messages: list = None, stream: bool = False):
        """General-purpose chat method for custom messages."""
        try:
            if not self._client:
                return self._local_response(prompt or str(messages))

            # Wrap into message format
            if messages is None and prompt:
                messages = [
                    {"role": "system", "content": "You are a professional trading assistant."},
                    {"role": "user", "content": prompt},
                ]

            if stream:
                return self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    stream=True,
                    max_tokens=500,
                    temperature=0.7,
                )
            else:
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=400,
                    temperature=0.5,
                )
                return response
        except Exception as e:
            self.logger.error(f"❌ GPTAdvisor.chat() failed: {e}")
            return f"Error: {e}"

    # ==========================================================
    # STREAMING MODE
    # ==========================================================
    def analyze_signal_stream(self, payload: dict):
        """Start GPT streaming analysis in a background thread."""
        thread = threading.Thread(target=self._stream_thread, args=(payload,), daemon=True)
        thread.start()

    def _stream_thread(self, payload: dict):
        """Stream GPT output token-by-token."""
        try:
            query = payload.get("query", "")
            logs = payload.get("logs", "")

            if not query:
                print("⚠️ Empty query received.")

                return

            context = build_context_from_account()
            full_prompt = f"{context}\n\nUser Query: {query}\nLogs:\n{logs}"

            if self._client:
                messages = [
                    {
                        "role": "system",
                        "content": "You are an expert AI trading assistant. Use account context to inform your analysis.",
                    },
                    {"role": "user", "content": full_prompt[:4000]},
                ]

                stream = self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    stream=True,
                    temperature=0.7,
                    max_tokens=400,
                )

                for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        token = chunk.choices[0].delta.content
                        self.stream_signal.emit(token)

                self.done_signal.emit("✅ Streaming completed.")
            else:
                text = self._local_response(query)
                self.stream_signal.emit(text)
                self.done_signal.emit("✅ Done (offline).")

        except Exception as e:
            self.logger.error(f"GPTAdvisor stream error: {e}")
            self.error_signal.emit(f"❌ {e}")

    # ==========================================================
    # OFFLINE MODE
    # ==========================================================
    def _local_response(self, prompt: str = None) -> str:
        """Fallback responses for offline mode."""
        text = (prompt or "").lower()
        if "buy" in text:
            return "📈 Local insight: Possible BUY signal detected."
        elif "sell" in text:
            return "📉 Local insight: Possible SELL opportunity."
        elif "trend" in text:
            return "📊 The trend appears neutral with moderate volatility."
        elif "error" in text or "log" in text:
            return "🪲 No critical errors detected in logs."
        else:
            return f"🧠 Local GPTAdvisor: '{prompt}' acknowledged."

    # ==========================================================
    # ASK INTERFACE (with Account Context)
    # ==========================================================
    def ask(self, query: str) -> str:
        """One-shot GPT query with automatic account context."""
        try:
            if not query or not query.strip():
                return "⚠️ Empty query."

            context = build_context_from_account()
            prompt = (
                "You are GPTAdvisor — a professional AI trading assistant. "
                "Use the following account data to provide insights:\n\n"
                f"{context}\n\nUser question:\n{query}"
            )

            if self._client:
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an AI trading assistant analyzing account data."},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=500,
                    temperature=0.5,
                )

                message_text = response.choices[0].message.content.strip()
                self.logger.info(f"🧠 GPTAdvisor response: {message_text[:120]}...")
                return message_text
            else:
                return self._local_response(query)

        except Exception as e:
            self.logger.error(f"❌ GPTAdvisor.ask() failed: {e}")
            return f"Error: {e}"
