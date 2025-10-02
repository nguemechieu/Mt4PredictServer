import json
import logging
import socket
import threading
import time

import numpy as np

from components.mt4_predictor import MT4Predictor

HOST = "127.0.0.1"
PORT = 50052


# ==========================
# Custom JSON Encoder
# ==========================
class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.ndarray,)):
            return obj.tolist()
        return super().default(obj)


# ==========================
# Predict Server
# ==========================
class PredictServer:
    def __init__(self):
        # Proper logger
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[logging.StreamHandler()]
        )
        self.logger = logging.getLogger("PredictServer")

        # Init networking
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.clients = []
        self._stop_event = threading.Event()

        # Predictor
        self.predictor = MT4Predictor()

    def start(self):
        self.server.bind((HOST, PORT))
        self.server.listen()
        self.logger.info(f"🟢 Socket Server started on {HOST}:{PORT}")

        while not self._stop_event.is_set():
            try:
                conn, addr = self.server.accept()
                self.clients.append(conn)
                threading.Thread(
                    target=self.handle_client, args=(conn, addr), daemon=True
                ).start()
            except OSError:
                break
            except Exception as e:
                self.logger.error(f"❌ Server accept error: {e}")

    def stop(self):
        self._stop_event.set()
        for c in self.clients:
            try:
                c.close()
            except Exception:
                pass
        self.server.close()
        self.logger.info("🛑 Socket Server stopped.")

    def handle_client(self, conn, addr):
        self.logger.info(f"🔗 Client connected: {addr}")
        with conn:
            try:
                while True:
                    data = conn.recv(4096)
                    if not data:
                        break

                    try:
                        msg = json.loads(data.decode().strip())
                    except Exception as e:
                        self.logger.error(f"⚠️ Bad JSON from {addr}: {data}/{e}")
                        continue

                    response = self.process_message(msg)
                    if response is not None:
                        try:
                            conn.sendall((json.dumps(response, cls=NpEncoder) + "\n").encode("utf-8"))
                        except Exception as e:
                            self.logger.error(f"❌ Send error: {e}")

            except Exception as e:
                self.logger.error(f"❌ Client error {addr}: {e}")
            finally:
                self.logger.info(f"🔌 Client disconnected: {addr}")
                if conn in self.clients:
                    self.clients.remove(conn)

    def process_message(self, msg: dict) -> dict:
        """Handle incoming messages and return a JSON response."""
        mtype = msg.get("type", "").lower()

        # === Ping / Pong ===
        if mtype == "ping":
            return {"type": "pong", "timestamp": time.time()}

        # === Trade Command ===
        elif mtype == "trade_command":
            symbol = msg.get("symbol", "")
            action = msg.get("action", "")
            lot = msg.get("lot_size", 0.1)
            self.logger.info(f"💹 TradeCommand received: {symbol} {action} {lot}")
            return {"status": "ok", "echo": msg}

        # === Prediction ===
        elif mtype == "prediction":
            symbol = msg.get("symbol", "")
            pred = msg.get("prediction", 0.0)
            self.logger.info(f"🧠 Prediction received for {symbol}: {pred}")
            return {"status": "ok", "echo": msg}

        # === Indicator Signal ===
        elif mtype == "indicator_signal":
            self.logger.info(f"📊 IndicatorSignal received: {msg}")

            # Build payload string from fields
            s1, s2, s3, s4 = msg.get("s1", 0), msg.get("s2", 0), msg.get("s3", 0), msg.get("s4", 0)
            payload = f"{s1},{s2},{s3},{s4},{msg.get('symbol','')}"

            result = self.predictor.predict(payload, msg.get("symbol", "EURUSD"))
            # Ensure pure Python types
            result["confidence"] = float(result.get("confidence", 0.0))
            return result

        # === Candle Batch ===
        elif mtype == "candle_batch":
            self.logger.info("🕯️ CandleBatch received")
            return {"status": "ok", "processed": True}

        # === Account Info ===
        elif mtype == "account_info":
            return {
                "balance": 10000.0,
                "equity": 10050.0,
                "margin": 200.0,
                "leverage": 100,
            }

        # === Open Positions ===
        elif mtype == "open_positions":
            return {
                "positions": [
                    {"ticket": 1, "symbol": "EURUSD", "type": "buy", "lots": 0.1, "profit": 15.2}
                ]
            }

        # === Get Command ===
        elif mtype == "get_command":
            return {"command": "none"}

        else:
            self.logger.warning(f"⚠️ Unknown message type: {mtype}")
            return {"status": "error", "reason": "unknown message"}


if __name__ == "__main__":
    srv = PredictServer()
    try:
        srv.start()
    except KeyboardInterrupt:
        srv.stop()
