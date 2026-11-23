"""OFFLINE simulator for the recovered copy-trader; no real broker adapters.

Only long-equity ENTRY is qualified. Options, exits and autonomous placeholder
strategies remain blocked. Limits are supplied by the caller, not strategy defaults.
SQLite is both fake broker and journal: this does NOT prove remote order reconciliation.
"""
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
import tempfile


def positive(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value) and value > 0


def timestamp(value):
    try:
        t = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if t.tzinfo is None:
            raise ValueError()
        return t
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError('INVALID_TIMESTAMP') from exc


@dataclass(frozen=True)
class SimulationLimits:
    max_order_notional: float
    max_gross_notional: float
    max_positions: int
    max_evidence_age_seconds: float

    def __post_init__(self):
        if not all(positive(v) for v in (self.max_order_notional, self.max_gross_notional, self.max_positions, self.max_evidence_age_seconds)) or type(self.max_positions) is not int:
            raise ValueError('INVALID_LIMITS')


class SQLiteFakeBroker:
    def __init__(self, path, *, initial_cash, limits):
        path = Path(path).resolve()
        if not path.is_relative_to(Path(tempfile.gettempdir()).resolve()):
            raise PermissionError('TEMPORARY_SIMULATION_STORE_REQUIRED')
        if not positive(initial_cash) or not isinstance(limits, SimulationLimits):
            raise ValueError('INVALID_CONFIGURATION')
        self.limits = limits
        self.in_intent = False
        self.fail_before_commit = False
        self.con = sqlite3.connect(path, isolation_level=None, timeout=2)
        self.con.row_factory = sqlite3.Row
        self.con.execute('PRAGMA synchronous=FULL')
        self.con.executescript('''
            CREATE TABLE IF NOT EXISTS simulation_meta(singleton INTEGER PRIMARY KEY CHECK(singleton=1), version INTEGER NOT NULL, initial_cash REAL NOT NULL, cash REAL NOT NULL, killed INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS simulation_holdings(holding_id TEXT PRIMARY KEY, ticker TEXT NOT NULL, quantity REAL NOT NULL, entry_price REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS simulation_intents(intent_id TEXT PRIMARY KEY, payload_hash TEXT NOT NULL, result TEXT NOT NULL);
        ''')
        self.con.execute('INSERT OR IGNORE INTO simulation_meta VALUES(1,1,?,?,0)', (initial_cash, initial_cash))
        if self.con.execute('SELECT version FROM simulation_meta').fetchone()[0] != 1:
            self.close()
            raise ValueError('UNSUPPORTED_SIMULATION_SCHEMA')
        self.reconcile()

    def close(self):
        self.con.close()

    def cash(self):
        return self.con.execute('SELECT cash FROM simulation_meta').fetchone()[0]

    def set_kill_switch(self, enabled):
        if type(enabled) is not bool:
            raise ValueError('INVALID_KILL_SWITCH')
        self.con.execute('UPDATE simulation_meta SET killed=?', (int(enabled),))

    def reconcile(self):
        try:
            return self._reconcile()
        except (ValueError, TypeError, KeyError, IndexError, OverflowError):
            raise PermissionError('RECONCILIATION_REQUIRED') from None

    def _reconcile(self):
        initial, cash = self.con.execute('SELECT initial_cash,cash FROM simulation_meta').fetchone()
        holdings = list(self.con.execute('SELECT * FROM simulation_holdings'))
        journals = list(self.con.execute('SELECT * FROM simulation_intents'))
        results = [json.loads(r['result']) for r in journals]
        by_id = {h['holding_id']: h for h in holdings}
        for journal, result in zip(journals, results):
            holding = by_id.get(result['holding_id'])
            if (holding is None or result['intent_id'] != journal['intent_id']
                    or not re.fullmatch('[0-9a-f]{64}', journal['payload_hash'])
                    or result['mode'] != 'paper_simulation' or result['broker_connected'] is not False
                    or result['execution_authorized'] is not False or result['action'] != 'BUY_ENTRY'
                    or result['asset_type'] != 'equity' or result['direction'] != 'long'
                    or holding['ticker'] != result['ticker']
                    or not re.fullmatch('[A-Z]{1,6}', result['ticker'])
                    or holding['quantity'] != result['quantity'] or holding['entry_price'] != result['price']
                    or not all(positive(result[k]) for k in ('quantity','price','total_cost'))
                    or not math.isclose(result['quantity']*result['price'], result['total_cost'], rel_tol=0, abs_tol=1e-7)):
                raise PermissionError('RECONCILIATION_REQUIRED')
        ids = {r['holding_id'] for r in results}
        cost = sum(r['total_cost'] for r in results)
        if (not positive(initial) or type(cash) not in (int,float) or not math.isfinite(cash) or cash < 0
                or ids != {h['holding_id'] for h in holdings} or len(results) != len(holdings)
                or not math.isclose(initial-cost, cash, abs_tol=1e-7)
                or any(not positive(h['quantity']) or not positive(h['entry_price']) for h in holdings)
                or not math.isclose(sum(h['quantity']*h['entry_price'] for h in holdings), cost, abs_tol=1e-7)):
            raise PermissionError('RECONCILIATION_REQUIRED')
        return {'status':'RECONCILED_LOCAL_SIMULATION','intents':len(results),'holdings':len(holdings),'broker_connected':False}

    def submit(self, mode, intent_id, signal, analyst, *, now):
        if mode != 'paper_simulation':
            raise PermissionError('SIMULATION_ONLY')
        if not isinstance(intent_id,str) or not intent_id.strip() or len(intent_id)>200:
            raise ValueError('INVALID_INTENT_ID')
        if not isinstance(signal,dict) or not positive(signal.get('price')):
            raise ValueError('INVALID_PRICE')
        if signal.get('action') != 'ENTRY' or signal.get('asset_type') != 'equity' or signal.get('direction') != 'long':
            raise PermissionError('UNQUALIFIED_ASSET_OR_ACTION')
        if not isinstance(signal.get('ticker'),str) or not re.fullmatch('[A-Z]{1,6}',signal['ticker']):
            raise ValueError('INVALID_TICKER')
        if signal.get('evidence_status') != 'observed':
            raise PermissionError('EVIDENCE_NOT_OBSERVED')
        payload = json.dumps({'signal':signal,'analyst':analyst},sort_keys=True,allow_nan=False)
        digest = hashlib.sha256(payload.encode()).hexdigest()
        self.con.execute('BEGIN IMMEDIATE')
        try:
            self.reconcile()
            if self.con.execute('SELECT killed FROM simulation_meta').fetchone()[0]:
                raise PermissionError('KILL_SWITCH')
            old = self.con.execute('SELECT payload_hash,result FROM simulation_intents WHERE intent_id=?',(intent_id,)).fetchone()
            if old:
                if old[0] != digest:
                    raise ValueError('INTENT_CONFLICT')
                self.con.execute('COMMIT')
                return json.loads(old[1])
            age = (timestamp(now)-timestamp(signal.get('observed_at'))).total_seconds()
            if age < 0 or age > self.limits.max_evidence_age_seconds:
                raise PermissionError('STALE_OR_FUTURE_EVIDENCE')
            # Run the recovered strategy, then veto its exact proposed ledger changes
            # within this same transaction. No strategy sizing is recreated here.
            from plugins.analyst_trader.portfolio_engine import DualPortfolioEngine
            self.in_intent = True
            result = DualPortfolioEngine(self)._simulate_copy_trade(signal,analyst)
            if result is None:
                raise PermissionError('INSUFFICIENT_CASH')
            gross, count = self.con.execute('SELECT COALESCE(SUM(quantity*entry_price),0),COUNT(*) FROM simulation_holdings').fetchone()
            if (result['total_cost'] > self.limits.max_order_notional or gross > self.limits.max_gross_notional
                    or count > self.limits.max_positions or self.cash() < 0):
                raise PermissionError('RISK_LIMIT')
            result.update(mode='paper_simulation',broker_connected=False,execution_authorized=False,intent_id=intent_id)
            self.con.execute('INSERT INTO simulation_intents VALUES(?,?,?)',(intent_id,digest,json.dumps(result,sort_keys=True,allow_nan=False)))
            if self.fail_before_commit:
                raise RuntimeError('INJECTED_CRASH')
            self.reconcile()
            self.con.execute('COMMIT')
            return result
        except BaseException:
            self.con.execute('ROLLBACK')
            raise
        finally:
            self.in_intent = False

    # Minimal concrete database port used by the genuine recovered ENTRY path.
    def get_portfolio(self, portfolio_id):
        if portfolio_id != 'copy_trader':
            raise PermissionError('UNQUALIFIED_STRATEGY')
        return {'cash_balance':self.cash()}

    def add_portfolio_holding(self, *, holding_id, portfolio_id, ticker, asset_type, direction, quantity, entry_price, strike, expiration):
        if not self.in_intent:
            raise PermissionError('SIMULATOR_TRANSACTION_REQUIRED')
        self.con.execute('INSERT INTO simulation_holdings VALUES(?,?,?,?)',(holding_id,ticker,quantity,entry_price))
        return {'holding_id':holding_id}

    def update_portfolio_balance(self, portfolio_id, *, cash_delta, realized_pnl_delta):
        if not self.in_intent:
            raise PermissionError('SIMULATOR_TRANSACTION_REQUIRED')
        self.con.execute('UPDATE simulation_meta SET cash=cash+?',(cash_delta,))
