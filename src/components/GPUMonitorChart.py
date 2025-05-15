import GPUtil
import psutil
import matplotlib.pyplot as plt
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas


class GPUMonitorChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GPU Monitor")

        self.layout = QVBoxLayout()

        self.label = QLabel("🔍 Monitoring GPU Stats")
        self.layout.addWidget(self.label)

        self.canvas = FigureCanvas(plt.Figure(figsize=(5, 3)))
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.layout.addWidget(self.canvas)
        self.ax = self.canvas.figure.subplots()

        self.gpu_load_history = []
        self.gpu_mem_used_history = []
        self.gpu_temp_history = []
        self.timestamps = []

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_chart)
        self.timer.start(2000)

    def update_chart(self):
        gpus = GPUtil.getGPUs()
        if not gpus:
            self.label.setText("⚠️ No GPU detected")
            return
        gpu = gpus[0]
        self.label.setText(
            f"GPU: {gpu.name} | Load: {gpu.load * 100:.1f}% | Mem Used: {gpu.memoryUsed:.1f}MB | Temp: {gpu.temperature:.1f}°C"
        )

        self.gpu_load_history.append(gpu.load * 100)
        self.gpu_mem_used_history.append(gpu.memoryUsed)
        self.gpu_temp_history.append(gpu.temperature)
        self.timestamps.append(len(self.timestamps))

        if len(self.timestamps) > 30:
            self.timestamps = self.timestamps[-30:]
            self.gpu_load_history = self.gpu_load_history[-30:]
            self.gpu_mem_used_history = self.gpu_mem_used_history[-30:]
            self.gpu_temp_history = self.gpu_temp_history[-30:]

        self.ax.clear()
        self.ax.plot(self.timestamps, self.gpu_load_history, label="Load %")
        self.ax.plot(self.timestamps, self.gpu_mem_used_history, label="Memory Used (MB)")
        self.ax.plot(self.timestamps, self.gpu_temp_history, label="Temperature °C")
        self.ax.legend()
        self.ax.set_title("GPU Usage Over Time")
        self.ax.set_xlabel("Time (samples)")
        self.ax.set_ylabel("Value")
        self.ax.grid(True)
        self.canvas.draw()
