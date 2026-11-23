#!/usr/bin/env python3
"""
strategy_logger.py - Quantitative Strategy Execution & Audit Trail Logger.

Persists all quantitative strategy events, heatmap captures, flow evaluation traces,
and execution triggers into the SQLite `recorded_strategies` table in `analyst_trading.db`.
Provides a unified feedback loop for the nightly backtester and learning flywheel.
"""

import json
import time
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger("strategy_logger")


def get_db():
    """Lazy loader for AnalystDatabase to avoid circular imports."""
    try:
        from plugins.analyst_trader.db import AnalystDatabase
        return AnalystDatabase()
    except Exception as e:
        logger.warning("Could not initialize AnalystDatabase in strategy_logger: %s", e)
        return None


def log_event(event_type: str, payload: Dict[str, Any], source: str = "", db_path: Optional[str] = None) -> Optional[str]:
    """
    Log a quantitative strategy event, heatmap analysis, or trade trigger.
    
    Args:
        event_type: Category (e.g., 'skylit_heatmap_analysis', 'flow_candidate_evaluation', 'actionable_alert_published')
        payload: Event metadata dictionary
        source: Originating script or engine name
        db_path: Optional explicit SQLite database path
        
    Returns:
        trace_id: Unique trace identifier string or None on failure
    """
    if not isinstance(payload, dict):
        return None

    ticker = str(payload.get("ticker", "UNKNOWN")).upper().strip()
    strategy_name = str(payload.get("strategy_name") or payload.get("strategy") or "INSTITUTIONAL_WHALE_SWEEP")
    action = str(payload.get("action", "EVALUATE"))
    status = str(payload.get("status", "SUCCESS"))
    directional_bias = payload.get("directional_bias")
    target_node = payload.get("target_node")
    touch_prob_3d = payload.get("touch_prob_3d")
    screenshot_path = payload.get("screenshot_path") or payload.get("local_chart_path")
    source_script = source or payload.get("source_script", "strategy_logger")

    holding_id = payload.get("holding_id")
    flow_id = payload.get("flow_id")
    parent_trace_id = payload.get("parent_trace_id")
    entry_price = payload.get("entry_price")
    exit_price = payload.get("exit_price")
    quantity = payload.get("quantity")
    if quantity is None:
        quantity = payload.get("trimmed_quantity")
    if quantity is None:
        quantity = payload.get("closed_quantity")
    realized_pnl = payload.get("realized_pnl")
    outcome_label = payload.get("outcome_label")

    # Extract or serialize quantitative metrics
    quant_metrics = payload.get("quant_metrics") or payload.get("quant_result") or payload.get("quant_snapshot")
    quant_metrics_json = json.dumps(quant_metrics) if isinstance(quant_metrics, (dict, list)) else (
        quant_metrics if isinstance(quant_metrics, str) else None
    )

    now_iso = datetime.now(timezone.utc).isoformat()
    trace_id = payload.get("trace_id") or f"trace_{ticker}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"

    if db_path:
        from plugins.analyst_trader.db import AnalystDatabase
        db = AnalystDatabase(db_path)
    else:
        db = get_db()
    if db:
        try:
            trace_id = db.save_recorded_strategy({
                "trace_id": trace_id,
                "event_type": event_type,
                "strategy_name": strategy_name,
                "ticker": ticker,
                "action": action,
                "status": status,
                "directional_bias": directional_bias,
                "target_node": float(target_node) if target_node is not None else None,
                "touch_prob_3d": float(touch_prob_3d) if touch_prob_3d is not None else None,
                "quant_metrics_json": quant_metrics_json,
                "screenshot_path": str(screenshot_path) if screenshot_path else None,
                "source_script": source_script,
                "holding_id": holding_id,
                "flow_id": flow_id,
                "parent_trace_id": parent_trace_id,
                "entry_price": float(entry_price) if entry_price is not None else None,
                "exit_price": float(exit_price) if exit_price is not None else None,
                "quantity": float(quantity) if quantity is not None else None,
                "realized_pnl": float(realized_pnl) if realized_pnl is not None else None,
                "outcome_label": outcome_label,
                "payload_json": payload,
                "timestamp": now_iso,
                "created_at": now_iso
            })
            logger.info("📝 Logged Strategy Event [%s] for $%s (Trace: %s)", strategy_name, ticker, trace_id)
            return trace_id
        except Exception as err:
            logger.error("Failed to persist recorded strategy event for $%s: %s", ticker, err)
            return None

    return None


def list_recorded_strategies(
    limit: int = 50,
    ticker: Optional[str] = None,
    strategy_name: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Query recent strategy executions from the audit database."""
    db = get_db()
    if not db:
        return []
    try:
        return db.list_recorded_strategies(limit=limit, ticker=ticker, strategy_name=strategy_name)
    except Exception as err:
        logger.error("Failed to query recorded strategies: %s", err)
        return []


if __name__ == "__main__":
    t_id = log_event("test_event", {"ticker": "SPY", "strategy_name": "A+_DREAM_SETUP", "action": "TEST"})
    print("Logged test strategy event trace:", t_id)
