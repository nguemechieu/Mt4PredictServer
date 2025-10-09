import psutil
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import QTimer, Qt

class ResourceMonitorFrame(QWidget):
    """Displays live CPU/GPU (if available) and RAM usage under server logs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cpu_bar = QProgressBar()
        self.ram_bar = QProgressBar()
        self.gpu_label = QLabel("GPU: N/A")

        self._init_ui()
        self._init_timer()

    def _init_ui(self):
        layout = QVBoxLayout()

        # CPU
        cpu_layout = QHBoxLayout()
        cpu_label = QLabel("CPU Usage:")
        cpu_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.cpu_bar.setRange(0, 100)
        self.cpu_bar.setFormat("%p%")
        cpu_layout.addWidget(cpu_label)
        cpu_layout.addWidget(self.cpu_bar)

        # RAM
        ram_layout = QHBoxLayout()
        ram_label = QLabel("RAM Usage:")
        ram_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.ram_bar.setRange(0, 100)
        self.ram_bar.setFormat("%p%")
        ram_layout.addWidget(ram_label)
        ram_layout.addWidget(self.ram_bar)

        # GPU (Text Only)
        gpu_layout = QHBoxLayout()
        gpu_label_title = QLabel("GPU Status:")
        gpu_label_title.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        gpu_layout.addWidget(gpu_label_title)
        gpu_layout.addWidget(self.gpu_label)

        layout.addLayout(cpu_layout)
        layout.addLayout(ram_layout)
        layout.addLayout(gpu_layout)
        self.setLayout(layout)

    def _init_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_usage)
        self.timer.start(2000)  # update every 2 seconds

    def _update_usage(self):
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=None)
        self.cpu_bar.setValue(int(cpu_percent))

        # RAM usage
        mem = psutil.virtual_memory()
        self.ram_bar.setValue(int(mem.percent))

        # GPU check (fallback to text)
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]
                self.gpu_label.setText(f"{gpu.name}: {gpu.load*100:.1f}%")
            else:
                self.gpu_label.setText("GPU: None detected")
        except Exception:
            self.gpu_label.setText("GPU: psutil-only mode")
