import json
import logging
import os
import threading
import pandas as pd
from typing import Any, LiteralString
from PySide6.QtCore import QObject, Signal
from components import news_calendar  # Ensure this file exists

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


# ==========================================================
# 🧩 Helper: Account Context Loader
# ==========================================================
def build_context_from_account() -> str:
    """Safely load account info and orders from CSVs for GPT context."""
    try:
        sections = []

        # --- Account Info ---
        path = "./src/data/account_info.csv"
        if os.path.exists(path):
            acc = pd.read_csv(path).to_dict(orient="records")[-1]
            sections.append(
                f"📊 Account Summary\n"
                f"• Balance: ${acc.get('balance', 0):,.2f}\n"
                f"• Equity: ${acc.get('equity', 0):,.2f}\n"
                f"• Margin: ${acc.get('margin', 0):,.2f}\n"
                f"• Free Margin: ${acc.get('free_margin', 0):,.2f}\n"
                f"• Leverage: {acc.get('leverage', 'N/A')}\n"
                f"• Profit: ${acc.get('profit', 0):,.2f}\n"
            )

        # --- Open Orders ---
        path = "./src/data/open_orders.csv"
        if os.path.exists(path):
            open_orders = pd.read_csv(path)
            sections.append(f"📈 Open Orders: {len(open_orders)} active")
            if not open_orders.empty:
                for _, row in open_orders.head(3).iterrows():
                    sections.append(
                        f"  - {row.get('symbol', '?')} ({row.get('type', '?')}) "
                        f"@ {row.get('open_price', '?')} | Lots: {row.get('lots', '?')}"
                    )

        # --- Order History ---
        path = "./src/data/order_history.csv"
        if os.path.exists(path):
            hist = pd.read_csv(path)
            sections.append(f"📜 Closed Trades: {len(hist)} total")
            if not hist.empty and 'profit' in hist:
                total_pnl = hist['profit'].sum()
                avg_pnl = hist['profit'].mean()
                sections.append(f"Total PnL: {total_pnl:.2f} | Avg PnL per trade: {avg_pnl:.2f}")

        return "\n".join(sections) if sections else "⚠️ No account data found."

    except Exception as e:
        return f"⚠️ Error loading account data: {e}"


# ==========================================================
# 🤖 GPTAdvisor Class
# ==========================================================
def _local_response(text: str) -> str:
    text = text.lower()
    if "buy" in text:
        return "📈 Offline: Possible BUY signal."
    elif "sell" in text:
        return "📉 Offline: Possible SELL opportunity."
    elif "trend" in text:
        return "📊 Offline: Trend seems sideways, volatility moderate."
    return f"🧠 Offline GPTAdvisor: '{text}' noted."


