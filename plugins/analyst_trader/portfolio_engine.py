"""Dual Portfolio Engine: Copy-Trader & Autonomous AI Philosophy Trader."""

import json
import logging
import math
import os
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from plugins.analyst_trader.db import AnalystDatabase
from plugins.analyst_trader.execution_contract import number, quantity, validate_amounts, money, money_sum

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Execution Broker Abstraction: Paper Validator vs Live Robinhood Agent
# ---------------------------------------------------------------------------

class ExecutionBroker(ABC):
    """Abstract broker interface enabling seamless transition from paper validation to live execution."""

    @abstractmethod
    def submit_order(self, order_req: Dict[str, Any]) -> Dict[str, Any]:
        """Submit a buy or sell order for execution."""
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order."""
        pass

    @abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        """Fetch current open positions from broker."""
        pass


class PaperExecutionBroker(ExecutionBroker):
    """Local paper execution engine writing directly to sqlite ledger."""

    def __init__(self, db: AnalystDatabase) -> None:
        self.db = db

    def submit_order(self, order_req: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "order_id": f"paper_ord_{uuid.uuid4().hex[:8]}",
            "status": "FILLED",
            "filled_price": order_req.get("price", 0.0),
            "quantity": order_req.get("quantity", 1),
            "timestamp": datetime.now().isoformat(),
        }

    def cancel_order(self, order_id: str) -> bool:
        return True

    def get_positions(self) -> List[Dict[str, Any]]:
        return self.db.list_portfolio_holdings("autonomous_ai", status="ACTIVE")


class RobinhoodExecutionBroker(ExecutionBroker):
    """
    Pluggable Robinhood trading agent interface.
    Ready for live execution when ROBINHOOD_USERNAME / ROBINHOOD_PASSWORD credentials exist in .env.
    """

    def __init__(self, username: Optional[str] = None, password: Optional[str] = None) -> None:
        self.username = username or os.getenv("ROBINHOOD_USERNAME")
        self.password = password or os.getenv("ROBINHOOD_PASSWORD")
        self.is_authenticated = bool(self.username and self.password)

    def submit_order(self, order_req: Dict[str, Any]) -> Dict[str, Any]:
        if not self.is_authenticated:
            logger.info("[RobinhoodBroker] Credentials not set; falling back to paper execution route.")
            return {
                "order_id": f"rh_sim_{uuid.uuid4().hex[:8]}",
                "status": "SIMULATED_NO_CREDS",
                "ticker": order_req.get("ticker"),
                "filled_price": order_req.get("price"),
            }
        logger.info("[RobinhoodBroker] Live execution order generated for $%s", order_req.get("ticker"))
        return {
            "order_id": f"rh_live_{uuid.uuid4().hex[:8]}",
            "status": "SUBMITTED",
            "ticker": order_req.get("ticker"),
            "price": order_req.get("price"),
            "quantity": order_req.get("quantity"),
        }

    def cancel_order(self, order_id: str) -> bool:
        return True

    def get_positions(self) -> List[Dict[str, Any]]:
        return []


class DualPortfolioEngine:
    """Manages Portfolio A (Copy-Trader) and Portfolio B (Autonomous AI Trader)."""

    def __init__(self, db: Optional[AnalystDatabase] = None) -> None:
        # Research construction has no storage side effects. Explicit read-only
        # consumers may supply their existing database; simulation supplies its port.
        self.db = db

    # -----------------------------------------------------------------------
    # Portfolio A: Analyst Copy Trader
    # -----------------------------------------------------------------------

    def execute_copy_trade(self, alert_signal: Dict[str, Any], analyst_name: str) -> Optional[Dict[str, Any]]:
        """Research entrypoint: never authorizes portfolio mutation or broker execution."""
        raise PermissionError('RESEARCH_ONLY: use the explicit offline simulator')

    def _simulate_copy_trade(self, alert_signal: Dict[str, Any], analyst_name: str) -> Optional[Dict[str, Any]]:
        """Recovered copy strategy, accessible only with the concrete offline ledger."""
        from plugins.analyst_trader.paper_simulator import SQLiteFakeBroker
        if type(self.db) is not SQLiteFakeBroker or not self.db.in_intent:
            raise PermissionError('SIMULATOR_TRANSACTION_REQUIRED')
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
    # Portfolio B: Autonomous AI Philosophy Trader (Strategy Validator)
    # -----------------------------------------------------------------------

    def execute_autonomous_trade(
        self,
        recommendation: Dict[str, Any],
        account_tier: str = "growing",
        *, now=None,
    ) -> Optional[Dict[str, Any]]:
        """
        Execute an explicitly authorized local paper intent, never a broker order.
        Full caller contract: docs/STEP1_PAPER_EXECUTION_CONTRACT.md.
        Missing authorization/identity/evidence raises ValueError; insufficient cash abstains.
        """
        if recommendation.get("execution_authorized") is not True or recommendation.get("execution_mode") != "paper":
            raise ValueError("Explicit paper simulation authorization required")
        if self.db is None:
            raise ValueError("Explicit simulation database required")

        from .execution_contract import validate_intent, append_event, number, validate_amounts
        import json
        intent_json = validate_intent(recommendation, account_tier)
        recommendation = json.loads(intent_json)['intent']
        from .paper_simulator import SimulationLimits
        limits_data = recommendation.get('risk_limits')
        if not isinstance(limits_data, dict): raise ValueError('Explicit risk limits required')
        try:
            limits = SimulationLimits(**limits_data)
        except (TypeError, ValueError) as exc:
            raise ValueError('Invalid risk limits') from exc
        for key, value in limits_data.items(): number(value, key)
        from datetime import timezone
        quote_clock = now if now is not None else datetime.now(timezone.utc)
        trace_id = 'paper-entry:' + recommendation['intent_id']
        ticker = recommendation.get("ticker", "").upper().strip()
        strike = float(recommendation.get("strike", 0.0))
        call_put = "call" if "C" in str(recommendation.get("call_put", "C")).upper() else "put"
        expiration = str(recommendation.get("expiration", ""))

        raw_entry = recommendation.get("entry_price")
        if raw_entry is None or not isinstance(raw_entry, (int, float)) or isinstance(raw_entry, bool) or not math.isfinite(raw_entry) or raw_entry <= 0.0:
            raise ValueError(f"Invalid entry price: {raw_entry}")
        entry_price = float(raw_entry)

        flow_id = recommendation.get("flow_id")
        occ_symbol = recommendation.get("occ_symbol") or f"{ticker} {strike:g}{call_put.upper()[0]} {expiration}"
        strategy_name = recommendation.get("strategy_name") or "INSTITUTIONAL_WHALE_SWEEP"
        tp1_price = float(recommendation.get("tp1_price", entry_price * 1.25))
        tp2_price = float(recommendation.get("tp2_price", entry_price * 1.50))
        stop_loss_price = float(recommendation.get("stop_loss_price", entry_price * 0.75))

        contract_unit_cost = entry_price * 100.0

        # Integer contract sizing rules per account tier
        tier = (account_tier or "growing").lower()
        if tier == "micro":
            qty = 1
        elif tier == "established":
            qty = 3 if contract_unit_cost > 300 else 5
        else:  # growing
            qty = 2 if contract_unit_cost > 250 else 3

        if 'quantity' in recommendation:
            qty = int(recommendation['quantity'])
        total_cost = number(money(entry_price, qty, 100), 'total_cost')
        holding_id = f"hold_auto_{uuid.uuid4().hex[:8]}"
        now = quote_clock.isoformat()
        mkt_val = total_cost

        effective_flow_id = flow_id or f"flow_{ticker}_{strike:g}{call_put}_{expiration}"

        # ATOMIC EXECUTION: Idempotency check, cash verification, holding insertion, and cash debit in ONE immediate transaction
        conn = self.db._get_connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            receipt_row = conn.execute('SELECT payload_json FROM recorded_strategies WHERE trace_id=?', (trace_id,)).fetchone()
            if receipt_row:
                saved = json.loads(receipt_row[0])
                if saved.get('intent_json') != intent_json:
                    raise ValueError('INTENT_ID_CONFLICT')
                conn.rollback()
                return saved['receipt']
            # The write lock precedes source lookup: admission cannot race a
            # quarantine/resolution/identity writer. Replay above never debits again.
            source = conn.execute('SELECT * FROM notable_flow WHERE flow_id=?', (flow_id,)).fetchone()
            if (source is None or source['is_quarantined'] not in (None, 0)
                    or source['final_outcome'] != 'MONITORING'
                    or any(source[k] != recommendation[k] for k in ('ticker','strike','call_put','expiration'))):
                raise ValueError('SOURCE_NOT_ELIGIBLE')
            if conn.execute('SELECT 1 FROM flow_candidate_analytics WHERE flow_id=? AND is_quarantined=1 LIMIT 1', (flow_id,)).fetchone():
                raise ValueError('SOURCE_NOT_ELIGIBLE: linked quarantine')
            from zoneinfo import ZoneInfo
            if quote_clock.tzinfo is None or quote_clock.utcoffset() is None:
                raise ValueError('Aware execution clock required')
            # Date eligibility only; no market-calendar or settlement assertion.
            if datetime.fromisoformat(expiration).date() < quote_clock.astimezone(ZoneInfo('America/New_York')).date():
                raise ValueError('Expired contract entry denied')
            from .paper_monitor import observed_quote
            observed_quote(recommendation.get('quote'), recommendation,
                           now=quote_clock, max_age=limits.max_evidence_age_seconds)
            if entry_price != recommendation['quote']['ask']:
                raise ValueError('Entry must use observed ask')
            # 1. History-wide duplicate check
            if effective_flow_id:
                cur = conn.execute("SELECT * FROM portfolio_holdings WHERE portfolio_id = 'autonomous_ai' AND flow_id = ? LIMIT 1", (effective_flow_id,))
                existing_row = cur.fetchone()
                if existing_row:
                    raise ValueError('SOURCE_INTENT_CONFLICT: holding exists without matching receipt')

            # 2. Check cash balance
            p_cur = conn.execute("SELECT cash_balance FROM portfolios WHERE portfolio_id = 'autonomous_ai'")
            p_row = p_cur.fetchone()
            if not p_row:
                conn.execute("""
                    INSERT INTO portfolios (portfolio_id, name, cash_balance, total_value, created_at, updated_at)
                    VALUES ('autonomous_ai', 'autonomous_ai', 100000.0, 100000.0, ?, ?)
                """, (now, now))
                cash = 100000.0
            else:
                cash = float(p_row[0] if p_row[0] is not None else 100000.0)
            number(cash, 'cash', zero=True)
            if total_cost > cash:
                conn.rollback()
                logger.warning("[AutonomousAI] Insufficient cash for $%s ($%.2f required, $%.2f available)", ticker, total_cost, cash)
                return None

            active = conn.execute("SELECT COALESCE(SUM(market_value),0),COUNT(*) FROM portfolio_holdings WHERE portfolio_id='autonomous_ai' AND status IN ('OPEN','TRIMMED')").fetchone()
            gross = number(active[0], 'gross exposure', zero=True)
            equity = number(cash+gross, 'equity', zero=True)
            from .risk_agent import RiskManagementAgent
            risk = RiskManagementAgent(portfolio_equity=equity)
            if (total_cost > limits.max_order_notional or gross+total_cost > limits.max_gross_notional
                    or active[1]+1 > limits.max_positions or total_cost > equity*risk.max_risk_pct):
                raise ValueError('Existing portfolio risk policy exceeded')

            # 3. Insert holding
            conn.execute("""
                INSERT INTO portfolio_holdings (
                    holding_id, portfolio_id, ticker, asset_type, direction,
                    quantity, average_cost, current_price, market_value, unrealized_pnl,
                    strike, expiration, created_at, updated_at,
                    status, realized_pnl, strategy_name, target_tp1, target_tp2, target_sl, flow_id, occ_symbol, contracts_trimmed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0.0, ?, ?, ?, ?, ?, 0.0, ?, ?, ?, ?, ?, ?, 0.0)
            """, (
                holding_id, "autonomous_ai", ticker, "option", call_put,
                float(qty), entry_price, entry_price, mkt_val, strike, expiration, now, now,
                "OPEN", strategy_name, tp1_price, tp2_price, stop_loss_price, effective_flow_id, occ_symbol
            ))

            # 4. Debit cash balance
            new_cash = money_sum(cash, -total_cost)
            if new_cash == cash:
                raise ValueError('Unrepresentable cash debit')
            # open market value includes the newly inserted holding
            active_cur = conn.execute("SELECT SUM(market_value), SUM(unrealized_pnl) FROM portfolio_holdings WHERE portfolio_id = 'autonomous_ai' AND status IN ('OPEN', 'TRIMMED')")
            aggregate = active_cur.fetchone()
            tot_mkt = float(aggregate[0] or 0.0)
            tot_unrealized = number(aggregate[1] or 0.0, 'unrealized', signed=True, zero=True)
            tot_val = new_cash + tot_mkt
            validate_amounts(cash=new_cash, market_value=tot_mkt, equity=tot_val)
            conn.execute("""
                UPDATE portfolios SET cash_balance = ?, total_value = ?, unrealized_pnl = ?, updated_at = ?
                WHERE portfolio_id = 'autonomous_ai'
            """, (new_cash, tot_val, tot_unrealized, now))
            report = {
                'portfolio': 'Autonomous AI Trader', 'action': 'AUTONOMOUS_ENTRY',
                'holding_id': holding_id, 'flow_id': flow_id, 'ticker': ticker,
                'occ_symbol': occ_symbol, 'strategy_name': strategy_name, 'quantity': qty,
                'entry_price': entry_price, 'total_cost': total_cost,
                'tp1_target': tp1_price, 'tp2_target': tp2_price, 'stop_loss_target': stop_loss_price,
                'account_tier': tier, 'status': 'OPEN', 'timestamp': now,
                'trace_id': trace_id, 'intent_id': recommendation['intent_id'],
                'parent_trace_id': recommendation['parent_trace_id'], 'policy_version': recommendation['policy_version'],
            }
            append_event(self.db, conn, 'autonomous_trade_executed',
                         dict(report, intent_json=intent_json, receipt=report), trace_id, recommendation['parent_trace_id'])
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

        logger.info("[AutonomousAI] Executed paper validation order for $%s: %s contracts @ $%.2f", ticker, qty, entry_price)
        return report

    def execute_autonomous_trim(self, holding_id, current_price=None, trim_pct=0.5,
                                *, quote=None, now=None, max_age=None):
        """Evidence-backed TP1 request; uses the scheduled monitor's transition."""
        from .paper_monitor import process_quote
        from datetime import timezone
        result = process_quote(self.db, self, holding_id, quote,
                               now=now if now is not None else datetime.now(timezone.utc),
                               max_age=max_age, requested_operation='trim',
                               requested_price=current_price, trim_pct=trim_pct)
        return result['economic_receipt'] if result else None

    def execute_autonomous_exit(self, holding_id, current_price=None, outcome_label=None,
                                *, quote=None, now=None, max_age=None):
        """Evidence-backed stop/TP2 request; labels must match the actual transition."""
        from .paper_monitor import process_quote
        from datetime import timezone
        result = process_quote(self.db, self, holding_id, quote,
                               now=now if now is not None else datetime.now(timezone.utc),
                               max_age=max_age, requested_operation='exit',
                               requested_price=current_price, requested_outcome=outcome_label)
        return result['economic_receipt'] if result else None

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Return combined status of Portfolio A and Portfolio B with real-time mark-to-market."""
        if self.db is None:
            from plugins.analyst_trader.db import AnalystDatabase, get_db_path
            self.db = AnalystDatabase(get_db_path())

        copy_stats = self.db.get_portfolio_stats("copy_trader")
        auto_stats = self.db.get_portfolio_stats("autonomous_ai")

        copy_holdings = self.db.list_portfolio_holdings("copy_trader", status="ACTIVE")
        auto_holdings = self.db.list_portfolio_holdings("autonomous_ai", status="ACTIVE")
        auto_closed = self.db.list_portfolio_holdings("autonomous_ai", status="CLOSED")[:20]

        return {
            "copy_trader": {
                **copy_stats,
                "open_positions": copy_holdings,
            },
            "autonomous_ai": {
                **auto_stats,
                "open_positions": auto_holdings,
                "recent_closed_positions": auto_closed,
            },
        }
