import ctypes
import logging
import os
import platform
import shutil
import time
from ctypes import c_double, c_char_p, c_char, c_int, c_ubyte, POINTER, Structure

import pandas as pd

from src.components.mt4_predictor import MT4Predictor
from src.components.mt4_trainer import MT4Trainer


# Helper Function to Copy 32-bit DLL into MT4's Libraries Folder Mt4 runs only on 32 bits
def copy_dll_to_mt4_library():
    """
    Copies the 32-bit DLL file to the MT4 Libraries folder.

    Returns:
        str: The path to the copied DLL file if successful, otherwise None.
    """
    try:
        # Source path of your 32-bit DLL
        source_dll = os.path.abspath("src/dll/x86/PredictBridge.dll")

        # Locate MT4 libraries path
        mt4_base = os.path.join(os.environ.get("APPDATA", ""), "MetaQuotes", "Terminal")
        for folder in os.listdir(mt4_base):
            lib_path = os.path.join(mt4_base, folder, "MQL4", "Libraries")
            if os.path.exists(lib_path):
                target_dll = os.path.join(lib_path, "PredictBridge.dll")

                # Create the directory if it doesn't exist
                os.makedirs(lib_path, exist_ok=True)

                # Copy DLL
                shutil.copy2(source_dll, target_dll)
                print(f"✅ DLL copied to: {target_dll}")
                return target_dll

        print("❌ Could not find a valid MT4 Libraries folder.")
        return None

    except Exception as e:
        print(f"❌ Failed to copy DLL: {e}")
        return None


# === Struct for result ===
class PredictionResult(Structure):
    """
    A structure to hold prediction results from the DLL.

    Attributes:
        direction (str): The predicted direction (e.g., "Buy" or "Sell").
        confidence (float): The confidence level of the prediction.
    """
    _fields_ = [
        ("direction", c_char * 16),
        ("confidence", c_double)
    ]


def load_predict_dll() -> ctypes.CDLL:
    """
    Loads the appropriate PredictBridge DLL based on the system architecture.

    Returns:
        ctypes.CDLL: The loaded DLL object.
    """
    arch = platform.architecture()[0]
    dll_path = "src/dll/x64/PredictBridge.dll" if arch == "64bit" else "src/dll/x86/PredictBridge.dll"
    dll_path = os.path.abspath(dll_path)
    dll_ = ctypes.WinDLL(dll_path)

    # === Register all functions ===
    dll_.GetIndicatorSignal.argtypes = [c_double, c_double, c_double, c_double, POINTER(c_char), c_int]
    dll_.GetIndicatorSignal.restype = None  # Since we're working with an output buffer

    dll_.GetCandleBatch.argtypes = [POINTER(c_ubyte), c_int, POINTER(c_ubyte), c_int]
    dll_.GetCandleBatch.restype = None

    dll_.GetCommand.argtypes = [ctypes.POINTER(c_char), c_int]
    dll_.GetCommand.restype = None

    dll_.GetAccountInfo.argtypes = [ctypes.POINTER(c_char), c_int]
    dll_.GetAccountInfo.restype = None

    dll_.GetOpenPosition.argtypes = [ctypes.POINTER(c_char), c_int]
    dll_.GetOpenPosition.restype = None

    dll_.GetTradeHistory.argtypes = [ctypes.POINTER(c_char), c_int]
    dll_.GetTradeHistory.restype = None

    dll_.ReadSharedBuffer.argtypes = []
    dll_.ReadSharedBuffer.restype = c_char_p

    dll_.WriteToBridge.argtypes = [c_char_p]
    dll_.WriteToBridge.restype = None

    dll_.AppendToBridge.argtypes = [c_char_p]
    dll_.AppendToBridge.restype = None

    dll_.ClearBridge.argtypes = []
    dll_.ClearBridge.restype = None

    return dll_