class GPTAdvisor(QObject):
    """GPT-based Trading Analyst — integrates live account & economic calendar."""

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
                self.controller.logger.info("🤖 GPTAdvisor connected to OpenAI successfully.")
            except Exception as e:
                self.controller.logger.warning(f"⚠️ Failed to initialize OpenAI client: {e}")
        else:
            if self.controller:
                self.controller.logger.info("⚙️ GPTAdvisor running in offline mode (no API key).")
            else:
                self.logger.info("⚙️ GPTAdvisor running in offline mode (no API key).")

    # ==========================================================
    # STREAMING ANALYSIS
    # ==========================================================
    def analyze_signal_stream(self, payload: dict):
        """Run GPT stream analysis in background."""
        threading.Thread(target=self._stream_thread, args=(payload,), daemon=True).start()

    def _stream_thread(self, payload: dict):
        try:
            query = payload.get("query", "")
            symbol = payload.get("symbol", "Unknown")
            cur_dir = payload.get("direction", "neutral")
            conf = float(payload.get("confidence", 0.0))
            features = payload.get("features", [0, 0, 0, 0])
            recent_candles = payload.get("recent_candles", [])

            if not query:
                return

            context = build_context_from_account()
            news_summary = self._fetch_news_summary(3)

            # Build contextual prompt
            full_prompt = (
                f"You are a professional trading assistant.\n\n"
                f"=== SYMBOL === {symbol}\n"
                f"Predicted Direction: {cur_dir} (Confidence: {conf:.2f})\n"
                f"EMA Fast: {features[0]:.2f} | EMA Slow: {features[1]:.2f} | "
                f"RSI: {features[2]:.2f} | MACD: {features[3]:.2f}\n\n"
                f"=== MARKET CONTEXT (Last {len(recent_candles)} candles) ===\n"
                f"{json.dumps(recent_candles[-10:], indent=2)}\n\n"

                f"{context}\n\n"
                f"Upcoming Key Economic Events:\n{news_summary}\n\n"
                f"Question:\n{query}\n"
                f"Provide reasoning and a recommended action (BUY / SELL / HOLD)."
            )

            if not self._client:
                self.stream_signal.emit(_local_response(query))
                self.done_signal.emit("✅ Done (offline).")
                return

            stream = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a precise and analytical trading assistant."},
                    {"role": "user", "content": full_prompt[:4000]},
                ],
                stream=True,
                temperature=0.6,
                max_tokens=500,
            )

            # --- Stream results safely ---
            for event in stream:
                try:
                    if hasattr(event, "choices") and event.choices:
                        delta = event.choices[0].delta
                        if hasattr(delta, "content") and delta.content:
                            self.stream_signal.emit(delta.content)
                    elif isinstance(event, dict) and "choices" in event:
                        delta = event["choices"][0].get("delta", {})
                        if "content" in delta:
                            self.stream_signal.emit(delta["content"])
                except Exception as stream_err:
                    self.logger.warning(f"⚠️ Stream chunk parse error: {stream_err}")

            self.done_signal.emit("✅ Streaming completed.")

        except Exception as e:
            self.logger.error(f"Stream error: {e}")
            self.error_signal.emit(f"❌ Stream error: {e}")

    # ==========================================================
    # DIRECT ASK (One-shot Query)
    # ==========================================================
    def ask(self, query: str) -> str:
        """One-shot GPT query with full context (account + news)."""
        if not query or not query.strip():
            return "⚠️ Empty query."

        context = build_context_from_account()
        news_summary = self._fetch_news_summary(3)

        prompt = (
            "You are GPTAdvisor — an intelligent AI trader.\n"
            "Your goal: provide clear, data-driven trading insights.\n\n"
            f"{context}\n\n"
            "Upcoming Key Economic Events:\n"
            f"{news_summary}\n\n"
            f"Question:\n{query}\n"
            "Provide actionable insight considering account exposure, risk limits, and market events.\n"
        )

        try:
            if not self._client:
                return _local_response(query)

            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are GPTAdvisor, a professional trading analyst."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=500,
                temperature=0.5,
            )

            result = response.choices[0].message.content.strip()
            recent_loss = self.get_recent_loss()

            if recent_loss > 0:
                result += f"\n⚠️ Recent drawdown of {recent_loss:.2f} detected; reduce trade risk."
                self.logger.info(f"🧠 GPTAdvisor Response (risk warning): {result[:120]}...")
            else:
                self.logger.info(f"🧠 GPTAdvisor: {result[:120]}...")

            return result

        except Exception as e:
            self.logger.error(f"❌ GPTAdvisor.ask() failed: {e}")
            return f"Error: {e}"

    # ==========================================================
    # NEWS INTEGRATION
    # ==========================================================
    def _fetch_news_summary(self, max_events: int = 3) -> str | tuple[LiteralString, Any]:
        """Fetch and format the latest ForexFactory/FairEconomy news."""
        try:
            cal = news_calendar.NewsCalendar()
            cal.fetch()
            events = cal.upcoming(max_events)

            if not events:
                return "No major events in the next few days."

            formatted = []
            for e in events:
                dt_str = e["datetime"].strftime("%Y-%m-%d %H:%M UTC") if e["datetime"] else "?"
                formatted.append(
                    f"• {dt_str} — {e['country']} {e['title']} "
                    f"(Impact: {e['impact']}, Forecast: {e['forecast']}, Prev: {e['previous']})"
                )
            return "\n".join(formatted)
        except Exception as e:
            self.logger.warning(f"⚠️ Failed to load news data: {e}")
            return "⚠️ News unavailable."

    # ==========================================================
    # RISK CHECK: Recent Loss
    # ==========================================================
    def get_recent_loss(self) -> float:
        """Compute recent drawdown from last few closed trades."""
        try:
            path = "./src/data/order_history.csv"
            if not os.path.exists(path):
                return 0.0

            df = pd.read_csv(path)
            if "profit" not in df or df.empty:
                return 0.0

            recent = df.tail(5)["profit"]
            losses = recent[recent < 0]
            return abs(losses.sum()) if not losses.empty else 0.0

        except Exception as e:
            self.logger.warning(f"⚠️ get_recent_loss() failed: {e}")
            return 0.0
