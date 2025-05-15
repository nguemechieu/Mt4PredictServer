
import logging
import joblib
import numpy as np


class MT4Predictor:
    MODEL_PATH = "src/model/model.keras"
    SCALER_PATH = "src/model/scaler.pkl"

    def __init__(self,controller):
        self.model = None  # Initialize the model attribute
        self.scaler = None  # Initialize scaler attribute
        self.controller=controller
    def load_model(self):
        """Load the Keras model."""
        try:
            self.model = self.load_model(self.MODEL_PATH)
            logging.info("✅ Model loaded successfully.")
        except Exception as e:
            logging.error(f"❌ Failed to load model: {e}")
            raise e

    def load_scaler(self):
        """Load the scaler."""
        try:
            self.scaler = joblib.load(self.SCALER_PATH)
            logging.info("✅ Scaler loaded successfully.")
        except Exception as e:
            logging.error(f"❌ Failed to load scaler: {e}")
            raise e

    def validate_payload(self, payload):
        """
        Validate the input payload to ensure it contains numeric values.
        """
        if not isinstance(payload, (list, np.ndarray)) or len(payload) != 4:
            raise ValueError("Payload must be a list or array with exactly 4 elements.")
        
        if any(not isinstance(x, (int, float)) for x in payload):
            raise ValueError("All elements in the payload must be numeric (int or float).")

        return True

    def predict(self, payload):
        """Make a prediction based on input data."""
        try:
            # Validate the payload before proceeding
            self.validate_payload(payload)

            if self.model is None:
                self.load_model()  # Load the model if not already loaded
            
            if self.scaler is None:
                self.load_scaler()  # Load the scaler if not already loaded

            # Process the payload (values from MT4)
            signal_input = np.array([payload]).reshape(1, -1)  # Reshape for prediction input
            signal_scaled = self.scaler.transform(signal_input)  # Scale the input data

            # Predict the signal using the model
            prediction = self.model.predict(signal_scaled, verbose=0)[0][0]  # type: ignore

            # Determine the direction and confidence
            if prediction >= 0.55:
                direction, confidence = "up", prediction
            elif prediction <= 0.45:
                direction, confidence = "down", 1 - prediction
            else:
                direction, confidence = "neutral", 1 - abs(0.5 - prediction)

            result = f"{direction},{confidence:.5f}"
            logging.info(f"🧠 Prediction: {result}")
            return result

        except ValueError as e:
            logging.error(f"❌ Payload validation failed: {e}")
            return f"error,{e}"

        except Exception as e:
            logging.error(f"❌ Prediction error: {e}")
            return "error,signal_exception"
