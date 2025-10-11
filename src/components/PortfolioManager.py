import os, json, time, numpy as np, pandas as pd
from PySide6.QtCore import QTimer
# 🧠 GOAL
#
# Enable your AI to:
#
# Track all open positions across symbols
#
# Adjust lot sizes based on account balance & confidence
#
# Detect and react to volatility or drawdown spikes
#
# Suspend or resume trading autonomously
#
# Distribute risk among multiple currency pairs
class PortfolioManager:
    """
    💼 Autonomous Portfolio & Risk Manager
    Tracks exposure, volatility, and automatically adjusts trading activity.
    """

    def __init__(self, controller=None, account_path="src/data/account_info.csv"):
        self.controller = controller
        self.account_path = account_path
        self.portfolio_state = {}
        self.max_drawdown_pct = 10.0
        self.volatility_threshold = 0.8
        self.max_risk_exposure = 0.25  # 25% of balance
        self.symbol_weights = {}
        self.last_check_time = 0

    # --------------------------------------------------------------
    def _load_account(self):
        """Load latest account data"""
        if not os.path.exists(self.account_path):
            return {}
        df = pd.read_csv(self.account_path)
        if len(df) == 0:
            return {}
        return df.iloc[-1].to_dict()

    # --------------------------------------------------------------
    def evaluate_portfolio(self):
        """Compute live exposure, PnL, and volatility metrics"""
        acc = self._load_account()
        balance = float(acc.get("balance", 0))
        equity = float(acc.get("equity", balance))
        profit = float(acc.get("profit", 0))
        drawdown = (1 - (equity / balance)) * 100 if balance > 0 else 0

        # --- Risk exposure per symbol
        open_path = "./src/data/open_orders.csv"
        exposures = {}
        if os.path.exists(open_path):
            df = pd.read_csv(open_path)
            if len(df) > 0:
                grouped = df.groupby("symbol")["lots"].sum()
                exposures = grouped.to_dict()

        total_exposure = sum(exposures.values())
        risk_pct = (total_exposure / max(balance, 1)) * 100

        # --- Compute volatility proxy
        hist_path = "./src/data/order_history.csv"
        volatility = 0
        if os.path.exists(hist_path):
            hist_df = pd.read_csv(hist_path)
            if "profit" in hist_df:
                volatility = np.std(hist_df["profit"].tail(50))

        self.portfolio_state = {
            "balance": balance,
            "equity": equity,
            "drawdown_pct": round(drawdown, 2),
            "risk_pct": round(risk_pct, 2),
            "volatility": round(volatility, 2),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        if self.controller:
            self.controller.logger.info(f"💼 Portfolio State: {self.portfolio_state}")
        return self.portfolio_state

    # --------------------------------------------------------------
    def should_pause_trading(self):
        """Decide if trading should be paused due to risk"""
        s = self.portfolio_state
        if s.get("drawdown_pct", 0) > self.max_drawdown_pct:
            return True, "High drawdown"
        if s.get("risk_pct", 0) > (self.max_risk_exposure * 100):
            return True, "Overexposed capital"
        if s.get("volatility", 0) > self.volatility_threshold:
            return True, "High market volatility"
        return False, "Safe"

    # --------------------------------------------------------------
    def adjust_lot_size(self, confidence, risk_ratio=0.02):
        """Dynamic lot sizing based on confidence and equity"""
        balance = self.portfolio_state.get("balance", 0)
        base_lot = max(0.01, balance * risk_ratio / 1000)
        adj_factor = np.clip(confidence, 0.5, 1.2)
        return round(base_lot * adj_factor, 2)

    """Allocate more lot to pair with highest win rate"""
    def allocate_weights(self, symbols, performances):
        total_perf = sum(max(0.1, p) for p in performances.values())
        for sym in symbols:
         self.symbol_weights[sym] = performances.get(sym, 1) / total_perf
        return self.symbol_weights

