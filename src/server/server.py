"""
===============================================================
🔮 PredictServer — Universal JSON Bridge for MT4 DLL
---------------------------------------------------------------
Bridges MT4 <-> Python using a clean JSON socket protocol.

✅ Supports:
    • SendJSON / ReceiveJSON (from PredictBridge.dll)
    • Candle & indicator updates
    • AI predictions via Predictor
    • GPT reasoning integration
    • Automatic signal logging for retraining
    • Multi-symbol concurrent support
===============================================================
"""

import json
import logging
import os
import pandas as pd
import numpy as np
import socket
import threading
import time

from components.GPTAdvisor import GPTAdvisor
from components.TelegramNotifier import TelegramNotifier
from components.mt4_predictor import Predictor


# ==============================================================
# CONFIGURATION
# ==============================================================
HOST = "127.0.0.1"
PORT = 9999
BUFFER_SIZE = 4096


# ==============================================================
# JSON Helpers
# ==============================================================
class NpEncoder(json.JSONEncoder):
    """Safely encode numpy datatypes to JSON."""
    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.ndarray,)):
            return obj.tolist()
        return super().default(obj)


def _default_logger():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s — %(message)s",
        datefmt="%H:%M:%S",
    )
    return logging.getLogger("PredictServer")


# ==============================================================
# MAIN SERVER CLASS
# ==============================================================
class PredictServer:
    """🌐 PredictServer: Handles all MT4 <-> Python communication."""

    def __init__(self, controller=None):

        self.server_socket = None
        self.token = "8053577939:AAHalquHGZj9ppYjJgZQp3NJBTzdYy7N84A"
        self.controller = controller
        self.logger = getattr(controller, "logger", _default_logger())
        self.clients = {}
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self.candle_buffers = {}
        self.telegram = TelegramNotifier(token=self.token)

        self.gpt=GPTAdvisor(controller=self.controller)

        self.predictor = Predictor(controller=self.controller)

    # ==========================================================
    # 🔌 Server Lifecycle
    # ==========================================================
    def start(self):
        """Start TCP socket server."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((HOST, PORT))
            sock.listen(10)
            sock.settimeout(1.0)
            self.server_socket = sock
            self.logger.info(f"🟢 PredictServer started on {HOST}:{PORT}")
            threading.Thread(target=self._accept_loop, daemon=True).start()
        except Exception as e:
            self.logger.error(f"❌ Failed to start server: {e}")

    def stop(self):
        """Stop server and close all sockets cleanly."""
        self._stop_event.set()
        for addr, conn in list(self.clients.items()):
            try:
                conn.shutdown(socket.SHUT_RDWR)
                conn.close()
            except Exception:
                pass
        if hasattr(self, "server_socket"):
            try:
                self.server_socket.close()
            except Exception:
                pass
        self.logger.info("🛑 PredictServer stopped gracefully.")

    # ==========================================================
    # 🔁 Connection Handling
    # ==========================================================
    def _accept_loop(self):
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
            except Exception as e:
                self.logger.error(f"❌ Accept error: {e}")

    def _client_loop(self, conn, addr):
        try:
            while not self._stop_event.is_set():
                msg = self._recv_json(conn)
                if not msg:
                    continue

                response = self._handle_message(msg)
                if response:
                    self._send_json(conn, response)
        except Exception as e:
            self.logger.warning(f"⚠️ Client {addr} error: {e}")
        finally:
            with self._lock:
                self.clients.pop(addr, None)
            try:
                conn.close()
            except Exception:
                pass
            self.logger.info(f"🔌 Disconnected: {addr}")

    # ==========================================================
    # 📨 I/O (Send / Receive)
    # ==========================================================
    def _recv_json(self, conn):
        """Receive and decode JSON from MT4."""
        try:
            data = conn.recv(BUFFER_SIZE)
            if not data:
                return None
            text = data.decode("utf-8", errors="ignore").strip()
            if not text:
                return None

            for chunk in text.split("\n"):
                if chunk.strip():
                    try:
                        return json.loads(chunk)
                    except json.JSONDecodeError as e:
                        self.logger.error(f"❌ JSON decode error: {e} | Data: {chunk[:120]}")
        except socket.timeout:
            return None
        except Exception as e:
            self.logger.error(f"❌ Receive error: {e}")
        return None

    def _send_json(self, conn=None, payload=None):
        """Send structured JSON payload back to MT4."""
        try:
            packet = json.dumps(payload, cls=NpEncoder) + "\n"
            conn.sendall(packet.encode("utf-8"))
        except Exception as e:
            self.logger.error(f"❌ Send error: {e}")

    # ==========================================================
    # 🎯 Dispatcher
    # ==========================================================
    def _handle_message(self, msg: dict = None):
        """Route messages by 'type' key."""
        mtype = (msg.get("type") or "").lower()

        if mtype == "ping":
            return {"type": "pong", "status": "ready", "timestamp": time.time()}

        if mtype == "receive":
            return {"type": "server_status", "status": "ready", "timestamp": time.time()}

        if mtype == "status":
            return {"type": "status", "running": True, "clients": len(self.clients), "timestamp": time.time()}

        if mtype == "candles":

            return self._handle_candles(msg)
        if mtype == "account":
            return self._handle_account(msg)

        if mtype == "indicator_signal":
            return self._handle_indicator(msg)

        if mtype in ("ai_advice", "gpt_query"):


            return {"type": "ai_advice",
                    "status": "ok",
                    "reply": "AI processing stub active."}

        return {"type": "error",
                "status": "error",
                "reason": f"Unknown message type: {mtype}"}

    # ==========================================================
    # 🕯️ Candle Handling
    # ==========================================================
    def _handle_candles(self, msg=None):
        """Store and buffer incoming candle data."""
        symbol = msg.get("symbol", "UNKNOWN")
        candles = msg.get("data", [])
        if not isinstance(candles, list):
            return {"status": "error", "reason": "Invalid candle format"}

        df = pd.DataFrame(candles)
        path = f"./src/data/{symbol}_candles.csv"
        os.makedirs(os.path.dirname(path), exist_ok=True)

        with self._lock:
            if os.path.exists(path):
                old = pd.read_csv(path)
                df = pd.concat([old, df], ignore_index=True).drop_duplicates().tail(1000)
            df.to_csv(path, index=False)
            self.candle_buffers[symbol] = df.tail(1000)

        self.logger.info(f"📊 {symbol}: {len(df)} candles saved.")
        return {"status": "ok", "symbol": symbol, "received": len(df)}

    # ==========================================================
    # 📈 Indicator Handling (Prediction Entry Point)
    # ==========================================================
    # ==========================================================
    # 📈 Indicator Handling (Prediction Entry Point)
    # ==========================================================
    def _handle_indicator(self, msg=None):
        """Handle indicator payload from MT4 and call Predictor."""
        try:
            symbol = msg.get("symbol", "EURUSD")
            rsi = float(msg.get("rsi", 0))
            ema_fast = float(msg.get("ema_fast", 0))
            ema_slow = float(msg.get("ema_slow", 0))
            macd = float(msg.get("macd", 0))

            self.logger.info(
                f"📈 {symbol}: RSI={rsi:.2f}, EMA12={ema_fast:.5f}, EMA26={ema_slow:.5f}, MACD={macd:.5f}"
            )

            # --- Safe candle extraction ---
            candle_features = []
            with self._lock:
                df = self.candle_buffers.get(symbol)
                if df is not None and not df.empty:
                    # Take recent candle averages as additional context
                    for col in ["open", "high", "low", "close", "volume"]:
                        if col in df.columns:
                            candle_features.append(float(df[col].tail(20).mean()))
                # Pad missing with zeros
                while len(candle_features) < 5:
                    candle_features.append(0.0)

            # --- Construct final 9-feature vector ---
            payload = [rsi, ema_fast, ema_slow, macd] + candle_features[:5]

            # --- Predict with AI ---
            result = self.predictor.predict(symbol, payload)

            # --- Log signals per symbol for retraining ---
            try:
                os.makedirs("./src/data", exist_ok=True)
                signal_file = f"./src/data/signal_{symbol}.csv"
                df = pd.DataFrame([result])
                df.to_csv(
                    signal_file,
                    mode="a",
                    index=False,
                    header=not os.path.exists(signal_file),
                )
            except Exception as e:
                self.logger.warning(f"⚠️ Failed to log signal for {symbol}: {e}")

            return result

        except Exception as e:
            self.logger.error(f"❌ Indicator handling failed: {e}")
            return {"status": "error", "reason": f"Indicator handling failed: {e}"}

        # ==========================================================
    # 💰 Account Info Handling
    # ==========================================================
    # ==========================================================
    # 💰 Account Info Handling
    # ==========================================================
    def _handle_account(self, msg=None, equity_drop_threshold=5):
        """Handle account data, detect drawdown, and send alerts."""
        try:
            account_id = str(msg.get("account_id", "default"))
            balance = float(msg.get("balance", 0))
            equity = float(msg.get("equity", 0))
            margin = float(msg.get("margin", 0))
            free_margin = float(msg.get("free_margin", 0))
            leverage = int(msg.get("leverage", 100))
            currency = msg.get("currency", "USD")
            timestamp = round(time.time(), 2)

            os.makedirs("./src/data", exist_ok=True)
            acc_path = f"./src/data/account_{account_id}.csv"

            df = pd.DataFrame([{
                "timestamp": timestamp,
                "balance": balance,
                "equity": equity,
                "margin": margin,
                "free_margin": free_margin,
                "leverage": leverage,
                "currency": currency
            }])
            df.to_csv(acc_path, mode="a", index=False, header=not os.path.exists(acc_path))

            with self._lock:
                prev = getattr(self, "last_account_state", None)
                self.last_account_state = df.iloc[-1].to_dict()

            drawdown_alert = None
            if prev:
                prev_balance = float(prev.get("balance", balance))
                if prev_balance > 0:
                    drop_pct = ((prev_balance - equity) / prev_balance) * 100.0
                    if drop_pct >= equity_drop_threshold and not self.TradingPaused:
                        drawdown_alert = f"⚠️ Equity down {drop_pct:.2f}% — trading paused."
                        self.TradingPaused = True
                        self.send_account_info()
                    elif self.TradingPaused and drop_pct < equity_drop_threshold / 2:
                        drawdown_alert = f"✅ Equity recovered ({drop_pct:.2f}% drop) — trading resumed."
                        self.TradingPaused = False
                        self.send_account_info()

            self.logger.info(
                f"💰 Account[{account_id}] Balance={balance:.2f} | Equity={equity:.2f} | Margin={margin:.2f} | Paused={self.TradingPaused}"
            )

            if drawdown_alert:
                self.logger.warning(drawdown_alert)
                try:
                    text = f"{drawdown_alert}\nBalance: {balance:.2f} {currency}\nEquity: {equity:.2f} {currency}"
                    self.telegram.send(text)
                except Exception as e:
                    self.logger.error(f"Telegram alert failed: {e}")

            return {
                "status": "ok",
                "type": "account_ack",
                "account_id": account_id,
                "paused": self.TradingPaused,
                "timestamp": timestamp,
                "message": drawdown_alert or "Account info received successfully."
            }

        except Exception as e:
            self.logger.error(f"❌ Account handler failed: {e}")
            return {"status": "error", "type": "account_error", "reason": str(e)}

    # ==========================================================
    # 📤 Send Account Info
    # ==========================================================
    def send_account_info(self):
        """Push current account status (paused/resumed) to all MT4 clients."""
        try:
            with self._lock:
                state = getattr(self, "last_account_state", None)
            if not state:
                self.logger.warning("⚠️ No account state to send.")
                return

            payload = {
                "type": "account_update",
                "status": "ok",
                "paused": self.TradingPaused,
                "data": state,
                "timestamp": round(time.time(), 2)
            }

            for addr, conn in list(self.clients.items()):
                try:
                    self._send_json(conn, payload)
                except Exception as e:
                    self.logger.error(f"Send error to {addr}: {e}")

            self.logger.info("📤 Account update sent to all MT4 clients.")
        except Exception as e:
            self.logger.error(f"❌ send_account_info failed: {e}")


# ==============================================================
# 🧩 Run Standalone
# ==============================================================
if __name__ == "__main__":
    srv = PredictServer()
    try:
        srv.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        srv.stop()
