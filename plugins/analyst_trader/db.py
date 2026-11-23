import json
import logging
import math
import os
import sqlite3
import time
import random
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def get_db_path() -> Path:
    """Returns the primary database path adhering to profile-aware HERMES_HOME."""
    try:
        from hermes_constants import get_hermes_home
        hermes_home = get_hermes_home()
    except Exception:
        hermes_home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))

    data_dir = hermes_home / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    new_db = data_dir / "analyst_trading.db"
    old_db = hermes_home / "analyst_trading.db"
    
    # Auto-migrate legacy root DB if present and new DB doesn't exist
    if old_db.exists() and not new_db.exists():
        try:
            import shutil
            shutil.copy2(old_db, new_db)
            logger.info("Migrated legacy DB from %s to local NVMe path %s", old_db, new_db)
        except Exception as m_err:
            logger.warning("Failed to auto-migrate legacy DB: %s", m_err)
            
    return new_db


def retry_on_db_lock(max_retries: int = 3, base_delay: float = 0.1):
    """Decorator for SQLite write operations with exponential backoff and jitter."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except sqlite3.OperationalError as e:
                    if "locked" in str(e).lower() and attempt < max_retries - 1:
                        sleep_time = base_delay * (2 ** attempt) + random.uniform(0.02, 0.08)
                        logger.warning("SQLite locked on %s (attempt %d/%d). Retrying in %.3fs...",
                                       func.__name__, attempt + 1, max_retries, sleep_time)
                        time.sleep(sleep_time)
                    else:
                        raise
        return wrapper
    return decorator


class AnalystDatabase:
    """Manages SQLite tables for analyst performance, trade signals, and dual portfolios."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path or get_db_path()
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Returns a WAL-enabled SQLite connection with busy timeout."""
        conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        return conn

    @contextmanager
    def transaction(self, max_retries: int = 3):
        """Context manager providing an atomic transaction with lock retry handling."""
        conn = self._get_connection()
        for attempt in range(max_retries):
            try:
                with conn:
                    yield conn
                break
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower() and attempt < max_retries - 1:
                    sleep_time = 0.1 * (2 ** attempt) + random.uniform(0.02, 0.08)
                    logger.warning("DB locked in transaction (attempt %d/%d). Retrying in %.3fs...",
                                   attempt + 1, max_retries, sleep_time)
                    time.sleep(sleep_time)
                else:
                    conn.close()
                    raise
        conn.close()

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
                    total_trades INTEGER DEFAULT 0,
                    preferred_direction TEXT DEFAULT 'ANY',
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

            conn.execute("""
                CREATE TABLE IF NOT EXISTS notable_flow (
                    flow_id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    asset_type TEXT NOT NULL,
                    strike REAL NOT NULL,
                    call_put TEXT NOT NULL,
                    expiration TEXT NOT NULL,
                    dte INTEGER,
                    premium_usd REAL NOT NULL,
                    premium_raw TEXT,
                    raw_message_id TEXT,
                    channel_id TEXT,
                    chart_url TEXT,
                    local_chart_path TEXT,
                    drive_archive_url TEXT,
                    is_archived INTEGER DEFAULT 0,
                    vol_to_oi_ratio REAL,
                    is_sweep INTEGER DEFAULT 0,
                    intraday_volume INTEGER,
                    initial_oi INTEGER,
                    next_day_oi INTEGER,
                    oi_delta INTEGER,
                    is_carried_over INTEGER DEFAULT 0,
                    entry_contract_price REAL,
                    current_contract_price REAL,
                    mfe_max_gain_pct REAL DEFAULT 0.0,
                    mae_max_drawdown_pct REAL DEFAULT 0.0,
                    final_outcome TEXT DEFAULT 'MONITORING',
                    gex_regime TEXT,
                    flow_score REAL,
                    llm_review_status TEXT DEFAULT 'APPROVED',
                    llm_reasoning TEXT,
                    is_quarantined INTEGER DEFAULT 0,
                    quarantine_reason TEXT,
                    trade_timestamp TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(ticker, strike, call_put, expiration, trade_timestamp)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS flow_candidate_analytics (
                    analytics_id TEXT PRIMARY KEY,
                    flow_id TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    contract_symbol TEXT,
                    flow_tier TEXT NOT NULL,
                    conviction_score REAL,
                    entry_price REAL,
                    peak_price REAL,
                    trough_price REAL,
                    mfe_pct REAL,
                    mae_pct REAL,
                    intraday_vol INTEGER,
                    initial_oi INTEGER,
                    next_day_oi INTEGER,
                    oi_change_pct REAL,
                    is_overnight_hold INTEGER DEFAULT 0,
                    is_quarantined INTEGER DEFAULT 0,
                    quarantine_reason TEXT,
                    outcome_label TEXT NOT NULL,
                    correlations_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(flow_id) REFERENCES notable_flow(flow_id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS recorded_strategies (
                    trace_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    strategy_name TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    action TEXT NOT NULL,
                    status TEXT NOT NULL,
                    directional_bias TEXT,
                    target_node REAL,
                    touch_prob_3d REAL,
                    quant_metrics_json TEXT,
                    screenshot_path TEXT,
                    source_script TEXT,
                    holding_id TEXT,
                    flow_id TEXT,
                    parent_trace_id TEXT,
                    entry_price REAL,
                    exit_price REAL,
                    quantity REAL,
                    realized_pnl REAL,
                    outcome_label TEXT,
                    payload_json TEXT,
                    timestamp TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

            # Apply safe column additions for notable_flow schema upgrades
            for col in [
                ("strategy_name", "TEXT DEFAULT 'INSTITUTIONAL_WHALE_SWEEP'"),
                ("quant_metrics_json", "TEXT"),
                ("strategy_trace_id", "TEXT"),
                ("is_quarantined", "INTEGER DEFAULT 0"),
                ("quarantine_reason", "TEXT"),
                ("quarantine_batch_id", "TEXT"),
            ]:
                try:
                    conn.execute(f"ALTER TABLE notable_flow ADD COLUMN {col[0]} {col[1]}")
                except Exception:
                    pass

            for col in [
                ("is_quarantined", "INTEGER DEFAULT 0"),
                ("quarantine_reason", "TEXT"),
                ("quarantine_batch_id", "TEXT"),
            ]:
                try:
                    conn.execute(f"ALTER TABLE flow_candidate_analytics ADD COLUMN {col[0]} {col[1]}")
                except Exception:
                    pass

            self._migrate_nullable_analytics(conn)
            from .learning_store import migrate
            migrate(conn)

            for col in [
                ("total_trades", "INTEGER DEFAULT 0"),
                ("preferred_direction", "TEXT DEFAULT 'ANY'"),
            ]:
                try:
                    conn.execute(f"ALTER TABLE analyst_styles ADD COLUMN {col[0]} {col[1]}")
                except Exception:
                    pass

            for col in [
                ("holding_id", "TEXT"),
                ("flow_id", "TEXT"),
                ("parent_trace_id", "TEXT"),
                ("entry_price", "REAL"),
                ("exit_price", "REAL"),
                ("quantity", "REAL"),
                ("realized_pnl", "REAL"),
                ("outcome_label", "TEXT"),
                ("payload_json", "TEXT"),
            ]:
                try:
                    conn.execute(f"ALTER TABLE recorded_strategies ADD COLUMN {col[0]} {col[1]}")
                except Exception:
                    pass

            # Apply safe column additions for portfolio_holdings lifecycle tracking
            for col in [
                ("status", "TEXT DEFAULT 'OPEN'"),
                ("realized_pnl", "REAL DEFAULT 0.0"),
                ("closed_at", "TEXT"),
                ("strategy_name", "TEXT DEFAULT 'INSTITUTIONAL_WHALE_SWEEP'"),
                ("target_tp1", "REAL"),
                ("target_tp2", "REAL"),
                ("target_sl", "REAL"),
                ("flow_id", "TEXT"),
                ("occ_symbol", "TEXT"),
                ("contracts_trimmed", "REAL DEFAULT 0.0"),
                ("outcome_label", "TEXT"),
            ]:
                try:
                    conn.execute(f"ALTER TABLE portfolio_holdings ADD COLUMN {col[0]} {col[1]}")
                except Exception:
                    pass

            try:
                conn.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_portfolio_holdings_unique_flow
                    ON portfolio_holdings (portfolio_id, flow_id)
                    WHERE flow_id IS NOT NULL AND flow_id != ''
                """)
            except Exception:
                pass

    @staticmethod
    def _migrate_nullable_analytics(conn: sqlite3.Connection) -> None:
        """Relax only observation constraints, preserving stored values and indexes."""
        import re
        nullable = {'contract_symbol', 'conviction_score', 'entry_price', 'peak_price',
                    'trough_price', 'mfe_pct', 'mae_pct'}
        columns = list(conn.execute('PRAGMA table_info(flow_candidate_analytics)'))
        required = [row[1] for row in columns if row[1] in nullable and row[3]]
        if not required:
            return
        sql = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='flow_candidate_analytics'").fetchone()[0]
        new_sql = re.sub(r'(?i)CREATE TABLE\s+(?:IF NOT EXISTS\s+)?[\"`]?flow_candidate_analytics[\"`]?',
                         'CREATE TABLE flow_candidate_analytics_nullable', sql, count=1)
        for field in required:
            new_sql, count = re.subn(r'(?i)\b' + field + r'\s+(TEXT|REAL)\s+NOT\s+NULL\b',
                                     lambda m: field + ' ' + m.group(1), new_sql)
            if count != 1:
                raise ValueError('Unrecognized analytics schema; explicit migration required')
        objects = [row[0] for row in conn.execute("SELECT sql FROM sqlite_master WHERE tbl_name='flow_candidate_analytics' AND type IN ('index','trigger') AND sql IS NOT NULL")]
        names = ','.join('"' + row[1].replace('"', '""') + '"' for row in columns)
        conn.execute('SAVEPOINT nullable_analytics')
        try:
            conn.execute(new_sql)
            conn.execute(f'INSERT INTO flow_candidate_analytics_nullable ({names}) SELECT {names} FROM flow_candidate_analytics')
            conn.execute('DROP TABLE flow_candidate_analytics')
            conn.execute('ALTER TABLE flow_candidate_analytics_nullable RENAME TO flow_candidate_analytics')
            for statement in objects:
                conn.execute(statement)
            conn.execute('RELEASE nullable_analytics')
        except Exception:
            conn.execute('ROLLBACK TO nullable_analytics')
            conn.execute('RELEASE nullable_analytics')
            raise

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

    def save_learning_version(self, snapshot):
        from .learning_store import save_version
        return save_version(self, snapshot)

    def get_learning_version(self, version_id, decision_at=None):
        from .learning_store import get_version
        return get_version(self, version_id, decision_at)

    def save_analyst_style(self, analyst_name: str, preferred_tickers: List[str],
                           avg_holding_hours: Optional[float], win_rate: float, avg_roi_pct: float,
                           preferred_dte_min: Optional[int], preferred_dte_max: Optional[int],
                           strategy_summary: str, rules: Dict[str, Any],
                           total_trades: int = 0, preferred_direction: str = "ANY") -> None:
        conn = self._get_connection()
        now = datetime.now().isoformat()
        with conn:
            conn.execute("""
                INSERT INTO analyst_styles (
                    analyst_name, preferred_tickers, avg_holding_hours, win_rate,
                    avg_roi_pct, preferred_dte_min, preferred_dte_max, strategy_summary,
                    rules_json, total_trades, preferred_direction, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(analyst_name) DO UPDATE SET
                    preferred_tickers=excluded.preferred_tickers,
                    avg_holding_hours=excluded.avg_holding_hours,
                    win_rate=excluded.win_rate,
                    avg_roi_pct=excluded.avg_roi_pct,
                    preferred_dte_min=excluded.preferred_dte_min,
                    preferred_dte_max=excluded.preferred_dte_max,
                    strategy_summary=excluded.strategy_summary,
                    rules_json=excluded.rules_json,
                    total_trades=excluded.total_trades,
                    preferred_direction=excluded.preferred_direction,
                    updated_at=excluded.updated_at
            """, (analyst_name, json.dumps(preferred_tickers), avg_holding_hours, win_rate,
                  avg_roi_pct, preferred_dte_min, preferred_dte_max, strategy_summary,
                  json.dumps(rules), total_trades, preferred_direction, now))

    def get_analyst_style(self, analyst_name: str) -> Optional[Dict[str, Any]]:
        """Fetch style profile for a specific analyst."""
        conn = self._get_connection()
        cur = conn.execute("SELECT * FROM analyst_styles WHERE analyst_name = ?", (analyst_name,))
        row = cur.fetchone()
        if not row:
            return None
        res = dict(row)
        if res.get("preferred_tickers"):
            try:
                res["preferred_tickers"] = json.loads(res["preferred_tickers"])
            except Exception:
                pass
        if res.get("rules_json"):
            try:
                res["rules_json"] = json.loads(res["rules_json"])
            except Exception:
                pass
        return res

    def list_analyst_styles(self) -> List[Dict[str, Any]]:
        """Fetch all stored analyst styles."""
        conn = self._get_connection()
        cur = conn.execute("SELECT * FROM analyst_styles ORDER BY win_rate DESC")
        rows = []
        for r in cur.fetchall():
            item = dict(r)
            if item.get("preferred_tickers"):
                try:
                    item["preferred_tickers"] = json.loads(item["preferred_tickers"])
                except Exception:
                    pass
            if item.get("rules_json"):
                try:
                    item["rules_json"] = json.loads(item["rules_json"])
                except Exception:
                    pass
            rows.append(item)
        return rows

    def save_flow_candidate_analytics(self, analytics: Dict[str, Any]) -> None:
        """Upsert a flow candidate analytics record."""
        conn = self._get_connection()
        now = datetime.now().isoformat()
        analytics_id = analytics.get("analytics_id") or f"fca_{analytics['flow_id']}"
        correlations_json = analytics.get("correlations_json", "{}")
        if isinstance(correlations_json, dict):
            correlations_json = json.dumps(correlations_json)
        
        with conn:
            conn.execute('BEGIN IMMEDIATE')
            existing = conn.execute('SELECT flow_id FROM flow_candidate_analytics WHERE analytics_id=?', (analytics_id,)).fetchone()
            if existing and existing['flow_id'] != analytics.get('flow_id', ''):
                raise ValueError('ANALYTICS_SOURCE_ID_CONFLICT')
            conn.execute("""
                INSERT INTO flow_candidate_analytics (
                    analytics_id, flow_id, ticker, contract_symbol, flow_tier,
                    conviction_score, entry_price, peak_price, trough_price,
                    mfe_pct, mae_pct, intraday_vol, initial_oi, next_day_oi,
                    oi_change_pct, is_overnight_hold, outcome_label,
                    correlations_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(analytics_id) DO UPDATE SET
                    flow_id=excluded.flow_id,
                    ticker=excluded.ticker,
                    contract_symbol=excluded.contract_symbol,
                    flow_tier=excluded.flow_tier,
                    conviction_score=excluded.conviction_score,
                    entry_price=excluded.entry_price,
                    peak_price=excluded.peak_price,
                    trough_price=excluded.trough_price,
                    mfe_pct=excluded.mfe_pct,
                    mae_pct=excluded.mae_pct,
                    intraday_vol=excluded.intraday_vol,
                    initial_oi=excluded.initial_oi,
                    next_day_oi=excluded.next_day_oi,
                    oi_change_pct=excluded.oi_change_pct,
                    is_overnight_hold=excluded.is_overnight_hold,
                    outcome_label=excluded.outcome_label,
                    correlations_json=excluded.correlations_json,
                    updated_at=excluded.updated_at
            """, (
                analytics_id,
                analytics.get("flow_id", ""),
                analytics.get("ticker", ""),
                analytics.get("contract_symbol", ""),
                analytics.get("flow_tier", ""),
                float(analytics['conviction_score']) if analytics.get('conviction_score') is not None else None,
                float(analytics['entry_price']) if analytics.get('entry_price') is not None else None,
                float(analytics['peak_price']) if analytics.get('peak_price') is not None else None,
                float(analytics['trough_price']) if analytics.get('trough_price') is not None else None,
                float(analytics['mfe_pct']) if analytics.get('mfe_pct') is not None else None,
                float(analytics['mae_pct']) if analytics.get('mae_pct') is not None else None,
                int(analytics['intraday_vol']) if analytics.get('intraday_vol') is not None else None,
                int(analytics['initial_oi']) if analytics.get('initial_oi') is not None else None,
                int(analytics['next_day_oi']) if analytics.get('next_day_oi') is not None else None,
                float(analytics['oi_change_pct']) if analytics.get('oi_change_pct') is not None else None,
                int(analytics['is_overnight_hold']) if analytics.get('is_overnight_hold') is not None else None,
                analytics.get("outcome_label", "MONITORING"),
                correlations_json,
                analytics.get("created_at", now),
                now
            ))

    def list_flow_candidate_analytics(self, limit: int = 100, ticker: Optional[str] = None) -> List[Dict[str, Any]]:
        """Query flow candidate analytics records."""
        conn = self._get_connection()
        if ticker:
            cur = conn.execute(
                "SELECT * FROM flow_candidate_analytics WHERE ticker = ? AND (is_quarantined = 0 OR is_quarantined IS NULL) AND NOT EXISTS (SELECT 1 FROM notable_flow n WHERE n.flow_id=flow_candidate_analytics.flow_id AND COALESCE(n.is_quarantined,0) != 0) ORDER BY updated_at DESC LIMIT ?",
                (ticker.upper(), limit)
            )
        else:
            cur = conn.execute(
                "SELECT * FROM flow_candidate_analytics WHERE (is_quarantined = 0 OR is_quarantined IS NULL) AND NOT EXISTS (SELECT 1 FROM notable_flow n WHERE n.flow_id=flow_candidate_analytics.flow_id AND COALESCE(n.is_quarantined,0) != 0) ORDER BY updated_at DESC LIMIT ?",
                (limit,)
            )
        rows = []
        for r in cur.fetchall():
            item = dict(r)
            if item.get("correlations_json"):
                try:
                    item["correlations_json"] = json.loads(item["correlations_json"])
                except Exception:
                    pass
            rows.append(item)
        return rows

    def save_recorded_strategy(self, strategy_dict: Dict[str, Any], *, connection=None) -> str:
        """Append one event, ACK exact replay, and reject conflicting identity.

        Timestamp/created_at are storage metadata, not retry identity. All semantic
        columns and the full payload are compared under the same SQLite lock.
        """
        now = datetime.now(timezone.utc).isoformat()
        defaults = {'event_type': 'strategy_execution', 'strategy_name': 'INSTITUTIONAL_WHALE_SWEEP',
                    'action': 'EVALUATE', 'status': 'SUCCESS', 'source_script': 'strategy_logger'}
        fields = ('trace_id', 'event_type', 'strategy_name', 'ticker', 'action', 'status',
                  'directional_bias', 'target_node', 'touch_prob_3d', 'quant_metrics_json',
                  'screenshot_path', 'source_script', 'holding_id', 'flow_id', 'parent_trace_id',
                  'entry_price', 'exit_price', 'quantity', 'realized_pnl', 'outcome_label', 'payload_json')
        record = {key: strategy_dict.get(key, defaults.get(key)) for key in fields}
        if not isinstance(record['trace_id'], str) or not record['trace_id']:
            raise ValueError('Explicit nonempty event identity required')
        record['ticker'] = strategy_dict['ticker'].upper().strip()
        for key in ('target_node', 'touch_prob_3d', 'entry_price', 'exit_price', 'quantity', 'realized_pnl'):
            if record[key] is not None:
                if isinstance(record[key], bool):
                    raise ValueError('Boolean numeric event field: ' + key)
                record[key] = float(record[key])
                if not math.isfinite(record[key]):
                    raise ValueError('Non-finite event field: ' + key)
        def canonical_json(value):
            if value is None:
                return None
            if isinstance(value, str):
                value = json.loads(value)
            return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)
        for key in ('quant_metrics_json', 'payload_json'):
            record[key] = canonical_json(record[key])
        conn = connection if connection is not None else self._get_connection()
        owns_transaction = connection is None
        try:
            if owns_transaction:
                conn.execute('BEGIN IMMEDIATE')
            elif not conn.in_transaction:
                raise ValueError('Journal requires active caller transaction')
            previous = conn.execute('SELECT * FROM recorded_strategies WHERE trace_id=?', (record['trace_id'],)).fetchone()
            if previous:
                old = dict(previous)
                for key in ('quant_metrics_json', 'payload_json'):
                    old[key] = canonical_json(old[key])
                if any(old.get(key) != record[key] for key in fields):
                    raise ValueError('EVENT_ID_CONFLICT: ' + record['trace_id'])
                if owns_transaction:
                    conn.commit()
                return previous['trace_id']
            columns = ','.join(fields) + ',timestamp,created_at'
            placeholders = ','.join('?' for _ in range(len(fields) + 2))
            conn.execute(f'INSERT INTO recorded_strategies ({columns}) VALUES ({placeholders})',
                         (*[record[key] for key in fields], strategy_dict.get('timestamp', now), now))
            if owns_transaction:
                conn.commit()
            return record['trace_id']
        except Exception:
            if owns_transaction:
                conn.rollback()
            raise
        finally:
            if owns_transaction:
                conn.close()

    def list_recorded_strategies(
        self,
        limit: int = 100,
        ticker: Optional[str] = None,
        strategy_name: Optional[str] = None,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Query recorded strategy execution traces."""
        conn = self._get_connection()
        where_clauses = ["1=1"]
        params: List[Any] = []
        if ticker:
            where_clauses.append("ticker = ?")
            params.append(ticker.upper().strip())
        if strategy_name:
            where_clauses.append("strategy_name = ?")
            params.append(strategy_name.strip())
        
        where_str = " AND ".join(where_clauses)
        cur = conn.execute(
            f"SELECT * FROM recorded_strategies WHERE {where_str} ORDER BY timestamp DESC, trace_id DESC LIMIT ? OFFSET ?",
            (*params, limit, offset)
        )
        rows = []
        for r in cur.fetchall():
            item = dict(r)
            if item.get("quant_metrics_json"):
                try:
                    item["quant_metrics_json"] = json.loads(item["quant_metrics_json"])
                except Exception:
                    pass
            rows.append(item)
        return rows

    def add_portfolio_holding(
        self,
        holding_id: str,
        portfolio_id: str,
        ticker: str,
        asset_type: str,
        direction: str,
        quantity: float,
        entry_price: float,
        strike: Optional[float] = None,
        expiration: Optional[str] = None,
        strategy_name: str = "INSTITUTIONAL_WHALE_SWEEP",
        target_tp1: Optional[float] = None,
        target_tp2: Optional[float] = None,
        target_sl: Optional[float] = None,
        flow_id: Optional[str] = None,
        occ_symbol: Optional[str] = None,
        status: str = "OPEN",
    ) -> Dict[str, Any]:
        from .execution_contract import number, quantity as checked_quantity
        if portfolio_id == 'autonomous_ai':
            raise ValueError('Autonomous economics require journaled execution caller')
        checked_quantity(quantity, asset_type)
        number(entry_price, 'entry')
        number(entry_price * quantity * (100 if asset_type == 'option' else 1), 'notional')
        for value in (target_tp1, target_tp2, target_sl):
            if value is not None: number(value, 'target')
        conn = self._get_connection()
        now = datetime.now().isoformat()
        mkt_val = entry_price * quantity * (100.0 if asset_type == "option" else 1.0)
        with conn:
            conn.execute("""
                INSERT INTO portfolio_holdings (
                    holding_id, portfolio_id, ticker, asset_type, direction,
                    quantity, average_cost, current_price, market_value, unrealized_pnl,
                    strike, expiration, created_at, updated_at,
                    status, realized_pnl, strategy_name, target_tp1, target_tp2, target_sl, flow_id, occ_symbol, contracts_trimmed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0.0, ?, ?, ?, ?, ?, 0.0, ?, ?, ?, ?, ?, ?, 0.0)
            """, (
                holding_id, portfolio_id, ticker, asset_type, direction,
                quantity, entry_price, entry_price, mkt_val, strike, expiration, now, now,
                status, strategy_name, target_tp1, target_tp2, target_sl, flow_id, occ_symbol
            ))
        cur = conn.execute("SELECT * FROM portfolio_holdings WHERE holding_id = ?", (holding_id,))
        return dict(cur.fetchone())

    def get_portfolio_holding(self, holding_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single portfolio holding by holding_id."""
        conn = self._get_connection()
        cur = conn.execute("SELECT * FROM portfolio_holdings WHERE holding_id = ?", (holding_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def trim_portfolio_holding(
        self,
        holding_id: str,
        trim_qty: float,
        trim_price: float,
        realized_pnl: float,
        new_sl: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        from .execution_contract import number, quantity as checked_quantity
        number(trim_price, 'trim price')
        number(realized_pnl, 'pnl', signed=True, zero=True)
        conn = self._get_connection()
        cur = conn.execute("SELECT * FROM portfolio_holdings WHERE holding_id = ?", (holding_id,))
        row = cur.fetchone()
        if not row:
            return None
        h = dict(row)
        now = datetime.now().isoformat()
        if h['portfolio_id'] == 'autonomous_ai':
            raise ValueError('Autonomous economics require journaled execution caller')
        qty = checked_quantity(h['quantity'], h['asset_type'])
        checked_quantity(trim_qty, h['asset_type'])
        if trim_qty > qty: raise ValueError('Overtrim')
        remaining_qty = qty - trim_qty
        multiplier = 100.0 if h.get("asset_type") == "option" else 1.0
        new_market_val = trim_price * remaining_qty * multiplier
        entry_p = float(h.get("average_cost") or trim_price)
        is_short = (h.get("asset_type") != "option" and h.get("direction") in ("short", "sell"))
        unrealized = ((entry_p - trim_price) if is_short else (trim_price - entry_p)) * remaining_qty * multiplier
        new_status = "CLOSED" if remaining_qty <= 0 else "TRIMMED"
        target_sl = new_sl if new_sl is not None else h.get("target_sl")

        with conn:
            conn.execute("""
                UPDATE portfolio_holdings SET
                    quantity = ?,
                    contracts_trimmed = contracts_trimmed + ?,
                    realized_pnl = realized_pnl + ?,
                    current_price = ?,
                    market_value = ?,
                    unrealized_pnl = ?,
                    status = ?,
                    target_sl = ?,
                    updated_at = ?
                WHERE holding_id = ?
            """, (remaining_qty, trim_qty, realized_pnl, trim_price, new_market_val, unrealized, new_status, target_sl, now, holding_id))

        cur = conn.execute("SELECT * FROM portfolio_holdings WHERE holding_id = ?", (holding_id,))
        return dict(cur.fetchone())

    def close_portfolio_holding(
        self,
        holding_id: str,
        exit_price: float,
        realized_pnl: float,
        outcome_label: str = "CLOSED",
    ) -> Optional[Dict[str, Any]]:
        from .execution_contract import number
        number(exit_price, 'exit price')
        number(realized_pnl, 'pnl', signed=True, zero=True)
        conn = self._get_connection()
        cur = conn.execute("SELECT * FROM portfolio_holdings WHERE holding_id = ?", (holding_id,))
        row = cur.fetchone()
        if not row:
            return None
        if row['portfolio_id'] == 'autonomous_ai':
            raise ValueError('Autonomous economics require journaled execution caller')
        now = datetime.now().isoformat()
        with conn:
            conn.execute("""
                UPDATE portfolio_holdings SET
                    quantity = 0.0,
                    current_price = ?,
                    market_value = 0.0,
                    unrealized_pnl = 0.0,
                    realized_pnl = realized_pnl + ?,
                    status = 'CLOSED',
                    outcome_label = ?,
                    closed_at = ?,
                    updated_at = ?
                WHERE holding_id = ?
            """, (exit_price, realized_pnl, outcome_label, now, now, holding_id))

        cur = conn.execute("SELECT * FROM portfolio_holdings WHERE holding_id = ?", (holding_id,))
        return dict(cur.fetchone())

    def update_holding_market_price(self, holding_id: str, current_price: float, *, _connection=None) -> Optional[Dict[str, Any]]:
        """Research mark, not an executable quote; holding and stored equity share a lock."""
        from .execution_contract import number, quantity, validate_amounts, money, money_sum
        price = number(current_price, 'market price')
        conn = _connection if _connection is not None else self._get_connection()
        owns = _connection is None
        try:
            if owns: conn.execute('BEGIN IMMEDIATE')
            row = conn.execute('SELECT * FROM portfolio_holdings WHERE holding_id=?',(holding_id,)).fetchone()
            if row is None: return None
            h = dict(row)
            if h['status']=='CLOSED': return h
            qty = quantity(h['quantity'], h['asset_type'])
            entry = number(h['average_cost'],'entry')
            multiplier = 100 if h['asset_type']=='option' else 1
            value = money(price, qty, multiplier)
            short = h['asset_type']!='option' and h['direction'] in ('short','sell')
            pnl = money(price, qty, multiplier, basis=entry) * (-1 if short else 1)
            validate_amounts(market_value=value, unrealized=pnl)
            now = datetime.now().isoformat()
            conn.execute('UPDATE portfolio_holdings SET current_price=?,market_value=?,unrealized_pnl=?,last_price_updated_at=?,updated_at=? WHERE holding_id=?',(price,value,pnl,now,now,holding_id))
            p = conn.execute('SELECT cash_balance FROM portfolios WHERE portfolio_id=?',(h['portfolio_id'],)).fetchone()
            if p is None: raise ValueError('Missing portfolio')
            cash = number(p[0],'cash',zero=True)
            values = conn.execute("SELECT COALESCE(SUM(market_value),0),COALESCE(SUM(unrealized_pnl),0) FROM portfolio_holdings WHERE portfolio_id=? AND status IN ('OPEN','TRIMMED')",(h['portfolio_id'],)).fetchone()
            total = money_sum(cash, values[0])
            validate_amounts(equity=total,unrealized=values[1])
            conn.execute('UPDATE portfolios SET total_value=?,unrealized_pnl=?,updated_at=? WHERE portfolio_id=?',(total,values[1],now,h['portfolio_id']))
            if owns: conn.commit()
            return dict(conn.execute('SELECT * FROM portfolio_holdings WHERE holding_id=?',(holding_id,)).fetchone())
        except Exception:
            if owns: conn.rollback()
            raise
        finally:
            if owns: conn.close()

    def update_portfolio_balance(self, portfolio_id: str, cash_delta: float = 0.0, realized_pnl_delta: float = 0.0) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        p = self.get_portfolio(portfolio_id)
        if not p:
            return {}
        now = datetime.now().isoformat()
        current_cash = float(p.get("cash_balance") if p.get("cash_balance") is not None else 100000.0)
        new_cash = current_cash + cash_delta
        new_pnl = float(p.get("realized_pnl") if p.get("realized_pnl") is not None else 0.0) + realized_pnl_delta

        active_holdings = self.list_portfolio_holdings(portfolio_id, status="ACTIVE")
        open_market_val = sum(float(h.get("market_value") or 0.0) for h in active_holdings)
        tot_val = new_cash + open_market_val

        with conn:
            conn.execute("""
                UPDATE portfolios SET cash_balance = ?, realized_pnl = ?, total_value = ?, updated_at = ?
                WHERE portfolio_id = ?
            """, (new_cash, new_pnl, tot_val, now, portfolio_id))
        return self.get_portfolio(portfolio_id)

    def list_portfolio_holdings(self, portfolio_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        if status and status.upper() != "ALL":
            if status.upper() == "ACTIVE":
                cur = conn.execute(
                    "SELECT * FROM portfolio_holdings WHERE portfolio_id = ? AND status IN ('OPEN', 'TRIMMED') ORDER BY created_at DESC",
                    (portfolio_id,),
                )
            else:
                cur = conn.execute(
                    "SELECT * FROM portfolio_holdings WHERE portfolio_id = ? AND UPPER(status) = ? ORDER BY created_at DESC",
                    (portfolio_id, status.upper()),
                )
        else:
            cur = conn.execute(
                "SELECT * FROM portfolio_holdings WHERE portfolio_id = ? ORDER BY created_at DESC",
                (portfolio_id,),
            )
        return [dict(r) for r in cur.fetchall()]

    def get_portfolio_stats(self, portfolio_id: str) -> Dict[str, Any]:
        from .holding_statistics import statistics, finite
        view = statistics(self, portfolio_id)
        stats = view['total']
        conn = self._get_connection()
        try:
            row = conn.execute('SELECT * FROM portfolios WHERE portfolio_id=?', (portfolio_id,)).fetchone()
        finally:
            conn.close()
        portfolio = dict(row) if row else {}
        cash = portfolio.get('cash_balance')
        cash = cash if finite(cash) else None
        active = [h for h in view['holdings'] if h['holding_status'] in ('OPEN', 'TRIMMED')]
        known_marks = all(finite(h.get('estimated_market_value')) for h in active)
        market = sum(h['estimated_market_value'] for h in active) if known_marks else None
        return dict(portfolio_id=portfolio_id, name=portfolio.get('name', portfolio_id),
            cash_balance=cash, cash_as_of=portfolio.get('updated_at'),
            total_value=cash+market if cash is not None and market is not None else None,
            open_market_value=market, valuation_status=('unknown' if not known_marks else
                'stale_estimated_nonexecutable' if stats['stale_mark_count'] else
                'estimated_nonexecutable') if active else 'stored_paper_cash',
            unknown_mark_count=stats['unknown_mark_count'], stale_mark_count=stats['stale_mark_count'],
            mark_policy=stats['mark_policy'],
            realized_pnl=stats['gross_realized_pnl'], realized_pnl_basis='gross_before_unknown_costs',
            net_realized_pnl=stats['net_realized_pnl'], unrealized_pnl=stats['estimated_unrealized_pnl'],
            total_return_pct=None, active_positions_count=stats['open_count'],
            closed_positions_count=stats['closed_count'], winning_positions_count=stats['gross_wins'],
            win_rate_pct=stats['gross_win_rate_pct'], statistics=view,
            as_of=view['as_of'], mode='paper', performance_status='descriptive_not_validated')

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

    def update_position_trim_or_close(self, position_id: str, exit_price: Optional[float] = None,
                                       status: str = "TRIMMED", trim_ratio: float = 0.5,
                                       exit_message_id: Optional[str] = None,
                                       exit_time: Optional[str] = None,
                                       gain_per_con: Optional[float] = None) -> Dict[str, Any]:
        """Update position status when trimmed or closed, computing gain_per_con if provided."""
        conn = self._get_connection()
        pos = self.get_position(position_id)
        if not pos:
            raise ValueError(f"Position {position_id} not found")

        now = datetime.now().isoformat()
        t_exit = exit_time or now
        entry_p = float(pos["entry_price"])

        if gain_per_con is not None and entry_p > 0:
            exit_price = round(entry_p + (gain_per_con / 100.0), 2)
        elif exit_price is None or exit_price <= 0:
            exit_price = entry_p
        current_weight = float(pos["contracts_or_shares"])
        current_realized_pnl = float(pos.get("realized_pnl") or 0.0)

        multiplier = 100.0 if pos["asset_type"] == "option" else 1.0

        if status == "CLOSED" or trim_ratio >= 0.85 or current_weight * (1.0 - trim_ratio) <= 0.05:
            final_status = "CLOSED"
            trimmed_w = current_weight
            remaining_w = 0.0
        else:
            final_status = "TRIMMED"
            trimmed_w = round(current_weight * trim_ratio, 3)
            remaining_w = round(current_weight - trimmed_w, 3)

        if pos.get("asset_type") == "option" or pos["direction"] in ("call", "long"):
            segment_pnl = (exit_price - entry_p) * trimmed_w * multiplier
        else:
            segment_pnl = (entry_p - exit_price) * trimmed_w * multiplier

        new_realized_pnl = current_realized_pnl + segment_pnl
        curr_p = exit_price

        # Blended ROI % across all closed tranches (weighted average return)
        closed_cost_basis = entry_p * (1.0 - remaining_w) * multiplier
        if closed_cost_basis > 0:
            roi_pct = (new_realized_pnl / closed_cost_basis) * 100.0
        elif entry_p > 0:
            roi_pct = ((exit_price - entry_p) / entry_p) * 100.0
        else:
            roi_pct = 0.0

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

        # Log trade event record for trim/close tracking
        event_kind = "CLOSE" if final_status == "CLOSED" else "TRIM"
        self.log_trade_event(
            position_id=position_id,
            analyst_name=pos["analyst_name"],
            message_id=exit_message_id or f"msg_trim_{now}",
            event_type=event_kind,
            ticker=pos["ticker"],
            price=exit_price,
            details={"trim_ratio": trim_ratio, "quantity": trimmed_w,
                     "cost_basis": entry_p * trimmed_w * multiplier,
                     "segment_pnl": segment_pnl, "roi_pct": round(roi_pct, 2)},
            timestamp=t_exit
        )

        if final_status == "CLOSED":
            self.recalculate_analyst_stats(pos["analyst_name"])

        return self.get_position(position_id) or {}

    def log_trade_event(self, position_id: str, analyst_name: str, message_id: str,
                        event_type: str, ticker: str, price: Optional[float] = None,
                        details: Optional[Dict[str, Any]] = None,
                        timestamp: Optional[str] = None) -> None:
        conn = self._get_connection()
        now = datetime.now().isoformat()
        ts = timestamp or now
        details_str = json.dumps(details) if details else None

        with conn:
            if message_id:
                check = conn.execute(
                    "SELECT 1 FROM trade_events WHERE position_id = ? AND message_id = ? AND event_type = ?",
                    (position_id, message_id, event_type)
                ).fetchone()
                if check:
                    return
            conn.execute("""
                INSERT INTO trade_events (position_id, analyst_name, message_id, event_type, ticker, price, details_json, timestamp, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (position_id, analyst_name, message_id, event_type, ticker, price, details_str, ts, now))

    def recalculate_position_from_events(self, position_id: str) -> Dict[str, Any]:
        """Recalculate position status, blended exit price, and blended ROI % strictly from verified trade_events."""
        conn = self._get_connection()
        pos = self.get_position(position_id)
        if not pos:
            return {}

        cur = conn.execute(
            "SELECT * FROM trade_events WHERE position_id = ? AND event_type IN ('TRIM', 'CLOSE') ORDER BY created_at ASC",
            (position_id,)
        )
        events = [dict(r) for r in cur.fetchall()]
        entry_p = float(pos.get("entry_price") or 0.0)
        direction = pos.get("direction", "call")
        is_option = pos.get("asset_type") == "option"

        if not events:
            with conn:
                conn.execute(
                    "UPDATE positions SET status = 'OPEN', contracts_or_shares = 1.0, exit_price = NULL, roi_pct = 0.0 WHERE position_id = ?",
                    (position_id,)
                )
            return self.get_position(position_id) or {}

        gains = []
        prices = []
        has_close = False
        for ev in events:
            ev_price = float(ev.get("price") or 0.0)
            if ev_price <= 0:
                continue
            prices.append(ev_price)
            if is_option or direction in ("call", "long"):
                gain = ((ev_price - entry_p) / entry_p * 100.0) if entry_p > 0 else 0.0
            else:
                gain = ((entry_p - ev_price) / entry_p * 100.0) if entry_p > 0 else 0.0
            gains.append(gain)
            if ev.get("event_type") == "CLOSE":
                has_close = True

        if gains:
            blended_roi = round(sum(gains) / len(gains), 2)
            blended_exit = round(sum(prices) / len(prices), 2)
        else:
            blended_roi = 0.0
            blended_exit = entry_p

        final_status = "CLOSED" if (has_close or len(gains) >= 3) else "TRIMMED"
        rem_weight = 0.0 if final_status == "CLOSED" else round(max(0.0, 1.0 - (len(gains) * 0.25)), 2)

        with conn:
            conn.execute("""
                UPDATE positions
                SET status = ?,
                    exit_price = ?,
                    roi_pct = ?,
                    contracts_or_shares = ?,
                    updated_at = ?
                WHERE position_id = ?
            """, (final_status, blended_exit, blended_roi, rem_weight, datetime.now().isoformat(), position_id))

        return self.get_position(position_id) or {}

    def list_positions(self, analyst_name: Optional[str] = None, status: Optional[str] = None, timeframe: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
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
        if limit and int(limit) > 0:
            query += f" LIMIT {int(limit)}"
        cur = conn.execute(query, params)
        raw_positions = [dict(r) for r in cur.fetchall()]

        # Fetch trade_events to build explicit trim history per position
        pos_ids = [p["position_id"] for p in raw_positions]
        events_by_pos: Dict[str, List[Dict[str, Any]]] = {}
        if pos_ids:
            placeholders = ",".join("?" for _ in pos_ids)
            e_cur = conn.execute(f"SELECT * FROM trade_events WHERE position_id IN ({placeholders}) ORDER BY created_at ASC", pos_ids)
            for row in e_cur.fetchall():
                e_dict = dict(row)
                events_by_pos.setdefault(e_dict["position_id"], []).append(e_dict)

        positions = []
        for p in raw_positions:
            p_id = p["position_id"]
            p_events = events_by_pos.get(p_id, [])
            entry_p = float(p.get("entry_price") or 0.0)
            direction = p.get("direction", "call")

            seen_trims = set()
            trims = []
            for ev in p_events:
                if ev.get("event_type") in ("TRIM", "CLOSE"):
                    ev_price = float(ev.get("price") or 0.0)
                    msg_id = ev.get("message_id") or ""
                    dedup_key = (ev.get("event_type"), msg_id, ev_price)
                    if dedup_key in seen_trims:
                        continue
                    seen_trims.add(dedup_key)
                    if entry_p > 0 and ev_price > 0:
                        gain_pct = ((ev_price - entry_p) / entry_p * 100.0) if (p.get("asset_type") == "option" or direction in ("call", "long")) else ((entry_p - ev_price) / entry_p * 100.0)
                    else:
                        gain_pct = 0.0
                    try:
                        details = json.loads(ev.get('details_json') or '{}')
                        ev_qty = details.get('quantity') if isinstance(details, dict) else None
                    except (ValueError, TypeError):
                        ev_qty = None
                    # Older events do not contain quantities. Do not invent equal weights.
                    if isinstance(ev_qty, bool) or not isinstance(ev_qty, (int, float)) or not math.isfinite(ev_qty) or ev_qty <= 0:
                        ev_qty = None
                    trims.append({
                        "event_type": ev.get("event_type"),
                        "price": ev_price,
                        "quantity": ev_qty,
                        "gain_pct": round(gain_pct, 2),
                        "timestamp": ev.get("timestamp") or ev.get("created_at")
                    })

            # Fallback: if no trade_events exist but position status is TRIMMED or CLOSED and exit_price is present
            if not trims and p.get("exit_price") and p.get("status") in ("TRIMMED", "CLOSED"):
                ex_price = float(p["exit_price"])
                if entry_p > 0:
                    gain_pct = ((ex_price - entry_p) / entry_p * 100.0) if (p.get("asset_type") == "option" or direction in ("call", "long")) else ((entry_p - ex_price) / entry_p * 100.0)
                else:
                    gain_pct = float(p.get("roi_pct") or 0.0)
                trims.append({
                    "event_type": p["status"],
                    "price": ex_price,
                    "quantity": None,  # No tranche evidence; not an equal-weight fill.
                    "gain_pct": round(gain_pct, 2),
                    "timestamp": p.get("exit_time") or p.get("updated_at")
                })

            # Accessors never rewrite stored economics. Weighted exit is additional
            # descriptive metadata and unavailable for incomplete legacy histories.
            p['weighted_exit_price'] = None
            if trims and all(t.get('quantity') is not None for t in trims):
                total_qty = sum(t['quantity'] for t in trims)
                p['weighted_exit_price'] = round(sum(t['price'] * t['quantity'] for t in trims) / total_qty, 4)

            p["trims"] = trims
            p["events"] = p_events
            positions.append(p)

        return positions


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
                  orig_str, corr_str, confidence_score, reasoning, status, now, now))

        cur = conn.execute("SELECT * FROM reviewer_audits WHERE audit_id = ?", (audit_id,))
        return dict(cur.fetchone())

    def list_reviewer_audits(self, analyst_name: Optional[str] = None, status: Optional[str] = None, ticker: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """List recorded reviewer audits with joined raw message content."""
        conn = self._get_connection()
        query = """
            SELECT a.*, r.content, r.embeds_json, r.channel_name, r.timestamp as raw_timestamp
            FROM reviewer_audits a
            LEFT JOIN raw_messages r ON a.message_id = r.message_id
            WHERE 1=1
        """
        params: List[Any] = []
        if analyst_name:
            query += " AND a.analyst_name = ?"
            params.append(analyst_name)
        if status:
            query += " AND a.status = ?"
            params.append(status)
        if ticker:
            query += " AND (a.ticker = ? OR a.original_data_json LIKE ?)"
            params.append(ticker)
            params.append(f'%"{ticker}"%')

        query += " ORDER BY CASE WHEN a.ticker IS NOT NULL AND a.ticker != '' THEN 0 ELSE 1 END, a.created_at DESC LIMIT ?"
        params.append(limit)

        cur = conn.execute(query, params)
        results = []
        for r in cur.fetchall():
            row = dict(r)
            content = row.get("content") or ""
            embeds_json = row.get("embeds_json") or ""
            raw_text = content
            if embeds_json and embeds_json != "[]":
                try:
                    embeds = json.loads(embeds_json)
                    parts = []
                    for e in embeds:
                        t = e.get("title", "")
                        d = e.get("description", "")
                        if t or d:
                            parts.append(f"{t} {d}".strip())
                    if parts:
                        raw_text = " | ".join(parts)
                except Exception:
                    pass
            row["raw_text"] = raw_text
            results.append(row)
        return results

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
                    self.recalculate_position_from_events(existing["position_id"])
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
                self.recalculate_position_from_events(existing["position_id"])
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

    def save_notable_flow(self, flow_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Insert or update a notable flow trade while strictly preserving quarantine state and resolved outcomes."""
        conn = self._get_connection()
        now = datetime.now().isoformat()
        flow_id = flow_dict.get("flow_id") or f"flow_{flow_dict['ticker']}_{flow_dict.get('trade_timestamp', now)}"
        quant_json = flow_dict.get("quant_metrics_json")
        if isinstance(quant_json, (dict, list)):
            quant_json = json.dumps(quant_json)

        is_quarantined = flow_dict.get("is_quarantined")
        quarantine_reason = flow_dict.get("quarantine_reason")
        quarantine_batch_id = flow_dict.get("quarantine_batch_id")
        final_outcome = flow_dict.get("final_outcome")

        with conn:
            conn.execute("""
                INSERT INTO notable_flow (
                    flow_id, source, ticker, asset_type, strike, call_put, expiration, dte,
                    premium_usd, premium_raw, raw_message_id, channel_id, chart_url,
                    local_chart_path, drive_archive_url, is_archived, vol_to_oi_ratio,
                    is_sweep, flow_score, llm_review_status, llm_reasoning, trade_timestamp,
                    strategy_name, quant_metrics_json, strategy_trace_id,
                    is_quarantined, quarantine_reason, quarantine_batch_id, final_outcome,
                    entry_contract_price, current_contract_price,
                    mfe_max_gain_pct, mae_max_drawdown_pct, is_carried_over,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, ?, ?)
                ON CONFLICT(flow_id) DO UPDATE SET
                    source = excluded.source,
                    ticker = excluded.ticker,
                    asset_type = excluded.asset_type,
                    strike = excluded.strike,
                    call_put = excluded.call_put,
                    expiration = excluded.expiration,
                    dte = excluded.dte,
                    premium_usd = excluded.premium_usd,
                    premium_raw = excluded.premium_raw,
                    raw_message_id = excluded.raw_message_id,
                    channel_id = excluded.channel_id,
                    chart_url = COALESCE(excluded.chart_url, notable_flow.chart_url),
                    local_chart_path = COALESCE(excluded.local_chart_path, notable_flow.local_chart_path),
                    drive_archive_url = COALESCE(excluded.drive_archive_url, notable_flow.drive_archive_url),
                    is_archived = excluded.is_archived,
                    vol_to_oi_ratio = excluded.vol_to_oi_ratio,
                    is_sweep = excluded.is_sweep,
                    flow_score = excluded.flow_score,
                    llm_review_status = excluded.llm_review_status,
                    llm_reasoning = excluded.llm_reasoning,
                    trade_timestamp = excluded.trade_timestamp,
                    strategy_name = excluded.strategy_name,
                    quant_metrics_json = COALESCE(excluded.quant_metrics_json, notable_flow.quant_metrics_json),
                    strategy_trace_id = COALESCE(excluded.strategy_trace_id, notable_flow.strategy_trace_id),
                    is_quarantined = CASE WHEN COALESCE(notable_flow.is_quarantined,0) != 0 THEN notable_flow.is_quarantined ELSE COALESCE(excluded.is_quarantined, notable_flow.is_quarantined) END,
                    quarantine_reason = CASE WHEN COALESCE(notable_flow.is_quarantined,0) != 0 THEN notable_flow.quarantine_reason ELSE COALESCE(excluded.quarantine_reason, notable_flow.quarantine_reason) END,
                    quarantine_batch_id = CASE WHEN COALESCE(notable_flow.is_quarantined,0) != 0 THEN notable_flow.quarantine_batch_id ELSE COALESCE(excluded.quarantine_batch_id, notable_flow.quarantine_batch_id) END,
                    final_outcome = CASE 
                        WHEN excluded.final_outcome IS NOT NULL AND excluded.final_outcome != 'MONITORING' THEN excluded.final_outcome
                        WHEN notable_flow.final_outcome IS NOT NULL AND notable_flow.final_outcome != 'MONITORING' THEN notable_flow.final_outcome
                        ELSE COALESCE(excluded.final_outcome, notable_flow.final_outcome, 'MONITORING')
                    END,
                    entry_contract_price = COALESCE(excluded.entry_contract_price, notable_flow.entry_contract_price),
                    current_contract_price = COALESCE(excluded.current_contract_price, notable_flow.current_contract_price),
                    updated_at = excluded.updated_at
            """, (
                flow_id,
                flow_dict.get("source", "discord_notable_flow"),
                flow_dict["ticker"].upper().strip(),
                flow_dict.get("asset_type", "equity"),
                float(flow_dict["strike"]),
                flow_dict["call_put"].upper().strip(),
                flow_dict["expiration"].strip(),
                flow_dict.get("dte"),
                float(flow_dict["premium_usd"]),
                flow_dict.get("premium_raw", f"${float(flow_dict['premium_usd']):,.0f}"),
                flow_dict.get("raw_message_id"),
                flow_dict.get("channel_id"),
                flow_dict.get("chart_url"),
                flow_dict.get("local_chart_path"),
                flow_dict.get("drive_archive_url"),
                flow_dict.get("is_archived", 0),
                flow_dict.get("vol_to_oi_ratio"),
                flow_dict.get("is_sweep", 0),
                flow_dict.get("flow_score"),
                flow_dict.get("llm_review_status", "APPROVED"),
                flow_dict.get("llm_reasoning"),
                flow_dict.get("trade_timestamp", now),
                flow_dict.get("strategy_name", "INSTITUTIONAL_WHALE_SWEEP"),
                quant_json,
                flow_dict.get("strategy_trace_id"),
                is_quarantined,
                quarantine_reason,
                quarantine_batch_id,
                final_outcome or "MONITORING",
                float(flow_dict["entry_contract_price"]) if flow_dict.get("entry_contract_price") is not None else None,
                float(flow_dict["current_contract_price"]) if flow_dict.get("current_contract_price") is not None else None,
                now,
                now
            ))
        cur = conn.execute("SELECT * FROM notable_flow WHERE flow_id = ?", (flow_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def get_notable_flow_by_id(self, flow_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single notable flow row by flow_id."""
        conn = self._get_connection()
        cur = conn.execute("SELECT * FROM notable_flow WHERE flow_id = ?", (flow_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def get_notable_flow(
        self,
        limit: Any = 100,
        ticker: Optional[str] = None,
        asset_type: Optional[str] = None,
        call_put: Optional[str] = None,
        min_premium: Optional[float] = None,
        consolidate_duplicates: bool = True,
        include_quarantined: bool = False
    ) -> Any:
        if isinstance(limit, str):
            return self.get_notable_flow_by_id(limit)
        conn = self._get_connection()
        where_clauses = ["1=1"]
        params: List[Any] = []
        if not include_quarantined:
            where_clauses.append("(is_quarantined = 0 OR is_quarantined IS NULL)")
            where_clauses.append("NOT EXISTS (SELECT 1 FROM flow_candidate_analytics a WHERE a.flow_id = notable_flow.flow_id AND COALESCE(a.is_quarantined,0) != 0)")
        if ticker:
            where_clauses.append("ticker = ?")
            params.append(ticker.upper().strip())
        if asset_type:
            where_clauses.append("LOWER(asset_type) = ?")
            params.append(asset_type.lower().strip())
        if call_put:
            where_clauses.append("UPPER(call_put) LIKE ?")
            params.append(f"%{call_put.upper().strip()}%")
        if min_premium is not None and min_premium > 0:
            where_clauses.append("premium_usd >= ?")
            params.append(min_premium)
            
        where_str = " AND ".join(where_clauses)
        
        if consolidate_duplicates:
            # Consolidate duplicate prints for the exact same contract using the latest timestamp
            query = f"""
                SELECT * FROM (
                    SELECT *, ROW_NUMBER() OVER (
                        PARTITION BY ticker, strike, call_put, expiration 
                        ORDER BY trade_timestamp DESC, created_at DESC
                    ) as rn
                    FROM notable_flow
                    WHERE {where_str}
                ) WHERE rn = 1
                ORDER BY trade_timestamp DESC LIMIT ?
            """
        else:
            query = f"SELECT * FROM notable_flow WHERE {where_str} ORDER BY trade_timestamp DESC LIMIT ?"
            
        params.append(limit)
        cur = conn.execute(query, params)
        return [dict(r) for r in cur.fetchall()]

    def get_unarchived_flow_charts(self, days_old: int = 14) -> List[Dict[str, Any]]:
        """Find local charts older than days_old that need to be swept to Google Drive."""
        conn = self._get_connection()
        cur = conn.execute("""
            SELECT * FROM notable_flow
            WHERE is_archived = 0
              AND local_chart_path IS NOT NULL
              AND local_chart_path != ''
              AND date(created_at) <= date('now', '-' || ? || ' days')
        """, (days_old,))
        return [dict(r) for r in cur.fetchall()]

    def update_flow_archive_url(self, flow_id: str, drive_url: str) -> None:
        conn = self._get_connection()
        now = datetime.now().isoformat()
        with conn:
            conn.execute("""
                UPDATE notable_flow
                SET drive_archive_url = ?, is_archived = 1, local_chart_path = NULL, updated_at = ?
                WHERE flow_id = ?
            """, (drive_url, now, flow_id))


