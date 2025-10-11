import datetime
import os
import joblib

import pandas as pd
import numpy as np
from tensorflow.keras import Sequential
from tensorflow.keras.layers import Dense
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from tensorflow.keras.callbacks import TensorBoard


class MT4Trainer:
    """
    MT4Trainer trains and saves a small neural network to predict direction
    using signal data (RSI, EMA, MACD, etc.) and optional context features like
    previous loss and open/close prices.
    """

    def __init__(self, controller=None):
        self.controller = controller

    # ===============================================================
    # MAIN TRAINING ROUTINE
    # ===============================================================
    def train_and_save_model(
            self,
            symbol: str,
            signal_path: str,
            candle_path: str,
            model_path: str,
            scaler_path: str,
            order_history_path: str = "./src/data/order_history.csv",
    ) -> bool:
        try:
            # --- Ensure directories exist ---
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            os.makedirs("./src/logs", exist_ok=True)
            os.makedirs("./src/data", exist_ok=True)

            # --- Load data ---
            signal_data = pd.read_csv(signal_path)
            candle_data = pd.read_csv(candle_path)

            if signal_data.shape[1] < 4:
                self._log_error(symbol, f"Signal data must have ≥4 columns, found {signal_data.shape[1]}")
                return False

            if len(signal_data) < 10 or len(candle_data) < 10:
                self._log_warn(symbol, "Not enough data to train (need ≥10 rows).")
                return False

            # --- Fetch previous loss ---
            prev_loss = self._get_recent_loss(order_history_path)

            # --- Merge contextual features ---
            features = signal_data.iloc[-100:].copy()  # use last 100 rows for smoother training
            features["open"] = candle_data.iloc[-100:, 1].values
            features["close"] = candle_data.iloc[-100:, 2].values
            features["prev_loss"] = prev_loss
            x_train = features.values

            # --- Label: bullish candle (close > open) ---
            y_train = (candle_data.iloc[-100:, 2] > candle_data.iloc[-100:, 1]).astype(int).values

            self._log_info(symbol, f"✅ Input shape: {x_train.shape}")

            # --- Normalize features ---
            scaler = StandardScaler()
            x_scaled = scaler.fit_transform(x_train)
            joblib.dump(scaler, scaler_path)
            self._log_info(symbol, f"Scaler saved → {scaler_path}")

            # --- Split into training & validation ---
            x_train_split, x_val, y_train_split, y_val = train_test_split(
                x_scaled, y_train, test_size=0.2, random_state=42
            )

            # --- Remove old model if exists ---
            if os.path.exists(model_path):
                os.remove(model_path)
                self._log_warn(symbol, f"Old model deleted: {model_path}")

            # --- Build model ---
            model = Sequential([
                Dense(64, activation="relu", input_shape=(x_train.shape[1],)),
                Dense(32, activation="relu"),
                Dense(1, activation="sigmoid")
            ])
            model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])

            # --- TensorBoard setup ---
            log_dir = f"./src/logs/{symbol}_{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
            tensorboard_callback = TensorBoard(log_dir=log_dir, histogram_freq=1)

            # --- Train model with logging ---
            history = model.fit(
                x_train_split, y_train_split,
                validation_data=(x_val, y_val),
                epochs=25,
                batch_size=16,
                callbacks=[tensorboard_callback],
                verbose=0
            )

            # --- Save model ---
            model.save(model_path)
            self._log_info(symbol, f"✅ Model trained & saved → {model_path}")

            # --- Save metrics summary ---
            self._save_metrics_summary(symbol, history, log_dir)
            return True

        except Exception as e:
            self._log_error(symbol, f"❌ Training failed → {e}")
            return False

    # ===============================================================
    # INTERNAL UTILITIES
    # ===============================================================
    def _get_recent_loss(self, path: str) -> float:
        """Fetch last closed trade loss for context learning."""
        try:
            if not os.path.exists(path):
                return 0.0

            df = pd.read_csv(path)
            if df.empty or "profit" not in df.columns:
                return 0.0

            last_pnl = float(df["profit"].iloc[-1])
            return np.clip(last_pnl, -100.0, 100.0)
        except Exception as e:
            if self.controller:
                self.controller.logger.debug(f"⚠️ Could not load previous loss: {e}")
            return 0.0

    def _save_metrics_summary(self, symbol, history, log_dir):
        """Save final loss/accuracy summary for quick access."""
        try:
            metrics = {
                "final_loss": float(history.history["loss"][-1]),
                "final_acc": float(history.history["accuracy"][-1]),
                "val_loss": float(history.history["val_loss"][-1]),
                "val_acc": float(history.history["val_accuracy"][-1]),
                "log_dir": log_dir,
            }
            pd.DataFrame([metrics]).to_csv(f"{log_dir}/metrics_summary.csv", index=False)
            self._log_info(symbol, f"📊 Metrics summary saved to {log_dir}/metrics_summary.csv")
        except Exception as e:
            self._log_warn(symbol, f"⚠️ Could not save metrics summary: {e}")

    # ===============================================================
    # LOGGING HELPERS
    # ===============================================================
    def _log_info(self, symbol, msg):
        if self.controller and hasattr(self.controller, "logger"):
            self.controller.logger.info(f"[{symbol}] {msg}")
        else:
            self.controller.logger.info (f"[INFO] {symbol}: {msg}")

    def _log_warn(self, symbol, msg):
        if self.controller and hasattr(self.controller, "logger"):
            self.controller.logger.warning(f"[{symbol}] {msg}")
        else:
            self.controller.logger.info(f"[WARN] {symbol}: {msg}")

    def _log_error(self, symbol, msg):
        if self.controller and hasattr(self.controller, "logger"):
            self.controller.logger.error(f"[{symbol}] {msg}")
        else:
            self.controller.logger.info(f"[ERROR] {symbol}: {msg}")
