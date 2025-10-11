import json, os, pandas as pd
import time

from openai import OpenAI

class FeedbackTrainer:
    """
    📈 Continuous Learning Engine
    Correlates reasoning patterns with real results and refines GPT prompts.
    """

    def __init__(self, controller=None, log_path="src/logs/reasoning_log.jsonl"):
        self.controller = controller
        self.api_key = getattr(controller, "api_key", None)
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None
        self.log_path = log_path
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

    # ---------------------------------------------------------
    def analyze_reasoning(self, n_last=100):
        """Load recent reasoning logs and evaluate performance."""
        if not os.path.exists(self.log_path):
            return None

        df = pd.read_json(self.log_path, lines=True)
        df = df.tail(n_last)

        df["profit"] = df["outcome"].apply(
            lambda o: o.get("profit_pips") if isinstance(o, dict) else None
        )
        df["result"] = df["outcome"].apply(
            lambda o: o.get("result") if isinstance(o, dict) else None
        )

        win_rate = (df["result"] == "WIN").mean() * 100
        avg_profit = df["profit"].mean()

        summary = {
            "entries": len(df),
            "win_rate": round(win_rate, 2),
            "avg_profit": round(avg_profit, 2),
        }
        if self.controller:
            self.controller.logger.info(f"📊 Feedback summary: {summary}")
        return df, summary

    # ---------------------------------------------------------
    def gpt_reflect(self, df, summary):
        """Ask GPT to critique and improve its reasoning style."""
        if not self.client or df is None:
            return None

        # Take a few winning and losing examples
        good_examples = df[df["result"] == "WIN"].reasoning.tail(3).tolist()
        bad_examples = df[df["result"] == "LOSS"].reasoning.tail(3).tolist()

        prompt = f"""
        You are an AI trading model reviewing your past 100 trades.

        Summary:
        Win rate: {summary['win_rate']}%
        Avg profit: {summary['avg_profit']}

        Examples of good reasoning (led to profit):
        {json.dumps(good_examples, indent=2)}

        Examples of bad reasoning (led to loss):
        {json.dumps(bad_examples, indent=2)}

        Analyze what patterns in your reasoning led to profitable outcomes
        and what patterns caused losses.

        Then propose an improved reasoning style or prompt guidelines
        to reduce future mistakes.
        """

        try:
            resp = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=500,
            )
            reflection = resp.choices[0].message.content.strip()
            self._save_reflection(reflection)
            return reflection
        except Exception as e:
            print(f"⚠️ Reflection error: {e}")
            return None

    # ---------------------------------------------------------
    def _save_reflection(self, text):
        path = "src/logs/reflection_notes.txt"
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"\n\n[{time.strftime('%Y-%m-%d %H:%M:%S')}]\n{text}\n")
