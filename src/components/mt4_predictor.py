import ctypes
import logging
import os
import time
import joblib
import numpy as np
import pandas as pd
from keras.api.models import Sequential, load_model
from keras.api.layers import Dense
from sklearn.preprocessing import StandardScaler
from components.mt4_trainer import MT4Trainer

def extract_signal_values(message: str):
    """
    Extracts the first 4 floats from a signal string like:
    ":signal:0.7,0.6,0.4,0.9,EURUSD,..."
    """
    try:
        if ":" in message:
            message = message.split(":", 2)[-1]
        parts = message.split(",")
        if len(parts) < 4:
            raise ValueError("Less than 4 numeric values provided")
        return list(map(float, parts[:4]))
    except Exception as e:
        raise ValueError(f"Failed to extract signal values: {e}")

MODEL_PATH = "src/model/model.keras"
SCALER_PATH = "src/model/scaler.pkl"

def create_model_and_scaler_if_missing(model_path, scaler_path):
    os.makedirs(os.path.dirname(model_path), exist_ok=True)

    if os.path.exists(model_path) and os.path.exists(scaler_path):
        logging.info("✅ Model and scaler already exist.")
        return

    logging.warning("⚠️ Model or scaler missing — creating dummy versions...")

    x_train = np.random.rand(1000, 4)
    y_train = np.random.randint(0, 2, 1000)

    scaler = StandardScaler()
    x_scaled = scaler.fit_transform(x_train)
    joblib.dump(scaler, scaler_path)
    logging.info(f"✅ Dummy scaler saved at {scaler_path}")

    model = Sequential([
        Dense(64, activation="relu", input_shape=(4,)),
        Dense(32, activation="relu"),
        Dense(1, activation="sigmoid")
    ])
    model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
    model.fit(x_scaled, y_train, epochs=5, batch_size=32, verbose=0)
    model.save(model_path)
    logging.info(f"✅ Dummy model saved at {model_path}")

create_model_and_scaler_if_missing(MODEL_PATH, SCALER_PATH)

