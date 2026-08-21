"""Analyst Style Learning Engine & Discord Category Auto-Discovery."""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from plugins.analyst_trader.db import AnalystDatabase
from plugins.analyst_trader.parser import DiscordBackfillEngine

logger = logging.getLogger(__name__)


class CategoryAutoDiscoverer:
    """Discovers channels inside the Discord 'alerts' category and auto-registers new analysts."""

    def __init__(self, db: Optional[AnalystDatabase] = None) -> None:
        self.db = db or AnalystDatabase()
        self.engine = DiscordBackfillEngine(self.db)

    def sync_from_channel_directory(self) -> List[Dict[str, Any]]:
        """Sync analyst channels directly from ~/.hermes/channel_directory.json."""
        dir_path = Path.home() / ".hermes" / "channel_directory.json"
        if not dir_path.exists():
            return []

        try:
            with open(dir_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            discord_channels = data.get("platforms", {}).get("discord", [])
            newly_registered = []

            for ch in discord_channels:
                ch_id = ch.get("id", "")
                ch_name = ch.get("name", "")
                if not ch_id or ":" in ch_id:
                    continue
                if "🌟" in ch_name or "alert" in ch_name.lower() or "analyst" in ch_name.lower():
                    existing = self.db.get_analyst_by_channel(ch_id)
                    if not existing:
                        clean_name = ch_name.replace("🌟｜", "").replace("🛎️｜", "").replace("-", " ").title().strip()
                        analyst = self.db.register_analyst(ch_id, ch_name, clean_name)
                        newly_registered.append(analyst)
                        logger.info("Auto-synced analyst channel: #%s (ID: %s)", ch_name, ch_id)

            return newly_registered
        except Exception as e:
            logger.warning("Failed to sync analyst channels from channel_directory.json: %s", e)
            return []

    def discover_and_register_channels(self, channels_payload: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process list of channel dicts (from Discord API) and register analyst channels under 'alerts' category."""
        # Find category ID for 'alerts'
        category_ids = set()
        for ch in channels_payload:
            if ch.get("type") == 4 and "alert" in ch.get("name", "").lower():
                category_ids.add(ch.get("id"))

        newly_registered = []
        for ch in channels_payload:
            ch_id = ch.get("id")
            ch_name = ch.get("name", "")
            parent_id = ch.get("parent_id")

            # Check if channel is in 'alerts' category or named alert-like
            if (parent_id and parent_id in category_ids) or "🌟" in ch_name or "alert" in ch_name.lower() or "analyst" in ch_name.lower():
                existing = self.db.get_analyst_by_channel(ch_id)
                if not existing:
                    clean_name = ch_name.replace("🌟｜", "").replace("🛎️｜", "").replace("-", " ").title().strip()
                    analyst = self.db.register_analyst(ch_id, ch_name, clean_name)
                    newly_registered.append(analyst)
                    logger.info("Auto-discovered new analyst channel: #%s (ID: %s)", ch_name, ch_id)

        return newly_registered


class AnalystStyleLearner:
    """Analyzes historical trades to learn each analyst's trading style and philosophy."""

    def __init__(self, db: Optional[AnalystDatabase] = None) -> None:
        self.db = db or AnalystDatabase()

    def analyze_analyst(self, analyst_name: str) -> Dict[str, Any]:
        """Compute performance metrics and synthesize trading philosophy for an analyst."""
        positions = self.db.list_positions(analyst_name=analyst_name, limit=1000)
        closed_pos = [p for p in positions if p["status"] == "CLOSED"]

        if not closed_pos:
            return {
                "analyst_name": analyst_name,
                "total_trades": len(positions),
                "closed_trades": 0,
                "win_rate": 0.0,
                "strategy_summary": "Insufficient trade data to establish trading philosophy.",
                "rules": {}
            }

        total_trades = len(closed_pos)
        wins = [p for p in closed_pos if float(p["realized_pnl"]) > 0]
        losses = [p for p in closed_pos if float(p["realized_pnl"]) <= 0]
        win_rate = (len(wins) / total_trades) * 100.0 if total_trades > 0 else 0.0

        # Ticker preferences
        ticker_counts: Dict[str, int] = {}
        for p in closed_pos:
            t = p["ticker"]
            ticker_counts[t] = ticker_counts.get(t, 0) + 1
        preferred_tickers = [t for t, _ in sorted(ticker_counts.items(), key=lambda x: x[1], reverse=True)[:5]]

        # Holding duration calculation
        durations_hours = []
        for p in closed_pos:
            if p.get("entry_time") and p.get("exit_time"):
                try:
                    t_in = datetime.fromisoformat(p["entry_time"])
                    t_out = datetime.fromisoformat(p["exit_time"])
                    dur = (t_out - t_in).total_seconds() / 3600.0
                    if dur >= 0:
                        durations_hours.append(dur)
                except Exception:
                    pass

        avg_holding_hours = (sum(durations_hours) / len(durations_hours)) if durations_hours else 24.0

        # Average ROI
        rois = [float(p["roi_pct"]) for p in closed_pos if p.get("roi_pct") is not None]
        avg_roi_pct = (sum(rois) / len(rois)) if rois else 0.0

        # Formulate rules & philosophy
        rules = {
            "win_rate_pct": round(win_rate, 1),
            "avg_holding_hours": round(avg_holding_hours, 1),
            "top_tickers": preferred_tickers,
            "avg_roi_pct": round(avg_roi_pct, 1),
            "trade_frequency": "high" if total_trades > 20 else "moderate",
            "take_profit_discipline": "Takes partial profit at +25% ROI" if any(p["status"] == "TRIMMED" for p in positions) else "Holds full position until exit"
        }

        strategy_summary = (
            f"Analyst {analyst_name.title()} achieves a {win_rate:.1f}% win rate across {total_trades} closed trades. "
            f"Primarily trades {', '.join(preferred_tickers[:3]) or 'major tickers'} with an average hold time of {avg_holding_hours:.1f} hours. "
            f"Average trade ROI is {avg_roi_pct:+.1f}%."
        )

        # Save to database
        self.db.save_analyst_style(
            analyst_name=analyst_name,
            preferred_tickers=preferred_tickers,
            avg_holding_hours=avg_holding_hours,
            win_rate=win_rate,
            avg_roi_pct=avg_roi_pct,
            preferred_dte_min=0,
            preferred_dte_max=45,
            strategy_summary=strategy_summary,
            rules=rules
        )

        return {
            "analyst_name": analyst_name,
            "total_trades": total_trades,
            "win_rate": round(win_rate, 1),
            "avg_roi_pct": round(avg_roi_pct, 1),
            "preferred_tickers": preferred_tickers,
            "strategy_summary": strategy_summary,
            "rules": rules
        }
