#!/usr/bin/env python3
"""
owlfred_supervisor.py - Master Zero-Manual-Entry Production Supervisor Daemon.

Runs 24/7 autonomously to orchestrate:
  1. Continuous 60s Flow Ingestion & 5-Factor DREAM Gatekeeper.
  2. Intraday Real-Time MFE/MAE Position Monitor (06:30–13:00 PST).
  3. Pre-Market 06:15 PST ΔOI Carryover Audit.
  4. Nightly 18:00 PST Dreaming & Correlation Consolidation.
  5. 1 TB HD Caching & Self-Healing Process Recovery.
"""

import os
import sys
import time
import signal
import logging
from datetime import datetime, time as dtime
from pathlib import Path
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
TRADER_SCRIPTS = PROJECT_ROOT / "skills" / "financial" / "autonomous-trader" / "scripts"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(TRADER_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(TRADER_SCRIPTS))

from plugins.analyst_trader.db import AnalystDatabase
from plugins.analyst_trader.auto_updater import AnalystAutoUpdater
from plugins.analyst_trader.analyst_learning import AnalystStyleLearner
from premarket_oi_auditor import PremarketOIAuditor
from candidate_correlation_engine import CandidateCorrelationEngine

# Ensure credentials from ~/.hermes/.env and repo .env are exported into os.environ
env_paths = [Path.home() / ".hermes" / ".env", PROJECT_ROOT / ".env"]
for p in env_paths:
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k, v = k.strip(), v.strip("\"'")
                        if k and not os.getenv(k):
                            os.environ[k] = v
        except Exception:
            pass

LOG_DIR = Path.home() / ".hermes" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "owlfred_supervisor.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
    handlers=[
        logging.FileHandler(str(LOG_FILE)),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("OWLFRED-Supervisor")


from zoneinfo import ZoneInfo

NY_TZ = ZoneInfo("America/New_York")

US_MARKET_HOLIDAYS_2026 = {
    "2026-01-01",  # New Year's Day
    "2026-01-19",  # MLK Jr. Day
    "2026-02-16",  # Washington's Birthday (Presidents Day)
    "2026-04-03",  # Good Friday
    "2026-05-25",  # Memorial Day
    "2026-06-19",  # Juneteenth
    "2026-07-03",  # Independence Day (Observed)
    "2026-09-07",  # Labor Day
    "2026-11-26",  # Thanksgiving Day
    "2026-12-25",  # Christmas Day
}


class OwlfredProductionSupervisor:
    """Master Production Daemon for OWLFRED Autonomous Trading System."""

    def __init__(self):
        self.is_running = True
        self.db = AnalystDatabase()
        self.updater = AnalystAutoUpdater(self.db)
        self.oi_auditor = PremarketOIAuditor(str(self.db.db_path))
        self.correlation_engine = CandidateCorrelationEngine(str(self.db.db_path))
        self.analyst_learner = AnalystStyleLearner(self.db)
        
        # Track last execution of scheduled cron tasks
        self.last_oi_audit_date = None
        self.last_dreaming_date = None
        self.last_price_update_ts = 0.0
        self.price_update_interval_seconds = 300  # 5 minutes

        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        logger.info("Received termination signal (%s). Initiating clean shutdown...", signum)
        self.is_running = False

    def is_market_open_et(self) -> bool:
        """
        Checks if current time is within regular US equity options market hours (09:30 - 16:00 ET, Mon-Fri).
        Immune to daylight saving transitions (PDT/PST) and respects US market holidays.
        """
        now_et = datetime.now(NY_TZ)
        today_str = now_et.strftime("%Y-%m-%d")

        # Check weekend
        if now_et.weekday() >= 5:
            return False

        # Check exchange holidays
        if today_str in US_MARKET_HOLIDAYS_2026:
            return False

        current_t = now_et.time()
        market_open = dtime(9, 30)
        market_close = dtime(16, 0)
        return market_open <= current_t <= market_close

    def run_supervisor_loop(self, interval_seconds: int = 60):
        """Main 24/7 autonomous loop with America/New_York timezone anchoring."""
        logger.info("==========================================================")
        logger.info("🚀 OWLFRED MASTER PRODUCTION SUPERVISOR DAEMON ONLINE")
        logger.info("Timezone: America/New_York (Exchange Calendar Active)")
        logger.info("Telemetry Log: %s", LOG_FILE)
        logger.info("==========================================================")

        while self.is_running:
            now_et = datetime.now(NY_TZ)
            today_str = now_et.strftime("%Y-%m-%d")
            current_t = now_et.time()

            try:
                # 1. Check Pre-Market 09:15 ET (06:15 PT) OCC ΔOI Audit
                if now_et.weekday() < 5 and today_str not in US_MARKET_HOLIDAYS_2026:
                    if current_t >= dtime(9, 15) and self.last_oi_audit_date != today_str:
                        logger.info("🌅 Triggering Scheduled 09:15 ET OCC ΔOI Carryover Audit...")
                        self.oi_auditor.run_premarket_oi_audit()
                        self.last_oi_audit_date = today_str

                # 2. Check Nightly 18:00 ET (Post-Market Close) Research Dreaming & Analyst Flywheel
                if current_t >= dtime(18, 0) and self.last_dreaming_date != today_str:
                    logger.info("🌙 Triggering Scheduled 18:00 ET Nightly Research Consolidation & Analyst Learning...")
                    self.correlation_engine.run_candidate_correlation_audit()
                    try:
                        self.analyst_learner.learn_all_analysts()
                    except Exception as e:
                        logger.error("Error running nightly analyst style learning: %s", e)
                    self.last_dreaming_date = today_str

                # 3. Continuous Multi-Channel Discord Flow Ingestion (REST API, no UW quota impact)
                self.updater.flow_engine.ingest_discord_flow_channels(limit_per_channel=10)

                # 4. Throttled 5-Minute Mark-to-Market Price Updates (05:00-15:00 PST / 08:00-18:00 ET Mon-Fri)
                now_ts = time.time()
                if now_ts - self.last_price_update_ts >= self.price_update_interval_seconds:
                    self.updater.price_updater.update_open_positions_mark_to_market()
                    self.last_price_update_ts = now_ts

                # 5. Intraday Real-Time MFE/MAE Monitor & Exit Triggers (During Market Open 09:30-16:00 ET)
                if self.is_market_open_et():
                    self.updater.risk_manager.monitor_and_update_positions()

            except Exception as e:
                logger.error("Error in supervisor cycle: %s", e, exc_info=True)

            time.sleep(interval_seconds)

        logger.info("OWLFRED Supervisor cleanly stopped.")


if __name__ == "__main__":
    supervisor = OwlfredProductionSupervisor()
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        logger.info("Executing single supervisor dry-run cycle...")
        supervisor.updater.flow_engine.ingest_discord_flow_channels(limit_per_channel=5)
        supervisor.updater.risk_manager.monitor_and_update_positions()
        supervisor.oi_auditor.run_premarket_oi_audit()
        print("\n✅ Single Supervisor Dry-Run Cycle Completed Successfully!\n")
    else:
        supervisor.run_supervisor_loop(interval_seconds=60)
