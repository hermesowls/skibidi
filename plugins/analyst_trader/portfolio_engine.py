"""Dual Portfolio Engine: Copy-Trader & Autonomous AI Philosophy Trader."""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from plugins.analyst_trader.db import AnalystDatabase

logger = logging.getLogger(__name__)


class DualPortfolioEngine:
    """Manages Portfolio A (Copy-Trader) and Portfolio B (Autonomous AI Trader)."""

    def __init__(self, db: Optional[AnalystDatabase] = None) -> None:
        self.db = db or AnalystDatabase()

    # -----------------------------------------------------------------------
    # Portfolio A: Analyst Copy Trader
    # -----------------------------------------------------------------------

    def execute_copy_trade(self, alert_signal: Dict[str, Any], analyst_name: str) -> Optional[Dict[str, Any]]:
        """Mirror an analyst trade alert directly in Portfolio A (copy_trader)."""
        portfolio = self.db.get_portfolio("copy_trader")
        if not portfolio:
            return None

        action = alert_signal.get("action")
        ticker = alert_signal.get("ticker", "").upper()
        asset_type = alert_signal.get("asset_type", "equity")
        direction = alert_signal.get("direction", "call" if asset_type == "option" else "long")
        price = float(alert_signal.get("price", 1.0))
        strike = alert_signal.get("strike")
        expiration = alert_signal.get("expiration")

        cash = float(portfolio["cash_balance"])

        if action == "ENTRY":
            # Risk Management: Sizing = 5% of portfolio cash balance
            allocation = cash * 0.05
            qty = max(1.0, round(allocation / (price * (100.0 if asset_type == "option" else 1.0)), 2))
            total_cost = price * qty * (100.0 if asset_type == "option" else 1.0)

            if total_cost > cash:
                logger.warning("[CopyTrader] Insufficient cash for %s (%f required, %f available)", ticker, total_cost, cash)
                return None

            holding_id = f"hold_copy_{uuid.uuid4().hex[:8]}"
            holding = self.db.add_portfolio_holding(
                holding_id=holding_id,
                portfolio_id="copy_trader",
                ticker=ticker,
                asset_type=asset_type,
                direction=direction,
                quantity=qty,
                entry_price=price,
                strike=strike,
                expiration=expiration
            )
            self.db.update_portfolio_balance("copy_trader", cash_delta=-total_cost, realized_pnl_delta=0.0)

            report = {
                "portfolio": "Analyst Copy Trader",
                "action": "BUY_ENTRY",
                "analyst": analyst_name,
                "ticker": ticker,
                "asset_type": asset_type,
                "direction": direction,
                "strike": strike,
                "expiration": expiration,
                "quantity": qty,
                "price": price,
                "total_cost": total_cost,
                "holding_id": holding_id,
                "timestamp": datetime.now().isoformat()
            }
            logger.info("[CopyTrader] Executed copy entry for %s: %s", analyst_name, report)
            return report

        elif action in ("TRIM", "EXIT", "STOP_LOSS"):
            holdings = self.db.list_portfolio_holdings("copy_trader", status="OPEN")
            matching = [h for h in holdings if h["ticker"] == ticker]

            if not matching:
                return None

            h = matching[0]
            holding_id = h["holding_id"]
            qty = float(h["quantity"])
            entry_p = float(h["average_entry_price"])

            close_qty = qty * 0.5 if action == "TRIM" else qty
            revenue = price * close_qty * (100.0 if asset_type == "option" else 1.0)

            if direction in ("call", "long"):
                pnl = (price - entry_p) * close_qty * (100.0 if asset_type == "option" else 1.0)
            else:
                pnl = (entry_p - price) * close_qty * (100.0 if asset_type == "option" else 1.0)

            conn = self.db._get_connection()
            now = datetime.now().isoformat()
            with conn:
                if action == "TRIM":
                    conn.execute("""
                        UPDATE portfolio_holdings SET quantity = quantity - ?, realized_pnl = realized_pnl + ?
                        WHERE holding_id = ?
                    """, (close_qty, pnl, holding_id))
                else:
                    conn.execute("""
                        UPDATE portfolio_holdings SET status = 'CLOSED', closed_at = ?, realized_pnl = realized_pnl + ?
                        WHERE holding_id = ?
                    """, (now, pnl, holding_id))

            self.db.update_portfolio_balance("copy_trader", cash_delta=revenue, realized_pnl_delta=pnl)

            report = {
                "portfolio": "Analyst Copy Trader",
                "action": f"SELL_{action}",
                "analyst": analyst_name,
                "ticker": ticker,
                "price": price,
                "closed_quantity": close_qty,
                "realized_pnl": round(pnl, 2),
                "revenue": round(revenue, 2),
                "timestamp": now
            }
            logger.info("[CopyTrader] Executed copy exit for %s: %s", analyst_name, report)
            return report

        return None

    # -----------------------------------------------------------------------
    # Portfolio B: Autonomous AI Philosophy Trader
    # -----------------------------------------------------------------------

    def evaluate_autonomous_trade_setup(self, ticker: str, market_signal: str = "BULLISH") -> Optional[Dict[str, Any]]:
        """Generate autonomous trade based on synthesized analyst philosophy + market signal."""
        portfolio = self.db.get_portfolio("autonomous_ai")
        if not portfolio:
            return None

        # Gather learned styles across analysts
        conn = self.db._get_connection()
        cur = conn.execute("SELECT * FROM analyst_styles ORDER BY win_rate DESC")
        styles = cur.fetchall()

        if not styles:
            logger.info("[AutonomousAI] No learned analyst styles found yet. Run backfill first.")
            return None

        best_analyst = dict(styles[0])
        pref_tickers = json.loads(best_analyst.get("preferred_tickers", "[]")) if isinstance(best_analyst.get("preferred_tickers"), str) else []

        ticker_upper = ticker.upper()

        # Autonomous AI Trading Decision Rules
        asset_type = "option"
        direction = "call" if market_signal == "BULLISH" else "put"
        price = 2.50  # Simulated option price
        cash = float(portfolio["cash_balance"])

        # Size: 4% of cash balance
        allocation = cash * 0.04
        qty = max(1.0, round(allocation / (price * 100.0), 2))
        total_cost = price * qty * 100.0

        if total_cost > cash:
            return None

        holding_id = f"hold_auto_{uuid.uuid4().hex[:8]}"
        self.db.add_portfolio_holding(
            holding_id=holding_id,
            portfolio_id="autonomous_ai",
            ticker=ticker_upper,
            asset_type=asset_type,
            direction=direction,
            quantity=qty,
            entry_price=price,
            strike=100.0,
            expiration="30DTE"
        )
        self.db.update_portfolio_balance("autonomous_ai", cash_delta=-total_cost, realized_pnl_delta=0.0)

        report = {
            "portfolio": "Autonomous AI Trader",
            "action": "AUTONOMOUS_ENTRY",
            "inspiration_analyst": best_analyst["analyst_name"],
            "analyst_win_rate": best_analyst["win_rate"],
            "ticker": ticker_upper,
            "asset_type": asset_type,
            "direction": direction,
            "quantity": qty,
            "entry_price": price,
            "total_cost": total_cost,
            "holding_id": holding_id,
            "reasoning": f"Synthesized momentum setup inspired by Top Analyst {best_analyst['analyst_name']}'s trading rules.",
            "timestamp": datetime.now().isoformat()
        }
        logger.info("[AutonomousAI] Executed autonomous trade: %s", report)
        return report

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Return combined status of Portfolio A and Portfolio B."""
        copy_p = self.db.get_portfolio("copy_trader") or {}
        auto_p = self.db.get_portfolio("autonomous_ai") or {}

        copy_holdings = self.db.list_portfolio_holdings("copy_trader", status="OPEN")
        auto_holdings = self.db.list_portfolio_holdings("autonomous_ai", status="OPEN")

        return {
            "copy_trader": {
                "name": copy_p.get("name", "Copy Trader"),
                "cash_balance": round(float(copy_p.get("cash_balance", 0)), 2),
                "realized_pnl": round(float(copy_p.get("realized_pnl", 0)), 2),
                "open_positions_count": len(copy_holdings),
                "open_positions": copy_holdings
            },
            "autonomous_ai": {
                "name": auto_p.get("name", "Autonomous AI Trader"),
                "cash_balance": round(float(auto_p.get("cash_balance", 0)), 2),
                "realized_pnl": round(float(auto_p.get("realized_pnl", 0)), 2),
                "open_positions_count": len(auto_holdings),
                "open_positions": auto_holdings
            }
        }
