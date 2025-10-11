"""
===============================================================
🔮 PredictServer — Autonomous AI Trading Bridge
---------------------------------------------------------------
Bridges MT4 DLL ↔ Python backend with full AI intelligence.

✅ Features:
    • Persistent socket server for MT4 connection
    • Adaptive strategy learning
    • GPT reasoning and reflection
    • Autonomous portfolio & risk management
    • Telegram alerts and daily summaries
===============================================================
"""

import json
import logging
import os
import queue
import socket
import threading
import time

import numpy as np
import pandas as pd
from PySide6.QtGui import QColor

# === Internal Imports ===
from components.AdaptiveStrategyEngine import AdaptiveStrategyEngine
from components.FeedbackTrainer import FeedbackTrainer
from components.PortfolioManager import PortfolioManager
from components.ReasoningEngine import ReasoningEngine
from components.TelegramNotifier import TelegramNotifier
from src.components.GPTAdvisor import GPTAdvisor
from src.components.mt4_predictor import MT4Predictor

# ==========================================================
# Global Configuration
# ==========================================================
HOST = "127.0.0.1"
PORT = 9999
BUFFER_SIZE = 4096


# ==========================================================
# JSON Encoder (handles NumPy types)
# ==========================================================
class NpEncoder(json.JSONEncoder):
    """Ensure NumPy types are JSON-serializable."""
    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.ndarray,)):
            return obj.tolist()
        return super().default(obj)


# ==========================================================
# Utilities
# ==========================================================
def _default_logger():
    """Create a default logger if none is provided."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    return logging.getLogger("PredictServer")


def append_csv(path, new_df):
    """Safely append rows to CSV (no duplicates, no overwrite)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        new_df.to_csv(path, index=False)
    else:
        old = pd.read_csv(path)
        combined = pd.concat([old, new_df], ignore_index=True)
        combined.drop_duplicates(inplace=True)
        combined.to_csv(path, index=False)


