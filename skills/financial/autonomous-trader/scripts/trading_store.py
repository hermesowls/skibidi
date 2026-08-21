#!/usr/bin/env python3
"""
trading_store.py - Unified SQLite Trading Database Manager for Hermes Agent.
Provides structured, persistent SQL database tables at ~/.hermes/trading_logs/trading_store.sqlite:
- strategies: Modular strategy definitions, versions, conviction gates, sizing, rules
- notable_flow: Institutional options flow sweeps & dark pool alerts
- active_positions: Open paper positions, Finviz metrics, SMAs, sympathy nodes
- action_logs: Full audit history of decisions, trigger gate checks, and executions
"""

import os
import json
import sqlite3
from datetime import datetime

DB_PATH = os.path.expanduser("~/.hermes/trading_logs/trading_store.sqlite")


def get_db_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize SQL tables if they do not exist."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Strategies Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS strategies (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            version TEXT NOT NULL,
            horizon TEXT,
            risk_profile TEXT,
            conviction_threshold INTEGER NOT NULL,
            allocated_capital REAL NOT NULL,
            target_price_rule TEXT,
            stop_loss_rule TEXT,
            weights_json TEXT,
            rules_json TEXT,
            optimization_status TEXT,
            updated_at TEXT NOT NULL
        )
        """)

        # 2. Notable Flow Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS notable_flow (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            ticker TEXT NOT NULL,
            net_bias TEXT,
            total_premium REAL,
            ask_premium REAL,
            contracts INTEGER,
            alert_count INTEGER,
            vol_gt_oi_hits INTEGER,
            raw_json TEXT
        )
        """)

        # 3. Active Positions Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS active_positions (
            ticker TEXT PRIMARY KEY,
            mode TEXT NOT NULL,
            strategy_id TEXT,
            conviction_score INTEGER,
            allocated_capital REAL,
            target_price TEXT,
            stop_loss TEXT,
            status TEXT DEFAULT 'OPEN',
            finviz_json TEXT,
            sympathy_json TEXT,
            created_at TEXT NOT NULL
        )
        """)

        # 4. Action Logs Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS action_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            event_type TEXT NOT NULL,
            source_script TEXT NOT NULL,
            ticker TEXT,
            mode TEXT,
            conviction_score INTEGER,
            details_json TEXT
        )
        """)
        conn.commit()


# --- Strategies Functions ---

def sync_strategy_to_db(strat_data: dict):
    """Insert or replace a strategy definition into the SQLite strategies table."""
    init_db()
    s_id = strat_data.get("strategy_id", "").upper().strip()
    if not s_id:
        return

    weights_str = json.dumps(strat_data.get("weights", {}))
    rules_str = json.dumps(strat_data.get("rules", {}))

    with get_db_connection() as conn:
        conn.execute("""
        INSERT OR REPLACE INTO strategies (
            id, name, version, horizon, risk_profile, conviction_threshold,
            allocated_capital, target_price_rule, stop_loss_rule,
            weights_json, rules_json, optimization_status, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            s_id,
            strat_data.get("name", s_id),
            strat_data.get("version", "1.0.0"),
            strat_data.get("horizon", "N/A"),
            strat_data.get("risk_profile", "N/A"),
            int(strat_data.get("conviction_threshold", 80)),
            float(strat_data.get("allocated_capital", 200.0)),
            strat_data.get("target_price_rule", "Target (+3.0%)"),
            strat_data.get("stop_loss_rule", "Stop (-2.0%)"),
            weights_str,
            rules_str,
            strat_data.get("optimization_status", "Active"),
            strat_data.get("last_updated", datetime.now().isoformat())
        ))
        conn.commit()


def fetch_all_strategies() -> list[dict]:
    """Fetch all strategy rows from SQLite."""
    init_db()
    with get_db_connection() as conn:
        rows = conn.execute("SELECT * FROM strategies ORDER BY id ASC").fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["weights"] = json.loads(d["weights_json"]) if d["weights_json"] else {}
            d["rules"] = json.loads(d["rules_json"]) if d["rules_json"] else {}
            out.append(d)
        return out


# --- Active Positions Functions ---

def record_position(pos_data: dict):
    """Insert or update an active paper position in SQLite."""
    init_db()
    ticker = pos_data.get("ticker", "").upper().strip()
    if not ticker:
        return

    with get_db_connection() as conn:
        conn.execute("""
        INSERT OR REPLACE INTO active_positions (
            ticker, mode, strategy_id, conviction_score, allocated_capital,
            target_price, stop_loss, status, finviz_json, sympathy_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ticker,
            pos_data.get("mode", "VEX"),
            pos_data.get("strategy", "VEX_SWING"),
            int(pos_data.get("conviction_score", 80)),
            float(pos_data.get("allocated_capital", 200.0)),
            pos_data.get("target_price", "Target"),
            pos_data.get("stop_loss", "Stop"),
            pos_data.get("status", "OPEN"),
            json.dumps(pos_data.get("finviz_metrics", {})),
            json.dumps(pos_data.get("sympathy_nodes", [])),
            pos_data.get("timestamp", datetime.now().isoformat())
        ))
        conn.commit()


def fetch_active_positions() -> list[dict]:
    """Fetch all open paper positions."""
    init_db()
    with get_db_connection() as conn:
        rows = conn.execute("SELECT * FROM active_positions WHERE status LIKE 'OPEN%' ORDER BY created_at DESC").fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["finviz_metrics"] = json.loads(d["finviz_json"]) if d["finviz_json"] else {}
            d["sympathy_nodes"] = json.loads(d["sympathy_json"]) if d["sympathy_json"] else []
            out.append(d)
        return out


# --- Action Logs Functions ---

def log_action(event_type: str, source_script: str, ticker: str = None, mode: str = None, conviction_score: int = None, details: dict = None):
    """Record an audit action log into SQLite."""
    init_db()
    with get_db_connection() as conn:
        conn.execute("""
        INSERT INTO action_logs (timestamp, event_type, source_script, ticker, mode, conviction_score, details_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            event_type,
            source_script,
            ticker,
            mode,
            conviction_score,
            json.dumps(details or {})
        ))
        conn.commit()


def fetch_recent_actions(limit: int = 10) -> list[dict]:
    """Fetch recent action logs."""
    init_db()
    with get_db_connection() as conn:
        rows = conn.execute("SELECT * FROM action_logs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["details"] = json.loads(d["details_json"]) if d["details_json"] else {}
            out.append(d)
        return out


if __name__ == "__main__":
    init_db()
    print(f"✅ Initialized Unified Trading Store at {DB_PATH}")
    print(f"   Strategies in DB: {len(fetch_all_strategies())}")
    print(f"   Active Positions: {len(fetch_active_positions())}")
    print(f"   Action Logs     : {len(fetch_recent_actions())}")
