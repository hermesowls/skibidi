import sqlite3
from plugins.analyst_trader.db import get_db_path

conn = sqlite3.connect(get_db_path())
conn.row_factory = sqlite3.Row
cur = conn.execute("SELECT position_id, analyst_name, ticker, entry_price, current_price, roi_pct, last_price_updated_at, status FROM positions WHERE status='OPEN' LIMIT 15")
print("POSITIONS TABLE WITH LAST PRICE UPDATED TIMESTAMP:")
for r in cur.fetchall():
    d = dict(r)
    ts = d.get('last_price_updated_at') or 'Not updated yet'
    print(f"[{d['status']}] {d['ticker']} | Entry: ${d['entry_price']} | Current: ${d['current_price']} | ROI: {d['roi_pct']:.1f}% | Last Updated: {ts}")
