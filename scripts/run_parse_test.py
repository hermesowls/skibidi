import sqlite3, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from plugins.analyst_trader.db import get_db_path
from scripts.test_improved_parser import parse_owls_alert

conn = sqlite3.connect(get_db_path())
conn.row_factory = sqlite3.Row

cur = conn.execute("SELECT * FROM raw_messages")
rows = [dict(r) for r in cur.fetchall()]

extracted = []
for r in rows:
    embeds = json.loads(r['embeds_json']) if r.get('embeds_json') else None
    sig = parse_owls_alert(r['content'], embeds)
    if sig:
        extracted.append((r['analyst_name'], sig))

print(f"Extracted {len(extracted)} legitimate trade signals out of {len(rows)} messages:\n")
for analyst, s in extracted:
    exp_str = s['expiration'] or 'N/A'
    st_str = f"{s['strike']}{s['direction'][0].upper()}" if s['strike'] else ''
    print(f"Analyst: {analyst:<25} | [{s['action']:<5}] Ticker: {s['ticker']:<5} {st_str:<6} Exp: {exp_str:<6} @ ${s['price']:<6} (Author: {s['author']})")
