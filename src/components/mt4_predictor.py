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

from components.mt4_trainer import MT4Trainer

# ==============================================================
# CONSTANTS
# ==============================================================
MODEL_PATH = os.path.join("./model", "model/model.keras")
SCALER_PATH = os.path.join("./model", "model/scaler.pkl")
MIN_CONF_THRESHOLD = 0.6
FEATURE_COUNT = 9  # RSI, EMA_FAST, EMA_SLOW, MACD, CCI, OPEN, CLOSE, AVG_LOSS_LAST_3, RECENT_LOSS


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

        # --- Generate dummy 9-feature dataset ---
        x_train = np.random.rand(500, FEATURE_COUNT)
        y_train = np.random.randint(0, 2, 500)

        scaler = StandardScaler()
        x_scaled = scaler.fit_transform(x_train)
        joblib.dump(scaler, scaler_path)

        # --- Define small dense network ---
        model = Sequential([
            Dense(64, activation="relu", input_shape=(FEATURE_COUNT,)),
            Dense(32, activation="relu"),
            Dense(1, activation="sigmoid"),
        ])
        model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
        model.fit(x_scaled, y_train, epochs=5, batch_size=32, verbose=0)
        model.save(model_path)

        logging.info("✅ Default 9-feature model & scaler created successfully.")
    except Exception as e:
        raise RuntimeError(f"Model/scaler creation failed: {e}")


# ==============================================================
# MAIN CLASS — MT4Predictor
# ==============================================================
class MT4Predictor:
    """Lightweight AI predictor with dynamic retraining and GPT analysis."""

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
    # FEATURE EXTRACTION
    # ----------------------------------------------------------
    def _parse_payload(self, symbol=None, payload=None):
        """
        Extract 9 numeric features (RSI, EMA_FAST, EMA_SLOW, MACD, CCI, OPEN, CLOSE, AVG_LOSS_LAST_3, RECENT_LOSS)
        and optional symbol if passed in payload.
        """
        try:
            if payload is None:
                return None, symbol

            # --- Handle CSV-like string ---
            if isinstance(payload, str):
                parts = [p.strip() for p in payload.split(",") if p.strip()]
                nums, symbol_detected = [], None
                for p in parts:
                    try:
                        nums.append(float(p))
                    except ValueError:
                        if len(p) >= 3 and p.isalpha():
                            symbol_detected = p.upper()
                if len(nums) != FEATURE_COUNT:
                    return None, symbol_detected or symbol
                return nums, symbol_detected or symbol

            # --- Handle list or numpy array ---
            if isinstance(payload, (list, np.ndarray)):
                arr = list(payload)
                if len(arr) >= FEATURE_COUNT + 1 and isinstance(arr[-1], str):
                    symbol = arr[-1].upper()
                    arr = arr[:-1]
                if len(arr) != FEATURE_COUNT:
                    return None, symbol
                return [float(x) for x in arr], symbol

            return None, symbol
        except Exception as e:
            self._log(f"❌ Payload parse error: {e}", level="error")
            return None, symbol

    # ----------------------------------------------------------
    # RECENT LOSS TRACKER
    # ----------------------------------------------------------
    def _get_recent_loss(self) -> float:
        """Fetch recent drawdown from order history for model context."""
        try:
            hist_path = "./src/data/order_history.csv"
            if not os.path.exists(hist_path):
                return 0.0

            df = pd.read_csv(hist_path)
            if df.empty or "profit" not in df.columns:
                return 0.0

            last_profit = float(df["profit"].iloc[-1])
            return last_profit if last_profit < 0 else 0.0
        except Exception as e:
            self._log(f"⚠️ Could not read recent loss: {e}", level="warning")
            return 0.0

    # ----------------------------------------------------------
    # PREDICTION
    # ----------------------------------------------------------
    def predict(self, symbol=None, payload=None):
        """Runs scaled prediction and triggers GPT reasoning if available."""
        t0 = time.time()
        try:
            if payload is None or symbol is None:
                return {"status": "error", "message": "Payload and symbol required.", "timestamp": t0}

            values, symbol = self._parse_payload(symbol, payload)
            if values is None:
                return {"status": "error", "message": "Invalid payload format.", "timestamp": t0}

            self._lazy_load()

            # --- Prepare scaled input ---
            x = np.array([values])
            x_scaled = self.scaler.transform(x)

            with self._lock:
                prob = float(self.model.predict(x_scaled, verbose=0)[0][0])

            # --- Confidence interpretation ---
            prob = np.clip(prob, 0.05, 0.95)
            direction = "up" if prob >= 0.55 else "down"
            confidence = prob if direction == "up" else 1 - prob

            prev_loss = self._get_recent_loss()
            result = {
                "status": "ok",
                "type": "prediction",
                "symbol": symbol or "EURUSD",
                "direction": direction,
                "confidence": round(confidence, 4),
                "probability": round(prob, 4),
                "timestamp": round(time.time(), 2),
                "latency_ms": round((time.time() - t0) * 1000, 1),
                "recent_loss": round(prev_loss, 2),
            }

            # --- Track performance ---
            self._track(confidence)

            # --- GPT Analysis ---
            if getattr(self.controller, "gpt", None):
                try:
                    if prev_loss < 0:
                        result["analysis_hint"] = (
                            f"⚠️ Recent drawdown of {prev_loss:.2f} detected; "
                            "adjusting risk and reducing confidence in BUY setups."
                        )
                    self.controller.gpt.analyze_signal_stream(result)
                except Exception as e:
                    self._log(f"⚠️ GPT analysis failed: {e}", level="warning")

            return result

        except Exception as e:
            self._log(f"❌ Prediction error: {e}", level="error")
            return {"status": "error", "message": f"Prediction failed: {e}", "timestamp": time.time()}

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
        """Retrains model if forced or too many weak predictions."""
        try:
            should_train = force or self.low_confidence_count >= 5
            if not should_train:
                return

            signal_file = f"./src/data/signal_{symbol}.csv"
            candle_file = f"./src/data/candle_{symbol}.csv"
            if not os.path.exists(signal_file) or not os.path.exists(candle_file):
                self._log(f"⚠️ No training data for {symbol}. Skipping retrain.", level="warning")
                return

            def _train():
                self._log(f"🔁 Retraining model for {symbol} (force={force})...")
                self.trainer.train_and_save_model(symbol, signal_file, candle_file, MODEL_PATH, SCALER_PATH)
                self._lazy_load(force=True)
                self.low_confidence_count = 0
                self._log(f"✅ Retraining complete for {symbol}")

            threading.Thread(target=_train, daemon=True).start()

        except Exception as e:
            self._log(f"❌ Auto-train failed: {e}", level="error")

    # ----------------------------------------------------------
    # LOGGING HELPER
    # ----------------------------------------------------------
    def _log(self, msg, level="info"):
        if not self.controller or not hasattr(self.controller, "logger"):
            print(f"[MT4Predictor] {msg}")
            return

        log_func = getattr(self.controller.logger, level, self.controller.logger.info)
        log_func(msg)
