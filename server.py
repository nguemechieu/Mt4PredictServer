import logging
import os
import socket

import numpy as np

from tensorflow.keras.layers import Dense
from tensorflow.keras.models import Sequential, load_model

# --- Config ---
MODEL_PATH = "model.keras"
HOST, PORT = "127.0.0.1", 9999

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    handlers=[logging.FileHandler("predict_server.log"), logging.StreamHandler()],
)


# --- Dummy Model Builder ---
def create_dummy_model(path):
    model = Sequential(
        [
            Dense(64, activation="relu", input_shape=(3,)),
            Dense(32, activation="relu"),
            Dense(1, activation="sigmoid"),
        ]
    )
    model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
    X_dummy = np.random.rand(100, 3)
    y_dummy = np.random.randint(0, 2, size=(100, 1))
    model.fit(X_dummy, y_dummy, epochs=1, verbose=0)
    model.save(path)
    logging.info(f"✅ Dummy model created at: {path}")


# --- Ensure model exists ---
if not os.path.exists(MODEL_PATH):
    logging.warning("model.keras not found, creating a dummy model...")
    create_dummy_model(MODEL_PATH)

# --- Load model ---
model = load_model(MODEL_PATH)
expected_input_dim = model.input_shape[1]
logging.info("Model loaded successfully.")


# --- Input handler ---
def handle_input(data):
    try:
        values = list(map(float, data.strip().split(",")))
        if len(values) > expected_input_dim:
            return "error,0.0"

        padded = values + [0.0] * (expected_input_dim - len(values))
        x = np.array([padded])
        prediction = model.predict(x, verbose=0)[0][0]
        direction = "up" if prediction >= 0.5 else "down"
        return f"{direction},{prediction:.5f}"
    except Exception as e:
        logging.error(f"❌ Input error: {e}")
        return "error,0.0"


# --- Socket server ---
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()
    logging.info(f"Listening on {HOST}:{PORT} ...")

    while True:
        try:
            conn, addr = server.accept()
            with conn:
                logging.info(f"Connection from {addr}")
               
                data = conn.recv(1024).decode().strip()
                if data:
                    result = handle_input(data)
                    conn.sendall(result.encode())
        except Exception as e:
            logging.error(f"Server error: {e}")
