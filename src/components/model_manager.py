import json
import logging
import os
from datetime import datetime

import numpy as np
import pandas as pd

from components.mt4_trainer import MT4Trainer


class ModelManager:
    @staticmethod
    def get_mod_time(path):
        return os.path.getmtime(path) if os.path.exists(path) else 0

    @staticmethod
    def generate_dummy_data(symbol: str):
        symbol_upper = symbol.upper()
        signal_path = f"src/data/signal_data_{symbol_upper}.csv"
        candle_path = f"src/data/candle_data_{symbol_upper}.csv"

        logging.warning(f"⚠️ Generating dummy data for {symbol_upper}...")
        os.makedirs("src/data", exist_ok=True)

        signal = np.random.rand(1000, 4)
        pd.DataFrame(signal, columns=["s1", "s2", "s3", "s4"]).to_csv(signal_path, index=False)

        open_prices = np.random.rand(1000)
        close_prices = open_prices + np.random.normal(0, 0.001, 1000)
        ohlc = np.column_stack([
            open_prices, close_prices,
            np.maximum(open_prices, close_prices),
            np.minimum(open_prices, close_prices),
            np.random.randint(500, 1500, 1000)  # volume
        ])
        pd.DataFrame(ohlc, columns=["open", "close", "high", "low", "volume"]).to_csv(candle_path, index=False)

        logging.info(f"✅ Dummy data generated for {symbol_upper}.")

    @staticmethod
    def write_metadata(symbol, paths):
        metadata = {
            "symbol": symbol.upper(),
            "model_path": paths["model_path"],
            "scaler_path": paths["scaler_path"],
            "signal_data": paths["signal_data"],
            "candle_data": paths["candle_data"],
            "model_last_modified": datetime.fromtimestamp(ModelManager.get_mod_time(paths["model_path"])).isoformat() if os.path.exists(paths["model_path"]) else None,
            "scaler_last_modified": datetime.fromtimestamp(ModelManager.get_mod_time(paths["scaler_path"])).isoformat() if os.path.exists(paths["scaler_path"]) else None,
            "signal_data_last_modified": datetime.fromtimestamp(ModelManager.get_mod_time(paths["signal_data"])).isoformat() if os.path.exists(paths["signal_data"]) else None,
            "candle_data_last_modified": datetime.fromtimestamp(ModelManager.get_mod_time(paths["candle_data"])).isoformat() if os.path.exists(paths["candle_data"]) else None,
            "version": f"v{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "created": datetime.now().isoformat()
        }

        metadata_path = paths["metadata_path"]
        os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        logging.info(f"✅ Metadata written for {symbol.upper()}")
        return metadata

    @staticmethod
    def ensure_model_exists(symbol: str):
        symbol_upper = symbol.upper()
        base_model_dir = f"src/model/{symbol_upper}"
        signal_path = f"src/data/signal_data_{symbol_upper}.csv"
        candle_path = f"src/data/candle_data_{symbol_upper}.csv"
        model_path = os.path.join(base_model_dir, f"model_{symbol_upper}.keras")
        scaler_path = os.path.join(base_model_dir, f"scaler_{symbol_upper}.pkl")
        metadata_path = os.path.join(base_model_dir, "metadata.json")

        paths = {
            "model_path": model_path,
            "scaler_path": scaler_path,
            "signal_data": signal_path,
            "candle_data": candle_path,
            "metadata_path": metadata_path
        }

        model_mtime = ModelManager.get_mod_time(model_path)
        scaler_mtime = ModelManager.get_mod_time(scaler_path)
        signal_mtime = ModelManager.get_mod_time(signal_path)
        candle_mtime = ModelManager.get_mod_time(candle_path)

        needs_training = (
                not os.path.exists(model_path)
                or not os.path.exists(scaler_path)
                or signal_mtime > model_mtime
                or candle_mtime > model_mtime
        )

        if not os.path.exists(signal_path) or not os.path.exists(candle_path):
            ModelManager.generate_dummy_data(symbol)
            needs_training = True

        if needs_training:
            logging.warning(f"⚠️ Retraining model for {symbol_upper}...")
            trainer = MT4Trainer()
            success = trainer.train_and_save_model(
                symbol=symbol_upper,
                signal_path=signal_path.lower(),
                candle_path=candle_path.lower(),
                model_path=model_path.lower(),
                scaler_path=scaler_path.lower()
            )
            if not success:
                raise RuntimeError(f"❌ Training failed for {symbol_upper}.")
            else:
                logging.info(f"✅ Training complete for {symbol_upper}")
        else:
            logging.info(f"✅ Model for {symbol_upper} is up to date.")

        return ModelManager.write_metadata(symbol_upper, paths)
