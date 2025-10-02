import csv
import json
import os
import queue
import socket
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Tuple

from src.components.mt4_predictor import create_model_and_scaler_if_missing, MT4Predictor
from src.components.mt4_trainer import MT4Trainer

HOST = "127.0.0.1"
PORT = 50052
BUFFER_SIZE = 4096


@dataclass
class ClientMessage:
    type: str
    payload: Dict[str, Any]
    message_id: str


class PredictServer:
    def __init__(self, controller):
        self.controller = controller
        self.logger=controller.logger
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._last_pong_time = time.time()
        self._thread=None
        # Lifecycle
        self._stop_event = threading.Event()
        self._ping_thread = threading.Thread(target=self._ping_loop, daemon=True)
        self._ping_thread.start()

        # State
        self.clients: List[socket.socket] = []
        self.message_callbacks: Dict[str, Callable[[Dict], None]] = {}
        self.callback_queue: "queue.Queue[Tuple[str, Dict]]" = queue.Queue()
        self._last_pong_time = 0
        self._max_retries = 3
        self._retry_count = 0
        self.connected = False

        # AI components
        self.trainer = MT4Trainer(controller=controller)
        self.predictor = MT4Predictor(controller=controller)

    # -------------------------
    # Networking
    # -------------------------
    def start(self):
        self.server.bind((HOST, PORT))
        self.server.listen()
        self.controller.logger.info(f"🟢 Socket Server started on {HOST}:{PORT}")

        while not self._stop_event.is_set():
            try:
                conn, addr = self.server.accept()
                self.clients.append(conn)
                self._thread=threading.Thread(
                    target=self.handle_client, args=(conn, addr), daemon=True
                ).start()
            except Exception as e:
                self.controller.logger.error(f"❌ Server accept error: {e}")

    def handle_client(self, conn: socket.socket, addr):
        if conn:
            self.controller.logger.info(f"🔗 Connection established with {addr}")
        with conn:
            while not self._stop_event.is_set():
                try:
                    data = conn.recv(BUFFER_SIZE)
                    if not data:
                        break

                    message_str = data.decode("utf-8").strip()
                    self.controller.logger.debug(f"📩 Received: {message_str}")

                    try:
                        parsed = json.loads(message_str)
                        response = self._route_message(parsed)
                    except json.JSONDecodeError:
                        response = {"status": "error", "reason": "Invalid JSON"}

                    conn.sendall((json.dumps(response) + "\n").encode())
                except ConnectionResetError:
                    self.controller.logger.warning(f"⚠️ Connection lost with {addr}")
                    break
                except Exception as e:
                    self.controller.logger.error(f"❌ Client error {addr}: {e}")
                    break

        if conn in self.clients:
            self.clients.remove(conn)
        self.controller.logger.info(f"🔌 Connection closed: {addr}")

    def broadcast(self, message: Dict[str, Any]):
        msg_str = json.dumps(message) + "\n"
        for client in self.clients[:]:
            try:
                client.sendall(msg_str.encode())
            except Exception as ex:
                if client in self.clients:
                    self.clients.remove(client)
                self.controller.logger.warning(f"⚠️ Dropped client during broadcast: {ex}")

    # -------------------------
    # Command Routing
    # -------------------------
    def _route_message(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        """Route message by type/action."""
        message_id = msg.get("message_id")

        # Handle callbacks
        if message_id and message_id in self.message_callbacks:
            self.message_callbacks[message_id](msg)
            del self.message_callbacks[message_id]
            return {"status": "callback_handled"}

        action = msg.get("action")
        msg_type = msg.get("type")

        # ---- Ping ----
        if msg_type == "ping":
            self._last_pong_time = time.time()
            return {"type": "pong", "timestamp": int(time.time())}

        # ---- Signal Prediction ----
        if action == "signal":
            signal_str = msg.get("payload", {}).get("signal")
            prediction = self.predictor.predict(signal_str)
            if isinstance(prediction, str) and "," in prediction:
                direction, conf_str = prediction.split(",", 1)
                return {
                    "status": "success",
                    "direction": direction,
                    "confidence": float(conf_str),
                }
            return {"status": "error", "reason": "invalid prediction"}

        # ---- Account Info ----
        if action == "account_info":
            return {
                "status": "success",
                "data": {
                    "balance": 10000.0,
                    "equity": 9500.0,
                    "margin": 500.0,
                    "leverage": 500.0,
                },
            }

        # ---- Open Positions ----
        if action == "open_positions":
            return {
                "status": "success",
                "positions": [
                    {"symbol": "EURUSD", "type": "buy", "lot": 0.1, "profit": 15.3}
                ],
            }

        # ---- Trade Actions ----
        if action in ("buy", "sell", "close","reduce"):
            return {
                "status": "executed",
                "order": action,
                "symbol": msg.get("symbol"),
                "lot": msg.get("lot", 0.1),
            }

        return {"status": "ok", "echo": msg}

    # -------------------------
    # Health / Ping
    # -------------------------
    def _ping_loop(self):
        while not self._stop_event.is_set():
            try:
                if time.time() - self._last_pong_time > 30:
                    self._retry_count += 1
                    self.controller.logger.warning(
                        f"🔄 No pong in 30s. Retry {self._retry_count}/{self._max_retries}"
                    )
                    if self._retry_count >= self._max_retries:
                        self.connected = False
                        self.controller.logger.error("❌ Connection lost.")
                        self._retry_count = 0

                ping_id = str(uuid.uuid4())
                ping = {"type": "ping", "timestamp": int(time.time()), "message_id": ping_id}

                def on_reply(reply):
                    self.controller.logger.info(f"📨 Ping reply {ping_id}: {reply}")

                self.message_callbacks[ping_id] = on_reply
                self.broadcast(ping)
            except Exception as e:
                self.controller.logger.error(f"❌ Ping error: {e}")

            time.sleep(10)

    # -------------------------
    # Data & Signals
    # -------------------------
    def get_signals_data(self, symbol: str = "EURCAD") -> Tuple[str, str]:
        symbol = symbol.upper()
        s1, s2, s3, s4 = 0.7, 0.6, 0.4, 0.9
        timestamp = int(time.time())
        open_, high, low, close, volume = 1.39448, 1.39465, 1.39442, 1.39456, 339

        os.makedirs("src/data", exist_ok=True)
        signal_csv = f"src/data/signal_{symbol}.csv"
        candle_csv = f"src/data/candle_{symbol}.csv"

        self._append_csv(signal_csv, ["s1", "s2", "s3", "s4"], [s1, s2, s3, s4])
        self._append_csv(
            candle_csv,
            ["time", "open", "high", "low", "close", "volume"],
            [timestamp, open_, high, low, close, volume],
        )

        # Ensure model exists
        create_model_and_scaler_if_missing("src/model/model.keras", "src/model/scaler.pkl")
        # ⚠️ Consider training asynchronously, not every tick
        self.trainer.train_and_save_model(symbol, signal_csv, candle_csv, "src/model/model.keras", "./src/model/scaler.pkl")

        # Predict
        signal_str = f"{s1:.5f},{s2:.5f},{s3:.5f},{s4:.5f},{symbol},{timestamp},{open_},{close},{high},{low},{volume}"
        prediction = self.predictor.predict(signal_str)

        direction, confidence = "error", 0.0
        if isinstance(prediction, str) and "," in prediction:
            direction, conf_str = prediction.split(",", 1)
            confidence = float(conf_str)

        final_response = {
            "type": "signal",
            "message_id": str(uuid.uuid4()),
            "payload": {"symbol": symbol, "signal": signal_str, "direction": direction, "confidence": confidence},
        }

        self.broadcast(final_response)
        self.controller.logger.info(f"📤 Signal prediction sent: {final_response}")
        return signal_str, ",".join(map(str, [timestamp, open_, high, low, close, volume]))

    @staticmethod
    def _append_csv(file_path: str, header: List[str], row: List[Any]):
        new_file = not os.path.exists(file_path) or os.stat(file_path).st_size == 0
        with open(file_path, "a") as f:
            writer = csv.writer(f)
            if new_file:
                writer.writerow(header)
            writer.writerow(row)

    # -------------------------
    # Lifecycle
    # -------------------------
    def shutdown(self):
        self.controller.logger.info("🔕 Shutting down PredictServer...")
        self._stop_event.set()
        try:
            for client in self.clients:
                client.close()
        except Exception as e:
            self.controller.logger.error(e)
        finally:
            self.server.close()
        self._ping_thread.join(timeout=2.0)
