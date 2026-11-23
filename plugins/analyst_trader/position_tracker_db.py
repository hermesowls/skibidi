import os
import json
import sqlite3
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

def get_db_path() -> str:
    db_dir = Path.home() / ".hermes" / "trading_logs"
    db_dir.mkdir(parents=True, exist_ok=True)
    return str(db_dir / "simulated_positions.sqlite")

class PositionTrackerDB:
    """SQLite Position DB Tracker for Simulated Options & Stock Positions."""
    
    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path or get_db_path()
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS simulated_positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    asset_type TEXT NOT NULL,
                    rr_profile TEXT NOT NULL,
                    conviction_score REAL NOT NULL,
                    contract_name TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    current_price REAL NOT NULL,
                    target_tp REAL NOT NULL,
                    stop_loss REAL NOT NULL,
                    contracts_count INTEGER NOT NULL,
                    entry_ask REAL NOT NULL,
                    option_strike REAL,
                    option_dte INTEGER,
                    unrealized_pnl REAL DEFAULT 0.0,
                    unrealized_pnl_pct REAL DEFAULT 0.0,
                    status TEXT DEFAULT 'OPEN',
                    derivation_lineage_json TEXT
                )
            """)
            conn.commit()

    def add_simulated_position(self, pos: Dict[str, Any]) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO simulated_positions (
                    timestamp, ticker, asset_type, rr_profile, conviction_score,
                    contract_name, entry_price, current_price, target_tp, stop_loss,
                    contracts_count, entry_ask, option_strike, option_dte,
                    unrealized_pnl, unrealized_pnl_pct, status, derivation_lineage_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pos.get("timestamp", datetime.now(timezone.utc).isoformat()),
                pos.get("ticker", "").upper(),
                pos.get("asset_type", "OPTION_SINGLE"),
                pos.get("rr_profile", "HIGH_RR"),
                float(pos.get("conviction_score", 90.0)),
                pos.get("contract_name", f"{pos.get('ticker', '').upper()} Option"),
                float(pos.get("entry_price", pos.get("current_price", 0.0))),
                float(pos.get("current_price", pos.get("entry_price", 0.0))),
                float(pos.get("target_tp", 0.0)),
                float(pos.get("stop_loss", 0.0)),
                int(pos.get("contracts_count", 1)),
                float(pos.get("entry_ask", 0.0)),
                float(pos.get("option_strike", 0.0)),
                int(pos.get("option_dte", 30)),
                0.0,
                0.0,
                "OPEN",
                json.dumps(pos.get("derivation_lineage", {}))
            ))
            pos_id = cursor.lastrowid
            conn.commit()
            return {**pos, "id": pos_id, "status": "OPEN"}

    def get_simulated_positions(
        self,
        status_filter: Optional[str] = None,
        rr_filter: Optional[str] = None,
        asset_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        query = "SELECT * FROM simulated_positions WHERE 1=1"
        params = []
        
        if status_filter and status_filter != "ALL":
            query += " AND status = ?"
            params.append(status_filter)
        if rr_filter and rr_filter != "ALL":
            query += " AND rr_profile = ?"
            params.append(rr_filter)
        if asset_filter and asset_filter != "ALL":
            query += " AND asset_type = ?"
            params.append(asset_filter)
            
        query += " ORDER BY id DESC"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            results = []
            for r in rows:
                item = dict(r)
                if item.get("derivation_lineage_json"):
                    try:
                        item["derivation_lineage"] = json.loads(item["derivation_lineage_json"])
                    except Exception:
                        item["derivation_lineage"] = {}
                
                # Compute option_mark_price for display
                if item.get("asset_type") != "EQUITY":
                    entry_ask = float(item.get("entry_ask", 0.25))
                    curr_p = float(item.get("current_price", 12.0))
                    entry_p = float(item.get("entry_price", curr_p))
                    strike = float(item.get("option_strike", curr_p))
                    
                    # Moneyness Delta Model
                    delta_stock = curr_p - entry_p
                    moneyness = curr_p / max(0.01, strike)
                    if moneyness >= 1.05:
                        delta = 0.75
                    elif moneyness >= 0.98:
                        delta = 0.45
                    elif moneyness >= 0.90:
                        delta = 0.25
                    else:
                        delta = 0.12
                    
                    opt_mark = max(0.01, entry_ask + (delta_stock * delta))
                    item["option_mark_price"] = round(opt_mark, 2)
                    
                    # Recalculate realistic P&L
                    contracts = int(item.get("contracts_count", 10))
                    pnl = (opt_mark - entry_ask) * contracts * 100
                    pnl_pct = ((opt_mark - entry_ask) / entry_ask) * 100 if entry_ask > 0 else 0
                    item["unrealized_pnl"] = round(pnl, 2)
                    item["unrealized_pnl_pct"] = round(pnl_pct, 1)
                else:
                    item["option_mark_price"] = item.get("current_price")
                
                results.append(item)
            return results

    def update_mark_to_market(self, live_prices: Dict[str, float]) -> List[Dict[str, Any]]:
        """Update open positions with live stock prices and recalculate P&L and TP/SL status."""
        positions = self.get_simulated_positions(status_filter="OPEN")
        updated = []
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for pos in positions:
                ticker = pos["ticker"]
                if ticker not in live_prices:
                    continue
                
                curr_price = live_prices[ticker]
                entry_price = pos["entry_price"]
                entry_ask = pos["entry_ask"]
                contracts = pos["contracts_count"]
                asset_type = pos["asset_type"]
                tp = pos["target_tp"]
                sl = pos["stop_loss"]
                
                # Check status
                new_status = "OPEN"
                if curr_price >= tp:
                    new_status = "TP_HIT"
                elif curr_price <= sl:
                    new_status = "SL_HIT"
                
                # Mark-to-market P&L calculation
                if asset_type == "EQUITY":
                    pnl = (curr_price - entry_price) * contracts
                    pnl_pct = ((curr_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0
                else: # Options
                    strike = pos.get("option_strike", curr_price)
                    delta_stock = curr_price - entry_price
                    moneyness = curr_price / max(0.01, strike)
                    if moneyness >= 1.05:
                        delta = 0.75
                    elif moneyness >= 0.98:
                        delta = 0.45
                    elif moneyness >= 0.90:
                        delta = 0.25
                    else:
                        delta = 0.12
                    est_current_contract = max(0.01, entry_ask + (delta_stock * delta))
                    pnl = (est_current_contract - entry_ask) * contracts * 100
                    pnl_pct = ((est_current_contract - entry_ask) / entry_ask) * 100 if entry_ask > 0 else 0
                
                cursor.execute("""
                    UPDATE simulated_positions
                    SET current_price = ?, unrealized_pnl = ?, unrealized_pnl_pct = ?, status = ?
                    WHERE id = ?
                """, (curr_price, round(pnl, 2), round(pnl_pct, 2), new_status, pos["id"]))
                
                updated.append({**pos, "current_price": curr_price, "unrealized_pnl": round(pnl, 2), "status": new_status})
            
            conn.commit()
        return updated

    def close_simulated_position(self, position_id: int) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE simulated_positions SET status = 'CLOSED' WHERE id = ?", (position_id,))
            conn.commit()
            return cursor.rowcount > 0

    def delete_simulated_position(self, position_id: int) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM simulated_positions WHERE id = ?", (position_id,))
            conn.commit()
            return cursor.rowcount > 0

    def clear_simulated_positions(self) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM simulated_positions")
            conn.commit()
            return True

if __name__ == "__main__":
    db = PositionTrackerDB()
    test_pos = {
        "timestamp": "2026-08-15 00:00 PST",
        "ticker": "METC",
        "asset_type": "OPTION_SINGLE",
        "rr_profile": "HIGH_RR",
        "conviction_score": 96.0,
        "contract_name": "METC $12.00 CALL (9 DTE)",
        "entry_price": 11.19,
        "current_price": 11.19,
        "target_tp": 11.90,
        "stop_loss": 10.51,
        "contracts_count": 20,
        "entry_ask": 0.25,
        "option_strike": 12.0,
        "option_dte": 9,
        "derivation_lineage": {
            "flow": "UW Call Buy ($0.25 Ask)",
            "gex": "Negative Gamma Squeeze",
            "ofi": "Order Flow Imbalance +0.58",
            "ta": "TTM Squeeze Fired + 8/21 Cross",
            "risk": "ATR SL $10.51 / TP $11.90"
        }
    }
    created = db.add_simulated_position(test_pos)
    print("Created Position:", created)
    
    positions = db.get_simulated_positions()
    print(f"Retrieved {len(positions)} positions from DB.")