class PredictServer:
    """
    A server class to interact with the PredictBridge DLL and manage prediction-related operations.
    """

    def __init__(self,controller=None):

        """
        Initializes the PredictServer instance, setting up logging and loading required components.
        """
        self.controller= controller
        # === DLL Setup ===
        self.dll = load_predict_dll()

        # Ensure logs directory exists
        self.LOG_PATH = "src/logs/predict_server.log"
        log_dir = os.path.dirname(self.LOG_PATH)
        os.makedirs(log_dir, exist_ok=True)  # Creates directory if it doesn't exist

        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s", handlers=[logging.FileHandler(self.LOG_PATH, encoding="utf-8"), logging.StreamHandler()])

        self.predictor = MT4Predictor(self.controller)

        self.trainer = MT4Trainer(self.controller)
      

    def get_signals_data(self):
      # Example values from MT4 or other data sources
      o = 1.1500  # Example open price
      h = 1.1600  # Example high price
      Ll = 1.1400   # Example low price
      c = 1.1550  # Example close price

    # Create a ctypes buffer for the response (will hold the result from the DLL)
      response = (ctypes.c_char * 256)()  # Buffer to store the response from the DLL

    # Call the GetIndicatorSignal function in DLL (passing open, high, low, close data)
      self.dll.GetIndicatorSignal(o, h, Ll, c, response, len(response))

    # Convert the response from the DLL (e.g., "Processed: signal_direction") to a string
      response_str = response.value.decode('utf-8')
      logging.info(response_str)

    # Extracting the signal data from response (Here we're using the example values)
      return  {o,h,Ll,c} 
     
    # Return the signal data as a dictionary for better readability and usage
      



    def getCandles(self):
    # Prepare input data (a sample for demonstration)
      input_data = b"candles_batch_data"  # Example data, replace with actual data to send
      input_size = len(input_data)

    # Create ctypes buffer for the input
      input_buffer = ctypes.create_string_buffer(input_data)

    # Create an output buffer to store the result
      output_buffer = ctypes.create_string_buffer(4096)  # Adjust the size if necessary
      output_size = len(output_buffer)

    # Call the DLL function
      self. dll.GetCandleBatch(input_buffer, input_size, output_buffer, output_size)
    # Process the output (convert to Python string)
      output_data = output_buffer.value.decode('utf-8')

    # Print or return the result
      print(f"Received data: {output_data}")
      return output_data

    def safe_read_csv(self, filepath, retries=5, delay=0.1):
        """
        Safely reads a CSV file, retrying in case of a PermissionError.

        Args:
            filepath (str): The path to the CSV file.
            retries (int): The number of retry attempts.
            delay (float): The delay between retries in seconds.

        Returns:
            pd.DataFrame: The loaded DataFrame.
        """
        for attempt in range(retries):
            try:
                return pd.read_csv(filepath)
            except PermissionError as e:
                if attempt == retries - 1:
                    raise e
                time.sleep(delay)

    def send_via_dll(self, action: str):
        """
        Sends a command to the DLL and logs the response.

        Args:
            action (str): The action to be sent to the DLL.
        """
        try:
            # Prepare the message to be sent to the DLL
            action = action.strip().lower()

            if action == "account_info":
                response = self.send_command({"action": "account_info"})
            elif action == "open_positions":
                response = self.send_command({"action": "open_positions"})
            else:
                response = f"❌ Unsupported action: {action}"

            # Log response or handle it accordingly
            print(f"DLL Response for {action}: {response}")

        except Exception as e:
            print(f"Error in send_via_dll: {e}")

    def get_account_info(self):
        """
        Fetches account information from the DLL.

        Returns:
            dict: A dictionary containing account information.
        """
        try:
            account_info_buffer = ctypes.create_string_buffer(1024)
            self.dll.GetAccountInfo(account_info_buffer, 1024)
            account_info_str = account_info_buffer.value.decode("utf-8")
            account_info = self.parse_account_info(account_info_str)
            return account_info
        except Exception as e:
            logging.error(f"❌ Failed to fetch account info: {e}")
            return {}

    def get_open_position(self):
        """
        Fetches open positions from the DLL.

        Returns:
            list: A list of dictionaries containing open position details.
        """
        try:
            positions_buffer = ctypes.create_string_buffer(1024)
            self.dll.GetOpenPosition(positions_buffer, 1024)
            positions_str = positions_buffer.value.decode("utf-8")
            positions = self.parse_positions(positions_str)
            return positions
        except Exception as e:
            logging.error(f"❌ Failed to fetch open positions: {e}")
            return []

    def send_command(self, command: dict) -> str:
        """
        Sends a command to the DLL and retrieves the response.

        Args:
            command (dict): The command to be sent.

        Returns:
            str: The response from the DLL.
        """
        try:
            if not isinstance(command, dict) or "action" not in command:
                raise ValueError("Invalid command format. Must be a dict with 'action' key.")

            action = command["action"].lower()
            args = []

            if action in ["buy", "sell", "buylimit", "selllimit", "buystop", "sellstop"]:
                args = [command.get("symbol", ""), str(command.get("lot", 0.1)), str(command.get("sl", 50)), str(command.get("tp", 40))]
            elif action == "modify":
                args = [command.get("symbol", ""), str(command.get("sl", 0)), str(command.get("tp", 0))]
            elif action in ["close", "shutdown", "pause", "resume", "closeall"]:
                args = [command.get("symbol", "EURUSD")] if "symbol" in command else []
            elif action in ["account_info", "open_positions", "history", "trade_history"]:
                pass
            else:
                raise ValueError(f"Unsupported action: {action}")

            message = f"{action}:{','.join(args)}" if args else action

            # Write to DLL memory buffer
            self.dll.WriteToBridge(message.encode())
            response = self.dll.ReadSharedBuffer().decode().strip()

            logging.info(f"📤 Command Sent: {message}")
            logging.info(f"📥 SharedBuffer Response: {response}")
            return response

        except Exception as e:
            logging.error(f"❌ Failed to send command: {e}")
            return f"error,{e}"

    def parse_account_info(self, account_info_str):
        """
        Parses the account info string into a dictionary.

        Args:
            account_info_str (str): The account info string.

        Returns:
            dict: A dictionary containing parsed account information.
        """
        return {
            "Balance": 10000.00,
            "Equity": 10000.00,
            "Margin": 500.00,
            "FreeMargin": 9500.00,
            "Leverage": 100
        }

    def parse_positions(self, positions_str):
        """
        Parses the positions string into a list of dictionaries.

        Args:
            positions_str (str): The positions string.

        Returns:
            list: A list of dictionaries containing parsed position details.
        """
        return [
            {"Ticket": 1, "Symbol": "EURUSD", "Type": "Buy", "Lots": 1.0, "OpenPrice": 1.2000, "SL": 1.1900, "TP": 1.2100, "Profit": 100.0},
            {"Ticket": 2, "Symbol": "GBPUSD", "Type": "Sell", "Lots": 0.5, "OpenPrice": 1.3500, "SL": 1.3600, "TP": 1.3400, "Profit": -50.0}
        ]
