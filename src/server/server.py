import json
import logging
import os
import queue
import socket
import threading
import time
from functools import total_ordering

import numpy as np
import pandas as pd
from telegram import TelegramObject

from src.components.GPTAdvisor import GPTAdvisor
from src.components.mt4_predictor import MT4Predictor

HOST = "127.0.0.1"
PORT = 9999
BUFFER_SIZE = 4096
# ==========================================================
# JSON encoder for NumPy types
# ==========================================================
class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.ndarray,)):
            return obj.tolist()
        return super().default(obj)


# ==========================================================
# Default logger
# ==========================================================
def _default_logger():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    return logging.getLogger("PredictServer")




def append_csv(path, new_df):
    """Append rows to a CSV safely (avoiding overwrites)."""
    if not os.path.exists(path):
        new_df.to_csv(path, index=False)
    else:
        old = pd.read_csv(path)
        combined = pd.concat([old, new_df], ignore_index=True)
        combined.drop_duplicates(inplace=True)
        combined.to_csv(path, index=False)
class PredictServer:
    """Socket bridge between MT4 DLL and Python AI backend."""

    def __init__(self, controller=None):
        self.controller = controller
        self.logger = getattr(controller, "logger", _default_logger())

        # Core components
        self.gpt = GPTAdvisor(self.controller)
        self.predictor = MT4Predictor(self.controller)


        # Runtime state
        self.last_confidence = {}
        self.last_direction = {}
        self.last_gpt_time = {}
        self.account_info = {}
        self.order_history = []
        self.open_orders = []

        self.clients = []
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self.server_socket = None

        # Buffers
        self.candle_buffers = {}
        self.prediction_queues = {}
        self.active_workers = {}

    # ==========================================================
    # Lifecycle
    # ==========================================================
    def start(self):
        """Start the socket server."""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((HOST, PORT))
            self.server_socket.listen(5)
            self.logger.info(f"🟢 PredictServer listening on {HOST}:{PORT}")
            threading.Thread(target=self._accept_loop, daemon=True).start()
        except Exception as e:
            self.logger.error(f"❌ Server start failed: {e}")

    def stop(self):
        """Gracefully stop the server."""
        self._stop_event.set()
        for c in list(self.clients):
            try:
                c.close()
            except Exception as ex:
                self.logger.error(ex)


        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception as exx:
                self.logger.error(exx)

        self.logger.info("🛑 PredictServer stopped.")

    # ==========================================================
    # Connection Handling
    # ==========================================================
    def _accept_loop(self):
        while not self._stop_event.is_set():
            try:
                conn, addr = self.server_socket.accept()
                self.clients.append(conn)
                self.logger.info(f"🔗 Client connected: {addr}")
                threading.Thread(target=self._handle_client, args=(conn, addr), daemon=True).start()
            except OSError:
                break
            except Exception as e:
                self.logger.error(f"❌ Accept error: {e}")

    def _handle_client(self, conn, addr):
        """Handle each MT4 client."""
        try:
            while not self._stop_event.is_set():
                msg = self.receive_message(conn)
                if msg is None:
                    break
                response = self.process_message(msg)
                if response:
                    self.send_message(conn, response)
        except Exception as e:
            self.logger.error(f"❌ Client error {addr}: {e}")
        finally:
            conn.close()
            if conn in self.clients:
                self.clients.remove(conn)
            self.logger.info(f"🔌 Disconnected: {addr}")

    # ==========================================================
    # I/O
    # ==========================================================
    def receive_message(self, conn):
        try:
            data = conn.recv(BUFFER_SIZE)
            if not data:
                return None
            text = data.decode("utf-8", errors="ignore").strip()
            if not text:
                return None
            for chunk in text.split("\n"):
                if chunk.strip():
                    return json.loads(chunk)
            return None
        except Exception as e:
            self.logger.error(f"❌ Receive error: {e}")
            return None

    def send_message(self, conn, response):
        try:
            packet = json.dumps(response, cls=NpEncoder) + "\n"
            conn.sendall(packet.encode("utf-8"))
            self.logger.debug(f"📤 Sent: {packet.strip()}")
        except Exception as e:
            self.logger.error(f"❌ Send error: {e}")

    # ==========================================================
    # Dispatcher
    # ==========================================================
    def process_message(self, msg):
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
            return {"type": "info", "status": "error", "reason": str(e), "timestamp": time.time()}

    # ==========================================================
    # Candle Handler
    # ==========================================================
    def _process_candles(self, msg)->None:
        symbol = str(msg.get("symbol") or "EURUSD")
        candle = msg.get("candle") or {}
        ind_data = msg.get("indicators") or {}

        # --- Save account info ---
        self.account_info = msg.get("account_info", {})
        if self.account_info:
            df_acc = pd.DataFrame([self.account_info])
            df_acc.dropna()
            append_csv("./src/data/account_info.csv", df_acc)

        # --- Save order history ---
        self.order_history = msg.get("order_history", [])
        if isinstance(self.order_history, list) and len(self.order_history) > 0:
            df_hist = pd.DataFrame(self.order_history)
            append_csv("./src/data/order_history.csv", df_hist)

        # --- Save open orders ---
        self.open_orders = msg.get("open_orders", [])
        if isinstance(self.open_orders, list) and len(self.open_orders) > 0:
            df_open = pd.DataFrame(self.open_orders)
            append_csv("./src/data/open_orders.csv", df_open)

        # --- Validate candle ---
        if not isinstance(candle, dict) or not candle:
            raise {"type":"candles","status": "error", "reason": "missing candle data", "symbol": symbol}

        # --- Candle buffer ---
        with self._lock:
            if symbol not in self.candle_buffers:
                self.candle_buffers[symbol] = pd.DataFrame()
            if symbol not in self.prediction_queues:
                self.prediction_queues[symbol] = queue.Queue()

        df = pd.DataFrame([{
            "open": float(candle.get("open", 0.0)),
            "high": float(candle.get("high", 0.0)),
            "low": float(candle.get("low", 0.0)),
            "close": float(candle.get("close", 0.0)),
            "volume": float(candle.get("volume", 0.0))
        }])
        df['time']=   candle.get("time", 0)

        df+=df
        df.drop_duplicates(inplace=True)


        num_cols = ["open", "high", "low", "close", "volume"]
        df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce")


        with self._lock:
            old_df = self.candle_buffers[symbol]
            self.candle_buffers[symbol] = pd.concat([old_df, df], ignore_index=True).tail(10)
        total_candles = len(self.candle_buffers[symbol])
        if total_candles<10:
                return None



        self.logger.info(f"📊 {symbol}: {len(self.candle_buffers[symbol])} candles buffered")

        # --- Queue prediction ---
        features = [
            float(ind_data.get("ema_fast", 0.0)),
            float(ind_data.get("ema_slow", 0.0)),
            float(ind_data.get("rsi", 0.0)),
            float(ind_data.get("macd", 0.0))
            #float(ind_data.get("cci" , 0.0)),          # New
            #float(ind_data.get("last_open_price", 0.0)),    # New
            #float(ind_data.get("last_close_price" , 0.0)),   # New
            #float(ind_data.get("avg_loss_last_3" , 0.0)),    # New
        ]

        ind_data_df= pd.DataFrame([{
            "ema_fast": float(ind_data.get("ema_fast", 0.0)),
            "ema_slow": float(ind_data.get("ema_slow", 0.0)),
            "rsi": float(ind_data.get("rsi", 0.0)),
            "macd": float(ind_data.get("macd", 0.0))
            #"previous_loss": float(ind_data.get("previous_loss", 0.0)),
            #"last_open_price": float(ind_data.get("last_open_price", 0.0)),
            #"last_close_price": float(ind_data.get("last_close_price", 0.0)),
            #"avg_loss_last_3": float(ind_data.get("avg_loss_last_3", 0.0)),
        }])
        ind_data_df.to_csv("./src/data/signal_"+symbol+".csv")
        df.to_csv("./src/data/candle_"+symbol+".csv")

        model_path="./model/model.keras"
        scaler_path="./model/scaler.pkl"
        order_history_path="./src/data/order_history.csv"



        self.predictor.trainer.train_and_save_model(symbol,"./src/data/signal_"+symbol+".csv",
                                                    "./src/data/candle_"+symbol+".csv",model_path,scaler_path,
                                                    order_history_path )



        self.prediction_queues[symbol].put((symbol, features, df.iloc[-1].to_dict()))

        if symbol not in self.active_workers or not self.active_workers[symbol].is_alive():
            worker = threading.Thread(target=self._prediction_worker, args=(symbol,), daemon=True)
            self.active_workers[symbol] = worker
            worker.start()


        return None

    # ==========================================================
    # Prediction Worker
    # ==========================================================
    def _prediction_worker(self, symbol=None):
        q = self.prediction_queues[symbol]
        while not q.empty():
            try:
                symbol, features, candle = q.get()
                result = self.predictor.predict(symbol, features)
                cur_dir = str(result.get("direction", "neutral"))
                conf = float(result.get("confidence", 0.0))

                now = time.time()
                prev_dir = self.last_direction.get(symbol)
                prev_conf = self.last_confidence.get(symbol, 0.0)
                last_call = self.last_gpt_time.get(symbol, 0)
                cooldown = (now - last_call) > 300

                direction_changed = (prev_dir != cur_dir)
                confidence_changed = abs(prev_conf - conf) > 0.1

                if direction_changed or confidence_changed or cooldown:
                    prompt = (
                        f"You are a trading assistant.\n"
                        f"Symbol: {symbol}\nDirection: {cur_dir}\nConfidence: {conf:.2f}\n"
                        f"EMA Fast: {features[0]} | EMA Slow: {features[1]}\n"
                        f"RSI: {features[2]} | MACD: {features[3]}\n"
                        f"Position history : {self.order_history}\n"
                        f"Account info : {self.account_info}\n"
                        f"Open orders : {self.open_orders}\n"
                        "Provide reasoning and suggested action."
                    )
                    try:
                        gpt_response = self.gpt.ask(prompt)
                    except Exception as e:
                        gpt_response = f"GPT analysis failed: {e}"
                    self.last_gpt_time[symbol] = now
                else:
                    gpt_response = "No significant market change detected."

                # --- Reversal ---
                if prev_dir and prev_dir != cur_dir:
                    self.logger.warning(f"🔁 Reversal {symbol}: {prev_dir} → {cur_dir}")
                    reversal = {
                        "type": "trade_command",
                        "action": "CLOSE",
                        "symbol": symbol,
                        "reason": f"Reversal {prev_dir}→{cur_dir}",
                        "timestamp": time.time(),
                    }
                    for c in list(self.clients):
                        threading.Thread(target=self.send_message, args=(c, reversal), daemon=True).start()

                # --- Save ---
                self.last_direction[symbol] = cur_dir
                self.last_confidence[symbol] = conf

                record = {
                    "symbol": symbol,
                    "direction": cur_dir,
                    "confidence": conf,
                    "timestamp": time.time(),
                    "analysis": gpt_response,
                }
                self._save_prediction(record)

                response = {**record, "status": "ok"}
                for c in list(self.clients):
                    threading.Thread(target=self.send_message, args=(c, response), daemon=True).start()

            except Exception as e:
                self.logger.error(f"❌ Prediction thread error for {symbol}: {e}")

    # ==========================================================
    # Save Prediction
    # ==========================================================
    def _save_prediction(self, record):
        try:
            os.makedirs("./src/data", exist_ok=True)
            df = pd.DataFrame([record])

            path = "./src/data/predictions.csv"

            write_header = not os.path.exists(path)
            df.to_csv(path, mode="a", index=False, header=write_header)
        except Exception as e:
            self.logger.error(f"❌ Save prediction failed: {e}")



    def _process_gpt(self, msg=None):
        """
        Handle GPT or AI advisory queries with full trading context.
        Accepts:
            {
              "type": "gpt_query",
              "query": "Should I close EURUSD?",
              "context": {
                  "symbol": "EURUSD",
                  "indicators": {...}
              }
            }
        Returns:
            {
              "type": "ai_response",
              "status": "ok",
              "symbol": "EURUSD",
              "content": "...analysis...",
              "timestamp": ...
            }
        """


        try:
        # --- Validate GPT query ---
         query = (msg.get("query") or "").strip()
         if not query:
            return {"status": "error", "reason": "Empty GPT query.", "timestamp": time.time()}

         if not hasattr(self, "gpt") or self.gpt is None:
            return {"status": "error", "reason": "GPTAdvisor not initialized.", "timestamp": time.time()}

         context = msg.get("context", {})
         symbol = context.get("symbol", "N/A")
         indicators = context.get("indicators", {})

        # === Collect live data for GPT context ===
         acc_info = getattr(self, "account_info", {})
         open_orders = getattr(self, "open_orders", [])
         order_history = getattr(self, "order_history", [])

        # --- Format account info for GPT ---
         acc_summary = (
            f"Account Name: {acc_info.get('account_name', 'N/A')} | "
            f"Balance: ${acc_info.get('balance', 0):.2f} | "
            f"Equity: ${acc_info.get('equity', 0):.2f} | "
            f"Margin: ${acc_info.get('margin', 0):.2f} | "
            f"Free Margin: ${acc_info.get('free_margin', 0):.2f}"
            f"Profit: ${acc_info.get('profit', 0):.2f}"
        )

        # --- Summarize open orders ---
         open_summary = "No open orders."
         if isinstance(open_orders, list) and len(open_orders) > 0:
            open_summary = "\n".join([
                f"- {o.get('symbol', '?')} | {o.get('type', '?')} | Lots: {o.get('lots', '?')} | "
                f"Profit: {o.get('profit', 0):.2f}"
                for o in open_orders[:5]  # limit to 5 for readability
            ])

        # --- Summarize order history ---
         hist_summary = "No closed trades."
         if isinstance(order_history, list) and len(order_history) > 0:
            hist_df = pd.DataFrame(order_history)
            total_trades = len(hist_df)
            total_pnl = hist_df["profit"].sum() if "profit" in hist_df else 0.0
            win_rate = (
                (hist_df["profit"] > 0).sum() / total_trades * 100
                if total_trades > 0 else 0
            )
            hist_summary = (
                f"Total Trades: {total_trades} | "
                f"PnL: ${total_pnl:.2f} | Win Rate: {win_rate:.2f}%"
            )

        # === Build an advanced GPT prompt ===
         prompt = (
            f"You are a professional trading assistant analyzing real-time trading data.\n\n"
            f"=== USER QUERY ===\n{query}\n\n"
            f"=== SYMBOL ===\n{symbol}\n\n"
            f"=== TECHNICAL INDICATORS ===\n{json.dumps(indicators, indent=2)}\n\n"
            f"=== ACCOUNT OVERVIEW ===\n{acc_summary}\n\n"
            f"=== OPEN POSITIONS ===\n{open_summary}\n\n"
            f"=== TRADE HISTORY SUMMARY ===\n{hist_summary}\n\n"
            f"Based on all this information, provide:\n"
            f"1. A concise analysis of the market condition for {symbol}.\n"
            f"2. Whether to BUY, SELL, or HOLD.\n"
            f"3. Any risk or margin-related warnings.\n"
            f"4. Confidence level (0–100%)."
        )

        # --- Execute GPT query ---
         start = time.time()
         try:
            answer = self.gpt.ask(prompt)
         except Exception as e:
            self.logger.error(f"❌ GPT query failed: {e}")
            answer = f"⚠️ GPT request failed: {e}"
         latency = time.time() - start

        # --- Return structured response ---
         response = {
            "type": "ai_response",
            "status": "ok" if "⚠️" not in answer else "error",
            "symbol": symbol,
            "query": query,
            "content": answer,
            "latency_sec": round(latency, 2),
            "timestamp": time.time()
        }

        # --- Log GPT output ---
         self.logger.info(f"🧠 GPT Adviser [{symbol}] | {query[:50]}... ({latency:.2f}s)")

        # Optional: Save GPT log
         self._save_gpt_log(symbol, query, prompt, answer, latency)

         return response

        except Exception as e_:
         self.logger.error(f"❌ GPT processing exception: {e_}")
        return {"type":"info","status": "error", "reason": str(e_), "timestamp": time.time()}


# ==========================================================
# Optional GPT Log Saver
# ==========================================================
    def _save_gpt_log(self, symbol, query, prompt, answer, latency):
     """Save GPT requests and responses to a CSV log for later analysis."""
     try:
        os.makedirs("./src/data", exist_ok=True)
        path = "./src/data/gpt_log.csv"
        record = [{
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "symbol": symbol,
            "query": query,
            "prompt": prompt,
            "latency_sec": latency,
            "response_preview": answer[:200],
        }]
        df = pd.DataFrame(record)

        append_csv(path, df)
     except Exception as e:
        self.logger.error(f"❌ Failed to save GPT log: {e}")


