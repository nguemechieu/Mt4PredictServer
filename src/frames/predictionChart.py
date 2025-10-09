# frames/predictionChart.py
import random
import time
from collections import deque

import mplcursors  # 🔥 for interactive tooltips
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class PredictionChart(QWidget):
    """Live chart that displays model confidence and GPT trade markers."""

    def __init__(self, controller=None):
        super().__init__()
        self.controller = controller

        layout = QVBoxLayout(self)
        self.figure = Figure(facecolor="#1e1e1e")
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor("#1e1e1e")
        self.ax.tick_params(colors="white")
        self.ax.set_title("📈 Prediction Confidence & GPT Trades", color="white")

        # Rolling data (for last 100 points)
        self.x_data = deque(maxlen=100)
        self.conf_data = deque(maxlen=100)
        self.trades = []  # list of (x, y, type, info_dict)

        self.line, = self.ax.plot([], [], color="#00ffcc", lw=1.5, label="Confidence")
        self.scatter_buy = None
        self.scatter_sell = None
        self.scatter_hold = None

        self.ax.legend(facecolor="#222222", labelcolor="white")
        self.canvas.draw_idle()

        # Live refresh
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_chart)
        self.timer.start(1000)

        # Connect to AutoTradeManager if available
        self.autotrader = getattr(controller, "autotrade_manager", None)
        if self.autotrader:
            self.autotrader.decision_signal.connect(self._on_new_decision)

    # ------------------------------------------------------------------
    def add_confidence_point(self, conf_value):
        """Add new confidence value from model."""
        self.x_data.append(time.time())
        self.conf_data.append(conf_value)

    def _on_new_decision(self, decision):
        """Plot BUY/SELL/HOLD marker when GPT decides."""
        action = decision.get("action", "HOLD")
        conf = decision.get("confidence", random.uniform(0.5, 0.9))
        x = time.time()
        y = conf
        trade_info = {
            "action": action,
            "confidence": round(conf, 3),
            "symbol": decision.get("pair", "EURUSD"),
            "timestamp": decision.get("timestamp", "N/A"),
        }
        self.trades.append((x, y, action, trade_info))
        self.add_confidence_point(conf)
        self._update_chart(force=True)

    def _update_chart(self, force=False):
        """Refresh chart contents."""
        if not self.x_data:
            return
        self.line.set_data(self.x_data, self.conf_data)

        buys = [(x, y, info) for x, y, t, info in self.trades if t == "BUY"]
        sells = [(x, y, info) for x, y, t, info in self.trades if t == "SELL"]
        holds = [(x, y, info) for x, y, t, info in self.trades if t == "HOLD"]

        # Clear existing scatter plots
        self.ax.collections.clear()
        self.ax.lines = [self.line]

        if buys:
            bx, by, binfo = zip(*[(x, y, info) for x, y, info in buys])
            self.scatter_buy = self.ax.scatter(bx, by, color="#00ff00", marker="^", s=80, label="BUY")
        if sells:
            sx, sy, sinfo = zip(*[(x, y, info) for x, y, info in sells])
            self.scatter_sell = self.ax.scatter(sx, sy, color="#ff3333", marker="v", s=80, label="SELL")
        if holds:
            hx, hy, hinfo = zip(*[(x, y, info) for x, y, info in holds])
            self.scatter_hold = self.ax.scatter(hx, hy, color="#cccccc", marker="o", s=60, label="HOLD")

        self.ax.relim()
        self.ax.autoscale_view()
        self.ax.legend(facecolor="#222222", labelcolor="white")

        self.canvas.draw_idle()

        # Add hover tooltips once (lazy init)
        if not hasattr(self, "cursor_initialized"):
            self._init_tooltips()
            self.cursor_initialized = True

    def _init_tooltips(self):
        """Enable hover tooltips on BUY/SELL markers."""
        cursor = mplcursors.cursor(self.ax.collections, hover=True)

        @cursor.connect("add")
        def on_hover(sel):
            idx = sel.index
            artist = sel.artist
            label = artist.get_label()
            if not self.trades:
                return

            # Find corresponding trade
            for x, y, t, info in self.trades:
                if abs(sel.target[0] - x) < 0.01 and abs(sel.target[1] - y) < 0.01:
                    sel.annotation.set_text(
                        f"{info['symbol']} | {info['action']}\n"
                        f"Confidence: {info['confidence']}\n"
                        f"Time: {info['timestamp']}"
                    )
                    sel.annotation.get_bbox_patch().set(fc="#222222", alpha=0.9)
                    sel.annotation.get_text().set_color("white")
                    break

    def update_chart(self):
        pass
