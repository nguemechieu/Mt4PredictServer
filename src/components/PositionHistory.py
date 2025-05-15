import os
import pandas as pd
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QMessageBox
)


class PositionHistory(QWidget):
    def __init__(self, controller=None):
        super().__init__(controller)
        self.setWindowTitle("📜 Trade History & Performance")
        self.resize(1000, 600)
        self.controller = controller

        self.history_file = "src/data/trade_history.csv"
        self.ensure_file_exists()

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.header_label = QLabel("📄 Trade History")
        self.layout.addWidget(self.header_label)

        self.table = QTableWidget()
        self.layout.addWidget(self.table)

        summary_layout = QVBoxLayout()
        self.summary_label = QLabel()
        self.rank_label = QLabel()
        summary_layout.addWidget(self.summary_label)
        summary_layout.addWidget(self.rank_label)
        self.layout.addLayout(summary_layout)

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.load_data)
        self.layout.addWidget(refresh_btn)

        self.load_data()

    def ensure_file_exists(self):
        headers = ["Ticket", "Symbol", "Type", "Lots", "OpenPrice", "ClosePrice", "Profit"]
        if not os.path.exists(self.history_file):
            os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
            pd.DataFrame(columns=headers).to_csv(self.history_file, index=False)

    def load_data(self):
        if not os.path.exists(self.history_file):
            QMessageBox.warning(self, "File Missing", f"No trade history found at:\n{self.history_file}")
            return

        try:
            df = self.controller.predict_server.safe_read_csv(self.history_file)

            expected_cols = ["Ticket", "Symbol", "Type", "Lots", "OpenPrice", "ClosePrice", "Profit"]
            self.table.setRowCount(len(df))
            self.table.setColumnCount(len(expected_cols))
            self.table.setHorizontalHeaderLabels(expected_cols)

            for row in range(len(df)):
                for col in range(len(expected_cols)):
                    val = str(df.iloc[row][expected_cols[col]])
                    self.table.setItem(row, col, QTableWidgetItem(val))

            self.table.resizeColumnsToContents()

            if not df.empty:
                self.display_summary(df)
                self.display_performance_ranking(df)
            else:
                self.summary_label.setText("⚠️ No trades found.")
                self.rank_label.setText("")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load trade history:\n{e}")

    def display_summary(self, df):
        total_trades = len(df)
        total_profit = df['Profit'].sum()
        win_trades = df[df['Profit'] > 0]
        win_rate = len(win_trades) / total_trades * 100 if total_trades else 0

        summary_text = (
            f"📊 <b>Total Trades:</b> {total_trades} | "
            f"<b>Total PnL:</b> ${total_profit:.2f} | "
            f"<b>Win Rate:</b> {win_rate:.2f}%"
        )
        self.summary_label.setText(summary_text)

    def display_performance_ranking(self, df):
        try:
            best_trade = df.loc[df['Profit'].idxmax()]
            worst_trade = df.loc[df['Profit'].idxmin()]
            symbol_stats = df.groupby("Symbol")["Profit"].sum().sort_values(ascending=False)

            rank_text = (
                f"🥇 <b>Best Trade:</b> Ticket {int(best_trade['Ticket'])} | "
                f"Symbol: {best_trade['Symbol']} | Profit: ${best_trade['Profit']:.2f}<br>"
                f"❌ <b>Worst Trade:</b> Ticket {int(worst_trade['Ticket'])} | "
                f"Symbol: {worst_trade['Symbol']} | Loss: ${worst_trade['Profit']:.2f}<br>"
                f"📌 <b>Top Symbols:</b><br>"
            )
            for symbol, profit in symbol_stats.items():
                rank_text += f"&nbsp;&nbsp;• {symbol}: ${profit:.2f}<br>"

            self.rank_label.setText(rank_text)

        except Exception as e:
            self.rank_label.setText("⚠️ Error processing ranking.")
            print(f"Ranking error: {e}")
