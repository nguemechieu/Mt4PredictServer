
import logging
import os
import threading
import time
import joblib
import numpy as np
from tensorflow.keras import Sequential
from tensorflow.keras.layers import Dense
from tensorflow.keras.models import load_model
from sklearn.preprocessing import StandardScaler

from components.mt4_trainer import MT4Trainer


# ==============================================================
# CONSTANTS
# ==============================================================
MODEL_PATH = os.path.join("./src/model", "model/model.keras")
SCALER_PATH = os.path.join("./src/model", "model/scaler.pkl")
MIN_CONF_THRESHOLD = 0.6


# ==============================================================
# CREATE DEFAULT MODEL & SCALER
# ==============================================================
def create_model_and_scaler_if_missing(model_path=MODEL_PATH, scaler_path=SCALER_PATH):
    """Ensures model/scaler exist; creates small default ones if missing."""
    try:
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        os.makedirs(os.path.dirname(scaler_path), exist_ok=True)

        if os.path.exists(model_path) and os.path.exists(scaler_path):
            return

        logging.warning("⚠️ Missing model or scaler → generating defaults.")

        # Default scaler and dummy model
        x_train = np.random.rand(500, 4)
        y_train = np.random.randint(0, 2, 500)

        scaler = StandardScaler()
        x_scaled = scaler.fit_transform(x_train)
        joblib.dump(scaler, scaler_path)

        model = Sequential([
            Dense(32, activation="relu", input_shape=(4,)),
            Dense(16, activation="relu"),
            Dense(1, activation="sigmoid"),
        ])
        model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
        model.fit(x_scaled, y_train, epochs=3, batch_size=32, verbose=0)
        model.save(model_path)

        logging.info("✅ Default model & scaler created successfully.")
    except Exception as e:
        raise RuntimeError(f"Model/scaler creation failed: {e}")


# ==============================================================
# MAIN CLASS — MT4Predictor
# ==============================================================
class MT4Predictor:
    """Lightweight prediction + self-healing wrapper for MT4 signals."""

    def __init__(self, controller=None):
        self.controller = controller
        self.trainer = MT4Trainer(controller)
        self._lock = threading.Lock()

        self.model = None
        self.scaler = None
        self.last_model_load = 0
        self.feedback_buffer = []
        self.performance_log = []
        self.low_confidence_count = 0
        self.max_recent = 50

    # ----------------------------------------------------------
    # MODEL / SCALER MANAGEMENT
    # ----------------------------------------------------------
    def _lazy_load(self, force=False):
        """Load or reload model/scaler if missing or stale."""
        with self._lock:
            if not force and self.model and self.scaler:
                return
            create_model_and_scaler_if_missing()
            self.model = load_model(MODEL_PATH)
            self.scaler = joblib.load(SCALER_PATH)
            self.last_model_load = time.time()
            self._log("✅ Model and scaler loaded.")

    # ----------------------------------------------------------
    # VALIDATION
    # ----------------------------------------------------------
    def _parse_payload(self, symbol=None,payload=None):
        """Extracts 4 numeric inputs and symbol if present."""
        try:

            if payload is None:
                return None, None

            # Fast numeric parsing (string or list)
            if isinstance(payload, str):
                parts = payload.split(",")
                nums = []
                for p in parts:
                    p = p.strip()
                    if not p:
                        continue
                    try:
                        nums.append(float(p))
                    except ValueError:
                        if len(p) >= 3 and p.isalpha():
                            symbol = p.upper()
                if len(nums) != 4:
                    return None, None
                return nums, symbol

            if isinstance(payload, (list, np.ndarray)):
                arr = list(payload)
                if len(arr) >= 5 and isinstance(arr[-1], str):
                    symbol = arr[-1].upper()
                    arr = arr[:-1]
                if len(arr) != 4:
                    return None, None
                return [float(x) for x in arr], symbol

            return None, None
        except Exception as e:
            self._log(f"❌ Payload parse error: {e}", level="error")
            return None, None

    # ----------------------------------------------------------
    # PREDICTION
    # ----------------------------------------------------------
    def predict(self, symbol=None, payload=None):
        """Runs scaled prediction and triggers GPT reasoning if available."""
        t0 = time.time()
        try:
            if payload is None or symbol is None:
                return {
                    "status": "error",
                    "message": "Payload and symbol are required.",
                    "timestamp": time.time()
                }
            values, symbol = self._parse_payload(symbol,payload)
            if values is None:
                return {"direction": "error", "confidence": 0.0}

            self._lazy_load()

            x = np.array([values])
            x_scaled = self.scaler.transform(x)

            with self._lock:
                prob = float(self.model.predict(x_scaled, verbose=0)[0][0])

            prob = np.clip(prob, 0.05, 0.95)
            direction = "up" if prob >= 0.55 else "down"
            confidence = prob if prob >= 0.55 else 1 - prob

            result = {
                "status": "ok",
                "type": "prediction",
                "symbol": symbol or "EURUSD",
                "direction": direction,
                "confidence": round(confidence, 4),
                "probability": round(prob, 4),
                "timestamp": round(time.time(), 2),
                "latency_ms": round((time.time() - t0) * 1000, 1),
            }

            # Track performance
            self._track(confidence)

            # Trigger GPT analysis if connected
            if getattr(self.controller, "gpt", None):
                try:
                    self.controller.gpt.analyze_signal_stream(result)
                except Exception as e:
                    self._log(f"⚠️ GPT analysis failed: {e}", level="warning")

            return result

        except Exception as e:
            self._log(f"❌ Prediction error: {e}", level="error")
            return {
                "status": "error",
                "message": "Prediction failed.",
                "timestamp": time.time()
            }
    # ----------------------------------------------------------
    # PERFORMANCE TRACKING
    # ----------------------------------------------------------
    def _track(self, conf):
        self.performance_log.append(conf)
        if len(self.performance_log) > self.max_recent:
            self.performance_log.pop(0)

        avg_conf = float(np.mean(self.performance_log))
        if conf < MIN_CONF_THRESHOLD:
            self.low_confidence_count += 1
        else:
            self.low_confidence_count = max(0, self.low_confidence_count - 1)

        self._log(f"📊 Avg Conf={avg_conf:.3f} | Weak={self.low_confidence_count}")

    # ----------------------------------------------------------
    # AUTO TRAINING
    # ----------------------------------------------------------
    def auto_train_if_needed(self, symbol, force=False):
        """Retrains if forced or too many low-confidence results."""
        try:
            should_train = force or self.low_confidence_count >= 5
            if not should_train:
                return

            signal_file = f"src/data/signal_{symbol}.csv"
            candle_file = f"src/data/candle_{symbol}.csv"
            if not os.path.exists(signal_file) or not os.path.exists(candle_file):
                self._log(f"⚠️ No data for {symbol}. Skipping retrain.")
                return

            def _train():
                self._log(f"🔁 Retraining model for {symbol} (force={force})...")
                self.trainer.train_and_save_model(
                    symbol, signal_file, candle_file, MODEL_PATH, SCALER_PATH
                )
                self._lazy_load(force=True)
                self.low_confidence_count = 0
                self._log(f"✅ Retraining complete for {symbol}")

            threading.Thread(target=_train, daemon=True).start()

        except Exception as e:
            self._log(f"❌ Auto-train failed: {e}", level="error")

    # ----------------------------------------------------------
    # LOGGING UTIL
    # ----------------------------------------------------------
    def _log(self, msg, level="info"):
        log = getattr(self.controller, "logger", logging)
        getattr(log, level, log.info)(msg)

