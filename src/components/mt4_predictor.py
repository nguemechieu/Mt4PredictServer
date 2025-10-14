"""
===============================================================
🤖 MT4Predictor — AI Signal Engine for PredictServer
---------------------------------------------------------------
Handles ML-based predictions, confidence tracking, and
auto-retraining logic for MT4 JSON bridge.
===============================================================
"""

import logging
import os
import threading
import time
import joblib
import numpy as np
import pandas as pd
from tensorflow.keras import Sequential
from tensorflow.keras.layers import Dense
from tensorflow.keras.models import load_model
from sklearn.preprocessing import StandardScaler

from components.GPTAdvisor import GPTAdvisor
from components.mt4_trainer import MT4Trainer


# ==============================================================
# CONSTANTS
# ==============================================================
MODEL_PATH = "./src/model/model.keras"
SCALER_PATH = "./src/model/scaler.pkl"
FEATURE_COUNT = 9
MIN_CONF_THRESHOLD = 0.6


# ==============================================================
# CREATE MODEL & SCALER IF MISSING
# ==============================================================
def create_model_and_scaler_if_missing(model_path=MODEL_PATH, scaler_path=SCALER_PATH):
    """Ensure model/scaler exist; create minimal defaults if missing."""
    try:
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        os.makedirs(os.path.dirname(scaler_path), exist_ok=True)

        if os.path.exists(model_path) and os.path.exists(scaler_path):
            return

        logging.warning("⚠️ Missing model or scaler → generating default placeholders...")

        x_train = np.random.rand(5500, FEATURE_COUNT)
        y_train = np.random.randint(0, 2, 5500)

        scaler = StandardScaler()
        x_scaled = scaler.fit_transform(x_train)
        joblib.dump(scaler, scaler_path)

        model = Sequential([
            Dense(64, activation="relu", input_shape=(FEATURE_COUNT,)),
            Dense(32, activation="relu"),
            Dense(1, activation="sigmoid"),
        ])
        model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
        model.fit(x_scaled, y_train, epochs=5, batch_size=32, verbose=0)
        model.save(model_path)

        logging.info("✅ Default model & scaler created successfully.")
    except Exception as e:
        raise RuntimeError(f"Model/scaler creation failed: {e}")


