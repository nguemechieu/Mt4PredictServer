import logging
import os

import joblib
import pandas as pd
from keras import Sequential
from keras.src.layers import Dense
from sklearn.preprocessing import StandardScaler

BASE_MODEL_DIR = "src/model"
MODEL_PATH = os.path.join(BASE_MODEL_DIR, "model.keras")
SCALER_PATH = os.path.join(BASE_MODEL_DIR, "scaler.pkl")
SIGNAL_DATA_CSV = "src/data/signal_data.csv"
CANDLE_DATA_CSV = "src/data/candle_data.csv"

class MT4Trainer:
    
    def __init__(self,controller=None):
        os.makedirs(BASE_MODEL_DIR, exist_ok=True)
        os.makedirs("src/logs", exist_ok=True)
        os.makedirs("src/data", exist_ok=True)
        self.controller=controller
    def train_and_save_model(self):
        try:
            signal_data = pd.read_csv(SIGNAL_DATA_CSV, header=None)
            candle_data = pd.read_csv(CANDLE_DATA_CSV, header=None)

            if len(signal_data) < 1000 or len(candle_data) < 1000:
                logging.warning("❌ Not enough data to train model.")
                return False

            x_train = signal_data.iloc[-1000:].values
            y_train = (candle_data.iloc[-1000:, 2] > candle_data.iloc[-1000:, 1]).astype(int).values

            scaler = StandardScaler()
            x_scaled = scaler.fit_transform(x_train)
            joblib.dump(scaler, SCALER_PATH)

            model = Sequential([Dense(64, activation="relu", input_shape=(x_scaled.shape[1],)), Dense(32, activation="relu"), Dense(1, activation="sigmoid")])
            model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
            model.fit(x_scaled, y_train, epochs=10, batch_size=32, verbose=0)
            model.save(MODEL_PATH)
            logging.info("✅ Model trained and saved.")
            return True
        except Exception as e:
            logging.error(f"❌ Training failed: {e}")
            return False
