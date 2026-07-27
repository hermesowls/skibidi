#!/usr/bin/env python3
"""Central append-only strategy event logger for paper trading workflows.

Writes both JSONL and SQLite so we can audit every signal, evaluation,
execution, position snapshot, and close outcome later.
"""
import json, os, sqlite3, uuid
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path(os.path.expanduser("~/.hermes/trading_logs"))
JSONL_PATH = LOG_DIR / "strategy_events.jsonl"
SQLITE_PATH = LOG_DIR / "strategy_events.sqlite"

SCHEMA = """
CREATE TABLE IF NOT EXISTS strategy_events (
    id TEXT PRIMARY KEY,
    ts_utc TEXT NOT NULL,
    event_type TEXT NOT NULL,
    run_id TEXT,
    source TEXT,
    strategy TEXT,
    portfolio TEXT,
    ticker TEXT,
    mode TEXT,
    action TEXT,
    conviction_score REAL,
    order_id TEXT,
    status TEXT,
    payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_strategy_events_ts ON strategy_events(ts_utc);
CREATE INDEX IF NOT EXISTS idx_strategy_events_ticker ON strategy_events(ticker);
CREATE INDEX IF NOT EXISTS idx_strategy_events_strategy ON strategy_events(strategy);
CREATE INDEX IF NOT EXISTS idx_strategy_events_run ON strategy_events(run_id);
"""

def _ensure_db():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(SQLITE_PATH) as con:
        con.executescript(SCHEMA)

def log_event(event_type, payload, *, run_id=None, source=None):
    """Append one event. Payload must be JSON-serializable."""
    _ensure_db()
    event = {
        "id": str(uuid.uuid4()),
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "run_id": run_id or payload.get("run_id") or os.getenv("STRATEGY_RUN_ID") or os.getenv("HERMES_CRON_EXECUTION_ID"),
        "source": source or payload.get("source") or os.getenv("STRATEGY_SOURCE") or os.path.basename(__file__),
        "strategy": payload.get("strategy"),
        "portfolio": payload.get("portfolio"),
        "ticker": payload.get("ticker"),
        "mode": payload.get("mode"),
        "action": payload.get("action"),
        "conviction_score": payload.get("conviction_score"),
        "order_id": payload.get("order_id"),
        "status": payload.get("status"),
        "payload": payload,
    }
    with JSONL_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, sort_keys=True, default=str) + "\n")
    with sqlite3.connect(SQLITE_PATH) as con:
        con.execute(
            """INSERT INTO strategy_events
            (id, ts_utc, event_type, run_id, source, strategy, portfolio, ticker, mode, action,
             conviction_score, order_id, status, payload_json)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event["id"], event["ts_utc"], event["event_type"], event["run_id"], event["source"],
                event["strategy"], event["portfolio"], event["ticker"], event["mode"], event["action"],
                event["conviction_score"], event["order_id"], event["status"], json.dumps(payload, sort_keys=True, default=str)
            ),
        )
    return event["id"]

def latest_events(limit=20):
    _ensure_db()
    with sqlite3.connect(SQLITE_PATH) as con:
        con.row_factory = sqlite3.Row
        return [dict(r) for r in con.execute(
            "SELECT ts_utc,event_type,source,strategy,ticker,mode,action,conviction_score,order_id,status FROM strategy_events ORDER BY ts_utc DESC LIMIT ?",
            (limit,),
        )]
