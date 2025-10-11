import os, json, numpy as np
from datetime import datetime

class AdaptiveStrategyEngine:
    """
    🧠 Adaptive Strategy Engine
    Learns from trade outcomes and tunes parameters automatically.
    """

    def __init__(self, controller=None, history_path="src/data/trade_history.json"):
        self.controller = controller
        self.history_path = history_path
        self.strategy_path = "src/config/strategy.json"
        os.makedirs(os.path.dirname(history_path), exist_ok=True)
        self.history = self._load_json(history_path, [])
        self.strategy = self._load_json(self.strategy_path, self._default_strategy())
        self.trade_counter = 0

    # --------------------------------------------------------------
    def _default_strategy(self):
        return {
            "rsi_period": 14,
            "rsi_buy_threshold": 30,
            "rsi_sell_threshold": 70,
            "ema_fast": 12,
            "ema_slow": 26,
            "risk_ratio": 0.02
        }

    def _load_json(self, path, default):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default

    def _save_json(self, path, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    # --------------------------------------------------------------
    def record_trade(self, symbol, indicators, decision, profit_pips):
        """Save completed trade for later learning."""
        result = "WIN" if profit_pips > 0 else "LOSS"
        entry = {
            "symbol": symbol,
            "timestamp": datetime.utcnow().isoformat(),
            "indicators": indicators,
            "decision": decision,
            "result": result,
            "profit_pips": profit_pips
        }
        self.history.append(entry)
        self.trade_counter += 1
        if self.trade_counter >= 10:
            self.analyze_performance()
            self.trade_counter = 0
        self._save_json(self.history_path, self.history)

    # --------------------------------------------------------------
    def analyze_performance(self):
        """Compute win rate and adjust parameters."""
        if len(self.history) < 20:
            return

        recent = self.history[-50:]
        profits = [t["profit_pips"] for t in recent]
        wins = [p for p in profits if p > 0]
        win_rate = len(wins) / len(recent)

        avg_profit = np.mean(profits)
        volatility = np.std(profits)

        # --- adaptive logic ---
        s = self.strategy.copy()

        if win_rate > 0.65:
            s["risk_ratio"] = min(0.05, s["risk_ratio"] + 0.005)
            s["rsi_buy_threshold"] = max(25, s["rsi_buy_threshold"] - 1)
            s["rsi_sell_threshold"] = min(75, s["rsi_sell_threshold"] + 1)
        elif win_rate < 0.45:
            s["risk_ratio"] = max(0.01, s["risk_ratio"] - 0.005)
            s["rsi_buy_threshold"] = min(35, s["rsi_buy_threshold"] + 1)
            s["rsi_sell_threshold"] = max(65, s["rsi_sell_threshold"] - 1)

        if volatility > 50:  # high variance → reduce EMA speed
            s["ema_fast"] = max(8, s["ema_fast"] - 1)
            s["ema_slow"] = min(40, s["ema_slow"] + 1)

        self.strategy = s
        self._save_json(self.strategy_path, s)

        print(f"📊 Auto-optimization complete — WinRate:{win_rate:.2f}, Avg:{avg_profit:.1f}, Vol:{volatility:.1f}")
        if self.controller:
            self.controller.logger.info(f"📈 Strategy updated: {json.dumps(s)}")

    # --------------------------------------------------------------
    def get_strategy(self):
        return self.strategy
