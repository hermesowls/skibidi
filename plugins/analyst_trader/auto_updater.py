"""Automated Discord Analyst Backfill & Real-time Interval Polling Engine.

Fetches historical trade alerts from all accessible analyst channels into analyst_trading.db,
and continuously polls for new analyst alerts at regular intervals (60s).
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
import requests  # type: ignore

# Ensure project root & autonomous-trader scripts are in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TRADER_SCRIPTS = PROJECT_ROOT / "skills" / "financial" / "autonomous-trader" / "scripts"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(TRADER_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(TRADER_SCRIPTS))

from plugins.analyst_trader.db import AnalystDatabase
from plugins.analyst_trader.parser import DiscordBackfillEngine
from plugins.analyst_trader.portfolio_engine import DualPortfolioEngine
from plugins.analyst_trader.price_updater import UnusualWhalesPriceUpdater
from plugins.analyst_trader.scrapers import get_scraper_for_analyst
from plugins.analyst_trader.llm_reviewer import LLMTradeReviewer
from flow_ingestion_engine import FlowIngestionEngine
from autonomous_risk_manager import AutonomousRiskManager

logger = logging.getLogger(__name__)

ACCESSIBLE_ANALYST_CHANNELS = [
    {"id": "1268307222384083046", "name": "jon-and-kian", "analyst_name": "Jon & Kian"},
    {"id": "1268307222384083047", "name": "eva-alerts", "analyst_name": "Eva"},
    {"id": "1268307222384083048", "name": "ab-alerts", "analyst_name": "AB"},
    {"id": "1268307222384083049", "name": "muggzone-options", "analyst_name": "Muggzone Options"},
]


def get_dynamic_analyst_channels() -> list[dict]:
    """Dynamically discover all analyst channels from channel_directory.json."""
    ch_file = Path.home() / ".hermes" / "channel_directory.json"
    if not ch_file.exists():
        return ACCESSIBLE_ANALYST_CHANNELS

    try:
        with open(ch_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        discord_channels = data.get("platforms", {}).get("discord", [])
        discovered = []
        seen = set()

        for ch in discord_channels:
            name = ch.get("name", "")
            ch_id = str(ch.get("id") or "")
            if not ch_id or not ch_id.isdigit() or ch_id in seen or ch.get("type") == "thread":
                continue

            name_lower = name.lower()
            if any(kw in name_lower for kw in ["all-alerts", "alert-setup", "start-here"]):
                continue

            if any(kw in name_lower for kw in [
                "jon-and-kian", "eva", "ab", "giul-heatseeker", "muggzone", "shabs-sky",
                "tt", "neal", "florida-man", "common-stock", "bobby-spx", "vix-insights",
                "0dte-insights", "ximes-dubz", "np", "robindahood"
            ]):
                clean_name = name.replace("🌟｜", "").replace("🛎️｜", "").replace("📖｜", "").replace("⚙️｜", "").replace("-", " ").title().strip()
                if clean_name.upper() in ("AB", "TT", "NP"):
                    clean_name = clean_name.upper()
                elif "Jon" in clean_name and "Kian" in clean_name:
                    clean_name = "Jon & Kian"

                seen.add(ch_id)
                discovered.append({
                    "id": str(ch_id),
                    "name": name,
                    "analyst_name": clean_name
                })

        return discovered if discovered else ACCESSIBLE_ANALYST_CHANNELS
    except Exception as e:
        logger.warning("Failed to load dynamic analyst channels: %s", e)
        return ACCESSIBLE_ANALYST_CHANNELS


def get_discord_token() -> str:
    """Retrieve Discord Bot Token from ~/.hermes/.env or environment."""
    token = os.getenv("DISCORD_BOT_TOKEN")
    if token:
        return token

    env_path = Path.home() / ".hermes" / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("DISCORD_BOT_TOKEN="):
                    return line.strip().split("=", 1)[1].strip("\"'")
    return ""


class AnalystAutoUpdater:
    def __init__(self, db: AnalystDatabase | None = None) -> None:
        self.db = db or AnalystDatabase()
        self.engine = DiscordBackfillEngine(self.db)
        self.portfolio_engine = DualPortfolioEngine(self.db)
        self.price_updater = UnusualWhalesPriceUpdater(self.db)
        self.reviewer = LLMTradeReviewer()
        self.flow_engine = FlowIngestionEngine(self.db)
        self.risk_manager = AutonomousRiskManager(self.db.db_path)
        self.token = get_discord_token()
        self.last_price_update_ts = 0.0
        self.price_update_interval_seconds = 300  # 5 minutes

    def fetch_channel_messages(self, channel_id: str, limit: int = 100) -> list[dict]:
        """Fetch latest messages from a Discord channel via REST API."""
        if not self.token:
            logger.warning("No DISCORD_BOT_TOKEN available")
            return []

        headers = {"Authorization": f"Bot {self.token}"}
        url = f"https://discord.com/api/v10/channels/{channel_id}/messages?limit={limit}"
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                return resp.json()
            else:
                logger.debug("Fetch messages for channel %s failed HTTP %s", channel_id, resp.status_code)
                return []
        except Exception as e:
            logger.warning("HTTP request error for channel %s: %s", channel_id, e)
            return []

    def backfill_all_channels(self, limit_per_channel: int = 50) -> dict:
        """Perform initial historical backfill for all accessible analyst channels."""
        total_fetched = 0
        total_positions_created = 0

        channels = get_dynamic_analyst_channels()
        logger.info("Starting historical backfill across %d analyst channels...", len(channels))
        for ch in channels:
            ch_id = ch["id"]
            ch_name = ch["name"]
            analyst_name = ch["analyst_name"]

            messages = self.fetch_channel_messages(ch_id, limit=limit_per_channel)
            total_fetched += len(messages)

            # Messages arrive newest-first; process in chronological order (oldest-first)
            for msg in reversed(messages):
                msg_id = str(msg.get("id") or "")
                if not msg_id:
                    continue
                author_id = str(msg.get("author", {}).get("id") if isinstance(msg.get("author"), dict) else "0000")
                content = msg.get("content", "") or ""
                embeds = msg.get("embeds", []) or []
                timestamp = msg.get("timestamp")

                pos = self.engine.process_raw_alert(
                    message_id=msg_id,
                    channel_id=ch_id,
                    channel_name=ch_name,
                    analyst_name=analyst_name,
                    author_id=author_id,
                    content=content,
                    embeds=embeds,
                    timestamp=timestamp
                )
                if pos:
                    total_positions_created += 1

        # Run MTM price update after backfill
        try:
            self.price_updater.update_open_positions_mark_to_market()
        except Exception as e:
            logger.warning("MTM price update post-backfill failed: %s", e)

        return {
            "status": "success",
            "messages_processed": total_fetched,
            "positions_processed": total_positions_created
        }

    def reap_expired_positions(self) -> int:
        """
        Friday 16:15 ET (and continuous interval) Expired Position Reaper.
        Transitions active simulated contracts whose expiration <= today to CLOSED_EXPIRED_OUT with realized PnL = -100.0%.
        """
        from zoneinfo import ZoneInfo
        now_et = datetime.now(ZoneInfo("America/New_York"))
        today_str = now_et.strftime("%Y-%m-%d")
        
        reaped_count = 0
        try:
            with self.db.transaction() as conn:
                cur = conn.cursor()
                # Find open positions
                cur.execute("""
                    SELECT id, ticker, strike, call_put, expiration, entry_price, quantity 
                    FROM active_positions 
                    WHERE status IN ('OPEN', 'VIRTUAL_FILLED', 'PARTIALLY_TRIMMED', 'ELIGIBLE_FOR_FILL')
                """)
                rows = cur.fetchall()
                for row in rows:
                    pos_id = row[0]
                    exp_str = str(row[4] or "")
                    is_expired = False
                    try:
                        if "/" in exp_str:
                            parts = exp_str.split("/")
                            m, d = int(parts[0]), int(parts[1])
                            y = int(parts[2])
                            if y < 100: y += 2000
                            exp_date = datetime(y, m, d)
                        elif "-" in exp_str:
                            exp_date = datetime.strptime(exp_str, "%Y-%m-%d")
                        else:
                            exp_date = None
                        
                        if exp_date and exp_date.date() <= now_et.date():
                            is_expired = True
                    except Exception:
                        pass
                    
                    if is_expired:
                        cur.execute("""
                            UPDATE active_positions 
                            SET status = 'CLOSED_EXPIRED_OUT',
                                current_price = 0.00,
                                realized_pnl_pct = -100.0,
                                closed_at = ?
                            WHERE id = ?
                        """, (now_et.isoformat(), pos_id))
                        reaped_count += 1
                        logger.info("Reaped expired contract #%s ($%s %s) -> CLOSED_EXPIRED_OUT (-100%%)", pos_id, row[1], exp_str)
        except Exception as e:
            logger.error("Error running Expired Position Reaper: %s", e)
        return reaped_count

    def start_polling_loop(self, interval_seconds: int = 60) -> None:
        """Run continuous interval polling loop to sync new analyst trade alerts."""
        logger.info("Starting Analyst Auto-Updater interval loop (polling every %ds)...", interval_seconds)

        # Do initial backfill on startup
        self.backfill_all_channels(limit_per_channel=50)

        while True:
            try:
                # 1. Sweep expired positions (Terminal Expired Reaper)
                self.reap_expired_positions()

                # 2. Poll each accessible channel for new alerts
                channels = get_dynamic_analyst_channels()
                for ch in channels:
                    messages = self.fetch_channel_messages(ch["id"], limit=10)
                    for msg in reversed(messages):
                        msg_id = str(msg.get("id") or "")
                        if not msg_id:
                            continue
                        author_id = str(msg.get("author", {}).get("id") if isinstance(msg.get("author"), dict) else "0000")
                        self.engine.process_raw_alert(
                            message_id=msg_id,
                            channel_id=ch["id"],
                            channel_name=ch["name"],
                            analyst_name=ch["analyst_name"],
                            author_id=author_id,
                            content=msg.get("content", "") or "",
                            embeds=msg.get("embeds", []) or [],
                            timestamp=msg.get("timestamp")
                        )
                    # Hybrid LLM Reviewer audit pass
                    try:
                        self.reviewer.audit_channel_batch(
                            analyst_name=ch["analyst_name"],
                            db=self.db,
                            limit=10,
                            auto_reconcile=True
                        )
                    except Exception as rev_err:
                        logger.debug("LLM Reviewer audit for %s failed: %s", ch["analyst_name"], rev_err)

                # 3. Throttled 5-Minute Mark-to-Market contract prices (05:00-15:00 PST Mon-Fri)
                now_ts = time.time()
                if now_ts - self.last_price_update_ts >= self.price_update_interval_seconds:
                    self.price_updater.update_open_positions_mark_to_market()
                    self.last_price_update_ts = now_ts

                # 4. 60-Second Real-Time Autonomous Position MFE/MAE Monitor & Exit Triggers
                try:
                    self.risk_manager.monitor_and_update_positions()
                except Exception as risk_err:
                    logger.debug("Autonomous risk management cycle error: %s", risk_err)

                # 5. Poll and ingest Notable Flow channels (#notable-flow & #notable-etf-flow)
                try:
                    self.flow_engine.ingest_discord_flow_channels(limit_per_channel=10)
                except Exception as flow_err:
                    logger.debug("Flow ingestion cycle error: %s", flow_err)

            except Exception as e:
                logger.error("Error in analyst auto-updater polling loop: %s", e, exc_info=True)

            time.sleep(interval_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    updater = AnalystAutoUpdater()
    updater.start_polling_loop(interval_seconds=60)
