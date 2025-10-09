import os

import pandas as pd
import matplotlib.pyplot as plt
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QMessageBox, QSizePolicy, QHBoxLayout
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.font_manager import fontManager

try:
    fontManager.addfont("C:/Windows/Fonts/seguiemj.ttf")
    plt.rcParams['font.family'] = 'Segoe UI Emoji'
except Exception:
    pass
class PositionHistory(QWidget):
    """Displays trade history, performance metrics, and profitability chart."""

    def __init__(self, controller=None):
        super().__init__(controller)
        self.setWindowTitle("📜 Trade History & Performance")
        self.resize(1100, 700)
        self.controller = controller
        self.history_path = "./src/data/order_history.csv"

        # === Layout ===
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Header
        header = QLabel("<h2>📄 Trade History</h2>")
        layout.addWidget(header)

        # Table
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        # Summary + Ranking
        self.summary_label = QLabel()
        self.rank_label = QLabel()
        layout.addWidget(self.summary_label)
        layout.addWidget(self.rank_label)

        # Chart area
        self.figure, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.canvas)

        # Buttons
        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton("🔄 Refresh Data")
        refresh_btn.clicked.connect(self.load_data)
        clear_btn = QPushButton("🧹 Clear History")
        clear_btn.clicked.connect(self.clear_history)
        btn_layout.addWidget(refresh_btn)
        btn_layout.addWidget(clear_btn)
        layout.addLayout(btn_layout)

        # Initial load + auto refresh
        self.load_data()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.load_data)
        self.timer.start(20000)  # every 20s

    # ------------------------------------------------------------------
    def _load_csv(self):
        """Safely read CSV file."""
        if not os.path.exists(self.history_path):
            return pd.DataFrame(columns=[
                "Ticket", "Symbol", "Type", "Lots",
                "OpenPrice", "ClosePrice", "Profit", "Analysis"
            ])
        try:
            df = pd.read_csv(self.history_path)
            return df
        except Exception as e:
            QMessageBox.warning(self, "Read Error", f"Failed to read order history:\n{e}")
            return pd.DataFrame()

    # ------------------------------------------------------------------
    def load_data(self):
        """Load trade history and update UI."""
        df = self._load_csv()

        if df.empty:
            self.table.setRowCount(0)
            self.summary_label.setText("⚠️ No trades found.")
            self.rank_label.setText("")
            self.ax.clear()
            self.canvas.draw()
            return

        # --- Normalize columns ---
        df.columns = [c.strip().capitalize() for c in df.columns]
        for col in ["Ticket", "Symbol", "Type", "Lots", "Openprice", "Closeprice", "Profit", "Analysis"]:
            if col not in df.columns:
                df[col] = ""

        # --- Populate table ---
        expected_cols = ["Ticket", "Symbol", "Type", "Lots", "Openprice", "Closeprice", "Profit", "Analysis"]
        self.table.setRowCount(len(df))
        self.table.setColumnCount(len(expected_cols))
        self.table.setHorizontalHeaderLabels(expected_cols)

        for row in range(len(df)):
            for col, name in enumerate(expected_cols):
                val = str(df.iloc[row][name])
                item = QTableWidgetItem(val)

                if name.lower() == "profit":
                    try:
                        p = float(val)
                        if p < 0:
                            item.setForeground(Qt.red)
                        elif p > 0:
                            item.setForeground(Qt.darkGreen)
                    except Exception:
                        pass

                self.table.setItem(row, col, item)

        self.table.resizeColumnsToContents()

        # --- Update summary, ranking, and chart ---
        self.display_summary(df)
        self.display_performance_ranking(df)
        self.plot_profitability(df)

    # ------------------------------------------------------------------
    def display_summary(self, df):
        """Compute total PnL and win rate."""
        try:
            total_trades = len(df)
            total_profit = df["Profit"].sum()
            win_trades = df[df["Profit"] > 0]
            win_rate = len(win_trades) / total_trades * 100 if total_trades else 0

            summary_text = (
                f"📊 <b>Total Trades:</b> {total_trades} | "
                f"<b>Total PnL:</b> ${total_profit:.2f} | "
                f"<b>Win Rate:</b> {win_rate:.2f}%"
            )
            self.summary_label.setText(summary_text)
        except Exception as e:
            self.summary_label.setText("⚠️ Error calculating summary.")
            if self.controller:
                self.controller.logger.error(f"Summary error: {e}")

    # ------------------------------------------------------------------
    def display_performance_ranking(self, df):
        """Show best/worst trades and per-symbol stats."""
        try:
            best_trade = df.loc[df["Profit"].idxmax()]
            worst_trade = df.loc[df["Profit"].idxmin()]
            symbol_stats = df.groupby("Symbol")["Profit"].sum().sort_values(ascending=False)

            rank_text = (
                f"🥇 <b>Best Trade:</b> Ticket {int(best_trade['Ticket'])} | "
                f"Symbol: {best_trade['Symbol']} | Profit: ${best_trade['Profit']:.2f}<br>"
                f"❌ <b>Worst Trade:</b> Ticket {int(worst_trade['Ticket'])} | "
                f"Symbol: {worst_trade['Symbol']} | Loss: ${worst_trade['Profit']:.2f}<br>"
                f"📌 <b>Top Performing Symbols:</b><br>"
            )

            for symbol, profit in symbol_stats.items():
                color = "green" if profit > 0 else "red"
                rank_text += f"&nbsp;&nbsp;• <font color='{color}'>{symbol}: ${profit:.2f}</font><br>"

            self.rank_label.setText(rank_text)
        except Exception as e:
            self.rank_label.setText("⚠️ Error calculating performance ranking.")
            if self.controller:
                self.controller.logger.error(f"Ranking error: {e}")

    # ------------------------------------------------------------------
    def plot_profitability(self, df):
        """Draw cumulative profitability chart."""
        try:
            df = df.copy()
            df["CumulativePnL"] = df["Profit"].cumsum()

            self.ax.clear()
            self.ax.plot(df.index, df["CumulativePnL"], marker="o", color="blue", label="Cumulative PnL", linewidth=2)
            self.ax.bar(df.index, df["Profit"], color=df["Profit"].apply(lambda x: "green" if x > 0 else "red"),
                        alpha=0.5, label="Trade PnL")

            self.ax.set_title("Profitability Over Time ($)", fontsize=12)


            self.ax.set_xlabel("Trade #")
            self.ax.set_ylabel("PnL ($)")
            self.ax.legend()
            self.ax.grid(True)
            self.canvas.draw()
        except Exception as e:
            if self.controller:
                self.controller.logger.error(f"Plot error: {e}")

    # ------------------------------------------------------------------
    def clear_history(self):
        """Clear history table and delete CSV."""
        try:
            if os.path.exists(self.history_path):
                os.remove(self.history_path)
            self.table.setRowCount(0)
            self.summary_label.setText("🧹 History cleared.")
            self.rank_label.setText("")
            self.ax.clear()
            self.canvas.draw()
        except Exception as e:
            QMessageBox.warning(self, "Clear Error", f"Failed to clear history:\n{e}")
