import sqlite3
from plugins.analyst_trader.db import get_db_path

conn = sqlite3.connect(get_db_path())
conn.row_factory = sqlite3.Row

cur = conn.execute("SELECT position_id, ticker, asset_type, strike, status, entry_price, exit_price, current_price, roi_pct, realized_pnl, notes FROM positions")
rows = [dict(r) for r in cur.fetchall()]

print("ALL POSITIONS IN SQLITE (INCLUDING CLOSED AND TRIMMED):\n")
for r in rows:
    exit_p = f"${r['exit_price']:.2f}" if r['exit_price'] is not None else "N/A"
    curr_p = f"${r['current_price']:.2f}" if r['current_price'] is not None else "N/A"
    st = f"{r['strike']}C" if r['strike'] else ""
    print(f"[{r['status']:<6}] {r['ticker']:<5} {st:<6} | Entry: ${r['entry_price']:.2f} | Exit: {exit_p:<7} | Current: {curr_p:<7} | Realized/Unrealized ROI: {r['roi_pct']:+.1f}%")
