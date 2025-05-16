import logging
import os
import joblib
import pandas as pd
from keras import Sequential
from keras.api.layers import Dense
from sklearn.preprocessing import StandardScaler

class MT4Trainer:

    def __init__(self, controller=None):
        self.controller = controller



    def train_and_save_model(self,symbol, signal_path, candle_path, model_path, scaler_path):
         try:
            # === Ensure directories exist ===
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            os.makedirs("src/logs", exist_ok=True)
            os.makedirs("src/data", exist_ok=True)

            # === Step 1: Load data ===
            signal_data = pd.read_csv(signal_path)
            candle_data = pd.read_csv(candle_path)

            if signal_data.shape[1] != 4:
                logging.error(f"❌ {symbol}: signal data must have 4 columns. Found: {signal_data.shape[1]}")
                return False
            if candle_data.shape[1] < 3:
                logging.error(f"❌ {symbol}: candle data must have at least 3 columns.")
                return False
            if len(signal_data) < 10 or len(candle_data) < 10:
                logging.warning(f"❌ {symbol}: Not enough data to train (need ≥10 rows).")
                return False

            # === Step 2: Prepare training set ===
            x_train = signal_data.iloc[-10:].values
            y_train = (candle_data.iloc[-10:, 2] > candle_data.iloc[-10:, 1]).astype(int).values

            logging.info(f"✅ {symbol}: Training feature shape: {x_train.shape}")

            # === Step 3: Scale and save scaler ===
            scaler = StandardScaler()
            x_scaled = scaler.fit_transform(x_train)
            joblib.dump(scaler, scaler_path)
            logging.info(f"✅ {symbol}: Scaler saved to {scaler_path}")

            # === Step 4: Delete old model if exists ===
            if os.path.exists(model_path):
                os.remove(model_path)
                logging.info(f"⚠️ {symbol}: Old model deleted: {model_path}")

            # === Step 5: Build and train model ===
            model = Sequential([
                Dense(64, activation="relu", input_shape=(4,)),
                Dense(32, activation="relu"),
                Dense(1, activation="sigmoid")
            ])
            model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
            model.fit(x_scaled, y_train, epochs=10, batch_size=32, verbose=0)
            model.save(model_path)
            logging.info(f"✅ {symbol}: Model trained and saved to {model_path}")
            return True

         except Exception as e:
             self.controller.logger.error(f"❌ {symbol}: Training failed - {e}")
             return False