class MT4Predictor:
    def __init__(self, controller=None):
        self.controller = controller
        self.model = None
        self.scaler = None
        self.trainer = MT4Trainer(self.controller)

    def log(self, message):
        if self.controller and hasattr(self.controller, "logger"):
            self.controller.logger.info(message)
        else:
            logging.info(message)

    def log_error(self, message):
        if self.controller and hasattr(self.controller, "logger"):
            self.controller.logger.error(message)
        else:
            logging.error(message)

    def load_model(self):
        try:
            self.model = load_model(MODEL_PATH)
            self.log("✅ Model loaded successfully.")
        except Exception as e:
            self.log_error(f"❌ Failed to load model: {e}")
            raise RuntimeError("Model loading failed.") from e

    def load_scaler(self):
        try:
            if not os.path.exists(SCALER_PATH):
                self.log("⚠️ Scaler not found. Creating default scaler...")
                dummy_data = np.array([[0.0] * 4, [1.0] * 4])
                scaler = StandardScaler().fit(dummy_data)
                os.makedirs(os.path.dirname(SCALER_PATH), exist_ok=True)
                joblib.dump(scaler, SCALER_PATH)
                self.log("✅ Default scaler created and saved.")
            self.scaler = joblib.load(SCALER_PATH)
            self.log("✅ Scaler loaded successfully.")
        except Exception as e:
            self.log_error(f"❌ Failed to load or create scaler: {e}")
            raise RuntimeError("Scaler loading failed.") from e

    def validate_payload(self, payload1):
        try:
            payload = extract_signal_values(payload1)
        except Exception as e:
            self.log_error(f"❌ Failed to extract signal values: {e}")
            return None

        if not isinstance(payload, (list, np.ndarray)) or len(payload) != 4:
            self.log_error(f"❌ Invalid payload size or type: {payload}")
            return None

        if any(not isinstance(x, (int, float)) for x in payload):
            self.log_error(f"❌ Non-numeric values in payload: {payload}")
            return None

        return payload

    def predict(self, payload):
        """
        Accepts signal string payload (e.g., "0.7,0.6,0.4,0.9,EURUSD,...")
        and returns dict: {"direction": str, "confidence": float}
        """
        try:
            signal = self.validate_payload(payload)
            if signal is None:
                return {"direction": "error", "confidence": 0.0}

            if self.model is None:
                self.load_model()
            if self.scaler is None:
                self.load_scaler()

            self.log(f"📩 Signal received: {payload}")
            input_data = np.array([signal])
            scaled_data = self.scaler.transform(input_data)

            prediction = self.model.predict(scaled_data, verbose=0)[0][0]

            if prediction >= 0.55:
                direction, confidence = "up", prediction
            elif prediction <= 0.45:
                direction, confidence = "down", 1 - prediction
            else:
                direction, confidence = "neutral", 1 - abs(0.5 - prediction)

            result = {"direction": direction, "confidence": round(confidence, 5)}
            self.log(f"🧠 Prediction: {result}")
            return result

        except Exception as e:
            self.log_error(f"❌ Prediction error: {e}")
            return {"direction": "error", "confidence": 0.0}

    def safe_read_csv(self, filepath, retries=5, delay=0.1):
        for attempt in range(retries):
            try:
                return pd.read_csv(filepath)
            except PermissionError as e:
                if attempt == retries - 1:
                    raise e
                time.sleep(delay)

    def get_account_info(self):
        try:
            buffer = ctypes.create_string_buffer(1024)
            self.controller.predict_server.dll.GetAccountInfo(buffer, 1024)
            decoded = buffer.value.decode("utf-8")
            return self.parse_account_info(decoded)
        except Exception as e:
            self.log_error(f"❌ Failed to fetch account info: {e}")
            return {}

    def get_open_position(self):
        try:
            buffer = ctypes.create_string_buffer(1024)
            self.controller.predict_server.dll.GetOpenPositions(buffer, 1024)
            decoded = buffer.value.decode("utf-8")
            return self.parse_positions(decoded)
        except Exception as e:
            self.log_error(f"❌ Failed to fetch open positions: {e}")
            return []

    def send_command(self, command: dict) -> str:
        try:
            if not isinstance(command, dict) or "action" not in command:
                raise ValueError("Invalid command format. Must be a dict with 'action' key.")

            action = command["action"].lower()
            args = []

            if action in ["buy", "sell", "buylimit", "selllimit", "buystop", "sellstop"]:
                args = [command.get("symbol", ""), str(command.get("lot", 0.1)), str(command.get("sl", 50)), str(command.get("tp", 40))]
            elif action == "modify":
                args = [command.get("symbol", ""), str(command.get("sl", 0)), str(command.get("tp", 0))]
            elif action in ["close", "shutdown", "pause", "resume", "closeall"]:
                args = [command.get("symbol", "EURUSD")] if "symbol" in command else []
            elif action in ["account_info", "open_positions", "history", "trade_history"]:
                pass
            else:
                raise ValueError(f"Unsupported action: {action}")

            message = f"{action}:{','.join(args)}" if args else action
            self.controller.predict_server.dll.WriteToBridge(message.encode())
            response = self.controller.predict_server.dll.ReadSharedBuffer().decode().strip()

            self.log(f"📤 Command Sent: {message}")
            self.log(f"📥 SharedBuffer Response: {response}")
            return response

        except Exception as e:
            self.log_error(f"❌ Failed to send command: {e}")
            return f"error,{e}"

    def parse_account_info(self, account_info_str):
        return {
            "balance": account_info_str.strip(),
            "equity": 0.0,
            "margin": 0.0,
            "leverage": 0
        }

    def parse_positions(self, positions_str):
        return [{
            "Ticket": positions_str,
            "Symbol": "EURUSD",
            "Type": "Buy",
            "Lots": 1.0,
            "OpenPrice": 1.2000,
            "SL": 1.1900,
            "TP": 1.2100,
            "Profit": 100.0
        }]
