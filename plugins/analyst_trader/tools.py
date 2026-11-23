"""Hermes Tool & Action Dispatcher for Analyst Trading System."""

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from plugins.analyst_trader.db import AnalystDatabase
from plugins.analyst_trader.parser import DiscordBackfillEngine, TradeSignalParser
from plugins.analyst_trader.analyst_learning import AnalystStyleLearner, CategoryAutoDiscoverer
from plugins.analyst_trader.portfolio_engine import DualPortfolioEngine

logger = logging.getLogger(__name__)

# Initialize singletons
db = AnalystDatabase()
backfill_engine = DiscordBackfillEngine(db)
style_learner = AnalystStyleLearner(db)
auto_discoverer = CategoryAutoDiscoverer(db)
portfolio_engine = DualPortfolioEngine(db)


def analyst_trading_tool(action: str, **kwargs: Any) -> str:
    """Execute analyst trading actions for Hermes agent."""
    action = action.lower().strip()

    if action == "status":
        summary = portfolio_engine.get_portfolio_summary()
        analysts = db.list_analysts()
        positions = db.list_positions(status="OPEN")
        return json.dumps({
            "status": "success",
            "portfolios": summary,
            "analyst_count": len(analysts),
            "analysts": analysts,
            "open_positions_count": len(positions),
            "open_positions": positions
        }, indent=2)

    elif action == "performance":
        analyst_name = kwargs.get("analyst_name")
        analysts = db.list_analysts()
        results = []
        if analyst_name:
            res = style_learner.analyze_analyst(analyst_name)
            results.append(res)
        else:
            for a in analysts:
                res = style_learner.analyze_analyst(a["display_name"])
                results.append(res)

        return json.dumps({
            "status": "success",
            "performance_summaries": results
        }, indent=2)

    elif action == "process_alert":
        content = kwargs.get("content", "")
        embeds = kwargs.get("embeds")
        analyst_name = kwargs.get("analyst_name", "Unknown Analyst")
        channel_id = kwargs.get("channel_id", "0000")
        channel_name = kwargs.get("channel_name", "alerts")
        message_id = kwargs.get("message_id", f"msg_{datetime.now().timestamp()}")

        pos = backfill_engine.process_raw_alert(
            message_id=message_id,
            channel_id=channel_id,
            channel_name=channel_name,
            analyst_name=analyst_name,
            author_id="0000",
            content=content,
            embeds=embeds
        )

        copy_report = None
        if pos and pos.get("entry_price"):
            copy_report = portfolio_engine.execute_copy_trade(
                alert_signal={
                    "action": "ENTRY" if pos["status"] == "OPEN" else pos["status"],
                    "ticker": pos["ticker"],
                    "asset_type": pos["asset_type"],
                    "direction": pos["direction"],
                    "price": pos["entry_price"],
                    "strike": pos.get("strike"),
                    "expiration": pos.get("expiration")
                },
                analyst_name=analyst_name
            )

        return json.dumps({
            "status": "success",
            "position": pos,
            "copy_trade": copy_report
        }, indent=2)

    elif action == "auto_discover":
        channels = kwargs.get("channels", [])
        newly_registered = auto_discoverer.discover_and_register_channels(channels)
        return json.dumps({
            "status": "success",
            "newly_registered_count": len(newly_registered),
            "newly_registered": newly_registered
        }, indent=2)

    elif action == "autonomous_trade":
        ticker = kwargs.get("ticker", "SPY")
        market_signal = kwargs.get("signal", "BULLISH")
        trade_report = portfolio_engine.evaluate_autonomous_trade_setup(ticker, market_signal)
        return json.dumps({
            "status": "success",
            "trade_report": trade_report
        }, indent=2)

    else:
        return json.dumps({
            "status": "error",
            "error": f"Unknown action '{action}'. Valid actions: status, performance, process_alert, auto_discover, autonomous_trade"
        }, indent=2)


# Register Tool in Hermes Tool Registry
try:
    from tools.registry import registry

    schema = {
        "name": "analyst_trading",
        "description": "Manage analyst alert ingestion, query analyst win rates/styles, and inspect copy-trader & autonomous AI trading portfolios.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["status", "performance", "process_alert", "auto_discover", "autonomous_trade"],
                    "description": "Action to perform."
                },
                "analyst_name": {
                    "type": "string",
                    "description": "Analyst name filter for performance queries or alert processing."
                },
                "ticker": {
                    "type": "string",
                    "description": "Stock/Option ticker symbol for autonomous trade setup."
                },
                "content": {
                    "type": "string",
                    "description": "Alert content text for process_alert."
                }
            },
            "required": ["action"]
        }
    }

    registry.register("analyst_trading", "analyst_trader", schema, analyst_trading_tool)
    logger.info("Registered tool 'analyst_trading' with Hermes registry")
except Exception as e:
    logger.debug("Failed to register analyst_trading tool with registry: %s", e)
