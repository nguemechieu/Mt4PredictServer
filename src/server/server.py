import csv
import json
import os
import socket
import threading
import time
import uuid
from typing import final

from components.mt4_predictor import create_model_and_scaler_if_missing
from components.mt4_trainer import MT4Trainer
from src.components.mt4_predictor import MT4Predictor

HOST = '127.0.0.1'
PORT = 50052

clients = []
message_callbacks = {}  # Track responses by message_id

message = {
    "type": "signal",
    "payload": {
        "type": "signal",
        "symbol": "USDCAD",
        "data": {
            "s1": 33.30644,
            "s2": 1.39557,
            "s3": 1.39621,
            "s4": 33.30644,
            "time": 1747378800,
            "open": 1.39448,
            "close": 1.39456,
            "high": 1.39465,
            "low": 1.39442,
            "volume": 339
        }
    },
    "message_id": "720c0985-0bcc-a151-ff21-75568ac686ad"
}
class PredictServer:
    def __init__(self, controller=None):
        self.controller = controller
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.connected = False
        self._pending_signal_request = None
        self._stop_event = threading.Event()
        self._last_pong_time = 0
        self._max_retries = 3
        self._retry_count = 0

        self._ping_thread = threading.Thread(target=self._ping_loop, daemon=True)
        self._ping_thread.start()

        self.trainer = MT4Trainer(self.controller)
        self.predictor = MT4Predictor(self.controller)

    def handle_client(self, conn, addr):
        self.controller.logger.info(f"🔗 Connection established with {addr}")
        with conn:
            while not self._stop_event.is_set():
                try:
                    data = conn.recv(4096)
                    if not data:
                        break
                    message_ = data.decode('utf-8').strip()
                    self.controller.logger.info(f"📩 Received from {addr}: {message_}")

                    try:
                        parsed = json.loads(message_)
                        message_id = parsed.get("message_id")

                        if message_id and message_id in message_callbacks:
                            message_callbacks[message_id](parsed)
                            del message_callbacks[message_id]
                            continue

                        response = self.send_command(parsed)
                        if isinstance(response, dict) and message_id:
                            response["message_id"] = message_id
                    except json.JSONDecodeError:
                        response = {"status": "error", "reason": "Invalid JSON"}

                    conn.sendall((json.dumps(response) + '\n').encode())
                    self.controller.logger.info(f"📤 Sent to {addr}: {response}")
                except ConnectionResetError:
                    self.controller.logger.warning(f"⚠️ Connection lost with {addr}")
                    break
        self.controller.logger.info(f"🔌 Connection closed: {addr}")
        if conn in clients:
            clients.remove(conn)

    def start(self):
        self.server.bind((HOST, PORT))
        self.server.listen()
        self.controller.logger.info(f"🟢 Socket Server started on {HOST}:{PORT}")

        while not self._stop_event.is_set():
            conn, addr = self.server.accept()
            clients.append(conn)
            threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True).start()

    def get_account_info(self):
        return self.send_command({"action": "account_info"})

    def get_open_positions(self):
        return self.send_command({"action": "open_positions"})


    def send_command(self, cmd):
        action = cmd.get("action")

        if cmd.get("type") == "ping":
            return {"type": "pong", "timestamp": int(time.time())}

        if action == "account_info":
            return {
                "status": "success",
                "data": {
                    "balance": 10000.0,
                    "equity": 9500.0,
                    "margin": 500.0,
                    "leverage": 500.0
                }
            }

        if action == "open_positions":
            return {
                "status": "success",
                "positions": [
                    {"symbol": "EURUSD", "type": "buy", "lot": 0.1, "profit": 15.3}
                ]
            }

        if action == "signal_response":
            return {"status": "received", "signal": cmd.get("data", {})}

        if action == "buy":
            return {
                "status": "executed",
                "order": "buy",
                "symbol": cmd.get("symbol", "EURUSD"),
                "lot": cmd.get("lot", 0.1)
            }

        if action == "sell":
            return {
                "status": "executed",
                "order": "sell",
                "symbol": cmd.get("symbol", "EURUSD"),
                "lot": cmd.get("lot", 0.1)
            }

        if action == "close":
            return {
                "status": "executed",
                "order": "close",
                "symbol": cmd.get("symbol", "EURUSD")
            }

        return {"status": "ok", "echo": cmd}

    def _ping_loop(self):
        while not self._stop_event.is_set():
            try:
                if time.time() - self._last_pong_time > 30:
                    self._retry_count += 1
                    self.controller.logger.warning(f"🔄 No pong in 30s. Retry {self._retry_count}/{self._max_retries}")
                    if self._retry_count >= self._max_retries:
                        self.connected = False
                        self.controller.logger.error("❌ Connection lost. Marked as disconnected.")
                        self._retry_count = 0

                ping_id = str(uuid.uuid4())
                ping = {"type": "ping", "timestamp": int(time.time()), "message_id": ping_id}

                def on_reply(reply):
                    self.controller.logger.info(f"📨 Matched ping reply {ping_id}: {reply}")

                message_callbacks[ping_id] = on_reply

                for client in clients:
                    try:
                        client.sendall((json.dumps(ping) + '\n').encode())
                    except Exception:
                        continue

                self.controller.logger.info("📶 Ping broadcast to MT4.")
            except Exception as e:
                self.controller.logger.error(f"❌ Ping error: {e}")
            time.sleep(10)

    def shutdown(self):
        self.controller.logger.info("🔕 Shutting down PredictServer...")
        self._stop_event.set()
        self._ping_thread.join(timeout=2.0)


    def get_signals_data(self, symbol="EURJPY"):
     symbol_str = symbol.upper()

     # Dummy values for testing/training
     s1, s2, s3, s4 = 0.7, 0.6, 0.4, 0.9
     timestamp = int(time.time())
     open_, high, low, close, volume = 1.39448, 1.39465, 1.39442, 1.39456, 339

     os.makedirs("src/data", exist_ok=True)

     signal_csv = f"src/data/signal_data_{symbol_str}.csv"
     candle_csv = f"src/data/candle_data_{symbol_str}.csv"

    # Save signal
     with open(signal_csv, "a", newline="") as f:
        writer = csv.writer(f)
        if os.stat(signal_csv).st_size == 0:
            writer.writerow(["s1", "s2", "s3", "s4"])
        writer.writerow([s1, s2, s3, s4])

    # Save candle
     with open(candle_csv, "a", newline="") as f:
        writer = csv.writer(f)
        if os.stat(candle_csv).st_size == 0:
            writer.writerow(["time", "open", "high", "low", "close", "volume"])
        writer.writerow([timestamp, open_, high, low, close, volume])

    # Ensure model exists
     create_model_and_scaler_if_missing("src/model/model.keras", "src/model/scaler.pkl")
     self.trainer.train_and_save_model(symbol_str, signal_csv, candle_csv, "src/model/model.keras", "src/model/scaler.pkl")

    # Construct signal string
     signal_str = f"{s1:.5f},{s2:.5f},{s3:.5f},{s4:.5f},{symbol},{timestamp},{open_},{close},{high},{low},{volume}"

    # 🔮 Predict
     prediction_result = self.predictor.predict(signal_str)

     if isinstance(prediction_result, str) and "," in prediction_result:
        direction, confidence = prediction_result.split(",", 1)
     else:
        direction, confidence = "error", "0.0"

     message_id = str(uuid.uuid4())

     final_response = {
        "type": "signal",
        "message_id": message_id,
        "payload": {
            "symbol": symbol,
            "signal": signal_str,
            "direction": direction,
            "confidence": float(confidence)
        }
    }

     def on_reply(reply):
        self.controller.logger.info(f"📨 Matched reply for {message_id}: {reply}")

     message_callbacks[message_id] = on_reply

     for client in clients:
        try:
            client.sendall((json.dumps(final_response) + '\n').encode())
        except Exception as e:
            self.controller.logger.error(f"❌ Failed to communicate with client: {e}")

     self.controller.logger.info(f"📤 Sent signal prediction: {final_response}")
     return signal_str, ",".join(map(str, [timestamp, open_, high, low, close, volume]))
