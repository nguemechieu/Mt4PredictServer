import os
import socket
import threading
from datetime import datetime

import numpy as np
import logging
import pandas as pd
from keras.api.layers import Dense
from keras.api.models import Sequential, load_model

# --- Config ---
MODEL_PATH = "src/model/model.keras"
HOST, PORT = "127.0.0.1", 9999
AUTH_TOKEN = "sopotek123"  # Optional: Add auth if needed later
candle_data = []  # Global variable to store candle data

# --- Logging Setup ---
os.makedirs("src/logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    handlers=[
        logging.FileHandler("src/logs/predict_server.log", encoding="utf-8"),
        logging.StreamHandler()
    ],
)

# --- Dummy Model Builder ---
def create_dummy_model(path):
    logging.info("Creating dummy model...")
    model = Sequential([
        Dense(64, activation="relu", input_shape=(3,)),
        Dense(32, activation="relu"),
        Dense(1, activation="sigmoid"),
    ])
    model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
    x_dummy = np.random.rand(100, 3)
    y_dummy = np.random.randint(0, 2, size=(100, 1))
    model.fit(x_dummy, y_dummy, epochs=1, verbose=0)
    model.save(path)
    logging.info(f"✅ Dummy model created at: {path}")

def load_model_from_disk(path):
    if not os.path.exists(path):
        logging.warning("Model not found, creating a dummy model...")
        create_dummy_model(path)
    return load_model(path)

def process_input(data, model, expected_input_dim):
    try:
        if data:
            logging.info(f"RECEIVED :{data}")

            # Split the input data string by commas
            values = data.strip().split(",")  # Split by commas

            if len(values) < expected_input_dim + 1:
                raise ValueError(f"Expected at least {expected_input_dim + 1} values, got {len(values)}")

            # Extract signal features (first `expected_input_dim` values)
            signal_features = np.array([float(v) for v in values[:expected_input_dim]]).reshape(1, expected_input_dim)

            # Extract symbol (the part after the 4th value, which is the 'E' or currency pair)
            symbol = values[4]  # This should be the currency pair (e.g., EURUSD)

            # Extract remaining candle data (and include timestamp)
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Get current timestamp
            candle_data = [timestamp] + [float(v) for v in values[5:]]  # Include timestamp as the first value
            logging.info(f"Candle data saved: {candle_data}")

            # Save the candle data with symbol and timestamp in a pandas DataFrame
            candle_df = pd.DataFrame([candle_data], columns=["timestamp", "open", "close", "high", "low", "volume"])

            # Append the data to a CSV file organized by symbol and timestamp
            with open(f"src/data/candle_data_{symbol}.csv", "a") as f:
                candle_df.to_csv(f, header=f.tell() == 0, index=False)

            # Predict using only the signals
            prediction = model.predict(signal_features, verbose=0)[0][0]
            if prediction >= 0.55:
                direction, confidence = "up", prediction
            elif prediction <= 0.45:
                direction, confidence = "down", 1 - prediction
            else:
                direction, confidence = "neutral", 1 - abs(0.5 - prediction)  # optional, can be just 0.0
                logging.info(f"Prediction: {direction} ({prediction:.5f})")

            # Save prediction to CSV
            with open("src/data/prediction_history.csv", "a") as f:
                f.write(f"{data},{prediction:.5f}\n")
            return f"{direction},{prediction:.5f}"

        elif data.strip() == "PING":
            return "pong"
        elif data.strip() == "RELOAD":
            return "reload"
        else:
            logging.warning(f"Unsupported command: {data}")
            return "error,0.0"

    except Exception as e:
        logging.error(f"❌ Input error: {e}")
        return "error,0.0"


# Train the model using training data
def train_model(model, x_train, y_train, epochs=1, batch_size=32):
    """Train the model with the given data."""
    logging.info(f"Training the model with {len(x_train)} samples...")
    model.fit(x_train, y_train, epochs=epochs, batch_size=batch_size, verbose=1)
    model.save(MODEL_PATH)  # Save the trained model to disk
    logging.info(f"✅ Model trained and saved at: {MODEL_PATH}")

def get_training_data():
    """Retrieve training data from the database."""
    candle_data_ = pd.read_csv("src/data/candle_data.csv", header=None)
    signal_data = pd.read_csv("src/data/signal_data.csv", header=None)
    return candle_data_, signal_data

