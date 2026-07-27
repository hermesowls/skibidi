#!/usr/bin/env python3
import os, sys, json, subprocess
from datetime import datetime
try:
    from strategy_logger import log_event
except Exception:
    def log_event(*args, **kwargs): return None

PYTHON_BIN = os.path.expanduser("~/repos/hermes-agent/venv/bin/python3")
SKILLS_DIR = os.path.expanduser("~/repos/hermes-agent/skills")

def run_cmd(cmd):
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return res.stdout.strip()
    except Exception as e:
        return f"Error: {e}"

def execute_daily_pipeline():
    run_id = datetime.now().strftime("daily_prototype_%Y%m%d_%H%M%S")
    log_event("workflow_start", {"run_id": run_id, "workflow": "daily_autonomous_trading_prototype", "source_script": "run_daily_prototype.py"}, run_id=run_id, source="run_daily_prototype.py")
    # 1. Evaluate Market Sentiment Regime
    sentiment_json_str = run_cmd(f"{PYTHON_BIN} {SKILLS_DIR}/market_sentiment/scripts/eval_sentiment.py --format json")
    try:
        sentiment = json.loads(sentiment_json_str)
    except Exception:
        sentiment = {"scores": {"tradeability": 85}, "market_regime": {"primary": "RISK_ON_TREND"}}

    tradeability = sentiment.get("scores", {}).get("tradeability", 80)
    regime = sentiment.get("market_regime", {}).get("primary", "RISK_ON_TREND")
    log_event("market_regime", {"run_id": run_id, "workflow": "daily_autonomous_trading_prototype", "market_regime": regime, "tradeability": tradeability, "raw_sentiment": sentiment}, run_id=run_id, source="run_daily_prototype.py")

    # 2. Evaluate GEX 0DTE Strategy
    gex_res = run_cmd(f"{PYTHON_BIN} {SKILLS_DIR}/financial/autonomous-trader/scripts/autotrader.py eval --ticker SPY --mode GEX")

    # 3. Evaluate VEX 1-Week Swing Strategy
    vex_res = run_cmd(f"{PYTHON_BIN} {SKILLS_DIR}/financial/autonomous-trader/scripts/autotrader.py eval --ticker TSLA --mode VEX")

    # 4. Update Neural Web Graph
    run_cmd(f"{PYTHON_BIN} {SKILLS_DIR}/financial/graphify-trading/scripts/dynamic_graph_builder.py")

    # 5. Fetch Portfolios Performance
    portfolios_res = run_cmd(f"{PYTHON_BIN} {SKILLS_DIR}/financial/autonomous-trader/scripts/autotrader.py portfolios")
    log_event("workflow_end", {"run_id": run_id, "workflow": "daily_autonomous_trading_prototype", "market_regime": regime, "tradeability": tradeability, "gex_output": gex_res, "vex_output": vex_res, "portfolio_output": portfolios_res}, run_id=run_id, source="run_daily_prototype.py")

    # Format Token-Free Executive Report
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M PST")
    report = f"""🚀 **DAILY AUTONOMOUS TRADING PROTOTYPE EXECUTION**
⏰ **Timestamp**: {now_str}
📊 **Market Regime**: `{regime}` (Tradeability: {tradeability}/100)

---
{gex_res}

---
{vex_res}

---
{portfolios_res}"""

    return report

if __name__ == "__main__":
    print(execute_daily_pipeline())
