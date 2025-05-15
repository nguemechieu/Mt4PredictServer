import subprocess
import tensorflow as tf
from tensorflow.python.client import device_lib
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton, QHBoxLayout
)

class GPUMonitor(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.output = None
        self.title = None
        self.timer = None
        self.controller = controller
        self.init_ui()
        self.init_timer()

        # Optional: Add global style (if needed)
        self.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #00ff00;
                border: 1px solid #444;
            }
            QPushButton {
                font-weight: bold;
            }
        """)

    def init_ui(self):
        layout = QVBoxLayout()

        self.title = QLabel("🖥 GPU Monitor")
        self.title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(self.title)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Courier New", 10))
        layout.addWidget(self.output)

        # Button row
        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh_gpu_info)

        memory_btn = QPushButton("⚙️ Enable Memory Growth")
        memory_btn.clicked.connect(self.enable_memory_growth)

        list_devices_btn = QPushButton("📋 List Devices")
        list_devices_btn.clicked.connect(self.list_tf_devices)

        btn_layout.addWidget(refresh_btn)
        btn_layout.addWidget(memory_btn)
        btn_layout.addWidget(list_devices_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

        self.refresh_gpu_info()  # Show initial info

    def init_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_gpu_info)
        self.timer.start(5000)  # Refresh every 5 seconds

    def refresh_gpu_info(self):
        try:
            result = subprocess.run(["nvidia-smi"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode == 0:
                self.output.setPlainText(result.stdout)
            else:
                self.output.setPlainText("❌ nvidia-smi not available or failed:\n" + result.stderr)
        except Exception as e:
            self.output.setPlainText(f"❌ Error fetching GPU info: {e}")

    def enable_memory_growth(self):
        try:
            gpus = tf.config.list_physical_devices('GPU')
            if not gpus:
                self.output.append("\n⚠️ No GPUs found to enable memory growth.")
                return
            for gpu in gpus:
                tf.config.experimental.set_memory_growth(gpu, True)
            self.output.append("\n✅ Memory growth enabled for all GPUs.")
        except Exception as e:
            self.output.append(f"\n❌ Error enabling memory growth: {e}")

    def list_tf_devices(self):
        try:
            devices = device_lib.list_local_devices()
            if not devices:
                self.output.append("\n⚠️ No devices found.")
                return
            device_str = "\n📋 TensorFlow Devices:\n"
            for d in devices:
                device_str += f"- {d.name} ({d.device_type})\n"
            self.output.append(device_str)
        except Exception as e:
            self.output.append(f"\n❌ Error listing TF devices: {e}")
