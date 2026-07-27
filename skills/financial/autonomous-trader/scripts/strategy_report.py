#!/usr/bin/env python3
import argparse, json, sqlite3
from pathlib import Path

DB = Path.home()/'.hermes/trading_logs/strategy_events.sqlite'

def rows(sql, args=()):
    if not DB.exists():
        return []
    with sqlite3.connect(DB) as con:
        con.row_factory = sqlite3.Row
        return [dict(r) for r in con.execute(sql, args)]

def latest(limit):
    rs = rows("SELECT ts_utc,event_type,source,strategy,portfolio,ticker,mode,action,conviction_score,order_id,status FROM strategy_events ORDER BY ts_utc DESC LIMIT ?", (limit,))
    print(json.dumps(rs, indent=2))

def summary():
    rs = rows("""
      SELECT strategy, ticker, event_type, COUNT(*) AS events,
             AVG(conviction_score) AS avg_conviction
      FROM strategy_events
      GROUP BY strategy, ticker, event_type
      ORDER BY strategy, ticker, event_type
    """)
    print("📚 **STRATEGY LOG SUMMARY**\n")
    if not rs:
        print("No strategy events logged yet.")
        return
    for r in rs:
        print(f"**Strategy**: {r['strategy'] or 'N/A'} | **Ticker**: {r['ticker'] or 'N/A'} | **Event**: {r['event_type']} | **Count**: {r['events']} | **Avg Conviction**: {float(r['avg_conviction'] or 0):.1f}")

if __name__ == '__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['latest','summary'], nargs='?', default='summary')
    ap.add_argument('--limit', type=int, default=20)
    a=ap.parse_args()
    latest(a.limit) if a.cmd == 'latest' else summary()
