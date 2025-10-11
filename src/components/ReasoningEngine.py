import os, json, datetime
import time

from openai import OpenAI

class ReasoningEngine:
    """
    🤖 Explainable AI Reasoning Layer
    Uses GPT to explain trade decisions and risk context.
    """

    def __init__(self, controller=None, log_path="./src/logs/reasoning_log.jsonl"):
        self.controller = controller
        self.api_key = getattr(controller, "api_key", None)
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None
        self.log_path = log_path
        os.makedirs(os.path.dirname(log_path), exist_ok=True)




# --------------------------------------------------------------
    def explain_decision(self, symbol, indicators, prediction, account_state):
        """
        Generate GPT reasoning text for the trade decision.
        - symbol: e.g. "EURUSD"
        - indicators: dict of numeric indicator values
        - prediction: {"signal":"BUY","confidence":0.83}
        - account_state: {"balance":..., "open_positions":n, "risk_ratio":...}
        """

        reflection = ""
        if os.path.exists("src/logs/reflection_notes.txt"):
            with open("src/logs/reflection_notes.txt", "r", encoding="utf-8") as f:
             reflection = f.readlines()[-10:]  # last few lines only

        prompt = f"""
You are an AI trading analyst. 
Use these reflection notes to improve your judgment:
{''.join(reflection)}

Now analyze the following indicators and explain your decision...
"""

        if not self.client:
            return "⚠️ GPT client not initialized."

        prompt = f"""
        You are an AI trading analyst integrated into an automated system.
        Analyze these trading indicators and explain the reasoning
        behind the decision in concise, professional terms.

        Symbol: {symbol}
        Indicators: {json.dumps(indicators, indent=2)}
        AI Prediction: {json.dumps(prediction, indent=2)}
        Account State: {json.dumps(account_state, indent=2)}

        Provide:
        1. Short summary of current market condition.
        2. Reason for BUY/SELL/HOLD decision.
        3. Expected short-term outcome (profit range or volatility).
        4. Risk evaluation (confidence level, drawdown alert, etc.).
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=300,
            )
            reasoning = response.choices[0].message.content.strip()
            self._log_reasoning(symbol, indicators, prediction, reasoning)
            return reasoning
        except Exception as e:
            err = f"⚠️ GPT Reasoning Error: {e}"
            print(err)
            return err

    # --------------------------------------------------------------
    def _log_reasoning(self, symbol, indicators, prediction, reasoning):
        """Save reasoning for later review."""
        entry = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "symbol": symbol,
            "indicators": indicators,
            "decision": prediction,
            "reasoning": reasoning,
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        if self.controller and hasattr(self.controller, "logger"):
            self.controller.logger.info(f"🧩 Reasoning logged for {symbol}")
    def update_reasoning_outcome(self, symbol, trade_result, profit_pips):
        """
        Update the last reasoning entry for a symbol with the actual outcome.
        """
        try:
         log_file = self.log_path
         if not os.path.exists(log_file):
            return

         lines = open(log_file, "r", encoding="utf-8").read().splitlines()
         for i in reversed(range(len(lines))):
            entry = json.loads(lines[i])
            if entry["symbol"] == symbol and "outcome" not in entry:
                entry["outcome"] = {
                    "result": "WIN" if profit_pips > 0 else "LOSS",
                    "profit_pips": profit_pips,
                    "verified_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                lines[i] = json.dumps(entry)
                break

         with open(log_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        except Exception as e:
         self.controller.logger.error(f"⚠️ Failed to update reasoning outcome: {e}")

