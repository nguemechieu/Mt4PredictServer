import io
import logging
import os
import subprocess
import sys

import tensorflow as tf
from PyQt5.QtCore import QTimer, Qt, QObject
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QTextEdit, QPushButton, QMessageBox, QHBoxLayout, QTabWidget
)

from components.predictionChart import PredictionChart
from components.tensorflow_metrics import TensorFlowMetricsTab

# --- Force UTF-8 encoding ---
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

LOG_PATH = "src/logs/predict_server.log"
PREDICTION_CSV = "src/data/prediction_history.csv"
SERVER_SCRIPT = "src/server/server.py"
from PyQt5.QtCore import QThread, pyqtSignal

class CommandWorker(QThread):
    result_signal = pyqtSignal(str)  # Signal to send the result back to the main thread
    error_signal = pyqtSignal(str)   # Signal to send any errors back to the main thread

    def __init__(self, param):
        super().__init__()
        self.param = param

    def run(self):
        try:
            # This is the subprocess call (running the server with the given command)
            command = ["python", "src/server/server.py", self.param]
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            # Capture the result
            output = result.stdout.strip() + ("\n" + result.stderr.strip() if result.stderr else "")

            # Emit the result back to the UI thread
            self.result_signal.emit(output if output else "✅ Command executed successfully with no output.")
        except Exception as e:
            # If there's an error, send the error message back to the UI thread
            self.error_signal.emit(f"❌ Command error: {e}")




class OutputReaderThread(QThread):
    output_signal = pyqtSignal(str)

    def __init__(self, process):
        super().__init__()
        self.process = process
        self.running = True

    def run(self):
        while self.running and self.process.poll() is None:
            try:
                line = self.process.stdout.readline()
                if line:
                    self.output_signal.emit(line.strip())
            except Exception as e:
                self.output_signal.emit(f"[Reader Error] {e}")

    def stop(self):
        self.running = False
        self.quit()
        self.wait()


def dark_theme_stylesheet():
    return """
    QWidget {
        background-color: #1e1e1e;
        color: #dcdcdc;
    }
    QPushButton {
        background-color: #3c3c3c;
        border: 1px solid #555;
        padding: 10px;
        font-size: 14px;
        color: white;
    }
    QPushButton:hover {
        background-color: #505050;
    }
    QTextEdit {
        background-color: #262626;
        border: 1px solid #444;
        color: #c8c8c8;
    }
    QLabel {
        color: #cccccc;
    }
    QComboBox {
        background-color: #3c3c3c;
        color: #ffffff;
        border: 1px solid #555;
        padding: 5px;
    }
    QComboBox:hover {
        background-color: #505050;
    }"""


class ServerDashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.command_output = None
        self.tensorflow_tab = None
        self.worker = None
        self.tabs = None
        self.status_label = None
        self.output = None
        self.gpu_status = None
        self.stop_btn = None
        self.chart = None
        self.symbol_selector = None
        self.reload_button = None
        self.model_summary = None
        self.prediction_history = None
        self.start_btn = None
        self.timer = None
        self.model_info = None
        self.logger = None
        self.process = None
        self.reader_thread = None
        self.setWindowTitle("Mt4PredictServer - Unified Dashboard")
        self.setWindowIcon(QIcon("logo.png"))
        self.setGeometry(400, 200, 1000, 800)
        self.setStyleSheet(dark_theme_stylesheet())
        self.init_ui()
        self.init_logger()
        self.init_timer()

    def init_ui(self):
        layout = QVBoxLayout()
        self.tabs = QTabWidget()

        # Server Tab
        self.status_label = QLabel("🔌 Status: <b><span style='color: red;'>Stopped</span></b>")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Segoe UI", 13))

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Courier New", 10))
        self.start_btn = QPushButton("Start Server")
        self.stop_btn = QPushButton("Stop Server")
        self.stop_btn.setEnabled(False)

        self.start_btn.clicked.connect(self.start_server)
        self.stop_btn.clicked.connect(self.stop_server)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)

        server_tab = QWidget()
        server_layout = QVBoxLayout()
        server_layout.addWidget(self.status_label)
        server_layout.addLayout(btn_layout)
        server_layout.addWidget(QLabel("🧾 Server Output Log:"))
        server_layout.addWidget(self.output)
        server_tab.setLayout(server_layout)

        # Chart Tab
        self.chart = PredictionChart(self)
        self.chart.setMinimumHeight(300)
        chart_tab = QWidget()
        chart_layout = QVBoxLayout()
        chart_layout.addWidget(QLabel("📈 Prediction Chart:"))
        chart_layout.addWidget(self.chart)
        chart_tab.setLayout(chart_layout)

        # GPU Tab
        self.gpu_status = QTextEdit()
        self.gpu_status.setReadOnly(True)
        self.gpu_status.setFont(QFont("Courier New", 10))
        self.gpu_status.setStyleSheet("background-color: #1E1E1E; color: #00FF00;")
        gpu_tab = QWidget()
        gpu_layout = QVBoxLayout()
        gpu_layout.addWidget(QLabel("🖥 GPU Status:"))
        gpu_layout.addWidget(self.gpu_status)
        gpu_tab.setLayout(gpu_layout)


        # Execute Command Tab
        execute_command_tab = QWidget()
        self.command_output = QTextEdit()
        self.command_output.setReadOnly(True)
        self.command_output.setFont(QFont("Courier New", 10))
        self.command_output.setStyleSheet("background-color:#1e1e1e; color: #00ffcc;")

        buy_btn = QPushButton("Buy")
        sell_btn = QPushButton("Sell")
        close_btn = QPushButton("Close")
        close_all_btn = QPushButton("Close All")
        modify_btn = QPushButton("Modify")
        alert_btn = QPushButton("Alert")
        log_btn = QPushButton("Log")
        pause_btn = QPushButton("Pause")
        resume_btn = QPushButton("Resume")
        shutdown_btn = QPushButton("Shutdown")
        buy_btn.clicked.connect(lambda: self.execute_command("buy"))
        sell_btn.clicked.connect(lambda: self.execute_command("sell"))
        close_btn.clicked.connect(lambda: self.execute_command("close"))
        close_all_btn.clicked.connect(lambda: self.execute_command("closeall"))
        modify_btn.clicked.connect(lambda: self.execute_command("modify"))
        alert_btn.clicked.connect(lambda: self.execute_command("alert"))
        log_btn.clicked.connect(lambda: self.execute_command("log"))
        pause_btn.clicked.connect(lambda: self.execute_command("pause"))
        resume_btn.clicked.connect(lambda: self.execute_command("resume"))
        shutdown_btn.clicked.connect(lambda: self.execute_command("shutdown"))

        execute_layout = QVBoxLayout()
        execute_layout.addWidget(QLabel("⚙️ Command Executor:"))
        execute_layout.addWidget(buy_btn)
        execute_layout.addWidget(sell_btn)
        execute_layout.addWidget(close_btn)
        execute_layout.addWidget(close_all_btn)
        execute_layout.addWidget(modify_btn)
        execute_layout.addWidget(alert_btn)
        execute_layout.addWidget(log_btn)
        execute_layout.addWidget(pause_btn)
        execute_layout.addWidget(resume_btn)
        execute_layout.addWidget(shutdown_btn)
        execute_layout.addWidget(QLabel("📤 Output:"))
        execute_layout.addWidget(self.command_output)
        execute_command_tab.setLayout(execute_layout)

        self.model_info = QTextEdit()
        self.model_info.setReadOnly(True)
        self.model_info.setFont(QFont("Courier New", 10))
        self.model_info.setStyleSheet("background-color: #1e1e1e; color: #00ffcc;")
        # Model Info Tab
        self.model_info = QTextEdit()
        self.model_info.setReadOnly(True)
        self.model_info.setFont(QFont("Courier New", 10))
        self.model_info.setStyleSheet("background-color: #1e1e1e; color: #00ffcc;")

        reload_button = QPushButton("🔄 Reload Model")
        reload_button.clicked.connect(self.reload_model_summary)

        model_tab = QWidget()
        model_layout = QVBoxLayout()
        model_layout.addWidget(QLabel("🧠 TensorFlow Model Info:"))
        model_layout.addWidget(reload_button)
        model_layout.addWidget(self.model_info)
        model_tab.setLayout(model_layout)


        self.tabs.addTab(server_tab, "Server")
        self.tabs.addTab(chart_tab, "Chart")
        self.tabs.addTab(gpu_tab, "GPU")
        self.tabs.addTab(model_tab, "Model")
        # Add TensorFlow Metrics tab
        self.tensorflow_tab = TensorFlowMetricsTab()
        self.tabs.addTab(self.tensorflow_tab, "TensorFlow Metrics")
        # Buttons to execute commands
        self.tabs.addTab(execute_command_tab, "Execute Command")

        layout.addWidget(self.tabs)
        self.setLayout(layout)
        self.reload_model_summary()

    def get_prediction_csv_path( self):
        """Get the path to the prediction CSV file."""
        return PREDICTION_CSV
    def execute_command(self, param):
    # Create a new CommandWorker for the given command
     self.worker = CommandWorker(param)

    # Connect the worker's signals to the appropriate slots
     self.worker.result_signal.connect(self.update_command_output)  # Handle result
     self.worker.error_signal.connect(self.update_command_output)   # Handle error

    # Start the worker thread
     self.worker.start()

    def update_command_output(self, message):
      """Method to update the command output in the UI (runs in the main thread)."""
      self.command_output.setPlainText(message)  # Update the QTextEdit widget with the output

    def reload_model_summary(self):
        try:
            model = tf.keras.models.load_model("src/model/model.keras")
            self.model_info.clear()
            self.model_info.append("Model Summary:")
            string_io = io.StringIO()
            model.summary(print_fn=lambda x: string_io.write(x + '\\n'))
            self.model_info.append(string_io.getvalue())
            self.model_info.append(f"Total Parameters: {model.count_params()}")
            self.model_info.append(f"Input Shape: {model.input_shape}")
            self.model_info.append(f"Output Shape: {model.output_shape}")
        except Exception as e:
            self.model_info.setPlainText(f"Failed to load model: {e}")

    def init_logger(self):
        self.logger = logging.getLogger("Mt4Logger")
        self.logger.setLevel(logging.DEBUG)

        class QtSignalEmitter(QObject):
            log_signal = pyqtSignal(str)

        class QtLogHandler(logging.Handler):
            def __init__(self):
                super().__init__()
                self.emitter = QtSignalEmitter()

            def emit(self, record):
                msg = self.format(record)
                self.emitter.log_signal.emit(msg)

        qt_handler = QtLogHandler()
        qt_handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
        qt_handler.emitter.log_signal.connect(self.append_log)
        self.logger.addHandler(qt_handler)

        file = logging.FileHandler("predict_server.log", encoding="utf-8")
        file.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
        self.logger.addHandler(file)

    def init_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_log_output)
        self.timer.start(3000)

    def append_log(self, msg):
        self.output.append(msg)
        self.output.verticalScrollBar().setValue(self.output.verticalScrollBar().maximum())

    def refresh_log_output(self):
        if os.path.exists(LOG_PATH):
            with open(LOG_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()[-25:]
                self.output.setPlainText("".join(lines))

        try:
            result = subprocess.run(["nvidia-smi"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode == 0:
                self.gpu_status.setPlainText(result.stdout)
            else:
                self.gpu_status.setPlainText("nvidia-smi not available or failed.")
        except Exception as e:
            self.gpu_status.setPlainText(f"Error fetching GPU status: {e}")

        self.chart.update_chart()

    def start_server(self):
        if self.process and self.process.poll() is None:
            QMessageBox.warning(self, "Already Running", "The server is already running.")
            return
        try:
            self.process = subprocess.Popen(
                [sys.executable, SERVER_SCRIPT],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                bufsize=1,
            )
            self.status_label.setText("🟢 Status: <b><span style='color: green;'>Running</span></b>")
            self.logger.info("✅ Server started.")
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)

            self.reader_thread = OutputReaderThread(self.process)
            self.reader_thread.output_signal.connect(self.append_log)
            self.reader_thread.start()
            self.logger.info("🟢 Reader thread started.")

        except Exception as e:
            QMessageBox.critical(self, "Startup Error", str(e))
            self.logger.error(f"❌ Failed to start server: {e}")

    def stop_server(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.logger.info("🛑 Server stopped.")

        if self.reader_thread:
            self.reader_thread.stop()

        self.status_label.setText("🔌 Status: <b><span style='color: red;'>Stopped</span></b>")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def closeEvent(self, event):
        if self.process and self.process.poll() is None:
            self.process.terminate()
        if self.reader_thread:
            self.reader_thread.stop()
        self.logger.info("👋 GUI closed.")
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ServerDashboard()
    window.show()
    app.setStyle("Fusion")
    sys.exit(app.exec_())