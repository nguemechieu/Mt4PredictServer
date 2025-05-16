import logging

import pytest
import ctypes
import os
import json
import time
from ctypes import c_char, POINTER, c_char_p

# === DLL Loader ===
@pytest.fixture(scope="module")
def dll_():
    dll_path = os.path.abspath("src/dll/x64/PredictBridge.dll")
    dll__ = ctypes.WinDLL(dll_path)

    dll__.WriteToBridge.argtypes = [c_char_p]
    dll__.WriteToBridge.restype = None

    dll__.ReadSharedBuffer.argtypes = []
    dll__.ReadSharedBuffer.restype = c_char_p

    dll__.ClearBridge.argtypes = []
    dll__.ClearBridge.restype = None



    return dll__

# === Test: Bridge communication ===
def test_bridge(dll_):
    ping_msg = json.dumps({"type": "ping", "timestamp": int(time.time())})
    dll_.WriteToBridge(ping_msg.encode())
    time.sleep(2)

    raw = dll_.ReadSharedBuffer().decode().strip()
    #assert "pong" in raw.lower(), f"Expected pong in response, got: {raw}"
    print("raw :",raw)
# === Test: Account Info ===


def test_communication(dll_= None):
    try:
        # Send
        message = json.dumps({"action": "ping", "timestamp": int(time.time())})
        dll_.WriteToBridge(message.encode("utf-8"))
        logging.info(f"📤 Test Ping Sent: {message}")

        time.sleep(1.5)

        # Read
        response = dll_.ReadSharedBuffer().decode("utf-8").strip()
        if response:
            logging.info(f"📥 Received: {response}")
        else:
            logging.warning("⚠️ No response received from MT4.")

        dll_.ClearBridge()
    except Exception as e:
        logging.error(f"❌ Test communication failed: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("🔧 Tester Script Starting...")
    try:
        dll = dll_()
        test_bridge(dll)
        test_communication(dll)
    except Exception as e:
        print("❌ Error:", str(e))
