"""SQLite Database Manager for Analyst Performance Tracking and Dual Portfolios."""

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def get_db_path() -> Path:
    base_dir = Path.home() / ".hermes"
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / "analyst_trading.db"


class AnalystDatabase:
    """Manages SQLite tables for analyst performance, trade signals, and dual portfolios."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path or get_db_path()
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        """Create tables if they do not exist."""
        conn = self._get_connection()
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS raw_messages (
                    message_id TEXT PRIMARY KEY,
                    channel_id TEXT NOT NULL,
                    channel_name TEXT NOT NULL,
                    analyst_name TEXT NOT NULL,
                    author_id TEXT NOT NULL,
                    content TEXT,
                    embeds_json TEXT,
                    timestamp TEXT NOT NULL,
                    processed INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS analysts (
                    analyst_id TEXT PRIMARY KEY,
                    channel_id TEXT UNIQUE NOT NULL,
                    channel_name TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    total_signals INTEGER DEFAULT 0,
                    winning_signals INTEGER DEFAULT 0,
                    losing_signals INTEGER DEFAULT 0,
                    win_rate REAL DEFAULT 0.0,
                    avg_roi_pct REAL DEFAULT 0.0,
                    style_category TEXT DEFAULT 'general',
                    last_backfilled_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    position_id TEXT PRIMARY KEY,
                    analyst_name TEXT NOT NULL,
                    channel_id TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    asset_type TEXT NOT NULL, -- 'option' | 'equity'
                    direction TEXT NOT NULL,  -- 'call' | 'put' | 'long' | 'short'
                    strike REAL,
                    expiration TEXT,
                    contracts_or_shares REAL DEFAULT 1.0,
                    entry_price REAL NOT NULL,
                    current_price REAL,
                    exit_price REAL,
                    status TEXT NOT NULL,     -- 'OPEN' | 'TRIMMED' | 'CLOSED' | 'EXPIRED'
                    realized_pnl REAL DEFAULT 0.0,
                    roi_pct REAL DEFAULT 0.0,
                    entry_time TEXT NOT NULL,
                    exit_time TEXT,
                    entry_message_id TEXT,
                    exit_message_id TEXT,
                    last_price_updated_at TEXT,
                    notes TEXT,
                    confidence_score REAL DEFAULT 0.95,
                    llm_reasoning TEXT,
                    verification_status TEXT DEFAULT 'VERIFIED',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS trade_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    position_id TEXT NOT NULL,
                    analyst_name TEXT NOT NULL,
                    message_id TEXT NOT NULL,
                    event_type TEXT NOT NULL, -- 'ENTRY' | 'TRIM' | 'CLOSE'
                    ticker TEXT NOT NULL,
                    price REAL,
                    confidence_score REAL DEFAULT 0.95,
                    llm_reasoning TEXT,
                    verification_status TEXT DEFAULT 'VERIFIED',
                    details_json TEXT,
                    timestamp TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

            # Apply safe column additions if upgrading existing schema
            for col in [("confidence_score", "REAL DEFAULT 0.95"), ("llm_reasoning", "TEXT"), ("verification_status", "TEXT DEFAULT 'VERIFIED'")]:
                try:
                    conn.execute(f"ALTER TABLE positions ADD COLUMN {col[0]} {col[1]}")
                except Exception:
                    pass
                try:
                    conn.execute(f"ALTER TABLE trade_events ADD COLUMN {col[0]} {col[1]}")
                except Exception:
                    pass

            conn.execute("""
                CREATE TABLE IF NOT EXISTS portfolios (
                    portfolio_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,       -- 'copy_trader' | 'autonomous_ai'
                    cash_balance REAL DEFAULT 100000.0,
                    total_value REAL DEFAULT 100000.0,
                    realized_pnl REAL DEFAULT 0.0,
                    unrealized_pnl REAL DEFAULT 0.0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS portfolio_holdings (
                    holding_id TEXT PRIMARY KEY,
                    portfolio_id TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    asset_type TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    strike REAL,
                    expiration TEXT,
                    quantity REAL NOT NULL,
                    average_cost REAL NOT NULL,
                    current_price REAL,
                    market_value REAL,
                    unrealized_pnl REAL,
                    last_price_updated_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (portfolio_id) REFERENCES portfolios (portfolio_id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS analyst_styles (
                    analyst_name TEXT PRIMARY KEY,
                    preferred_tickers TEXT,
                    avg_holding_hours REAL,
                    win_rate REAL,
                    avg_roi_pct REAL,
                    preferred_dte_min INTEGER,
                    preferred_dte_max INTEGER,
                    strategy_summary TEXT,
                    rules_json TEXT,
                    updated_at TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS reviewer_audits (
                    audit_id TEXT PRIMARY KEY,
                    message_id TEXT NOT NULL,
                    analyst_name TEXT NOT NULL,
                    ticker TEXT,
                    discrepancy_type TEXT NOT NULL,
                    original_data_json TEXT,
                    corrected_data_json TEXT,
                    confidence_score REAL NOT NULL,
                    reasoning TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

    def get_portfolio(self, portfolio_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cur = conn.execute("SELECT * FROM portfolios WHERE portfolio_id = ?", (portfolio_id,))
        row = cur.fetchone()
        if not row:
            now = datetime.now().isoformat()
            with conn:
                conn.execute("""
                    INSERT INTO portfolios (portfolio_id, name, cash_balance, total_value, created_at, updated_at)
                    VALUES (?, ?, 100000.0, 100000.0, ?, ?)
                """, (portfolio_id, portfolio_id, now, now))
            cur = conn.execute("SELECT * FROM portfolios WHERE portfolio_id = ?", (portfolio_id,))
            row = cur.fetchone()
        return dict(row) if row else None

    def save_analyst_style(self, analyst_name: str, preferred_tickers: List[str],
                           avg_holding_hours: float, win_rate: float, avg_roi_pct: float,
                           preferred_dte_min: int, preferred_dte_max: int,
                           strategy_summary: str, rules: Dict[str, Any]) -> None:
        conn = self._get_connection()
        now = datetime.now().isoformat()
        with conn:
            conn.execute("""
                INSERT INTO analyst_styles (
                    analyst_name, preferred_tickers, avg_holding_hours, win_rate,
                    avg_roi_pct, preferred_dte_min, preferred_dte_max, strategy_summary,
                    rules_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(analyst_name) DO UPDATE SET
                    preferred_tickers=excluded.preferred_tickers,
                    avg_holding_hours=excluded.avg_holding_hours,
                    win_rate=excluded.win_rate,
                    avg_roi_pct=excluded.avg_roi_pct,
                    preferred_dte_min=excluded.preferred_dte_min,
                    preferred_dte_max=excluded.preferred_dte_max,
                    strategy_summary=excluded.strategy_summary,
                    rules_json=excluded.rules_json,
                    updated_at=excluded.updated_at
            """, (analyst_name, json.dumps(preferred_tickers), avg_holding_hours, win_rate,
                  avg_roi_pct, preferred_dte_min, preferred_dte_max, strategy_summary,
                  json.dumps(rules), now))

    def add_portfolio_holding(self, holding_id: str, portfolio_id: str, ticker: str,
                              asset_type: str, direction: str, quantity: float,
                              entry_price: float, strike: Optional[float] = None,
                              expiration: Optional[str] = None) -> Dict[str, Any]:
        conn = self._get_connection()
        now = datetime.now().isoformat()
        mkt_val = entry_price * quantity * (100.0 if asset_type == "option" else 1.0)
        with conn:
            conn.execute("""
                INSERT INTO portfolio_holdings (
                    holding_id, portfolio_id, ticker, asset_type, direction,
                    quantity, average_cost, current_price, market_value, unrealized_pnl,
                    strike, expiration, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0.0, ?, ?, ?, ?)
            """, (holding_id, portfolio_id, ticker, asset_type, direction,
                  quantity, entry_price, entry_price, mkt_val, strike, expiration, now, now))
        cur = conn.execute("SELECT * FROM portfolio_holdings WHERE holding_id = ?", (holding_id,))
        return dict(cur.fetchone())

    def update_portfolio_balance(self, portfolio_id: str, cash_delta: float = 0.0, realized_pnl_delta: float = 0.0) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        p = self.get_portfolio(portfolio_id)
        if not p:
            return {}
        now = datetime.now().isoformat()
        new_cash = float(p.get("cash_balance") or 100000.0) + cash_delta
        new_pnl = float(p.get("realized_pnl") or 0.0) + realized_pnl_delta
        tot_val = new_cash + new_pnl
        with conn:
            conn.execute("""
                UPDATE portfolios SET cash_balance = ?, realized_pnl = ?, total_value = ?, updated_at = ?
                WHERE portfolio_id = ?
            """, (new_cash, new_pnl, tot_val, now, portfolio_id))
        return self.get_portfolio(portfolio_id)

    def list_portfolio_holdings(self, portfolio_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cur = conn.execute("SELECT * FROM portfolio_holdings WHERE portfolio_id = ? ORDER BY created_at DESC", (portfolio_id,))
        return [dict(r) for r in cur.fetchall()]

    def register_analyst(self, channel_id: str, channel_name: str, display_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        now = datetime.now().isoformat()
        clean_name = display_name or channel_name.replace("-", " ").title().strip()
        analyst_id = f"analyst_{channel_id}"

        with conn:
            conn.execute("""
                INSERT INTO analysts (analyst_id, channel_id, channel_name, display_name, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(channel_id) DO UPDATE SET
                    channel_name=excluded.channel_name,
                    display_name=excluded.display_name,
                    updated_at=excluded.updated_at
            """, (analyst_id, channel_id, channel_name, clean_name, now, now))

        return self.get_analyst_by_channel(channel_id)

    def get_analyst_by_channel(self, channel_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cur = conn.execute("SELECT * FROM analysts WHERE channel_id = ?", (channel_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def list_analysts(self, timeframe: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cur = conn.execute("SELECT * FROM analysts ORDER BY display_name ASC")
        analysts = [dict(r) for r in cur.fetchall()]

        if not timeframe or timeframe == "all_time":
            return analysts

        # Calculate dynamic stats for timeframe window (weekly = 7d, monthly = 30d)
        now = datetime.now()
        days = 7 if timeframe == "weekly" else 30
        cutoff = (now - timedelta(days=days)).isoformat()

        updated_list = []
        for a in analysts:
            an_name = a.get("display_name") or a.get("channel_name")
            cur_p = conn.execute("""
                SELECT * FROM positions
                WHERE (analyst_name = ? OR analyst_name = ?) AND entry_time >= ?
            """, (an_name, a.get("analyst_id"), cutoff))
            pos_list = [dict(r) for r in cur_p.fetchall()]
            closed = [p for p in pos_list if p.get("status") == "CLOSED"]

            tot = len(pos_list)
            wins = sum(1 for p in closed if float(p.get("realized_pnl") or p.get("roi_pct") or 0) > 0)
            losses = sum(1 for p in closed if float(p.get("realized_pnl") or p.get("roi_pct") or 0) < 0)
            win_rate = (wins / len(closed) * 100.0) if len(closed) > 0 else 0.0
            avg_roi = (sum(float(p.get("roi_pct") or 0) for p in closed) / len(closed)) if len(closed) > 0 else 0.0

            a_copy = dict(a)
            a_copy["total_signals"] = tot
            a_copy["winning_signals"] = wins
            a_copy["losing_signals"] = losses
            a_copy["win_rate"] = round(win_rate, 2)
            a_copy["avg_roi_pct"] = round(avg_roi, 2)
            a_copy["timeframe"] = timeframe
            updated_list.append(a_copy)

        return updated_list

    def save_raw_message(self, message_id: str, channel_id: str, channel_name: str,
                         analyst_name: str, author_id: str, content: str,
                         embeds: Optional[List[Dict[str, Any]]] = None,
                         timestamp: Optional[str] = None) -> bool:
        conn = self._get_connection()
        cur = conn.execute("SELECT 1 FROM raw_messages WHERE message_id = ?", (message_id,))
        is_new = cur.fetchone() is None

        now = datetime.now().isoformat()
        ts = timestamp or now
        embeds_str = json.dumps(embeds) if embeds else None

        # Auto-register analyst if channel_id is provided
        if channel_id and channel_id != "0000":
            try:
                self.register_analyst(channel_id, channel_name, analyst_name)
            except Exception as e:
                logger.debug("Auto-register analyst failed: %s", e)

        with conn:
            conn.execute("""
                INSERT INTO raw_messages (message_id, channel_id, channel_name, analyst_name, author_id, content, embeds_json, timestamp, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(message_id) DO UPDATE SET content=excluded.content, embeds_json=excluded.embeds_json
            """, (message_id, channel_id, channel_name, analyst_name, author_id, content, embeds_str, ts, now))

        return is_new

    def mark_message_processed(self, message_id: str) -> None:
        conn = self._get_connection()
        with conn:
            conn.execute("UPDATE raw_messages SET processed = 1 WHERE message_id = ?", (message_id,))

    def create_position(self, position_id: str, analyst_name: str, channel_id: str,
                        ticker: str, asset_type: str, direction: str, entry_price: float,
                        contracts_or_shares: float = 1.0, strike: Optional[float] = None,
                        expiration: Optional[str] = None, entry_time: Optional[str] = None,
                        entry_message_id: Optional[str] = None, notes: Optional[str] = None) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        now = datetime.now().isoformat()
        t_entry = entry_time or now

        # Ensure analyst entry exists for analyst_name
        try:
            self.register_analyst(channel_id, channel_id, analyst_name)
        except Exception:
            pass

        with conn:
            conn.execute("""
                INSERT INTO positions (
                    position_id, analyst_name, channel_id, ticker, asset_type, direction,
                    strike, expiration, contracts_or_shares, entry_price, current_price,
                    status, entry_time, entry_message_id, notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, ?, ?, ?, ?)
                ON CONFLICT(position_id) DO UPDATE SET
                    current_price=excluded.entry_price,
                    updated_at=excluded.updated_at
            """, (position_id, analyst_name, channel_id, ticker, asset_type, direction,
                  strike, expiration, contracts_or_shares, entry_price, entry_price,
                  t_entry, entry_message_id, notes, now, now))

        return self.get_position(position_id)

    def get_position(self, position_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cur = conn.execute("SELECT * FROM positions WHERE position_id = ?", (position_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def find_open_position(self, analyst_name: str, ticker: str,
                           strike: Optional[float] = None, expiration: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Locate an existing OPEN or TRIMMED position matching ticker."""
        conn = self._get_connection()
        ticker_clean = ticker.upper()

        if strike and expiration:
            cur = conn.execute("""
                SELECT * FROM positions
                WHERE ticker = ? AND strike = ? AND expiration = ? AND status IN ('OPEN', 'TRIMMED')
                ORDER BY created_at DESC LIMIT 1
            """, (ticker_clean, strike, expiration))
        elif strike:
            cur = conn.execute("""
                SELECT * FROM positions
                WHERE ticker = ? AND strike = ? AND status IN ('OPEN', 'TRIMMED')
                ORDER BY created_at DESC LIMIT 1
            """, (ticker_clean, strike))
        else:
            cur = conn.execute("""
                SELECT * FROM positions
                WHERE ticker = ? AND status IN ('OPEN', 'TRIMMED')
                ORDER BY created_at DESC LIMIT 1
            """, (ticker_clean,))

        row = cur.fetchone()
        return dict(row) if row else None

    def update_position_trim_or_close(self, position_id: str, exit_price: float,
                                      status: str, trim_ratio: float = 0.5,
                                      exit_message_id: Optional[str] = None,
                                      exit_time: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Trim or Close a position with weighted trim adjustments and blended ROI calculation."""
        conn = self._get_connection()
        pos = self.get_position(position_id)
        if not pos:
            raise ValueError(f"Position {position_id} not found")

        now = datetime.now().isoformat()
        t_exit = exit_time or now
        entry_p = float(pos["entry_price"])
        current_weight = float(pos["contracts_or_shares"])
        current_realized_pnl = float(pos.get("realized_pnl") or 0.0)

        if status == "CLOSED" or trim_ratio >= 0.85 or current_weight * (1.0 - trim_ratio) <= 0.05:
            final_status = "CLOSED"
            remaining_w = 0.0
            multiplier = 100.0 if pos["asset_type"] == "option" else 1.0
            if pos["direction"] in ("call", "long"):
                new_realized_pnl = (exit_price - entry_p) * multiplier
            else:
                new_realized_pnl = (entry_p - exit_price) * multiplier
            roi_pct = ((exit_price - entry_p) / entry_p) * 100.0 if entry_p > 0 else 0.0
            curr_p = exit_price
        else:
            final_status = "TRIMMED"
            trimmed_w = round(current_weight * trim_ratio, 3)
            remaining_w = round(current_weight - trimmed_w, 3)
            multiplier = 100.0 if pos["asset_type"] == "option" else 1.0
            if pos["direction"] in ("call", "long"):
                segment_pnl = (exit_price - entry_p) * current_weight * multiplier
            else:
                segment_pnl = (entry_p - exit_price) * current_weight * multiplier
            new_realized_pnl = current_realized_pnl + segment_pnl
            curr_p = exit_price
            roi_pct = ((exit_price - entry_p) / entry_p) * 100.0 if entry_p > 0 else 0.0

        with conn:
            conn.execute("""
                UPDATE positions SET
                    contracts_or_shares = ?,
                    exit_price = ?,
                    current_price = ?,
                    status = ?,
                    realized_pnl = ?,
                    roi_pct = ?,
                    exit_time = ?,
                    exit_message_id = ?,
                    updated_at = ?
                WHERE position_id = ?
            """, (remaining_w, exit_price, curr_p, final_status, new_realized_pnl, round(roi_pct, 2), t_exit, exit_message_id, now, position_id))

        if final_status == "CLOSED":
            self.recalculate_analyst_stats(pos["analyst_name"])

        return self.get_position(position_id)

    def log_trade_event(self, position_id: str, analyst_name: str, message_id: str,
                        event_type: str, ticker: str, price: Optional[float] = None,
                        details: Optional[Dict[str, Any]] = None,
                        timestamp: Optional[str] = None) -> None:
        conn = self._get_connection()
        now = datetime.now().isoformat()
        ts = timestamp or now
        details_str = json.dumps(details) if details else None

        with conn:
            conn.execute("""
                INSERT INTO trade_events (position_id, analyst_name, message_id, event_type, ticker, price, details_json, timestamp, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (position_id, analyst_name, message_id, event_type, ticker, price, details_str, ts, now))

    def list_positions(self, analyst_name: Optional[str] = None, status: Optional[str] = None, timeframe: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        query = "SELECT * FROM positions WHERE 1=1"
        params = []

        if analyst_name:
            query += " AND analyst_name = ?"
            params.append(analyst_name)
        if status:
            query += " AND status = ?"
            params.append(status)
        if timeframe and timeframe != "all_time":
            days = 7 if timeframe == "weekly" else 30
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            query += " AND entry_time >= ?"
            params.append(cutoff)

        query += " ORDER BY created_at DESC"
        cur = conn.execute(query, params)
        return [dict(r) for r in cur.fetchall()]

    def recalculate_analyst_stats(self, analyst_name: str, timeframe: Optional[str] = None) -> Dict[str, Any]:
        conn = self._get_connection()
        query = "SELECT * FROM positions WHERE (analyst_name = ? OR analyst_name LIKE ?) AND status = 'CLOSED'"
        params = [analyst_name, f"%{analyst_name}%"]

        if timeframe and timeframe != "all_time":
            days = 7 if timeframe == "weekly" else 30
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            query += " AND entry_time >= ?"
            params.append(cutoff)

        cur = conn.execute(query, params)
        closed_positions = [dict(r) for r in cur.fetchall()]

        total_signals = len(closed_positions)
        winning_signals = sum(1 for p in closed_positions if float(p.get("realized_pnl") or p.get("roi_pct") or 0) > 0)
        losing_signals = sum(1 for p in closed_positions if float(p.get("realized_pnl") or p.get("roi_pct") or 0) < 0)
        win_rate = (winning_signals / total_signals * 100.0) if total_signals > 0 else 0.0
        avg_roi_pct = sum(float(p.get("roi_pct") or 0) for p in closed_positions) / total_signals if total_signals > 0 else 0.0

        now = datetime.now().isoformat()
        with conn:
            conn.execute("""
                UPDATE analysts SET
                    total_signals = ?,
                    winning_signals = ?,
                    losing_signals = ?,
                    win_rate = ?,
                    avg_roi_pct = ?,
                    updated_at = ?
                WHERE display_name = ? OR channel_name = ?
            """, (total_signals, winning_signals, losing_signals, round(win_rate, 2), round(avg_roi_pct, 2), now, analyst_name, analyst_name))

        return {
            "analyst_name": analyst_name,
            "total_signals": total_signals,
            "win_rate": round(win_rate, 2),
            "avg_roi_pct": round(avg_roi_pct, 2)
        }

    def save_reviewer_audit(self, audit_id: str, message_id: str, analyst_name: str,
                            ticker: Optional[str], discrepancy_type: str,
                            original_data: Optional[Dict[str, Any]],
                            corrected_data: Optional[Dict[str, Any]],
                            confidence_score: float, reasoning: str,
                            status: str = "NEEDS_REVIEW") -> Dict[str, Any]:
        """Record an LLM Reviewer Audit entry for verification and auto-reconciliation."""
        conn = self._get_connection()
        now = datetime.now().isoformat()
        orig_str = json.dumps(original_data) if original_data else None
        corr_str = json.dumps(corrected_data) if corrected_data else None

        with conn:
            conn.execute("""
                INSERT INTO reviewer_audits (
                    audit_id, message_id, analyst_name, ticker, discrepancy_type,
                    original_data_json, corrected_data_json, confidence_score, reasoning,
                    status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(audit_id) DO UPDATE SET
                    discrepancy_type=excluded.discrepancy_type,
                    original_data_json=excluded.original_data_json,
                    corrected_data_json=excluded.corrected_data_json,
                    confidence_score=excluded.confidence_score,
                    reasoning=excluded.reasoning,
                    status=excluded.status,
                    updated_at=excluded.updated_at
            """, (audit_id, message_id, analyst_name, ticker, discrepancy_type,
                  orig_str, corr_str, float(confidence_score), reasoning, status, now, now))

        cur = conn.execute("SELECT * FROM reviewer_audits WHERE audit_id = ?", (audit_id,))
        return dict(cur.fetchone())

    def list_reviewer_audits(self, analyst_name: Optional[str] = None, status: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """List recorded reviewer audits."""
        conn = self._get_connection()
        query = "SELECT * FROM reviewer_audits WHERE 1=1"
        params: List[Any] = []
        if analyst_name:
            query += " AND analyst_name = ?"
            params.append(analyst_name)
        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cur = conn.execute(query, params)
        return [dict(r) for r in cur.fetchall()]

    def reconcile_position_from_audit(self, audit_id: str) -> Dict[str, Any]:
        """Apply corrective database actions based on LLM Reviewer audit findings."""
        conn = self._get_connection()
        cur = conn.execute("SELECT * FROM reviewer_audits WHERE audit_id = ?", (audit_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Reviewer audit {audit_id} not found")

        audit = dict(row)
        disc_type = audit["discrepancy_type"]
        corr_data = json.loads(audit["corrected_data_json"]) if audit.get("corrected_data_json") else {}
        analyst_name = audit["analyst_name"]
        ticker_str = str(audit["ticker"] or corr_data.get("ticker") or "")

        if not corr_data or disc_type == "MATCHED_ACCURATE":
            now = datetime.now().isoformat()
            with conn:
                conn.execute("UPDATE reviewer_audits SET status = 'VERIFIED', updated_at = ? WHERE audit_id = ?", (now, audit_id))
            return {"status": "VERIFIED", "audit_id": audit_id, "action_taken": "No correction required"}

        action_taken = ""

        if disc_type == "MISSED_SIGNAL":
            action = corr_data.get("action", "ENTRY")
            if action == "ENTRY":
                pos_id = f"pos_rev_{audit['message_id']}"
                self.create_position(
                    position_id=pos_id,
                    analyst_name=analyst_name,
                    channel_id="reconciled",
                    ticker=ticker_str,
                    asset_type=corr_data.get("asset_type", "option"),
                    direction=corr_data.get("direction", "call"),
                    entry_price=float(corr_data.get("price") or corr_data.get("entry_price") or 1.0),
                    strike=corr_data.get("strike"),
                    expiration=corr_data.get("expiration"),
                    entry_message_id=audit["message_id"],
                    notes="Reconciled by LLM Reviewer Agent"
                )
                action_taken = f"Created missing ENTRY position for {ticker_str}"
            else:
                existing = self.find_open_position(analyst_name, ticker_str)
                if existing:
                    self.update_position_trim_or_close(
                        position_id=existing["position_id"],
                        exit_price=float(corr_data.get("price") or existing["entry_price"]),
                        status="CLOSED" if action == "EXIT" else "TRIMMED",
                        trim_ratio=float(corr_data.get("trim_ratio", 0.5)),
                        exit_message_id=audit["message_id"]
                    )
                    action_taken = f"Updated existing position {ticker_str} to {action}"

        elif disc_type in ("ACTION_MISMATCH", "PRICE_MISMATCH", "TICKER_MISMATCH"):
            existing = self.find_open_position(analyst_name, ticker_str)
            if existing:
                act = corr_data.get("action", "TRIM")
                exit_p = float(corr_data.get("price") or corr_data.get("exit_price") or existing["entry_price"])
                self.update_position_trim_or_close(
                    position_id=existing["position_id"],
                    exit_price=exit_p,
                    status="CLOSED" if act == "EXIT" else "TRIMMED",
                    trim_ratio=float(corr_data.get("trim_ratio", 0.5)),
                    exit_message_id=audit["message_id"]
                )
                action_taken = f"Reconciled {ticker_str} to status {act} at ${exit_p}"

        now = datetime.now().isoformat()
        with conn:
            conn.execute("UPDATE reviewer_audits SET status = 'RECONCILED', updated_at = ? WHERE audit_id = ?", (now, audit_id))

        self.recalculate_analyst_stats(analyst_name)
        return {
            "status": "RECONCILED",
            "audit_id": audit_id,
            "action_taken": action_taken or f"Reconciled {ticker_str}"
        }

