import sys, json, os
from pathlib import Path

env_path = Path.home() / ".hermes" / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

sys.path.insert(0, str(Path(__file__).parent.parent))

from plugins.analyst_trader.signal_reviewer import AnalystSignalReviewer

reviewer = AnalystSignalReviewer()

test_messages = [
    ("RARE Trim", "can take some RARE profits at 12%. De risk bio", [{"title": "CLOSE:", "description": "can take some RARE profits at 12%. De risk bio"}]),
    ("FCX Entry Typo", "FCX 75C 09/21 Exp. at 3.0", [{"title": "OPEN:", "description": "FCX 75C 09/21 Exp. at 3.0"}]),
    ("RKLB Exit Runner", "Sold another RKLB at 6.60! One free runner for ER", [{"title": "CLOSE:", "description": "Sold another RKLB at 6.60! One free runner for ER"}]),
    ("General Chat", "Flat open this monday, SPX above 7760 can setup for 7777...", [{"title": "Update:", "description": "Flat open this monday..."}])
]

print("LLM ANALYST SIGNAL REVIEWER TEST:\n")
for name, text, embeds in test_messages:
    res = reviewer.review_signal(text, embeds)
    print(f"--- Alert: {name} ---")
    print(f"Text: '{text}'")
    print("LLM Review Output:", json.dumps(res, indent=2))
    print()