# ==============================================================
# MAIN CLASS — Predictor
# ==============================================================
class Predictor:
    """Lightweight AI predictor with auto-training and GPT analysis."""

    def __init__(self, controller=None):
        self.controller = controller
        self.trainer = MT4Trainer(controller)
        self._lock = threading.Lock()
        self.model = None
        self.scaler = None
        self.last_model_load = 0
        self.performance_log = []
        self.low_confidence_count = 0
        self.max_recent = 50
        self.gpt = GPTAdvisor(controller=controller)  # persistent GPT instance

        # fallback logger if controller missing
        if self.controller and hasattr(self.controller, "logger"):
            self.logger = self.controller.logger
        else:
            logging.basicConfig(level=logging.INFO)
            self.logger = logging.getLogger("MT4Predictor")

    # ----------------------------------------------------------
    # MODEL / SCALER MANAGEMENT
    # ----------------------------------------------------------
    def _lazy_load(self, force=False):
        """Load or reload model/scaler if missing or stale."""
        with self._lock:
            if not force and self.model is not None and self.scaler is not None:
                return
            create_model_and_scaler_if_missing()
            self.model = load_model(MODEL_PATH)
            self.scaler = joblib.load(SCALER_PATH)
            self.last_model_load = time.time()
            self.logger.info("✅ Model and scaler loaded.")

    # ----------------------------------------------------------
    # PAYLOAD PARSER
    # ----------------------------------------------------------
    def _parse_payload(self, symbol=None, payload=None):
        """Normalize indicator payload to numeric array."""
        try:
            if payload is None:
                return None, symbol

            # string form: "0.7,0.6,0.5,EURUSD"
            if isinstance(payload, str):
                parts = [p.strip() for p in payload.split(",") if p.strip()]
                nums, detected = [], symbol
                for p in parts:
                    try:
                        nums.append(float(p))
                    except ValueError:
                        detected = p.upper()
                return (nums if nums else None), detected

            # numeric array
            if isinstance(payload, (list, np.ndarray)):
                arr = list(payload)
                if len(arr) >= FEATURE_COUNT + 1 and isinstance(arr[-1], str):
                    symbol = arr[-1].upper()
                    arr = arr[:-1]
                return [float(x) for x in arr[:FEATURE_COUNT]], symbol

            return None, symbol
        except Exception as e:
            self.logger.error(f"❌ Payload parse error: {e}")
            return None, symbol

    # ----------------------------------------------------------
    # LOSS TRACKER
    # ----------------------------------------------------------
    def _get_recent_loss(self):
        """Return most recent negative trade result (if any)."""
        try:
            path = "./src/data/order_history.csv"
            if not os.path.exists(path):
                return 0.0
            df = pd.read_csv(path)
            if df.empty or "profit" not in df.columns:
                return 0.0
            last_profit = float(df["profit"].iloc[-1])
            return last_profit if last_profit < 0 else 0.0
        except Exception as e:
            self.logger.warning(f"⚠️ Could not read recent loss: {e}")
            return 0.0

    # ----------------------------------------------------------
    # PREDICTION CORE
    # ----------------------------------------------------------
    def predict(self, symbol=None, payload=None):
        """Run scaled model prediction and return AI trade signal."""
        t0 = time.time()
        try:
            if payload is None or symbol is None:
                return {"status": "error", "message": "Payload and symbol required", "timestamp": t0}

            values, symbol = self._parse_payload(symbol, payload)
            if values is None:
                return {"status": "error", "message": "Invalid payload format", "timestamp": t0}

            self._lazy_load()

            x = np.array([values])
            x_scaled = self.scaler.transform(x)

            with self._lock:
                prob = float(self.model.predict(x_scaled, verbose=0)[0][0])

            prob = np.clip(prob, 0.05, 0.95)
            direction = "BUY" if prob >= 0.55 else "SELL"
            confidence = prob if direction == "BUY" else 1 - prob

            prev_loss = self._get_recent_loss()
            latency = round((time.time() - t0) * 1000, 1)

            result = {
                "status": "ok",
                "type": "signal_response",
                "symbol": symbol,
                "direction": direction,
                "confidence": round(confidence, 4),
                "probability": round(prob, 4),
                "timestamp": round(time.time(), 2),
                "latency_ms": latency,
                "recent_loss": round(prev_loss, 2),
            }

            if prev_loss < 0:
                result["analysis_hint"] = f"⚠️ Drawdown {prev_loss:.2f} detected — reduce BUY risk."

            self._track(confidence)
           # self.gpt.analyze_signal_stream(result)

            # maybe trigger auto-training if confidence is weak
            self.auto_train_if_needed(symbol)

            return result

        except Exception as e:
            self.logger.error(f"❌ Prediction error: {e}")
            return {"status": "error", "message": f"Prediction failed: {e}", "timestamp": time.time()}

    # ----------------------------------------------------------
    # PERFORMANCE TRACKING
    # ----------------------------------------------------------
    def _track(self, conf):
        """Track recent confidence for stability monitoring."""
        self.performance_log.append(conf)
        if len(self.performance_log) > self.max_recent:
            self.performance_log.pop(0)

        avg_conf = float(np.mean(self.performance_log))
        if conf < MIN_CONF_THRESHOLD:
            self.low_confidence_count += 1
        else:
            self.low_confidence_count = max(0, self.low_confidence_count - 1)

        self.logger.info(f"📊 AvgConf={avg_conf:.3f} | WeakCount={self.low_confidence_count}")

    # ----------------------------------------------------------
    # AUTO TRAINING
    # ----------------------------------------------------------
    def auto_train_if_needed(self, symbol, force=False):
        """Trigger retraining if confidence is consistently weak."""
        try:
            if not force and self.low_confidence_count < 5:
                return

            signal_file = f"./src/data/signal_{symbol}.csv"
            candle_file = f"./src/data/{symbol}_candles.csv"

            if not os.path.exists(signal_file) or not os.path.exists(candle_file):
                self.logger.warning(f"⚠️ Missing training data for {symbol}. Skipping retrain.")
                return

            threading.Thread(
                target=self._train,
                args=(symbol, signal_file, candle_file, force),
                daemon=True,
            ).start()

        except Exception as e:
            self.logger.error(f"❌ Auto-train failed: {e}")

    def _train(self, symbol, signal_file, candle_file, force=True):
        """Background model retraining job."""
        try:
            self.logger.info(f"🔁 Retraining model for {symbol} (force={force})...")
            self.trainer.train_and_save_model(symbol, signal_file, candle_file, MODEL_PATH, SCALER_PATH)
            self._lazy_load(force=True)
            self.low_confidence_count = 0
            self.logger.info(f"✅ Retraining complete for {symbol}")
        except Exception as e:
            self.logger.error(f"❌ Retrain error for {symbol}: {e}")