def handle_training_data(data):
    """Handle training data collection and model training.
    :param data: format received from MT4 EA (e.g. "signal1,signal2,signal3,signal4,symbol,open,close,high,low,volume")
    """
    # Retrieve training data from the database

    # Extract signal data and candle data from the received data
    signal_data = data.split(",")[:4]  # First 4 values are signals
    candle_data = data.split(",")[5:]  # Remaining values are candle data

    # Save the received candle data to a CSV file or database
    with open("src/data/candle_data.csv", "a") as f:
        f.write(",".join(candle_data) + "\n")
    # Save the received signal data to a CSV file or database
    with open("src/data/signal_data.csv", "a") as f:
        f.write(",".join(signal_data) + "\n")

    # Load the training data from the CSV files
    candle_data__, signal_data = get_training_data()

    if candle_data__ is None or signal_data is None:
        logging.error("❌ No training data available.")
        return

    # Ensure there is enough data
    if len(candle_data__) < 100 or len(signal_data) < 100:
        logging.error("❌ Not enough data to train the model.")
        return

    # Use the last part of candle data and signal data for training
    x_train = candle_data__[-100:]  # Use the last 100 candle data for features
    y_train = signal_data[-100:]  # Use the last 100 signal data for labels

    # Load the model from disk
    model = load_model_from_disk(MODEL_PATH)

    # Train the model with the retrieved data
    train_model(model, x_train, y_train)
    logging.info("✅ Model training completed.")
    # Create training summary
    with open("src/logs/training_summary.txt", "w") as f:
        f.write(f"Trained on {len(x_train)} samples.\n")
        f.write(f"Model saved at: {MODEL_PATH}\n")
        f.write(f"Training data: {x_train}\n")
        f.write(f"Signal data: {y_train}\n")

# Handle socket commands
def send_command_to_mt4(command: str, payload: str = "") -> str:
    """
    Send a custom command to the MT4 EA through the TCP socket.
    :param command: e.g. 'buy', 'sell', 'close', 'closeall', 'alert', 'log', etc.
    :param payload: e.g. 'EURUSD,0.1', 'USDJPY', or a log message
    :return: Response string from MT4 EA
    """
    message = f"{command}:{payload}"
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((HOST, PORT))
            sock.sendall(message.encode())
            response = sock.recv(1024).decode()
            logging.info(f"📤 Sent command: {message}")
            logging.info(f"📥 Response from EA: {response}")
            return response
    except Exception as e:
        logging.error(f"❌ Failed to send command '{command}': {e}")
        return "error"

# === High-Level Shortcuts ===

def send_buy(symbol="EURUSD", lot=0.1):
    return send_command_to_mt4("buy", f"{symbol},{lot}")

def send_sell(symbol="EURUSD", lot=0.1):
    return send_command_to_mt4("sell", f"{symbol},{lot}")

def send_close(symbol="EURUSD"):
    return send_command_to_mt4("close", symbol)

def send_close_all():
    return send_command_to_mt4("closeall")

def send_modify(symbol="EURUSD", sl=1.1000, tp=1.1100):
    return send_command_to_mt4("modify", f"{symbol},{sl},{tp}")

def send_alert(message="Warning"):
    return send_command_to_mt4("alert", message)

def send_log(message="Debug info"):
    return send_command_to_mt4("log", message)

def send_pause():
    return send_command_to_mt4("pause")

def send_resume():
    return send_command_to_mt4("resume")

def send_shutdown():
    return send_command_to_mt4("shutdown")

def handle_client(conn, addr, model_ref, model_lock):
    with conn:
        logging.info(f"📥 Connection from {addr}")
        try:
            data = conn.recv(1024).decode().strip()
            if data:
                with model_lock:
                    model = model_ref[0]
                    expected_input_dim = model.input_shape[1]

                response = process_input(data, model, expected_input_dim)

                logging.info(f"📤 Sending response: {response}")
                if response.startswith("error"):
                    logging.error(f"❌ Error processing input: {response}")
                    conn.sendall(response.encode())
                    return
                if response == "pong":
                    logging.info("🌐 PING received, responding with PONG.")

                if response == "reload":
                    logging.info("🔁 Reloading model...")
                    with model_lock:
                        model_ref[0] = load_model_from_disk(MODEL_PATH)
                    response = "model_reloaded"

                # Handle training data
                if response == "train":
                    logging.info("🔁 Training model with new data...")
                    handle_training_data(data)
                    response = "model_trained"

                conn.sendall(response.encode())
        except Exception as e:
            logging.error(f"Client handler error: {e}")
            conn.sendall("error,0.0".encode())

def start_socket_server():
    model = load_model_from_disk(MODEL_PATH)
    model_ref = [model]  # Mutable reference
    model_lock = threading.Lock()

    logging.info("✅ Model loaded. Server is ready.")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()

    logging.info(f"🚀 Listening on {HOST}:{PORT} ...")

    try:
        while True:
            conn, addr = server.accept()
            threading.Thread(
                target=handle_client,
                args=(conn, addr, model_ref, model_lock),
                daemon=True
            ).start()
    except KeyboardInterrupt:
        logging.info("🛑 Server shutdown requested.")
    except Exception as e:
        logging.error(f"Server error: {e}")
    finally:
        server.close()


start_socket_server()