# ==========================================================
# Main Server Class
# ==========================================================
class PredictServer:
    """
    🌐 PredictServer — The bridge between MT4 Expert Advisor and AI Core.

    Responsibilities:
        • Manage socket connections with MT4
        • Handle candle/indicator updates
        • Route GPT reasoning and adaptive strategy calls
        • Enforce risk controls & trading hours
        • Send Telegram alerts and daily AI reflections
    """

    # ------------------------------------------------------
    def __init__(self, controller=None):
        self.controller = controller
        self.logger = getattr(controller, "logger", _default_logger())

        # === Core Intelligence Components ===
        self.gpt = GPTAdvisor(controller)
        self.predictor = MT4Predictor(controller)
        self.adaptive_engine = AdaptiveStrategyEngine(controller, "./src/data/order_history.csv")
        self.reasoning_engine = ReasoningEngine(controller)
        self.portfolio = PortfolioManager(controller)
        self.notifier = TelegramNotifier(controller=controller)

        # === State Memory ===
        self.confidence = 0.0
        self.last_confidence = {}
        self.last_direction = {}
        self.last_gpt_time = {}
        self.account_info = {}
        self.order_history = []
        self.open_orders = []

        # === Networking & Concurrency ===
        self.server_socket = None
        self.clients = {}
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self.candle_buffers = {}
        self.prediction_queues = {}
        self.active_workers = {}

        # Start Daily Reporting Thread
        threading.Thread(target=self._daily_cycle, daemon=True).start()

    # ======================================================
    # Lifecycle Management
    # ======================================================
    def start(self):
        """Start persistent TCP server."""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((HOST, PORT))
            self.server_socket.listen(10)
            self.server_socket.settimeout(1.0)
            self.logger.info(f"🟢 PredictServer listening on {HOST}:{PORT}")

            threading.Thread(target=self._accept_loop, daemon=True).start()
        except Exception as e:
            self.logger.error(f"❌ Server start failed: {e}")

    def stop(self):
        """Gracefully shut down server and all client connections."""
        self._stop_event.set()
        try:
            for addr, conn in list(self.clients.items()):
                try:
                    conn.shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass
                conn.close()
                self.logger.info(f"🔌 Closed connection: {addr}")

            if self.server_socket:
                self.server_socket.close()

            self.logger.info("🛑 PredictServer stopped.")
        except Exception as e:
            self.logger.error(f"❌ Stop error: {e}")

    # ======================================================
    # Connection Management
    # ======================================================
    def _accept_loop(self):
        """Accept incoming MT4 connections."""
        while not self._stop_event.is_set():
            try:
                conn, addr = self.server_socket.accept()
                conn.settimeout(15.0)
                with self._lock:
                    self.clients[addr] = conn
                self.logger.info(f"🔗 Client connected: {addr}")

                threading.Thread(target=self._client_loop, args=(conn, addr), daemon=True).start()
            except socket.timeout:
                continue
            except OSError:
                break
            except Exception as e:
                self.logger.error(f"❌ Accept error: {e}")

    def _client_loop(self, conn, addr):
        """Handle each connected MT4 client."""
        try:
            while not self._stop_event.is_set():
                msg = self.receive_message(conn)
                if msg is None:
                    continue

                # Ping-pong keep alive
                if msg.get("type") == "ping":
                    self.send_message(conn, {"type": "pong", "timestamp": time.time()})
                    continue

                # Route message
                response = self.process_message(msg)
                if response:
                    self.send_message(conn, response)

        except socket.timeout:
            self.logger.debug(f"⚠️ Idle timeout from {addr}, keeping alive...")
        except (ConnectionResetError, ConnectionAbortedError, OSError):
            self.logger.warning(f"⚠️ Connection lost: {addr}")
        finally:
            with self._lock:
                self.clients.pop(addr, None)
            conn.close()
            self.logger.info(f"🔌 Disconnected: {addr}")

    # ======================================================
    # I/O Handlers
    # ======================================================
    def receive_message(self, conn):
        """Safely receive JSON messages from MT4."""
        try:
            data = conn.recv(BUFFER_SIZE)
            if not data:
                return None
            text = data.decode("utf-8", errors="ignore").strip()
            for chunk in text.split("\n"):
                if chunk.strip():
                    return json.loads(chunk)
        except socket.timeout:
            return None
        except Exception as e:
            self.logger.error(f"❌ Receive error: {e}")
        return None

    def send_message(self, conn, response):
        """Send a structured JSON response to MT4."""
        try:
            packet = json.dumps(response, cls=NpEncoder) + "\n"
            conn.sendall(packet.encode("utf-8"))
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            self.logger.error(f"❌ Send error: {e}")

    # ======================================================
    # Dispatcher
    # ======================================================
    def process_message(self, msg):
        """Dispatch messages based on their type."""
        mtype = (msg.get("type") or "").lower()
        try:
            if mtype == "ping":
                return {"type": "pong", "timestamp": time.time()}
            elif mtype == "candles":
                return self._process_candles(msg)
            elif mtype in ("ai_advice", "gpt_query"):
                return self._process_gpt(msg)
            else:
                return {"status": "error", "reason": f"Unknown message type '{mtype}'"}
        except Exception as e:
            self.logger.error(f"❌ Process error: {e}")
            return {"status": "error", "reason": str(e), "timestamp": time.time()}

    # ======================================================
    # Candle Data Handler
    # ======================================================
    def _process_candles(self, msg):
        """Handle incoming candle and indicator updates."""
        symbol = str(msg.get("symbol") or "EURUSD")
        candle = msg.get("candle") or {}
        ind_data = msg.get("indicators") or {}

        # Save account and trade data
        self._update_account_data(msg)

        # Validate candle
        if not isinstance(candle, dict) or not candle:
            raise ValueError(f"Invalid candle data for {symbol}")

        # Buffer candles
        self._update_candle_buffer(symbol, candle)

        # Skip until enough candles accumulated
        if len(self.candle_buffers[symbol]) < 10:
            return None

        # --- Adaptive Strategy and Reasoning ---
        self._handle_trade_logic(symbol, ind_data)
        return None

    def _update_account_data(self, msg):
        """Save account info, open orders, and order history."""
        self.account_info = msg.get("account_info", {})
        if self.account_info:
            append_csv("./src/data/account_info.csv", pd.DataFrame([self.account_info]))

        self.order_history = msg.get("order_history", [])
        if self.order_history:
            append_csv("./src/data/order_history.csv", pd.DataFrame(self.order_history))

        self.open_orders = msg.get("open_orders", [])
        if self.open_orders:
            append_csv("./src/data/open_orders.csv", pd.DataFrame(self.open_orders))

    def _update_candle_buffer(self, symbol, candle):
        """Maintain rolling candle data buffer."""
        with self._lock:
            if symbol not in self.candle_buffers:
                self.candle_buffers[symbol] = pd.DataFrame()
            if symbol not in self.prediction_queues:
                self.prediction_queues[symbol] = queue.Queue()

        df = pd.DataFrame([{
            "time": candle.get("time", 0),
            "open": candle.get("open", 0.0),
            "high": candle.get("high", 0.0),
            "low": candle.get("low", 0.0),
            "close": candle.get("close", 0.0),
            "volume": candle.get("volume", 0.0),
        }])

        with self._lock:
            combined = pd.concat([self.candle_buffers[symbol], df], ignore_index=True)
            self.candle_buffers[symbol] = combined.tail(10)

        self.logger.info(f"📊 {symbol}: {len(self.candle_buffers[symbol])} candles buffered")

    def _handle_trade_logic(self, symbol, ind_data):
        """Run adaptive strategy, reasoning, and prediction logic."""
        # Record trade metrics
        self.adaptive_engine.record_trade(
            symbol=symbol,
            indicators={
                "rsi": ind_data.get("rsi", 0.0),
                "ema_fast": ind_data.get("ema_fast", 0.0),
                "ema_slow": ind_data.get("ema_slow", 0.0),
            },
            decision="BUY",
            profit_pips=self.account_info.get("profit", 0.0),
        )

        # Generate reasoning
        reasoning_text = self.reasoning_engine.explain_decision(
            symbol=symbol,
            indicators=ind_data,
            prediction={"signal": "BUY", "confidence": self.confidence},
            account_state={
                "balance": self.account_info.get("balance", 0.0),
                "risk_ratio": self.adaptive_engine.get_strategy()["risk_ratio"],
            },
        )

        # Save and retrain model incrementally
        self._retrain_predictor(symbol, ind_data)
        self._queue_prediction(symbol, ind_data)
        self.logger.info(f"🧠 Reasoning complete for {symbol}: {reasoning_text[:100]}...")

    def _retrain_predictor(self, symbol, ind_data):
        """Train ML model on latest signal data."""
        signal_path = f"./src/data/signal_{symbol}.csv"
        candle_path = f"./src/data/candle_{symbol}.csv"
        model_path = "./model/model.keras"
        scaler_path = "./model/scaler.pkl"
        order_history_path = "./src/data/order_history.csv"

        ind_df = pd.DataFrame([ind_data])
        ind_df.to_csv(signal_path, index=False)
        self.candle_buffers[symbol].to_csv(candle_path, index=False)

        self.predictor.trainer.train_and_save_model(
            symbol, signal_path, candle_path, model_path, scaler_path, order_history_path
        )

    def _queue_prediction(self, symbol, ind_data):
        """Add data to prediction queue and start worker if idle."""
        features = [
            ind_data.get("ema_fast", 0.0),
            ind_data.get("ema_slow", 0.0),
            ind_data.get("rsi", 0.0),
            ind_data.get("macd", 0.0),
        ]
        self.prediction_queues[symbol].put((symbol, features, {}))
        if symbol not in self.active_workers or not self.active_workers[symbol].is_alive():
            worker = threading.Thread(target=self._prediction_worker, args=(symbol,), daemon=True)
            self.active_workers[symbol] = worker
            worker.start()

    # ======================================================
    # Prediction Worker
    # ======================================================
    def _prediction_worker(self, symbol):
        """Continuously process prediction queue for a symbol."""
        if not self._within_trading_hours():
            self.logger.info("🌙 Outside trading hours — paused.")
            self.notifier.send("🌙 AI paused — outside trading window (6 AM–6 PM UTC).")
            time.sleep(60 * 60)
            return

        # Risk controls
        state = self.portfolio.evaluate_portfolio()
        pause, reason = self.portfolio.should_pause_trading()
        if pause:
            self.logger.warning(f"🚫 Trading paused due to: {reason}")
            self.notifier.send(f"⚠️ Trading paused — {reason}")
            return

        self.lot_size = self.portfolio.adjust_lot_size(self.confidence, risk_ratio=0.02)
        self.logger.info(f"📏 Adjusted lot size: {self.lot_size}")

        q = self.prediction_queues[symbol]
        while not q.empty():
            try:
                symbol, features, _ = q.get()
                result = self.predictor.predict(symbol, features)
                self._handle_prediction_result(symbol, features, result)
            except Exception as e:
                self.logger.error(f"❌ Prediction worker error ({symbol}): {e}")

    def _handle_prediction_result(self, symbol, features, result):
        """Process prediction results, send updates, and log outcomes."""
        cur_dir = result.get("direction", "neutral")
        conf = float(result.get("confidence", 0.0))

        prev_dir = self.last_direction.get(symbol)
        prev_conf = self.last_confidence.get(symbol, 0.0)
        now = time.time()
        cooldown = (now - self.last_gpt_time.get(symbol, 0)) > 300

        direction_changed = (prev_dir != cur_dir)
        confidence_changed = abs(prev_conf - conf) > 0.1

        # Trigger GPT reasoning if major change
        if direction_changed or confidence_changed or cooldown:
            prompt = (
                f"Symbol: {symbol}\nDirection: {cur_dir}\nConfidence: {conf:.2f}\n"
                f"EMA Fast: {features[0]} | EMA Slow: {features[1]}\n"
                f"RSI: {features[2]} | MACD: {features[3]}"
            )
            try:
                gpt_response = self.gpt.ask(prompt)
            except Exception as e:
                gpt_response = f"GPT analysis failed: {e}"
            self.last_gpt_time[symbol] = now
        else:
            gpt_response = "No significant change detected."

        # Handle reversals
        if prev_dir and prev_dir != cur_dir:
            self._send_reversal(symbol, prev_dir, cur_dir)

        # Update records
        self.last_direction[symbol] = cur_dir
        self.last_confidence[symbol] = conf

        record = {
            "symbol": symbol,
            "direction": cur_dir,
            "confidence": conf,
            "timestamp": now,
            "analysis": gpt_response,
        }
        self._save_prediction(record)

    def _send_reversal(self, symbol, prev_dir, cur_dir):
        """Send trade close signal on market reversal."""
        self.logger.warning(f"🔁 Reversal {symbol}: {prev_dir} → {cur_dir}")
        msg = {
            "type": "trade_command",
            "action": "CLOSE",
            "symbol": symbol,
            "reason": f"Reversal {prev_dir}→{cur_dir}",
            "timestamp": time.time(),
        }
        for c in list(self.clients.values()):
            threading.Thread(target=self.send_message, args=(c, msg), daemon=True).start()

    # ======================================================
    # GPT Query Handler
    # ======================================================
    def _process_gpt(self, msg):
        """Process GPT trading queries (advisory requests)."""
        try:
            query = (msg.get("query") or "").strip()
            if not query:
                return {"status": "error", "reason": "Empty GPT query"}

            symbol = msg.get("context", {}).get("symbol", "N/A")
            indicators = msg.get("context", {}).get("indicators", {})
            acc_info = self.account_info

            prompt = (
                f"You are an AI trading assistant.\n\n"
                f"Query: {query}\nSymbol: {symbol}\nIndicators: {json.dumps(indicators, indent=2)}\n"
                f"Balance: {acc_info.get('balance', 0)} | Equity: {acc_info.get('equity', 0)}"
            )
            start = time.time()
            answer = self.gpt.ask(prompt)
            latency = time.time() - start

            self._save_gpt_log(symbol, query, prompt, answer, latency)
            return {
                "type": "ai_response",
                "status": "ok",
                "symbol": symbol,
                "query": query,
                "content": answer,
                "latency_sec": round(latency, 2),
                "timestamp": time.time(),
            }
        except Exception as e:
            self.logger.error(f"❌ GPT process error: {e}")
            return {"status": "error", "reason": str(e)}

    # ======================================================
    # Helpers
    # ======================================================
    def _save_gpt_log(self, symbol, query, prompt, answer, latency):
        """Save GPT queries and responses to CSV."""
        try:
            record = [{
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "symbol": symbol,
                "query": query,
                "prompt": prompt,
                "response_preview": answer[:200],
                "latency_sec": latency,
            }]
            append_csv("./src/data/gpt_log.csv", pd.DataFrame(record))
        except Exception as e:
            self.logger.error(f"❌ Failed to save GPT log: {e}")

    def _within_trading_hours(self):
        """Return True if within 6 AM–6 PM UTC trading window."""
        hour = time.gmtime().tm_hour
        return 6 <= hour <= 18

    def _daily_cycle(self):
        """Run daily performance reflection and Telegram summary."""
        while not self._stop_event.is_set():
            try:
                time.sleep(60 * 60 * 24)  # every 24 hours
                portfolio_state = self.portfolio.evaluate_portfolio()
                feedback = FeedbackTrainer(controller=self.controller)
                df, summary = feedback.analyze_reasoning(n_last=100)
                reflection = feedback.gpt_reflect(df, summary) or "No reflection available."
                self.notifier.daily_summary(portfolio_state, summary, reflection)
                self.logger.info("📬 Daily summary sent.")
            except Exception as e:
                self.logger.error(f"❌ Daily cycle error: {e}")
