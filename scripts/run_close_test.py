import sqlite3, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from plugins.analyst_trader.db import get_db_path
from scripts.test_close_parser import parse_owls_alert

conn = sqlite3.connect(get_db_path())
conn.row_factory = sqlite3.Row

cur = conn.execute("SELECT * FROM raw_messages WHERE content LIKE '%RKLB%' OR embeds_json LIKE '%RKLB%' ORDER BY timestamp ASC")
rows = [dict(r) for r in cur.fetchall()]

print("PARSED RKLB ALERT SEQUENCE:")
for r in rows:
    embeds = json.loads(r['embeds_json']) if r.get('embeds_json') else None
    sig = parse_owls_alert(r['content'], embeds)
    if sig:
        print(f"Time: {r['timestamp'][:19]} | Action: [{sig['action']:<4}] | Ticker: {sig['ticker']:<5} | Price: ${sig['price']:<5.2f} | Text: {sig['raw_text'][:50]}")
